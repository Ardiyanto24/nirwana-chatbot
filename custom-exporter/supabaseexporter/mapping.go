package supabaseexporter

import (
	"encoding/hex"
	"encoding/json"
	"strings"

	"go.opentelemetry.io/collector/pdata/ptrace"
)

// layerNameFromScope menurunkan layer_name dari InstrumentationScope.Name
// (argumen get_tracer() Python, `scope_spans[].scope.name` di wire OTLP) -
// BUKAN dari span.Name() yang terbukti dipakai ulang >=13 lokasi lintas
// layer (mis. "chat"). Grep menyeluruh 29 nilai _TRACER_NAME di src/
// mengonfirmasi pola SELALU "<layer>" atau "<layer>.<modul>" (decisions.md
// Keputusan Jenis B, Temuan A riset M6.1).
func layerNameFromScope(scopeName string) string {
	if idx := strings.Index(scopeName, "."); idx != -1 {
		return scopeName[:idx]
	}
	return scopeName
}

// mapSpan mengonversi satu span OTel (+ nama scope induknya) jadi SpanRow
// siap simpan.
func mapSpan(scopeName string, span ptrace.Span) (SpanRow, error) {
	traceID := span.TraceID()
	spanID := span.SpanID()
	parentID := span.ParentSpanID()

	startedAt := span.StartTimestamp().AsTime()

	row := SpanRow{
		// hex.EncodeToString, BUKAN TraceID.String()/SpanID.String() -
		// docstring resmi pdata (pcommon/traceid.go) eksplisit menyarankan
		// ini untuk representasi identifier, String() murni untuk display
		// (decisions.md Keputusan 10).
		SpanID:    hex.EncodeToString(spanID[:]),
		TraceID:   hex.EncodeToString(traceID[:]),
		LayerName: layerNameFromScope(scopeName),
		StartedAt: startedAt,
	}

	name := span.Name()
	row.OperationName = &name

	if endedAt := span.EndTimestamp().AsTime(); !endedAt.IsZero() && endedAt.After(startedAt) {
		e := endedAt
		row.EndedAt = &e
		durationMs := int(endedAt.Sub(startedAt).Milliseconds())
		row.DurationMs = &durationMs
	}

	if !parentID.IsEmpty() {
		parentHex := hex.EncodeToString(parentID[:])
		row.ParentSpanID = &parentHex
	}

	attrs := span.Attributes().AsRaw()
	if raw, ok := attrs["error.type"]; ok {
		if s, ok := raw.(string); ok && s != "" {
			row.ErrorType = &s
		}
	}

	attrJSON, err := json.Marshal(attrs)
	if err != nil {
		return SpanRow{}, err
	}
	row.Attributes = string(attrJSON)

	return row, nil
}

// mappedSpan pasangan SpanRow dengan penanda apakah span ini "anchor" -
// span pembawa session.id+turn.index (satu-satunya sumber trace-level
// session_id/turn_index yang WAJIB ada untuk baris `traces`, lihat
// decisions.md Keputusan 6 "Strategi Buffering").
type mappedSpan struct {
	Row       SpanRow
	SessionID *string
	TurnIndex *int
	Status    *string
}

// MapTraces mengonversi satu batch ptrace.Traces (bisa berisi banyak
// trace_id sekaligus, sesuai batching Collector) jadi daftar mappedSpan -
// murni transformasi data, TIDAK menyentuh Storage/DB (testable tanpa
// koneksi nyata, mirror pola storage.go).
func MapTraces(td ptrace.Traces) ([]mappedSpan, error) {
	var results []mappedSpan

	for _, rs := range td.ResourceSpans().All() {
		for _, ss := range rs.ScopeSpans().All() {
			scopeName := ss.Scope().Name()
			for _, span := range ss.Spans().All() {
				row, err := mapSpan(scopeName, span)
				if err != nil {
					return nil, err
				}

				ms := mappedSpan{Row: row}
				attrs := span.Attributes()
				if v, ok := attrs.Get("session.id"); ok {
					s := v.AsString()
					ms.SessionID = &s
				}
				if v, ok := attrs.Get("turn.index"); ok {
					n := int(v.Int())
					ms.TurnIndex = &n
				}
				if v, ok := attrs.Get("riwayat.status"); ok {
					s := v.AsString()
					ms.Status = &s
				}

				results = append(results, ms)
			}
		}
	}

	return results, nil
}

// isAnchor: span ini membawa identitas trace-level lengkap (session.id +
// turn.index) yang dibutuhkan untuk membuat baris `traces` - forced
// senantiasa TRUE hanya untuk span invoke_agent (satu-satunya span yang
// men-set kedua atribut ini, turn_pipeline.py:180-186).
func (m mappedSpan) isAnchor() bool {
	return m.SessionID != nil && m.TurnIndex != nil
}
