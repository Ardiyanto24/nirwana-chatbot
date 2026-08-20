# Logs — Milestone 6.1: Membangun Exporter Dasar yang Menulis ke Supabase

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan — user eksplisit meminta riset mendalam ("pastikan breakdown dulu detail") sebelum plan ditulis, konsisten pola yang sudah ditegakkan di M5.4.

**Apa yang dilakukan**
1. Baca `docs/02-implementation-plan/rancangan-custom-exporter-supabase.md` penuh (Lingkup+KK M6.1/M6.2, Catatan Ketidakpastian fallback sidecar Python, Catatan Serah Terima).
2. Cek lingkungan: `go version` → `command not found` (Go belum terinstal), `docker --version` → tersedia v29.2.1.
3. Baca `infra/observability/otel-collector-config.yaml`+`docker-compose.yml` existing — menemukan komentar placeholder "slot exporter kedua" (`otlphttp/supabase_exporter`, ditandai eksplisit "Bentuk contoh (belum aktif)").
4. 2 agent Explore dijalankan PARALEL (foreground):
   - Agent 1: riset kontrak span Bagian 2/3/4 `rancangan-observability-ai-chatbot.md`, atribut trace-level nyata di kode (`turn_pipeline.py`, `riwayat_percakapan.py`, `tracing.py`), kredensial existing (`provision_readonly_role.py` M5.2), catatan project-wide PIC 6.
   - Agent 2: riset teknis (WebSearch ke dokumentasi resmi OpenTelemetry) perbandingan native `ocb` exporter vs standalone Go OTLP listener — struktur kode, kompleksitas, bukti risiko version-pinning.
5. Grep manual lanjutan (bukan lewat agent) untuk presisi: seluruh `get_tracer(` call site di `src/` (42 lokasi) dan seluruh definisi `_TRACER_NAME`/`_RETRIEVER_TRACER_NAME` (29 nilai unik) — mengonfirmasi algoritma `layer_name = scope.Name` dipotong titik pertama.
6. Baca langsung `src/main.py` (baris 130-170) dan `src/orchestration/riwayat_percakapan.py` (penuh) — menemukan `riwayat.simpan` dibuka SETELAH `invoke_agent` `with`-block exit, tanpa context parent — gap arsitektur baru yang tidak diantisipasi sebelum riset ini.
7. Baca `src/schemas/orchestration.py` (`KeadaanTurn`) dan `src/orchestration/turn_pipeline.py` (baris 150-194) — mengonfirmasi pola `opentelemetry.context.attach()`/`detach()` sudah ada presedennya (M7.7) untuk dipakai ulang di perbaikan gap.
8. 4 `AskUserQuestion` diajukan lewat 2 putaran (arsitektur exporter+gap riwayat.simpan+toolchain Go dalam 1 putaran; nama folder+struktur repo di putaran terpisah setelah temuan lanjutan) — seluruhnya dijawab dengan opsi Rekomendasi.
9. Plan lengkap ditulis (Context+11 Keputusan+11 Checkpoint/20 Task), diajukan via `ExitPlanMode` — disetujui user.
10. `milestones/6.1-.../decisions.md` ditulis — 7 entri Jenis A (5 dari `AskUserQuestion`, 2 dari penalaran teknis dikonfirmasi lewat persetujuan plan) + 4 entri Jenis B (forced).

**Temuan**
- **Gap arsitektur `riwayat.simpan` (BARU, belum pernah tercatat manapun sebelumnya)**: span ini jadi TRACE AKAR TERPISAH dari `invoke_agent` (trace_id berbeda), bukan anak — dikonfirmasi kode langsung, bukan tebakan. Dikonfirmasi juga SPAN_DEFS seed M5.2/M5.3 memang tidak pernah memodelkan span ini sebagai bagian tree (tanpa disadari sebagai gap saat itu). Kalau dibiarkan, `traces.status` permanen NULL untuk data asli.
- **Algoritma `layer_name`/`operation_name` genuinely terpecahkan lewat riset**: `span.name()` TIDAK cukup (dipakai ulang ≥13 lokasi), disambiguator sesungguhnya adalah instrumentation scope name (`get_tracer()` argument), dikonfirmasi 29 nilai unik seluruhnya mengikuti pola `<layer>.<modul>` yang konsisten dengan 10 `layer_name` bucket yang sudah dipakai dashboard M5.1-5.4.
- **Ordering problem (BatchSpanProcessor + nested span semantics)**: `invoke_agent` (satu-satunya pembawa `session.id`/`turn.index`) SELALU berakhir belakangan dibanding anak-anaknya — memaksa strategi buffering, bukan cuma "nice to have".
- **`ocb` menggantikan SELURUH image Collector**, bukan komponen tempel — implikasi langsung: `builder-config.yaml` wajib mendaftarkan seluruh komponen existing (M5.1 spanmetrics dkk) atau berisiko regresi total.
- **`role_title` genuinely dead** sebagai span attribute di seluruh `src/` — dikonfirmasi grep menyeluruh, bukan asumsi.

**Error/Kegagalan (jika ada)**
Tidak ada error teknis pada tahap riset ini.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` lengkap 11 entri (7 Jenis A + 4 Jenis B), seluruh entri Jenis A memuat "Opsi yang Dipertimbangkan tapi Ditolak" sesuai `template-decisions.md`. Daftar Isi Keputusan mencakup seluruh 11 entri dengan checkpoint terkait.

**Commit:** `1c3712f` — `docs(milestone-6.1): keputusan desain exporter dasar Supabase`

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada — seluruh riset dan klarifikasi (termasuk 2 putaran `AskUserQuestion`) terjadi SEBELUM Checkpoint 1 resmi dimulai (bagian dari "Rencanakan sebelum mengimplementasikan"), dicatat sebagai bagian narasi Task 1 di atas.
