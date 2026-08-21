package supabaseexporter

import (
	"context"
	"testing"
	"time"
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
	buf := NewBuffer(fw)
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

// TestBuffer_TraceSudahDikenalLangsungInsert - kebalikan kasus di atas:
// begitu trace_id sudah dikenal (anchor sudah pernah tiba), span
// berikutnya untuk trace_id yang sama langsung ditulis tanpa ditahan.
func TestBuffer_TraceSudahDikenalLangsungInsert(t *testing.T) {
	fw := &fakeWriter{}
	buf := NewBuffer(fw)
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
	buf := NewBuffer(fw)
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
