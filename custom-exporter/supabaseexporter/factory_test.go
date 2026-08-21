package supabaseexporter

import (
	"testing"
	"time"

	"go.opentelemetry.io/collector/confmap"
)

// TestCreateDefaultConfig_RetryQueueDefaultsResmi memverifikasi
// createDefaultConfig() memakai nilai default RESMI exporterhelper
// (configretry.NewDefaultBackOffConfig()/exporterhelper.NewDefaultQueueConfig())
// sesuai decisions.md M6.2 Keputusan 1 - bukan nilai custom buatan sendiri.
func TestCreateDefaultConfig_RetryQueueDefaultsResmi(t *testing.T) {
	cfg, ok := createDefaultConfig().(*Config)
	if !ok {
		t.Fatalf("createDefaultConfig() bukan *Config")
	}

	if !cfg.RetrySettings.Enabled {
		t.Errorf("retry harus enabled by default, dapat %v", cfg.RetrySettings.Enabled)
	}
	if cfg.RetrySettings.InitialInterval != 5*time.Second {
		t.Errorf("InitialInterval default harus 5s, dapat %v", cfg.RetrySettings.InitialInterval)
	}
	if cfg.RetrySettings.MaxElapsedTime != 5*time.Minute {
		t.Errorf("MaxElapsedTime default harus 5m, dapat %v", cfg.RetrySettings.MaxElapsedTime)
	}

	if !cfg.QueueSettings.HasValue() {
		t.Fatalf("queue harus enabled by default (HasValue), dapat kosong")
	}
	q := cfg.QueueSettings.Get()
	if q.NumConsumers != 10 {
		t.Errorf("NumConsumers default harus 10 (Keputusan 5, TIDAK diturunkan paksa), dapat %d", q.NumConsumers)
	}
	if q.QueueSize != 1000 {
		t.Errorf("QueueSize default harus 1000, dapat %d", q.QueueSize)
	}

	if cfg.BufferEvictionTTL != 60*time.Minute {
		t.Errorf("BufferEvictionTTL default harus 60 menit (Keputusan 3), dapat %v", cfg.BufferEvictionTTL)
	}
}

// TestConfig_UnmarshalYAMLOverrideSebagianSajaMempertahankanDefaultLain
// mereplikasi persis alur nyata Collector: mulai dari createDefaultConfig(),
// lalu confmap.Unmarshal() YAML di atasnya - field yang TIDAK disebut di
// YAML harus tetap default, field yang disebut harus ter-override. Ini
// membuktikan Keputusan 1 (YAML-configurable) genuinely bekerja tanpa
// logic fallback manual buatan sendiri (confmap yang menangani merge).
func TestConfig_UnmarshalYAMLOverrideSebagianSajaMempertahankanDefaultLain(t *testing.T) {
	cfg := createDefaultConfig().(*Config)
	cfg.DSN = "postgres://default-tidak-terpakai"

	conf := confmap.NewFromStringMap(map[string]any{
		"dsn": "postgres://dari-yaml",
		"retry_on_failure": map[string]any{
			"max_elapsed_time": "10m",
		},
		"sending_queue": map[string]any{
			"num_consumers": 4,
		},
		"buffer_eviction_ttl": "30m",
	})

	if err := conf.Unmarshal(cfg); err != nil {
		t.Fatalf("Unmarshal error: %v", err)
	}

	if cfg.DSN != "postgres://dari-yaml" {
		t.Errorf("DSN harus ter-override YAML, dapat %q", cfg.DSN)
	}
	if cfg.RetrySettings.MaxElapsedTime != 10*time.Minute {
		t.Errorf("MaxElapsedTime harus ter-override jadi 10m, dapat %v", cfg.RetrySettings.MaxElapsedTime)
	}
	// InitialInterval TIDAK disebut di YAML - harus tetap default 5s.
	if cfg.RetrySettings.InitialInterval != 5*time.Second {
		t.Errorf("InitialInterval TIDAK disebut YAML, harus tetap default 5s, dapat %v", cfg.RetrySettings.InitialInterval)
	}
	if cfg.QueueSettings.Get() == nil {
		t.Fatalf("QueueSettings harus tetap terisi setelah Unmarshal")
	}
	if cfg.QueueSettings.Get().NumConsumers != 4 {
		t.Errorf("NumConsumers harus ter-override jadi 4, dapat %d", cfg.QueueSettings.Get().NumConsumers)
	}
	// QueueSize TIDAK disebut YAML - harus tetap default 1000.
	if cfg.QueueSettings.Get().QueueSize != 1000 {
		t.Errorf("QueueSize TIDAK disebut YAML, harus tetap default 1000, dapat %d", cfg.QueueSettings.Get().QueueSize)
	}
	if cfg.BufferEvictionTTL != 30*time.Minute {
		t.Errorf("BufferEvictionTTL harus ter-override jadi 30m, dapat %v", cfg.BufferEvictionTTL)
	}
}

func TestConfig_ValidateDSNKosongDitolak(t *testing.T) {
	cfg := createDefaultConfig().(*Config)
	cfg.DSN = ""
	if err := cfg.Validate(); err == nil {
		t.Errorf("Validate() harus error saat DSN kosong")
	}
}

func TestConfig_ValidateBufferEvictionTTLNolAtauNegatifDitolak(t *testing.T) {
	cfg := createDefaultConfig().(*Config)
	cfg.DSN = "postgres://valid"
	cfg.BufferEvictionTTL = 0
	if err := cfg.Validate(); err == nil {
		t.Errorf("Validate() harus error saat BufferEvictionTTL 0")
	}

	cfg.BufferEvictionTTL = -1 * time.Minute
	if err := cfg.Validate(); err == nil {
		t.Errorf("Validate() harus error saat BufferEvictionTTL negatif")
	}
}

func TestConfig_ValidateKombinasiValidLolos(t *testing.T) {
	cfg := createDefaultConfig().(*Config)
	cfg.DSN = "postgres://valid"
	if err := cfg.Validate(); err != nil {
		t.Errorf("Validate() TIDAK boleh error untuk config default+DSN valid, dapat: %v", err)
	}
}
