// Package supabaseexporter menulis span OTel Collector ke tabel
// traces/spans Supabase (Milestone 6.1, PIC 6). storage.go berisi lapisan
// data murni: struct row + fungsi pembangun SQL (testable tanpa koneksi
// nyata, decisions.md Checkpoint 5 Task 8) + wrapper method Storage yang
// menjalankan query lewat pgx (driver Postgres Go, decisions.md
// Keputusan 9).
package supabaseexporter

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// TraceRow mirrors kontrak tabel `traces` (Bagian 4
// rancangan-observability-ai-chatbot.md, PERSIS src/db/models.py
// TraceRow M5.2) - satu baris per trace (= satu turn user).
type TraceRow struct {
	TraceID   string
	SessionID string
	TurnIndex int
	StartedAt time.Time
	EndedAt   *time.Time
	Status    *string
	RoleTitle *string
}

// SpanRow mirrors kontrak tabel `spans` - satu baris per span. Attributes
// disimpan SUDAH dalam bentuk JSON string (bukan map[string]any) - proses
// marshal terjadi di layer pemetaan (Checkpoint 6, mapping.go), supaya
// storage.go murni concern penyimpanan, tidak menangani error marshal.
type SpanRow struct {
	SpanID        string
	TraceID       string
	ParentSpanID  *string
	LayerName     string
	OperationName *string
	StartedAt     time.Time
	EndedAt       *time.Time
	DurationMs    *int
	ErrorType     *string
	Attributes    string
}

// traceUpsertArgs membangun SQL+args UPSERT traces - ON CONFLICT DO UPDATE
// (bukan DO NOTHING) supaya pengiriman ulang span yang sama (SDK retry)
// tidak gagal, dan field yang sebelumnya NULL (mis. status, terisi
// belakangan saat span riwayat.simpan tiba - lihat strategi buffering
// Checkpoint 7) bisa terisi tanpa menimpa nilai yang sudah ada dengan
// NULL (COALESCE mempertahankan nilai lama kalau nilai baru NULL).
func traceUpsertArgs(t TraceRow) (string, []any) {
	sql := `INSERT INTO traces (trace_id, session_id, turn_index, started_at, ended_at, status, role_title)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (trace_id) DO UPDATE SET
  ended_at = COALESCE(EXCLUDED.ended_at, traces.ended_at),
  status = COALESCE(EXCLUDED.status, traces.status),
  role_title = COALESCE(EXCLUDED.role_title, traces.role_title)`
	args := []any{t.TraceID, t.SessionID, t.TurnIndex, t.StartedAt, t.EndedAt, t.Status, t.RoleTitle}
	return sql, args
}

// spanInsertArgs membangun SQL+args INSERT spans - ON CONFLICT DO NOTHING
// (bukan DO UPDATE) karena span_id unik per span dan datanya tidak pernah
// berubah setelah diekspor (beda dari traces yang genuinely bisa
// diperbarui bertahap).
func spanInsertArgs(s SpanRow) (string, []any) {
	sql := `INSERT INTO spans (span_id, trace_id, parent_span_id, layer_name, operation_name, started_at, ended_at, duration_ms, error_type, attributes)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
ON CONFLICT (span_id) DO NOTHING`
	args := []any{
		s.SpanID, s.TraceID, s.ParentSpanID, s.LayerName, s.OperationName,
		s.StartedAt, s.EndedAt, s.DurationMs, s.ErrorType, s.Attributes,
	}
	return sql, args
}

// Storage membungkus pool koneksi pgx yang di-scope kredensial write-only
// exporter (nirwana_exporter_writer, Milestone 6.1 Checkpoint 4 - GRANT
// SELECT+INSERT saja pada traces/spans).
type Storage struct {
	pool *pgxpool.Pool
}

func NewStorage(ctx context.Context, dsn string) (*Storage, error) {
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, err
	}
	return &Storage{pool: pool}, nil
}

func (s *Storage) Close() {
	s.pool.Close()
}

func (s *Storage) UpsertTrace(ctx context.Context, t TraceRow) error {
	sql, args := traceUpsertArgs(t)
	_, err := s.pool.Exec(ctx, sql, args...)
	return err
}

func (s *Storage) InsertSpan(ctx context.Context, sp SpanRow) error {
	sql, args := spanInsertArgs(sp)
	_, err := s.pool.Exec(ctx, sql, args...)
	return err
}

// TraceExists mengecek apakah baris traces untuk trace_id ini sudah ada -
// dipakai strategi buffering Checkpoint 7 untuk memutuskan apakah span
// yang baru tiba boleh langsung di-INSERT atau perlu ditahan dulu.
func (s *Storage) TraceExists(ctx context.Context, traceID string) (bool, error) {
	var exists bool
	err := s.pool.QueryRow(ctx, "SELECT EXISTS(SELECT 1 FROM traces WHERE trace_id = $1)", traceID).Scan(&exists)
	return exists, err
}
