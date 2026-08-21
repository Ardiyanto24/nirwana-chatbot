package supabaseexporter

import (
	"encoding/hex"
	"testing"
	"time"

	"go.opentelemetry.io/collector/pdata/pcommon"
	"go.opentelemetry.io/collector/pdata/ptrace"
)

func TestLayerNameFromScope(t *testing.T) {
	cases := map[string]string{
		"orchestration":                    "orchestration",
		"input_layer":                      "input_layer",
		"domain_gate.cakupan_individu":     "domain_gate",
		"retriever.retriever":              "retriever",
		"context_resolution.rewrite":       "context_resolution",
		"orchestration.riwayat_percakapan": "orchestration",
	}
	for scope, want := range cases {
		if got := layerNameFromScope(scope); got != want {
			t.Errorf("layerNameFromScope(%q) = %q, ingin %q", scope, got, want)
		}
	}
}

func addSpan(ss ptrace.ScopeSpans, traceIDByte, spanIDByte byte, name string, start time.Time) ptrace.Span {
	span := ss.Spans().AppendEmpty()
	var traceID [16]byte
	traceID[15] = traceIDByte
	var spanID [8]byte
	spanID[7] = spanIDByte
	span.SetTraceID(pcommon.TraceID(traceID))
	span.SetSpanID(pcommon.SpanID(spanID))
	span.SetName(name)
	span.SetStartTimestamp(pcommon.NewTimestampFromTime(start))
	span.SetEndTimestamp(pcommon.NewTimestampFromTime(start.Add(100 * time.Millisecond)))
	return span
}

// TestMapTraces_SpanNamaSamaDiScopeBerbeda mereplikasi PERSIS masalah nyata
// yang ditemukan riset M6.1: span.Name()="chat" dipakai ulang >=13 lokasi
// lintas layer berbeda - membuktikan layer_name TETAP benar per span
// walau nama span identik, karena diambil dari scope (bukan span.Name()).
func TestMapTraces_SpanNamaSamaDiScopeBerbeda(t *testing.T) {
	td := ptrace.NewTraces()
	rs := td.ResourceSpans().AppendEmpty()
	now := time.Now()

	ssDomainGate := rs.ScopeSpans().AppendEmpty()
	ssDomainGate.Scope().SetName("domain_gate.identifikasi")
	addSpan(ssDomainGate, 1, 1, "chat", now)

	ssRetriever := rs.ScopeSpans().AppendEmpty()
	ssRetriever.Scope().SetName("retriever.kecocokan_makna")
	addSpan(ssRetriever, 1, 2, "chat", now)

	mapped, err := MapTraces(td)
	if err != nil {
		t.Fatalf("MapTraces error: %v", err)
	}
	if len(mapped) != 2 {
		t.Fatalf("harus 2 span termapping, dapat %d", len(mapped))
	}

	if mapped[0].Row.OperationName == nil || *mapped[0].Row.OperationName != "chat" {
		t.Errorf("span pertama operation_name harus 'chat'")
	}
	if mapped[0].Row.LayerName != "domain_gate" {
		t.Errorf("span pertama (scope domain_gate.identifikasi) layer_name = %q, ingin domain_gate", mapped[0].Row.LayerName)
	}
	if mapped[1].Row.LayerName != "retriever" {
		t.Errorf("span kedua (scope retriever.kecocokan_makna) layer_name = %q, ingin retriever", mapped[1].Row.LayerName)
	}
	if mapped[0].Row.OperationName != nil && mapped[1].Row.OperationName != nil &&
		*mapped[0].Row.OperationName != *mapped[1].Row.OperationName {
		t.Errorf("kedua span seharusnya operation_name SAMA ('chat') meski layer_name beda")
	}
}

func TestMapTraces_AnchorSpanMembawaSessionDanTurnIndex(t *testing.T) {
	td := ptrace.NewTraces()
	rs := td.ResourceSpans().AppendEmpty()
	ss := rs.ScopeSpans().AppendEmpty()
	ss.Scope().SetName("orchestration")
	span := addSpan(ss, 2, 1, "invoke_agent", time.Now())
	span.Attributes().PutStr("session.id", "sess-1")
	span.Attributes().PutInt("turn.index", 1)

	mapped, err := MapTraces(td)
	if err != nil {
		t.Fatalf("MapTraces error: %v", err)
	}
	if !mapped[0].isAnchor() {
		t.Errorf("span dengan session.id+turn.index harus terdeteksi sebagai anchor")
	}
	if *mapped[0].SessionID != "sess-1" || *mapped[0].TurnIndex != 1 {
		t.Errorf("session_id/turn_index salah: %v/%v", *mapped[0].SessionID, *mapped[0].TurnIndex)
	}
}

func TestMapTraces_SpanBiasaBukanAnchor(t *testing.T) {
	td := ptrace.NewTraces()
	rs := td.ResourceSpans().AppendEmpty()
	ss := rs.ScopeSpans().AppendEmpty()
	ss.Scope().SetName("domain_gate.otorisasi")
	addSpan(ss, 3, 1, "authorization.check", time.Now())

	mapped, err := MapTraces(td)
	if err != nil {
		t.Fatalf("MapTraces error: %v", err)
	}
	if mapped[0].isAnchor() {
		t.Errorf("span tanpa session.id/turn.index TIDAK boleh terdeteksi sebagai anchor")
	}
}

func TestMapSpan_TraceIDSpanIDHexEncodedStandarOTel(t *testing.T) {
	td := ptrace.NewTraces()
	rs := td.ResourceSpans().AppendEmpty()
	ss := rs.ScopeSpans().AppendEmpty()
	ss.Scope().SetName("execution.klasifikasi_respons")
	addSpan(ss, 0xAB, 0xCD, "execute_tool", time.Now())

	mapped, err := MapTraces(td)
	if err != nil {
		t.Fatalf("MapTraces error: %v", err)
	}
	row := mapped[0].Row
	if len(row.TraceID) != 32 {
		t.Errorf("trace_id harus 32 hex char, dapat %d: %s", len(row.TraceID), row.TraceID)
	}
	if len(row.SpanID) != 16 {
		t.Errorf("span_id harus 16 hex char, dapat %d: %s", len(row.SpanID), row.SpanID)
	}
	if _, err := hex.DecodeString(row.TraceID); err != nil {
		t.Errorf("trace_id bukan hex valid: %v", err)
	}
}

func TestMapSpan_ErrorTypeDariAttribute(t *testing.T) {
	td := ptrace.NewTraces()
	rs := td.ResourceSpans().AppendEmpty()
	ss := rs.ScopeSpans().AppendEmpty()
	ss.Scope().SetName("domain_gate.otorisasi")
	span := addSpan(ss, 4, 1, "authorization.check", time.Now())
	span.Attributes().PutStr("error.type", "ditolak_otorisasi")

	mapped, err := MapTraces(td)
	if err != nil {
		t.Fatalf("MapTraces error: %v", err)
	}
	if mapped[0].Row.ErrorType == nil || *mapped[0].Row.ErrorType != "ditolak_otorisasi" {
		t.Errorf("error_type harus 'ditolak_otorisasi', dapat %v", mapped[0].Row.ErrorType)
	}
}

func TestMapSpan_DurationMsDihitungDariStartEnd(t *testing.T) {
	td := ptrace.NewTraces()
	rs := td.ResourceSpans().AppendEmpty()
	ss := rs.ScopeSpans().AppendEmpty()
	ss.Scope().SetName("orchestration")
	addSpan(ss, 5, 1, "chat", time.Now())

	mapped, err := MapTraces(td)
	if err != nil {
		t.Fatalf("MapTraces error: %v", err)
	}
	if mapped[0].Row.DurationMs == nil || *mapped[0].Row.DurationMs != 100 {
		t.Errorf("duration_ms harus 100 (start+100ms=end), dapat %v", mapped[0].Row.DurationMs)
	}
}
