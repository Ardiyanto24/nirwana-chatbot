package supabaseexporter

import (
	"strings"
	"testing"
	"time"
)

func TestTraceUpsertArgs_UrutanDanNilaiSesuaiSkema(t *testing.T) {
	started := time.Date(2026, 8, 21, 10, 0, 0, 0, time.UTC)
	status := "berhasil"
	role := "General Manager"
	tr := TraceRow{
		TraceID:   "trace-1",
		SessionID: "sess-1",
		TurnIndex: 1,
		StartedAt: started,
		EndedAt:   nil,
		Status:    &status,
		RoleTitle: &role,
	}

	sql, args := traceUpsertArgs(tr)

	if !strings.Contains(sql, "INSERT INTO traces") {
		t.Errorf("sql harus mengandung INSERT INTO traces, dapat: %s", sql)
	}
	if !strings.Contains(sql, "ON CONFLICT (trace_id) DO UPDATE") {
		t.Errorf("sql harus UPSERT (ON CONFLICT DO UPDATE), dapat: %s", sql)
	}
	if len(args) != 7 {
		t.Fatalf("args harus 7 elemen (trace_id,session_id,turn_index,started_at,ended_at,status,role_title), dapat %d", len(args))
	}
	if args[0] != "trace-1" || args[1] != "sess-1" || args[2] != 1 {
		t.Errorf("urutan args pertama salah: %v", args[:3])
	}
}

func TestTraceUpsertArgs_ColumnsTidakBolehMenimpaDenganNULL(t *testing.T) {
	// COALESCE(EXCLUDED.status, traces.status) - mempertahankan status lama
	// kalau upsert baru datang tanpa status (nil), bukan menimpanya jadi NULL.
	// Ini forced oleh strategi buffering Checkpoint 7 (status baru diketahui
	// belakangan lewat span riwayat.simpan, invoke_agent sendiri tidak
	// membawa status).
	sql, _ := traceUpsertArgs(TraceRow{TraceID: "t1", SessionID: "s1", TurnIndex: 1, StartedAt: time.Now()})
	if !strings.Contains(sql, "COALESCE(EXCLUDED.status, traces.status)") {
		t.Errorf("sql harus pakai COALESCE untuk status supaya tidak ditimpa NULL, dapat: %s", sql)
	}
}

func TestSpanInsertArgs_UrutanDanNilaiSesuaiSkema(t *testing.T) {
	started := time.Date(2026, 8, 21, 10, 0, 1, 0, time.UTC)
	ended := started.Add(500 * time.Millisecond)
	parent := "span-root"
	op := "chat"
	dur := 500
	errType := "ditolak_otorisasi"
	sr := SpanRow{
		SpanID:        "span-child",
		TraceID:       "trace-1",
		ParentSpanID:  &parent,
		LayerName:     "domain_gate",
		OperationName: &op,
		StartedAt:     started,
		EndedAt:       &ended,
		DurationMs:    &dur,
		ErrorType:     &errType,
		Attributes:    `{"rbac.decision":"deny"}`,
	}

	sql, args := spanInsertArgs(sr)

	if !strings.Contains(sql, "INSERT INTO spans") {
		t.Errorf("sql harus mengandung INSERT INTO spans, dapat: %s", sql)
	}
	if !strings.Contains(sql, "ON CONFLICT (span_id) DO NOTHING") {
		t.Errorf("sql harus DO NOTHING (span_id unik, data tidak berubah), dapat: %s", sql)
	}
	if len(args) != 10 {
		t.Fatalf("args harus 10 elemen sesuai kolom spans, dapat %d", len(args))
	}
	if args[0] != "span-child" || args[1] != "trace-1" {
		t.Errorf("urutan args span_id/trace_id salah: %v", args[:2])
	}
	if args[8] != &errType {
		t.Errorf("args[8] harus pointer ErrorType")
	}
}

func TestSpanInsertArgs_ParentSpanIDNilUntukSpanAkar(t *testing.T) {
	sr := SpanRow{
		SpanID:     "span-root",
		TraceID:    "trace-1",
		LayerName:  "orchestration",
		StartedAt:  time.Now(),
		Attributes: "{}",
	}
	_, args := spanInsertArgs(sr)
	// args[2] adalah `any` yang membungkus *string(nil) (SpanRow.ParentSpanID
	// tidak diisi) - dibandingkan terhadap (*string)(nil) yang typed SAMA,
	// BUKAN untyped nil (perbandingan `any != nil` SELALU true untuk
	// interface yang membungkus pointer nil bertipe - classic Go gotcha).
	if args[2] != (*string)(nil) {
		t.Errorf("parent_span_id harus nil untuk span akar (invoke_agent), dapat: %v", args[2])
	}
}
