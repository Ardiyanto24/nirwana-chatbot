package supabaseexporter

import (
	"context"
	"errors"
	"sort"
	"sync"
	"time"

	"go.uber.org/zap"
)

// traceSpanWriter adalah interface tipis yang dipenuhi *Storage - dipisah
// supaya Buffer testable tanpa koneksi Postgres nyata (fakeWriter di
// buffer_test.go), mirror filosofi storage.go/mapping.go (murni,
// testable).
type traceSpanWriter interface {
	UpsertTrace(ctx context.Context, t TraceRow) error
	InsertSpan(ctx context.Context, sp SpanRow) error
}

// Buffer menahan span sampai SELURUH prasyarat FK-nya terpenuhi: baris
// `traces` untuk trace_id-nya sudah ada, DAN span induk langsungnya
// (kalau bukan span akar) sudah ter-INSERT lebih dulu.
//
// Dua KOREKSI berturut-turut atas desain awal, keduanya ditemukan
// verifikasi produksi M6.1 (trace f831b5b7df9e903f1eb5b5095bf9fcde, lalu
// eadc58b474e238446e8e6b95a9e663ec):
//
// Koreksi 1: desain PERTAMA hanya men-gate berdasar "trace dikenal atau
// belum", lalu meng-insert LANGSUNG begitu trace dikenal - SALAH karena
// Collector `batch` processor mem-flush pushTraces() dalam BANYAK batch
// terpisah sepanjang durasi satu turn (bukan sekali di akhir): span
// cucu (mis. authorization.check) bisa tiba SETELAH trace dikenal tapi
// SEBELUM induk langsungnya sendiri sempat diproses. Diperbaiki dengan
// melacak span mana yang SUDAH tertulis (`written`, keyed span_id - unik
// per trace dalam praktiknya, 8 byte acak OTel): span baru HANYA ditulis
// kalau trace dikenal DAN (span akar ATAU induk langsungnya sudah ada di
// `written`) - kalau belum, ditahan di `pending` terlepas dari status
// "dikenal" trace-nya, di-drain kaskade begitu prasyaratnya terpenuhi.
//
// Koreksi 2: "span akar" SEMPAT diasumsikan sama dengan "span pembawa
// session.id+turn.index" (satu-satunya kriteria isAnchor() di
// mapping.go) - asumsi ini SALAH. Riset ulang (trace
// eadc58b474e238446e8e6b95a9e663ec) menemukan input.validate (M1.2),
// span `chat` penyusun narasi (M4.4), dan riwayat.simpan (M7.18) SEMUA
// turut men-set session.id+turn.index pada span mereka SENDIRI (untuk
// kebutuhan observability masing-masing, independen dari peran anchor) -
// SEMUANYA span NON-ROOT (py ParentSpanID). Kode lama meng-insert span
// isAnchor()==true TANPA memeriksa induknya (diasumsikan selalu span
// akar) - melanggar FK persis saat salah satu span ini tiba SEBELUM
// induknya sendiri ter-INSERT. Perbaikan: isAnchor() TETAP dipakai
// murni untuk memicu UpsertTrace+known[traceID] (aman dipanggil
// berkali-kali oleh beberapa span berbeda - traceUpsertArgs pakai
// COALESCE, ON CONFLICT DO UPDATE), TAPI keputusan "boleh insert
// langsung atau harus ditahan" SELALU lewat insertableLocked() yang
// sesungguhnya (span akar SEJATI = ParentSpanID nil, BUKAN lagi
// disamakan dengan isAnchor()).
//
// Cakupan SENGAJA dibatasi M6.1 (forced by Lingkup "jalur data paling
// sederhana"): `known`/`written` murni in-memory, tidak query existence ke
// DB saat cold-start proses baru. Trace yang span akarnya TIDAK PERNAH
// tiba (mis. proses_turn() crash sebelum invoke_agent selesai) SEBELUM
// M6.2 tertahan selamanya di memori (docs/keterbatasan-diterima.md #20).
//
// M6.2 (decisions.md Keputusan 3): setiap entri `pending` mencatat waktu
// KEDATANGAN-nya sendiri (`pendingEntry.arrivedAt`, BUKAN `Row.StartedAt`
// span aslinya - yang mencerminkan kapan span itu DIBUAT di sisi Python,
// bisa jauh lebih tua dari kapan ia genuinely tiba di buffer ini kalau
// pipeline upstream sempat delay). Goroutine background (`evictionLoop`)
// memeriksa berkala, membuang entri yang tertahan melebihi
// `evictionTTL` (default 60 menit, jauh di atas worst-case hang LLM
// tercatat project ~25 menit - keterbatasan-diterima.md #7) dengan WARN
// log per span (bukan silent drop).
type Buffer struct {
	mu      sync.Mutex
	writer  traceSpanWriter
	pending map[string][]pendingEntry
	known   map[string]bool
	written map[string]bool
	logger  *zap.Logger

	evictionTTL time.Duration
	stopCh      chan struct{}
	doneCh      chan struct{}
}

// pendingEntry membungkus mappedSpan dengan waktu kedatangannya di buffer -
// dasar perhitungan TTL eviction (Keputusan 3 M6.2), terpisah dari
// mappedSpan.Row.StartedAt yang murni properti span asli.
type pendingEntry struct {
	span      mappedSpan
	arrivedAt time.Time
}

// NewBuffer membuat Buffer DAN langsung menjalankan goroutine eviction
// background - dipasangkan dengan Stop() (dipanggil shutdown() tracesExporter,
// factory.go) supaya tidak goroutine leak saat Collector berhenti/restart.
func NewBuffer(writer traceSpanWriter, logger *zap.Logger, evictionTTL time.Duration) *Buffer {
	if logger == nil {
		logger = zap.NewNop()
	}
	if evictionTTL <= 0 {
		// Config.Validate() (factory.go) sudah menolak nilai <=0 sebelum
		// sampai sini - fallback ini murni jaring pengaman kalau Buffer
		// dipakai langsung (mis. dari test) tanpa lewat Validate().
		evictionTTL = 60 * time.Minute
	}
	b := &Buffer{
		writer:      writer,
		pending:     make(map[string][]pendingEntry),
		known:       make(map[string]bool),
		written:     make(map[string]bool),
		logger:      logger,
		evictionTTL: evictionTTL,
		stopCh:      make(chan struct{}),
		doneCh:      make(chan struct{}),
	}
	go b.evictionLoop()
	return b
}

// evictionLoop menjalankan evictExpired() secara periodik sampai Stop()
// dipanggil. Interval dipilih 1/10 TTL (dibatasi 1-5 menit) - cukup
// responsif tanpa membebani CPU untuk TTL yang sangat panjang/pendek.
func (b *Buffer) evictionLoop() {
	defer close(b.doneCh)

	interval := b.evictionTTL / 10
	if interval < time.Minute {
		interval = time.Minute
	}
	if interval > 5*time.Minute {
		interval = 5 * time.Minute
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-b.stopCh:
			return
		case now := <-ticker.C:
			b.evictExpired(now)
		}
	}
}

// Stop menghentikan goroutine eviction background dengan bersih, MENUNGGU
// goroutine genuinely selesai (bukan fire-and-forget) - dipanggil dari
// shutdown() tracesExporter.
func (b *Buffer) Stop() {
	close(b.stopCh)
	<-b.doneCh
}

// evictExpired memindai SELURUH pending, membuang entri yang tertahan
// melebihi evictionTTL. Dipanggil evictionLoop (waktu nyata) ATAU
// langsung oleh unit test (deterministik, tidak bergantung timing ticker
// nyata). WARN log per span yang di-evict - bukan silent drop, konsisten
// "Kejujuran terhadap keterbatasan" (CLAUDE.md).
func (b *Buffer) evictExpired(now time.Time) {
	b.mu.Lock()
	defer b.mu.Unlock()

	for traceID, entries := range b.pending {
		remaining := make([]pendingEntry, 0, len(entries))
		for _, e := range entries {
			waited := now.Sub(e.arrivedAt)
			if waited > b.evictionTTL {
				b.logger.Warn("Span dievict dari buffer - induk/span akar tidak pernah tiba dalam TTL",
					zap.String("trace_id", traceID),
					zap.String("span_id", e.span.Row.SpanID),
					zap.Duration("tertahan", waited),
					zap.Duration("ttl", b.evictionTTL))
				continue
			}
			remaining = append(remaining, e)
		}
		if len(remaining) == 0 {
			delete(b.pending, traceID)
		} else {
			b.pending[traceID] = remaining
		}
	}
}

// Ingest memproses satu span hasil MapTraces. Span pembawa metadata trace
// (session.id+turn.index - BISA LEBIH DARI SATU span per trace, lihat
// Koreksi 2 di atas) memicu upsert baris traces DAN known[traceID]=true,
// TAPI itu tidak membuat span itu sendiri otomatis insertable - keputusan
// insert-langsung-atau-tahan SELALU lewat insertableLocked() yang sama
// untuk SEMUA span (akar sejati = ParentSpanID nil, atau induk
// langsungnya sudah tertulis). Yang belum memenuhi syarat ditahan di
// pending sampai terpenuhi lewat drainLocked.
func (b *Buffer) Ingest(ctx context.Context, ms mappedSpan) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	traceID := ms.Row.TraceID

	if ms.isAnchor() {
		row := TraceRow{
			TraceID:   traceID,
			SessionID: *ms.SessionID,
			TurnIndex: *ms.TurnIndex,
			StartedAt: ms.Row.StartedAt,
			EndedAt:   ms.Row.EndedAt,
			Status:    ms.Status,
			RoleTitle: ms.RoleTitle,
		}
		if err := b.writer.UpsertTrace(ctx, row); err != nil {
			b.logger.Error("UpsertTrace gagal", zap.String("trace_id", traceID), zap.Error(err))
			return err
		}
		b.known[traceID] = true
	}

	if b.insertableLocked(ms) {
		if err := b.writer.InsertSpan(ctx, ms.Row); err != nil {
			parent := "<nil>"
			if ms.Row.ParentSpanID != nil {
				parent = *ms.Row.ParentSpanID
			}
			b.logger.Error("InsertSpan gagal",
				zap.String("trace_id", traceID), zap.String("span_id", ms.Row.SpanID),
				zap.String("parent_span_id", parent), zap.Error(err))
			return err
		}
		b.written[ms.Row.SpanID] = true
		return b.drainLocked(ctx, traceID)
	}

	b.pending[traceID] = append(b.pending[traceID], pendingEntry{span: ms, arrivedAt: time.Now()})
	return nil
}

// insertableLocked: trace-nya sudah py baris `traces` DAN (span ini akar
// ATAU induk langsungnya sudah tertulis).
func (b *Buffer) insertableLocked(ms mappedSpan) bool {
	if !b.known[ms.Row.TraceID] {
		return false
	}
	if ms.Row.ParentSpanID == nil {
		return true
	}
	return b.written[*ms.Row.ParentSpanID]
}

// drainLocked menulis berulang seluruh span tertahan untuk satu trace_id
// yang prasyaratnya SUDAH terpenuhi, sampai tidak ada lagi progres
// (fixpoint) - satu pass menangani satu "lapisan" nesting yang baru
// terbuka; span yang induknya baru saja ditulis di pass ini akan
// terdeteksi insertable di pass berikutnya, mencakup kedalaman nesting
// berapa pun tanpa asumsi urutan kedatangan. Dalam satu pass, span yang
// sama-sama insertable diurutkan naik berdasar StartedAt murni untuk
// keterbacaan urutan tulis (bukan correctness - correctness datang dari
// `written`/insertableLocked).
func (b *Buffer) drainLocked(ctx context.Context, traceID string) error {
	var errs []error
	for {
		remaining := make([]pendingEntry, 0, len(b.pending[traceID]))
		var ready []pendingEntry
		for _, e := range b.pending[traceID] {
			if b.insertableLocked(e.span) {
				ready = append(ready, e)
			} else {
				remaining = append(remaining, e)
			}
		}

		if len(ready) == 0 {
			if len(remaining) == 0 {
				delete(b.pending, traceID)
			} else {
				b.pending[traceID] = remaining
			}
			return errors.Join(errs...)
		}

		sort.SliceStable(ready, func(i, j int) bool {
			return ready[i].span.Row.StartedAt.Before(ready[j].span.Row.StartedAt)
		})

		// Span yang GAGAL ditulis (mis. FK yang genuinely tak terduga)
		// TIDAK BOLEH menghentikan pass ini - siblingnya yang SAMA-SAMA
		// insertable pada pass ini tetap harus dicoba, supaya satu span
		// bermasalah tidak diam-diam menjatuhkan seluruh drain trace ini
		// (Kejujuran terhadap keterbatasan - lihat CLAUDE.md).
		for _, e := range ready {
			if err := b.writer.InsertSpan(ctx, e.span.Row); err != nil {
				parent := "<nil>"
				if e.span.Row.ParentSpanID != nil {
					parent = *e.span.Row.ParentSpanID
				}
				b.logger.Error("InsertSpan gagal (drain)",
					zap.String("trace_id", traceID), zap.String("span_id", e.span.Row.SpanID),
					zap.String("parent_span_id", parent), zap.Error(err))
				errs = append(errs, err)
				continue
			}
			b.written[e.span.Row.SpanID] = true
		}

		b.pending[traceID] = remaining
	}
}

// PendingCount mengembalikan jumlah trace_id yang masih py span tertahan -
// dipakai unit test untuk verifikasi keadaan buffer, bukan logic produksi.
func (b *Buffer) PendingCount() int {
	b.mu.Lock()
	defer b.mu.Unlock()
	return len(b.pending)
}

// PendingSpansFor mengembalikan salinan span (mappedSpan, tanpa arrivedAt)
// yang tertahan untuk satu trace_id - dipakai unit test.
func (b *Buffer) PendingSpansFor(traceID string) []mappedSpan {
	b.mu.Lock()
	defer b.mu.Unlock()
	out := make([]mappedSpan, len(b.pending[traceID]))
	for i, e := range b.pending[traceID] {
		out[i] = e.span
	}
	return out
}
