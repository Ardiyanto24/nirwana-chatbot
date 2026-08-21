package supabaseexporter

import (
	"context"
	"errors"
	"time"

	"go.opentelemetry.io/collector/component"
	"go.opentelemetry.io/collector/config/configoptional"
	"go.opentelemetry.io/collector/config/configretry"
	"go.opentelemetry.io/collector/exporter"
	"go.opentelemetry.io/collector/exporter/exporterhelper"
	"go.opentelemetry.io/collector/pdata/ptrace"
)

const typeStr = "supabase"

// Config M6.2 - DSN (M6.1) + retry/queue (M6.2, decisions.md Keputusan 1).
// RetrySettings/QueueSettings memakai TIPE RESMI configretry/exporterhelper
// langsung (bukan field custom flat per-parameter) - field-name mapstructure
// (`retry_on_failure`/`sending_queue`) konsisten konvensi SELURUH exporter
// resmi OTel Collector (mis. otlpexporter), dan confmap sudah menangani
// merge default<-override YAML otomatis untuk kedua tipe ini tanpa perlu
// logic fallback manual (lihat createDefaultConfig()). BufferEvictionTTL
// (Keputusan 3, default 60 menit) diteruskan ke Buffer di Checkpoint 4.
type Config struct {
	DSN               string                                                   `mapstructure:"dsn"`
	RetrySettings     configretry.BackOffConfig                                `mapstructure:"retry_on_failure"`
	QueueSettings     configoptional.Optional[exporterhelper.QueueBatchConfig] `mapstructure:"sending_queue"`
	BufferEvictionTTL time.Duration                                            `mapstructure:"buffer_eviction_ttl"`
}

func (c *Config) Validate() error {
	if c.DSN == "" {
		return errors.New("dsn wajib diisi (connection string role nirwana_exporter_writer)")
	}
	if c.BufferEvictionTTL <= 0 {
		return errors.New("buffer_eviction_ttl wajib positif")
	}
	return nil
}

// createDefaultConfig menetapkan default resmi exporterhelper untuk retry
// (Enabled=true, InitialInterval=5s, MaxInterval=30s, MaxElapsedTime=5m -
// configretry.NewDefaultBackOffConfig()) dan queue (QueueSize=1000,
// NumConsumers=10 - exporterhelper.NewDefaultQueueConfig(), Keputusan 5
// TIDAK diturunkan paksa) - YAML exporters.supabase HANYA perlu mengisi
// field yang ingin di-override, sisanya otomatis pakai nilai ini (confmap
// merge, bukan logic manual).
func createDefaultConfig() component.Config {
	return &Config{
		RetrySettings:     configretry.NewDefaultBackOffConfig(),
		QueueSettings:     configoptional.Some(exporterhelper.NewDefaultQueueConfig()),
		BufferEvictionTTL: 60 * time.Minute,
	}
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

	te := &tracesExporter{storage: storage, buffer: NewBuffer(storage, set.TelemetrySettings.Logger, c.BufferEvictionTTL)}

	return exporterhelper.NewTraces(ctx, set, cfg, te.pushTraces,
		exporterhelper.WithShutdown(te.shutdown),
		exporterhelper.WithRetry(c.RetrySettings),
		exporterhelper.WithQueue(c.QueueSettings),
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
	te.buffer.Stop()
	te.storage.Close()
	return nil
}
