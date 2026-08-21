package supabaseexporter

import (
	"context"
	"errors"

	"go.opentelemetry.io/collector/component"
	"go.opentelemetry.io/collector/exporter"
	"go.opentelemetry.io/collector/exporter/exporterhelper"
	"go.opentelemetry.io/collector/pdata/ptrace"
)

const typeStr = "supabase"

// Config - satu-satunya field yang dibutuhkan M6.1 (DSN Postgres role
// nirwana_exporter_writer, Checkpoint 4). Retry/batching/queue config
// (M6.2) belum ditambahkan di sini - Lingkup M6.1 sengaja "jalur data
// paling sederhana".
type Config struct {
	DSN string `mapstructure:"dsn"`
}

func (c *Config) Validate() error {
	if c.DSN == "" {
		return errors.New("dsn wajib diisi (connection string role nirwana_exporter_writer)")
	}
	return nil
}

func createDefaultConfig() component.Config {
	return &Config{}
}

// NewFactory mendaftarkan exporter "supabase" ke OTel Collector -
// dipanggil builder-config.yaml (Checkpoint 8 Task 14) lewat ocb.
func NewFactory() exporter.Factory {
	return exporter.NewFactory(
		component.MustNewType(typeStr),
		createDefaultConfig,
		exporter.WithTraces(createTracesExporter, component.StabilityLevelDevelopment),
	)
}

type tracesExporter struct {
	storage *Storage
	buffer  *Buffer
}

func createTracesExporter(ctx context.Context, set exporter.Settings, cfg component.Config) (exporter.Traces, error) {
	c, ok := cfg.(*Config)
	if !ok {
		return nil, errors.New("tipe config tidak sesuai, harus *supabaseexporter.Config")
	}

	storage, err := NewStorage(ctx, c.DSN)
	if err != nil {
		return nil, err
	}

	te := &tracesExporter{storage: storage, buffer: NewBuffer(storage, set.TelemetrySettings.Logger)}

	return exporterhelper.NewTraces(ctx, set, cfg, te.pushTraces,
		exporterhelper.WithShutdown(te.shutdown),
	)
}

// pushTraces adalah jalur data utama (KK1+KK2 M6.1) - map batch span jadi
// mappedSpan (mapping.go), lalu serahkan tiap span ke Buffer (buffer.go)
// yang menangani urutan traces-sebelum-spans.
//
// SENGAJA TIDAK return err di tengah loop (beda dari desain awal) - satu
// batch dari `batch` processor Collector bisa membawa span dari BEBERAPA
// trace_id sekaligus; berhenti di kegagalan span PERTAMA membuang seluruh
// SISA span dalam batch yang sama tanpa pernah dicoba sama sekali,
// termasuk span trace_id LAIN yang tidak ada hubungannya dengan span yang
// gagal (ditemukan verifikasi produksi M6.1 - trace berisi 23 span
// berakhir 0 baris di Supabase gara-gara SATU span gagal di tengah
// loop). errors.Join mengumpulkan seluruh kegagalan supaya Collector
// tetap tahu batch ini bermasalah (metrik/log), tanpa mengorbankan span
// lain yang genuinely insertable.
func (te *tracesExporter) pushTraces(ctx context.Context, td ptrace.Traces) error {
	mapped, err := MapTraces(td)
	if err != nil {
		return err
	}
	var errs []error
	for _, ms := range mapped {
		if err := te.buffer.Ingest(ctx, ms); err != nil {
			errs = append(errs, err)
		}
	}
	return errors.Join(errs...)
}

func (te *tracesExporter) shutdown(context.Context) error {
	te.storage.Close()
	return nil
}
