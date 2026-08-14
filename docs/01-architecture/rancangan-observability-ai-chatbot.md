# Rancangan Arsitektur Observability — AI Chatbot RBAC

**Nirwana Hospitality Group — AI Chatbot Serving Layer**

| | |
|---|---|
| **Dokumen induk** | `arsitektur-ai-chatbot-rbac.md` |
| **Tujuan dokumen** | Mengunci kontrak observability (skema span, arsitektur pipeline, skema penyimpanan) sebagai rujukan bersama SEBELUM dokumen panduan per-PIC ditulis — karena observability menyisipkan instrumentasi ke *dalam* implementasi semua PIC lain, bukan berdiri di sampingnya |
| **Status** | Rancangan awal — kontrak ini boleh direvisi selama implementasi, tapi perubahan wajib dikomunikasikan ke seluruh PIC yang bergantung padanya (lihat Bagian 5) |
| **Standar yang diikuti** | OpenTelemetry (OTel) — traces, metrics, logs. Konvensi atribut GenAI (`gen_ai.*`) mengikuti OpenTelemetry GenAI Semantic Conventions. **Konvensi ini masih pre-stable/eksperimental** (belum rilis 1.0, nama atribut bisa berubah) — versi yang jadi acuan pembangunan perlu dikunci eksplisit oleh PIC 1 saat setup, dicatat di kode (bukan cuma di dokumen ini). |

---

## 1. Prinsip Fondasi

1. **Instrumentasi sekali, backend fleksibel.** Aplikasi (9 layer) mengekspor telemetri lewat OTel SDK ke Collector lokal via OTLP. Aplikasi tidak pernah tahu atau peduli backend akhirnya Jaeger, Prometheus, atau Supabase — mengganti/menambah backend adalah perubahan konfigurasi Collector, bukan perubahan kode 9 layer.
2. **Dua tujuan, satu pipeline sumber.** Ada dua "konsumen" telemetri dengan sifat berbeda:
   - **Privat** (Jaeger + Prometheus + Grafana) — tooling debugging teknis untuk pemilik project, granular, tidak dipublikasikan.
   - **Publik** (Supabase + Next.js) — dashboard yang bisa diakses siapa saja sebagai bukti sistem berjalan dan diawasi, **isinya identik** dengan yang privat (bukan versi ringkas/redaksi) — alasan pemisahan murni operasional (keterbatasan publish gratis di Grafana Cloud, bukan alasan privasi data).
   - Kedua tujuan menerima **span yang sama persis** dari Collector (fan-out), bukan salah satu "diturunkan" dari yang lain.
3. **Default aman untuk konten sensitif.** Mengikuti default resmi OTel GenAI: instruksi, input, dan output LLM **tidak** direkam sebagai isi span secara default. Yang direkam adalah metadata terstruktur (model, token, status, durasi) — bukan teks mentah pertanyaan/jawaban yang berpotensi memuat PII (nama tamu, data payroll, dsb). Ini berlaku sama baik untuk jalur privat maupun publik.
4. **Satu trace per turn.** Seluruh 9 layer yang dilalui satu turn user berbagi satu `trace_id`, memakai `gen_ai.conversation.id` (diisi `session_id`) untuk mengaitkan lintas-turn dalam satu sesi.

---

## 2. Kontrak Span per Layer

Span dibungkus satu span induk `invoke_agent` per turn (operasi orkestrasi keseluruhan), berisi span anak sesuai layer yang dilalui.

| Layer | `gen_ai.operation.name` / jenis span | Atribut kunci |
|---|---|---|
| Input Layer | `input.validate` (non-LLM) | `session.id`, `turn.index` |
| Context Resolution — Langkah 2 (Pemetaan Ketergantungan) | `chat` | `gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens`, referensi `{session_id, turn_index}` yang dirujuk (bila ada) |
| Context Resolution — Langkah 3a (Rewrite) | `chat` | sama seperti di atas |
| Context Resolution — Langkah 3b (Tarik Session Memory) | `memory.retrieve` (non-LLM) | `session.id`, `turn.index` yang diquery, jumlah atomic intent ditemukan |
| Context Resolution — Langkah 7 (Pencocokan) | custom, non-LLM atau `chat` (tergantung mekanisme final — lihat status KERANGKA AWAL di dokumen induk) | jumlah atomic intent cocok/tidak cocok |
| Decomposition (Klasifikasi, Pemecahan, Verifikasi) | `chat` ×3 | + `intent.count`, `intent.relation_type` |
| Domain Gate | `chat` (identifikasi + verifikasi titik buta) + span non-LLM (lookup otorisasi) | + `rbac.domain`, `rbac.decision` (`allow`/`deny`), `error.type=ditolak_otorisasi` bila ditolak, penanda constraint cakupan-individu bila terdeteksi |
| Retriever | `chat` (kecocokan makna) + span pencarian (`gen_ai.retrieval.documents`) | + `retrieval.candidates_count`, `retrieval.selected_view` |
| Query Engine (Langkah 1 & 2) | `chat` ×2 | + `request.domain`, `request.view_name` |
| Verification Gate | span non-LLM (deterministik) | `error.type` bila gagal, `verification.check_name` |
| Execution | `execute_tool` | `http.response.status_code`, `error.type` (`400`/`403`/`404`/`5xx`/timeout), retry count |
| Interpretation (Narasi, Verifikasi Kesetiaan) | `chat` ×2 | `gen_ai.usage.*`, `narrative.turn_reference` (mengacu field `sumber` dari paket Session Memory) |

**Prinsip pengisian `error.type`**: nilainya mengikuti skema `status` yang sudah dikunci di dokumen arsitektur induk (`berhasil`/`sebagian`/`ditolak_otorisasi`/`gagal_teknis`/`terblokir_ketergantungan`) — satu kosakata yang sama dipakai baik di paket Session Memory maupun di span, supaya tidak ada dua "bahasa status" berbeda di sistem yang sama.

---

## 3. Arsitektur Pipeline

```
┌─────────────────────────────────────────────────────┐
│  9 Layer AI Chatbot (PIC 1-4)                              │
│  OTel SDK Python, emit span sesuai Bagian 2                    │
└─────────────────────────────────────────────────────┘
        │  OTLP/gRPC → localhost:4317 (endpoint disediakan
        │  PIC 1 sebagai bagian fondasi bersama)
        ▼
┌─────────────────────────────────────────────────────┐
│  OTel Collector  (fondasi bersama, dibangun PIC 1)               │
│  Receiver: OTLP  →  Processor: batch, memory_limiter,               │
│  attributes (enrichment)  →  Exporter: FAN-OUT ke 2 jalur                  │
└─────────────────────────────────────────────────────┘
        │                                    │
        ▼                                    ▼
┌──────────────────────┐      ┌──────────────────────────┐
│  JALUR PRIVAT              │      │  JALUR PUBLIK                       │
│  Exporter OTLP resmi          │      │  Custom Exporter (Go, PIC 6)             │
│  → Jaeger (trace)                │      │  → Supabase (Postgres)                     │
│  → Prometheus (metrics)             │      │  Skema HIERARKIS: tabel `traces`,                │
│  → Grafana (visualisasi,                │      │  tabel `spans` (spans.trace_id →                    │
│    akses privat pemilik project)              │      │  traces.id, spans.parent_span_id                        │
└──────────────────────┘      │  → spans.id, self-referencing)                          │
                                  └──────────────────────────┘
                                              │
                                              ▼
                                  ┌──────────────────────┐
                                  │  Next.js Dashboard Publik   │
                                  │  Query Supabase langsung,          │
                                  │  render:                                │
                                  │  • Daftar trace per turn/sesi              │
                                  │  • Waterfall view per trace                    │
                                  │    (durasi tiap span, urutan,                       │
                                  │    parent-child)                                        │
                                  │  • Metrics agregat (turunan dari                          │
                                  │    tabel spans, atau tabel ringkasan                             │
                                  │    terpisah bila query on-the-fly                                  │
                                  │    terlalu berat)                                                       │
                                  └──────────────────────┘
```

**Fallback eksplisit yang disepakati**: bila PIC 6 (Custom Exporter Go) menjadi bottleneck waktu yang tidak kunjung selesai, jalur publik dapat digantikan pendekatan sidecar Python (proses terpisah yang menerima OTLP secara paralel ke Collector, decode, lalu tulis langsung ke Supabase) — tanpa mengubah kontrak span di Bagian 2 maupun skema Supabase di Bagian 4. Keputusan pindah jalur ini tidak mempengaruhi PIC 1-5.

---

## 4. Skema Penyimpanan Supabase (Jalur Publik)

Bentuk hierarkis, mencerminkan struktur trace OTel (bukan tabel flat):

```sql
-- Satu baris per trace (= satu turn user)
traces (
  trace_id        text primary key,
  session_id      text not null,
  turn_index      int not null,
  started_at      timestamptz not null,
  ended_at        timestamptz,
  status          text,  -- status akhir turn: berhasil/sebagian/ditolak_otorisasi/
                          -- gagal_teknis/terblokir_ketergantungan
  role_title      text   -- untuk analisis distribusi, BUKAN identitas personal
)

-- Satu baris per span (banyak per trace)
spans (
  span_id         text primary key,
  trace_id        text references traces(trace_id),
  parent_span_id  text references spans(span_id),  -- null untuk span akar (invoke_agent)
  layer_name      text not null,  -- mis. "domain_gate", "retriever"
  operation_name  text,           -- gen_ai.operation.name, mis. "chat", "execute_tool"
  started_at      timestamptz not null,
  ended_at        timestamptz,
  duration_ms     int,
  error_type      text,           -- null bila sukses
  attributes      jsonb           -- atribut tambahan sesuai Bagian 2 per layer
)
```

**Catatan implementasi**: PIC 6 dan PIC 5 perlu menyepakati skema ini sebagai kontrak sejak awal — PIC 5 dapat mulai membangun UI Next.js dengan data dummy mengikuti skema ini, tanpa menunggu PIC 6 selesai, karena bentuk tabelnya sudah tetap.

---

## 5. Dependensi Antar-PIC untuk Observability

- **PIC 1** menyediakan endpoint OTLP Collector sebagai bagian fondasi deployment bersama — prasyarat sebelum PIC 2-4 dapat mengirim span apa pun.
- **PIC 2, 3, 4** wajib menginstrumentasi layer masing-masing sesuai kontrak Bagian 2 sebagai bagian dari definisi "selesai" pekerjaan mereka — bukan pekerjaan tambahan di akhir.
- **PIC 6** bergantung pada kontrak span final (Bagian 2) untuk menentukan pemetaan atribut ke skema Supabase (Bagian 4).
- **PIC 5** bergantung pada skema Supabase (Bagian 4) yang sudah stabil, tapi dapat mulai bekerja paralel dengan data dummy mengikuti skema yang sama.
- Perubahan pada Bagian 2 (kontrak span) di kemudian hari **wajib dikomunikasikan** ke PIC 6 (pemetaan skema) dan PIC 5 (kemungkinan field baru untuk ditampilkan) — pola yang sama seperti "Catatan Serah Terima" di dokumen pembanding project data platform.
