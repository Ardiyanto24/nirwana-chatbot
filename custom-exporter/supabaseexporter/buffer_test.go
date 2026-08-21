package supabaseexporter

import (
	"context"
	"testing"
	"time"

	"go.uber.org/zap"
)

// fakeWriter merekam pemanggilan UpsertTrace/InsertSpan di memori - tanpa
// koneksi Postgres nyata, mirror filosofi test storage.go/mapping.go.
type fakeWriter struct {
	upsertedTraces []TraceRow
	insertedSpans  []SpanRow
}

func (f *fakeWriter) UpsertTrace(ctx context.Context, t TraceRow) error {
	f.upsertedTraces = append(f.upsertedTraces, t)
	return nil
}

func (f *fakeWriter) InsertSpan(ctx context.Context, sp SpanRow) error {
	f.insertedSpans = append(f.insertedSpans, sp)
	return nil
}

func strPtr(s string) *string { return &s }
func intPtr(i int) *int       { return &i }

// TestBuffer_SpanAnakSebelumAnchor mereplikasi kondisi REALISTIS yang
// ditemukan riset M6.1 (bukan cuma KK2 sumber yang mengasumsikan parent
// selalu duluan): span anak tiba DULU (trace_id belum dikenal), lalu
// span invoke_agent (anchor) tiba belakangan - forced oleh
// BatchSpanProcessor Python SDK + nested span semantics (invoke_agent
// selalu berakhir/ter-export paling belakangan).
func TestBuffer_SpanAnakSebelumAnchor(t *testing.T) {
	fw := &fakeWriter{}
	buf := NewBuffer(fw, zap.NewNop())
	ctx := context.Background()
	now := time.Now()

	childSpan := mappedSpan{
		Row: SpanRow{
			SpanID:        "span-child",
			TraceID:       "trace-1",
			ParentSpanID:  strPtr("span-root"),
			LayerName:     "domain_gate",
			OperationName: strPtr("chat"),
			StartedAt:     now,
		},
	}

	if err := buf.Ingest(ctx, childSpan); err != nil {
		t.Fatalf("Ingest span anak error: %v", err)
	}

	// Span anak TIDAK BOLEH langsung ditulis - trace_id belum dikenal.
	if len(fw.insertedSpans) != 0 {
		t.Errorf("span anak seharusnya DITAHAN (belum ada baris traces), tapi %d span sudah ditulis", len(fw.insertedSpans))
	}
	if len(fw.upsertedTraces) != 0 {
		t.Errorf("belum boleh ada baris traces sebelum anchor tiba")
	}
	if buf.PendingCount() != 1 {
		t.Fatalf("harus ada 1 trace_id tertahan, dapat %d", buf.PendingCount())
	}
	if got := buf.PendingSpansFor("trace-1"); len(got) != 1 || got[0].Row.SpanID != "span-child" {
		t.Errorf("span anak yang tertahan salah: %+v", got)
	}

	anchorSpan := mappedSpan{
		Row: SpanRow{
			SpanID:        "span-root",
			TraceID:       "trace-1",
			LayerName:     "orchestration",
			OperationName: strPtr("invoke_agent"),
			StartedAt:     now.Add(-1 * time.Second),
		},
		SessionID: strPtr("sess-1"),
		TurnIndex: intPtr(1),
		RoleTitle: strPtr("General Manager"),
	}

	if err := buf.Ingest(ctx, anchorSpan); err != nil {
		t.Fatalf("Ingest anchor error: %v", err)
	}

	// Setelah anchor tiba: baris traces HARUS ada, span tertahan HARUS
	// ter-flush, urutan HARUS traces dulu baru span (parent-sebelum-child).
	if len(fw.upsertedTraces) != 1 {
		t.Fatalf("baris traces harus ter-upsert tepat 1x setelah anchor tiba, dapat %d", len(fw.upsertedTraces))
	}
	if fw.upsertedTraces[0].SessionID != "sess-1" || fw.upsertedTraces[0].TurnIndex != 1 {
		t.Errorf("session_id/turn_index baris traces salah: %+v", fw.upsertedTraces[0])
	}
	// Addendum M6.1 (keterbatasan-diterima.md #19): RoleTitle harus
	// diteruskan sampai TraceRow, bukan cuma diterima lalu dibuang.
	if fw.upsertedTraces[0].RoleTitle == nil || *fw.upsertedTraces[0].RoleTitle != "General Manager" {
		t.Errorf("role_title baris traces salah, dapat %v", fw.upsertedTraces[0].RoleTitle)
	}

	if len(fw.insertedSpans) != 2 {
		t.Fatalf("harus 2 span ter-INSERT setelah flush (anchor + child tertahan), dapat %d", len(fw.insertedSpans))
	}
	if fw.insertedSpans[0].SpanID != "span-root" {
		t.Errorf("span anchor harus ditulis LEBIH DULU (urutan[0]), dapat %s", fw.insertedSpans[0].SpanID)
	}
	if fw.insertedSpans[1].SpanID != "span-child" {
		t.Errorf("span anak tertahan harus ditulis SETELAH anchor (urutan[1]), dapat %s", fw.insertedSpans[1].SpanID)
	}

	if buf.PendingCount() != 0 {
		t.Errorf("buffer harus kosong setelah flush, tersisa %d trace_id", buf.PendingCount())
	}
}

// TestBuffer_CucuSebelumIndukNonRoot mereplikasi bug NYATA yang ditemukan
// verifikasi produksi M6.1 (skenario gop_margin, trace
// f831b5b7df9e903f1eb5b5095bf9fcde): FK spans_parent_span_id_fkey
// terlanggar karena flushLocked() dulu menulis span dalam urutan
// KEDATANGAN mentah, bukan urutan StartedAt. Trace multi-level -
// invoke_agent (anchor) -> domain_gate.periksa_otorisasi_semua (induk
// non-root) -> authorization.check (cucu) - induk non-root itu SENDIRI
// berakhir belakangan anaknya (nested span semantics), jadi cucu bisa
// tiba di buffer LEBIH DULU daripada induk langsungnya. Test ini
// sengaja meng-ingest cucu SEBELUM induk non-root-nya (kebalikan urutan
// StartedAt asli), lalu anchor terakhir - assert urutan tulis akhir
// tetap induk-sebelum-anak di SETIAP kedalaman.
func TestBuffer_CucuSebelumIndukNonRoot(t *testing.T) {
	fw := &fakeWriter{}
	buf := NewBuffer(fw, zap.NewNop())
	ctx := context.Background()
	now := time.Now()

	// StartedAt mencerminkan urutan MULAI nyata (induk selalu mulai
	// duluan): anchor (t+0s) -> induk non-root (t+1s) -> cucu (t+2s).
	grandchild := mappedSpan{
		Row: SpanRow{
			SpanID:        "span-grandchild",
			TraceID:       "trace-3",
			ParentSpanID:  strPtr("span-mid"),
			LayerName:     "domain_gate",
			OperationName: strPtr("authorization.check"),
			StartedAt:     now.Add(2 * time.Second),
		},
	}
	// Diingest DULUAN meski StartedAt-nya paling akhir - mensimulasikan
	// span cucu yang BERAKHIR (ter-export) lebih dulu daripada induk
	// non-root-nya sendiri.
	if err := buf.Ingest(ctx, grandchild); err != nil {
		t.Fatalf("Ingest cucu error: %v", err)
	}

	mid := mappedSpan{
		Row: SpanRow{
			SpanID:        "span-mid",
			TraceID:       "trace-3",
			ParentSpanID:  strPtr("span-root"),
			LayerName:     "domain_gate",
			OperationName: strPtr("domain_gate.periksa_otorisasi_semua"),
			StartedAt:     now.Add(1 * time.Second),
		},
	}
	if err := buf.Ingest(ctx, mid); err != nil {
		t.Fatalf("Ingest induk non-root error: %v", err)
	}

	anchor := mappedSpan{
		Row: SpanRow{
			SpanID:        "span-root",
			TraceID:       "trace-3",
			LayerName:     "orchestration",
			OperationName: strPtr("invoke_agent"),
			StartedAt:     now,
		},
		SessionID: strPtr("sess-3"),
		TurnIndex: intPtr(1),
	}
	if err := buf.Ingest(ctx, anchor); err != nil {
		t.Fatalf("Ingest anchor error: %v", err)
	}

	if len(fw.insertedSpans) != 3 {
		t.Fatalf("harus 3 span ter-INSERT (anchor + induk non-root + cucu), dapat %d", len(fw.insertedSpans))
	}

	posisi := make(map[string]int, 3)
	for i, sp := range fw.insertedSpans {
		posisi[sp.SpanID] = i
	}

	if posisi["span-root"] >= posisi["span-mid"] {
		t.Errorf("span-root (anchor) harus ditulis SEBELUM span-mid (induk non-root), posisi: %v", posisi)
	}
	if posisi["span-mid"] >= posisi["span-grandchild"] {
		t.Errorf("span-mid (induk non-root) harus ditulis SEBELUM span-grandchild (cucu) meski cucu tiba DULUAN di buffer - ini bug FK spans_parent_span_id_fkey yang ditemukan verifikasi produksi, posisi: %v", posisi)
	}
}

// TestBuffer_CucuTibaSetelahAnchorSebelumIndukNonRoot mereplikasi AKAR
// MASALAH SEBENARNYA dari bug produksi (trace f831b5b7df9e903f1eb5b5095b
// f9fcde) - beda dari TestBuffer_CucuSebelumIndukNonRoot di atas (yang
// hanya menguji urutan DALAM SATU flush pending sebelum anchor tiba).
// Collector `batch` processor mem-flush pushTraces() dalam BANYAK batch
// terpisah sepanjang durasi satu turn: anchor bisa tiba LEBIH DULU
// (trace jadi "dikenal"), lalu span cucu tiba di batch BERIKUTNYA
// SEBELUM induk langsungnya sendiri (juga non-root) sempat diproses.
// Fix StartedAt-sort SAJA tidak menangkap ini karena jalur "trace sudah
// dikenal -> insert langsung" (versi lama) tidak pernah mengecek span
// induknya sudah tertulis atau belum. Fix sebenarnya: `written` set +
// insertableLocked + drainLocked kaskade.
func TestBuffer_CucuTibaSetelahAnchorSebelumIndukNonRoot(t *testing.T) {
	fw := &fakeWriter{}
	buf := NewBuffer(fw, zap.NewNop())
	ctx := context.Background()
	now := time.Now()

	// Batch 1: HANYA anchor tiba (mensimulasikan invoke_agent ter-export
	// Collector lebih dulu, sebelum batch berikutnya membawa turunannya).
	anchor := mappedSpan{
		Row: SpanRow{
			SpanID:        "span-root",
			TraceID:       "trace-4",
			LayerName:     "orchestration",
			OperationName: strPtr("invoke_agent"),
			StartedAt:     now,
		},
		SessionID: strPtr("sess-4"),
		TurnIndex: intPtr(1),
	}
	if err := buf.Ingest(ctx, anchor); err != nil {
		t.Fatalf("Ingest anchor error: %v", err)
	}
	if len(fw.insertedSpans) != 1 || fw.insertedSpans[0].SpanID != "span-root" {
		t.Fatalf("anchor harus langsung ter-INSERT sendirian, dapat %+v", fw.insertedSpans)
	}

	// Batch 2: cucu tiba DULUAN dalam batch ini, induk non-root-nya
	// (span-mid) BELUM tiba sama sekali - trace SUDAH dikenal (anchor
	// sudah ada), tapi span-mid belum ter-INSERT.
	grandchild := mappedSpan{
		Row: SpanRow{
			SpanID:        "span-grandchild",
			TraceID:       "trace-4",
			ParentSpanID:  strPtr("span-mid"),
			LayerName:     "domain_gate",
			OperationName: strPtr("authorization.check"),
			StartedAt:     now.Add(2 * time.Second),
		},
	}
	if err := buf.Ingest(ctx, grandchild); err != nil {
		t.Fatalf("Ingest cucu error: %v", err)
	}
	// TIDAK boleh langsung ter-INSERT walau trace sudah dikenal - induk
	// langsungnya (span-mid) belum tertulis. Ini persis kondisi yang
	// SEBELUM PERBAIKAN melanggar spans_parent_span_id_fkey.
	if len(fw.insertedSpans) != 1 {
		t.Fatalf("cucu TIDAK BOLEH langsung ter-INSERT sebelum induk non-root-nya tertulis, dapat %d span ter-insert", len(fw.insertedSpans))
	}
	if buf.PendingCount() != 1 {
		t.Fatalf("trace-4 harus py 1 span tertahan (cucu), dapat pending count %d", buf.PendingCount())
	}

	// Batch 3: induk non-root akhirnya tiba.
	mid := mappedSpan{
		Row: SpanRow{
			SpanID:        "span-mid",
			TraceID:       "trace-4",
			ParentSpanID:  strPtr("span-root"),
			LayerName:     "domain_gate",
			OperationName: strPtr("domain_gate.periksa_otorisasi_semua"),
			StartedAt:     now.Add(1 * time.Second),
		},
	}
	if err := buf.Ingest(ctx, mid); err != nil {
		t.Fatalf("Ingest induk non-root error: %v", err)
	}

	// Sekarang HARUS 3 span ter-INSERT total (anchor + mid + cucu yang
	// otomatis ter-drain begitu induknya tertulis), urutan induk-sebelum-
	// anak terjaga.
	if len(fw.insertedSpans) != 3 {
		t.Fatalf("harus 3 span ter-INSERT setelah induk non-root tiba (drain kaskade cucu tertahan), dapat %d: %+v", len(fw.insertedSpans), fw.insertedSpans)
	}
	posisi := make(map[string]int, 3)
	for i, sp := range fw.insertedSpans {
		posisi[sp.SpanID] = i
	}
	if posisi["span-mid"] >= posisi["span-grandchild"] {
		t.Errorf("span-mid harus ditulis SEBELUM span-grandchild yang tadinya tertahan, posisi: %v", posisi)
	}
	if buf.PendingCount() != 0 {
		t.Errorf("buffer harus kosong setelah drain kaskade, tersisa %d trace_id", buf.PendingCount())
	}
}

// TestBuffer_SpanNonRootJugaBawaSessionTurnIndex mereplikasi AKAR MASALAH
// SEBENARNYA dari bug produksi (trace eadc58b474e238446e8e6b95a9e663ec,
// skenario m6.1-fk-fix-verify-3) - beda dari kedua test cucu/mid di atas
// yang HANYA menguji span TANPA session.id/turn.index. Riset ulang
// menemukan input.validate (M1.2), span `chat` narasi (M4.4), DAN
// riwayat.simpan (M7.18) SEMUA turut men-set session.id+turn.index pada
// span mereka SENDIRI (kebutuhan observability masing-masing) meski
// SEMUANYA span NON-ROOT (py ParentSpanID mengarah ke invoke_agent).
// Desain SEBELUM koreksi ini menyamakan isAnchor() (=py session.id+
// turn.index) dengan "span akar, selalu insertable" - salah, sehingga
// span non-root ini di-INSERT LANGSUNG tanpa mengecek induknya sendiri
// sudah tertulis atau belum, melanggar spans_parent_span_id_fkey persis
// saat tiba SEBELUM invoke_agent (mis. riwayat.simpan tiba di batch yang
// sama dengan invoke_agent tapi urutan pemrosesan dalam slice mapped
// menempatkannya lebih dulu).
func TestBuffer_SpanNonRootJugaBawaSessionTurnIndex(t *testing.T) {
	fw := &fakeWriter{}
	buf := NewBuffer(fw, zap.NewNop())
	ctx := context.Background()
	now := time.Now()

	// riwayat.simpan tiba DULUAN - non-root (ParentSpanID mengarah ke
	// invoke_agent), TAPI JUGA membawa session.id+turn.index sama seperti
	// invoke_agent. Trace belum "dikenal" sama sekali di titik ini.
	riwayatSimpan := mappedSpan{
		Row: SpanRow{
			SpanID:        "span-riwayat",
			TraceID:       "trace-5",
			ParentSpanID:  strPtr("span-root-5"),
			LayerName:     "orchestration",
			OperationName: strPtr("riwayat.simpan"),
			StartedAt:     now.Add(1 * time.Second),
		},
		SessionID: strPtr("sess-5"),
		TurnIndex: intPtr(1),
		Status:    strPtr("berhasil"),
	}
	if err := buf.Ingest(ctx, riwayatSimpan); err != nil {
		t.Fatalf("Ingest riwayat.simpan error: %v", err)
	}

	// Baris traces SUDAH boleh ter-upsert (riwayat.simpan JUGA sah
	// memicu UpsertTrace - mengisi status lebih awal), TAPI span
	// riwayat.simpan ITU SENDIRI TIDAK BOLEH langsung ter-INSERT karena
	// induknya (span-root-5) belum tertulis - ini persis kondisi yang
	// SEBELUM PERBAIKAN melanggar FK.
	if len(fw.upsertedTraces) != 1 {
		t.Fatalf("baris traces harus ter-upsert dari riwayat.simpan (span metadata, bukan cuma invoke_agent), dapat %d", len(fw.upsertedTraces))
	}
	if len(fw.insertedSpans) != 0 {
		t.Fatalf("riwayat.simpan TIDAK BOLEH langsung ter-INSERT sebelum induknya (invoke_agent) tertulis, dapat %d span ter-insert", len(fw.insertedSpans))
	}
	if buf.PendingCount() != 1 {
		t.Fatalf("trace-5 harus py 1 span tertahan (riwayat.simpan), dapat pending count %d", buf.PendingCount())
	}

	// invoke_agent (akar sejati, ParentSpanID nil) akhirnya tiba.
	anchor := mappedSpan{
		Row: SpanRow{
			SpanID:        "span-root-5",
			TraceID:       "trace-5",
			LayerName:     "orchestration",
			OperationName: strPtr("invoke_agent"),
			StartedAt:     now,
		},
		SessionID: strPtr("sess-5"),
		TurnIndex: intPtr(1),
	}
	if err := buf.Ingest(ctx, anchor); err != nil {
		t.Fatalf("Ingest anchor error: %v", err)
	}

	if len(fw.insertedSpans) != 2 {
		t.Fatalf("harus 2 span ter-INSERT (invoke_agent + riwayat.simpan yang ter-drain), dapat %d: %+v", len(fw.insertedSpans), fw.insertedSpans)
	}
	posisi := make(map[string]int, 2)
	for i, sp := range fw.insertedSpans {
		posisi[sp.SpanID] = i
	}
	if posisi["span-root-5"] >= posisi["span-riwayat"] {
		t.Errorf("invoke_agent (akar sejati) harus ditulis SEBELUM riwayat.simpan meski keduanya sama-sama membawa session.id+turn.index, posisi: %v", posisi)
	}
	if buf.PendingCount() != 0 {
		t.Errorf("buffer harus kosong setelah drain, tersisa %d trace_id", buf.PendingCount())
	}
}

// TestBuffer_TraceSudahDikenalLangsungInsert - kebalikan kasus di atas:
// begitu trace_id sudah dikenal (anchor sudah pernah tiba), span
// berikutnya untuk trace_id yang sama langsung ditulis tanpa ditahan.
func TestBuffer_TraceSudahDikenalLangsungInsert(t *testing.T) {
	fw := &fakeWriter{}
	buf := NewBuffer(fw, zap.NewNop())
	ctx := context.Background()

	anchor := mappedSpan{
		Row:       SpanRow{SpanID: "span-root", TraceID: "trace-2", LayerName: "orchestration", StartedAt: time.Now()},
		SessionID: strPtr("sess-2"),
		TurnIndex: intPtr(1),
	}
	if err := buf.Ingest(ctx, anchor); err != nil {
		t.Fatalf("Ingest anchor error: %v", err)
	}

	laterChild := mappedSpan{
		Row: SpanRow{SpanID: "span-later", TraceID: "trace-2", LayerName: "execution", StartedAt: time.Now()},
	}
	if err := buf.Ingest(ctx, laterChild); err != nil {
		t.Fatalf("Ingest span kemudian error: %v", err)
	}

	if len(fw.insertedSpans) != 2 {
		t.Fatalf("harus 2 span ter-INSERT (anchor + span kemudian, langsung tanpa ditahan), dapat %d", len(fw.insertedSpans))
	}
	if buf.PendingCount() != 0 {
		t.Errorf("tidak boleh ada yang tertahan untuk trace yang sudah dikenal")
	}
}

// TestBuffer_DuaTraceBerbedaTidakSalingMengganggu - buffer per-trace_id,
// span trace A yang tertahan tidak ikut ter-flush saat trace B dapat
// anchor-nya.
func TestBuffer_DuaTraceBerbedaTidakSalingMengganggu(t *testing.T) {
	fw := &fakeWriter{}
	buf := NewBuffer(fw, zap.NewNop())
	ctx := context.Background()

	childA := mappedSpan{Row: SpanRow{SpanID: "a-child", TraceID: "trace-A", LayerName: "domain_gate", StartedAt: time.Now()}}
	if err := buf.Ingest(ctx, childA); err != nil {
		t.Fatal(err)
	}

	anchorB := mappedSpan{
		Row:       SpanRow{SpanID: "b-root", TraceID: "trace-B", LayerName: "orchestration", StartedAt: time.Now()},
		SessionID: strPtr("sess-B"),
		TurnIndex: intPtr(1),
	}
	if err := buf.Ingest(ctx, anchorB); err != nil {
		t.Fatal(err)
	}

	if buf.PendingCount() != 1 {
		t.Fatalf("trace-A harus TETAP tertahan (belum dapat anchor sendiri), dapat pending count %d", buf.PendingCount())
	}
	if got := buf.PendingSpansFor("trace-A"); len(got) != 1 {
		t.Errorf("trace-A harus masih menahan 1 span, dapat %d", len(got))
	}
	for _, sp := range fw.insertedSpans {
		if sp.TraceID == "trace-A" {
			t.Errorf("span trace-A TIDAK BOLEH ikut ter-INSERT hanya karena trace-B dapat anchor")
		}
	}
}
