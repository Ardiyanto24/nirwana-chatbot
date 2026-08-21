package supabaseexporter

import (
	"context"
	"sync"
)

// traceSpanWriter adalah interface tipis yang dipenuhi *Storage - dipisah
// supaya Buffer testable tanpa koneksi Postgres nyata (fakeWriter di
// buffer_test.go), mirror filosofi storage.go/mapping.go (murni,
// testable).
type traceSpanWriter interface {
	UpsertTrace(ctx context.Context, t TraceRow) error
	InsertSpan(ctx context.Context, sp SpanRow) error
}

// Buffer menahan span untuk trace_id yang belum py baris `traces` -
// forced karena invoke_agent (satu-satunya span pembawa session.id+
// turn.index, WAJIB untuk kolom NOT NULL traces.session_id/turn_index)
// SELALU berakhir belakangan dibanding anak-anaknya (BatchSpanProcessor
// Python SDK + nested span semantics - lihat
// milestones/6.1-membangun-exporter-dasar/decisions.md Keputusan 6).
//
// Cakupan SENGAJA dibatasi (forced by Lingkup M6.1 "jalur data paling
// sederhana"): `known` murni in-memory, tidak query TraceExists ke DB
// saat cold-start proses baru - trace yang barisnya sudah ada di Supabase
// dari proses SEBELUMNYA akan dianggap "belum dikenal" lagi sampai anchor
// barunya terlihat proses ini. Trace yang anchor-nya TIDAK PERNAH tiba
// (mis. proses_turn() crash sebelum invoke_agent selesai) akan tertahan
// selamanya di memori - penanganan eviction/timeout adalah cakupan M6.2
// (reliability), BUKAN M6.1.
type Buffer struct {
	mu      sync.Mutex
	writer  traceSpanWriter
	pending map[string][]mappedSpan
	known   map[string]bool
}

func NewBuffer(writer traceSpanWriter) *Buffer {
	return &Buffer{
		writer:  writer,
		pending: make(map[string][]mappedSpan),
		known:   make(map[string]bool),
	}
}

// Ingest memproses satu span hasil MapTraces. Span anchor (bawa
// session.id+turn.index) memicu upsert baris traces lalu flush seluruh
// span yang sempat tertahan untuk trace_id yang sama. Span non-anchor
// untuk trace_id yang sudah dikenal langsung di-INSERT; yang belum
// dikenal ditahan.
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
		}
		if err := b.writer.UpsertTrace(ctx, row); err != nil {
			return err
		}
		b.known[traceID] = true

		if err := b.writer.InsertSpan(ctx, ms.Row); err != nil {
			return err
		}
		return b.flushLocked(ctx, traceID)
	}

	if b.known[traceID] {
		return b.writer.InsertSpan(ctx, ms.Row)
	}

	b.pending[traceID] = append(b.pending[traceID], ms)
	return nil
}

func (b *Buffer) flushLocked(ctx context.Context, traceID string) error {
	spans := b.pending[traceID]
	delete(b.pending, traceID)
	for _, sp := range spans {
		if err := b.writer.InsertSpan(ctx, sp.Row); err != nil {
			return err
		}
	}
	return nil
}

// PendingCount mengembalikan jumlah trace_id yang masih tertahan (belum
// ketemu anchor-nya) - dipakai unit test untuk verifikasi keadaan buffer,
// bukan logic produksi.
func (b *Buffer) PendingCount() int {
	b.mu.Lock()
	defer b.mu.Unlock()
	return len(b.pending)
}

// PendingSpansFor mengembalikan salinan span yang tertahan untuk satu
// trace_id - dipakai unit test.
func (b *Buffer) PendingSpansFor(traceID string) []mappedSpan {
	b.mu.Lock()
	defer b.mu.Unlock()
	out := make([]mappedSpan, len(b.pending[traceID]))
	copy(out, b.pending[traceID])
	return out
}
