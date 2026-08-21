# Decisions — Milestone 6.1: Membangun Exporter Dasar yang Menulis ke Supabase

Milestone pertama PIC 6 (Custom Exporter Supabase, Go) — satu-satunya pekerjaan project ini di luar Python. Plan sempat melalui riset mendalam (2 agent Explore paralel + pembacaan kode langsung ke `src/`) sebelum diajukan, dengan 6 keputusan genuinely terbuka diajukan ke user lewat 2 putaran `AskUserQuestion`.

---

### Keputusan 1: Arsitektur Exporter — Native OTel Collector Component via `ocb`

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion` putaran 1).

**Latar Belakang**
Dokumen sumber (`rancangan-custom-exporter-supabase.md`) secara literal meminta "komponen exporter yang mengimplementasikan interface exporter milik OTel Collector... dikompilasi bersama Collector lewat OpenTelemetry Collector Builder atau setara". Riset (agent Explore, WebSearch ke dokumentasi resmi OpenTelemetry) menemukan alternatif nyata: standalone Go service yang mendengarkan OTLP langsung (paket `pdata/ptrace/ptraceotlp` resmi, TANPA `ocb`) — arsitektur ini identik dengan "sidecar Python" yang disebut dokumen sumber sebagai fallback resmi, hanya ditulis Go sejak awal. Genuinely terbuka karena kedua jalur sama-sama valid secara teknis dengan trade-off nyata dan terverifikasi (bukan spekulasi).

**Keputusan yang Dipilih**
Native OTel Collector exporter component, dikompilasi via `ocb` (OpenTelemetry Collector Builder) jadi satu distribusi Collector custom.

**Alasan**
Sesuai literal niat dokumen sumber dan nilai portofolio yang disebutkan eksplisit ("kontribusi ke tingkat internal Collector, bukan sekadar proxy sederhana", `rancangan-custom-exporter-supabase.md` baris 67). Risiko nyata (version-pinning ketat `otelcol_version`/`exporterhelper`/`pdata`, breaking change terdokumentasi sering terjadi di `CHANGELOG-API.md` resmi, tidak ada tutorial resmi "build an exporter") dimitigasi via Checkpoint 3 sebagai *fast-fail gate* — skeleton kosong dibuktikan kompilasi+jalan SEBELUM logic Supabase ditulis, supaya kalau memang macet, keputusan pindah ke fallback bisa diambil SEBELUM sunk cost besar tertanam.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Standalone Go OTLP listener ("Go sidecar")** — dependency jauh lebih ringan (`pdata`+`grpc` biasa, tanpa `ocb`, tanpa version-pinning ketat, tanpa component lifecycle boilerplate), risiko jauh lebih rendah. Ditolak karena TIDAK genuinely menyentuh internal Collector — secara arsitektur sama persis dengan fallback sidecar yang dokumen sumber sendiri anggap sebagai jalan keluar "kalau bottleneck", bukan pilihan pertama yang dimaksudkan.

**Dampak**
Menentukan seluruh arsitektur teknis milestone (Checkpoint 3, 8, 9) — kalau nanti terbukti bottleneck, keputusan ini bisa direvisi eksplisit (dicatat sebagai keputusan baru), bukan diam-diam pivot.

---

### Keputusan 2: Perbaikan Gap Parenting `riwayat.simpan` — di Sumbernya, Sekarang

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion` putaran 1).

**Latar Belakang**
Riset menemukan `riwayat.simpan` (M7.18, pembawa satu-satunya sumber `traces.status`) dibuka SETELAH span `invoke_agent` sudah ditutup (`src/main.py:167-169`), tanpa context parent aktif — jadi ia jadi trace akar terpisah (trace_id BEDA), bukan anak `invoke_agent`. Dikonfirmasi dari kode langsung (`turn_pipeline.py:179`, `riwayat_percakapan.py:55`), bukan tebakan. Kalau dibiarkan: exporter Go tidak akan pernah bisa mengisi `traces.status` untuk trace utama, dan `/traces` (M5.3-5.4) akan terisi baris hantu 1-span per turn begitu data asli mengalir.

**Keputusan yang Dipilih**
Perbaiki di sumbernya (file kepemilikan M7.6/M7.18) sebagai Checkpoint 2 milestone ini, SEBELUM exporter Go mulai dibangun — bukan workaround korelasi di sisi Go, bukan diterima sebagai keterbatasan.

**Alasan**
Konsisten prinsip "Kejujuran terhadap keterbatasan" (`CLAUDE.md`) — membiarkan `traces.status` permanen NULL untuk data asli diam-diam merusak fitur inti M5.1-5.4 (distribusi status) yang sudah dibangun dan diverifikasi dengan data sample. Perbaikan di sumber genuinely lebih bersih: pola `opentelemetry.context.attach()`/`detach()` yang dibutuhkan SUDAH ada presedennya PERSIS di file yang sama (`turn_pipeline.py:160-174`, M7.7) — bukan pola baru yang perlu dipelajari/diverifikasi dari nol.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Korelasi `session_id`+`turn_index` di exporter Go** — menjaga PIC 6 self-contained, tapi menambah heuristik magic+rapuh (apa yang terjadi kalau turn diulang/retry dengan `session_id`+`turn_index` sama — false-merge risk) ke kode yang seharusnya sederhana di M6.1. Ditolak karena kompleksitas dipindah bukan dihilangkan, dan menambah kerapuhan baru.
- **Terima sebagai keterbatasan, revisit nanti** — tercepat untuk M6.1, tapi diam-diam merusak fitur distribusi status M5.1-5.4 begitu data asli mengalir. Ditolak, bertentangan prinsip kejujuran keterbatasan kalau dibiarkan tanpa rencana perbaikan konkret.

**Dampak**
Menyentuh `src/schemas/orchestration.py` (M7.6), `src/orchestration/turn_pipeline.py` (M7.6), `src/main.py`+`src/orchestration/riwayat_percakapan.py` (M7.18) — didokumentasikan sebagai addendum di `decisions.md` MASING-MASING milestone pemilik (Checkpoint 2 Task 2-3), bukan di file ini, mengikuti preseden M7.6/M7.7/M7.11/M7.17/M7.18.

---

### Keputusan 3: Toolchain Go — Instal Lokal

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion` putaran 1).

**Latar Belakang**
`go: command not found` dikonfirmasi di mesin developer. Docker tersedia (v29.2.1) — seluruh alur BISA murni lewat Docker tanpa instalasi apa pun di host.

**Keputusan yang Dipilih**
Instal Go lokal (installer resmi golang.org/winget).

**Alasan**
Iterasi (compile+test+run) jadi cepat (detik, bukan menit per percobaan) — penting karena ini bahasa yang genuinely baru dikerjakan pertama kali di project ini. Instalasi non-destruktif, tidak menyentuh apa pun yang sudah ada. Docker tetap dipakai untuk verifikasi akhir/deployment (Checkpoint 9), bukan satu-satunya jalur kerja.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Docker-only, tanpa install apa pun di host** — nol jejak di mesin host, tapi siklus edit-compile-test jauh lebih lambat (build image tiap percobaan). Ditolak karena kurang cocok untuk belajar bahasa baru sambil debugging error compile berulang (biaya iterasi terlalu tinggi untuk milestone yang sudah py risiko molor tersendiri, lihat Keputusan 1).

**Dampak**
Checkpoint 3 Task 4 (instalasi). Tidak berdampak ke milestone lain.

---

### Keputusan 4: Nama Folder — `custom-exporter/`

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion` putaran 2).

**Latar Belakang**
`CLAUDE.md` eksplisit menandai nama folder Go untuk PIC 6 sebagai keputusan yang harus diajukan ke user saat M6.1 dimulai ("bukan diasumsikan sepihak").

**Keputusan yang Dipilih**
`custom-exporter/` (root-level, sejajar `infra/observability/`, sejajar pola `dashboard/`).

**Alasan**
Konsisten terminologi yang SUDAH dipakai project ini sendiri (judul PIC 6 "Custom Exporter Supabase", komentar placeholder `otel-collector-config.yaml` M1.1 sudah menyebut `"custom-exporter"` sebagai nama hostname ilustratif).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`otel-collector-custom/`** — lebih eksplisit soal output akhirnya (distribusi Collector custom lengkap, bukan cuma komponen exporter tunggal). Ditolak murni preferensi konsistensi terminologi existing, bukan kesalahan teknis opsi ini.

**Dampak**
Seluruh path Checkpoint 3-9 (kode Go, `builder-config.yaml`, `Dockerfile`) berada di bawah `custom-exporter/`. Tabel "Struktur Repository" `CLAUDE.md`/`AGENT.md` wajib diperbarui (Checkpoint 11 Task 20).

---

### Keputusan 5: Struktur Repo — Bagian `nirwana-chatbot` yang Sama (Bukan Repo Terpisah)

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion` putaran 2).

**Latar Belakang**
Preseden M5.2 (`dashboard/`): folder Next.js dijadikan repo Git terpisah karena ekosistem package manager beda total (npm vs pip/uv) dan sensitivitas tooling npm terhadap folder ter-nest. `custom-exporter/` (Go) juga ekosistem berbeda total (`go.mod` vs `pyproject.toml`), tapi Go module system tidak sesensitif npm soal nested folder — `go.mod` bisa berdiri sendiri di subfolder tanpa friksi tooling material.

**Keputusan yang Dipilih**
`custom-exporter/` TETAP bagian repo Git `nirwana-chatbot` yang sama — bukan repo terpisah.

**Alasan**
Alasan spesifik yang memaksa pemisahan `dashboard/` (friksi tooling npm terhadap nested folder) TIDAK sepenuhnya berlaku untuk Go — satu histori commit lebih sederhana untuk kasus ini, tanpa kerugian teknis nyata yang teridentifikasi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Repo Git terpisah (mirror persis pola `dashboard/`)** — konsistensi preseden, histori commit Go terisolasi. Ditolak karena preseden `dashboard/` py alasan spesifik (friksi npm) yang tidak sepenuhnya sama untuk Go, dan kompleksitas tambahan (repo kedua, dua `git status` yang perlu dicek tiap checkpoint) tidak sepadan tanpa manfaat teknis nyata.

**Dampak**
Seluruh commit Checkpoint 2-11 masuk riwayat `nirwana-chatbot`, TIDAK ada repo kedua yang perlu dikelola terpisah (beda dari pola M5.2-5.4).

---

### Keputusan 6: Strategi Buffering untuk Trace Belum Dikenal

**Status:** Diputuskan sebelum implementasi (dari plan, penalaran teknis — bukan `AskUserQuestion` terpisah, trade-off dijelaskan penuh di Context plan dan dikonfirmasi lewat persetujuan `ExitPlanMode`).

**Latar Belakang**
Riset menemukan: `invoke_agent` (satu-satunya span pembawa `session.id`+`turn.index`, yang WAJIB ada untuk memenuhi kolom `traces.session_id`/`turn_index` NOT NULL) SELALU berakhir BELAKANGAN dibanding span anak-anaknya (`BatchSpanProcessor` Python SDK + nested span semantics — anak selesai sebelum induk exit dari `with`-block). Akibatnya span anak akan tiba di exporter SEBELUM span `invoke_agent` untuk `trace_id` yang sama, membuat insert langsung ke `spans` gagal (FK ke `traces` yang belum ada barisnya).

**Keputusan yang Dipilih**
Exporter menahan (buffer in-memory) span untuk `trace_id` yang belum py baris `traces`. Begitu span pembawa `session.id`+`turn.index` (anchor) tiba untuk `trace_id` itu, upsert baris `traces` lalu flush seluruh span tertahan.

**Alasan**
Satu-satunya cara mempertahankan skema Bagian 4 APA ADANYA (NOT NULL `session_id`/`turn_index`, FK `spans.trace_id`) tanpa data placeholder palsu yang sempat terlihat pembaca dashboard. Correctness untuk kondisi REALISTIS (bukan cuma kasus sederhana KK2 yang mengasumsikan parent selalu duluan) — tanpa ini, exporter akan gagal untuk SETIAP turn nyata, bukan cuma kasus tepi jarang.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Insert baris `traces` placeholder (sentinel `session_id`/`turn_index`) lalu UPSERT saat data asli tiba** — lebih sederhana (stateless), tapi mengekspos data placeholder palsu ke dashboard publik selama jendela waktu tertentu (bisa dilihat pembaca nyata). Ditolak, bertentangan prinsip "Kejujuran terhadap keterbatasan" — tidak boleh menyamarkan data belum lengkap sebagai data asli.
- **Terima sebagai keterbatasan (exporter hanya bekerja untuk test sintetis, bukan turn nyata)** — tercepat, tapi membuat seluruh milestone secara fungsional tidak berguna untuk tujuan aslinya begitu PIC 6 selesai. Ditolak.

**Dampak**
Checkpoint 7 (logic buffering) — komponen paling kompleks secara teknis di M6.1. `role_title` (tidak pernah jadi span attribute, lihat Keputusan 7) TETAP NULL meski buffering diterapkan, karena sumbernya memang tidak ada di span manapun.

---

### Keputusan 7: `role_title` Tidak Diperbaiki di Milestone Ini

**Status:** Diputuskan sebelum implementasi (dari plan, penalaran teknis, dikonfirmasi lewat persetujuan `ExitPlanMode`).

**Latar Belakang**
Grep menyeluruh `src/` mengonfirmasi `role_title` TIDAK PERNAH jadi span attribute di mana pun — hanya dipakai sebagai parameter fungsi RBAC internal, tidak pernah `span.set_attribute()`.

**Keputusan yang Dipilih**
Tidak diperbaiki di M6.1 — `traces.role_title` akan tetap NULL untuk data asli exporter Go.

**Alasan**
KK1 M6.1 secara literal hanya mewajibkan "nama layer, durasi, status" terisi — `role_title` TIDAK disebut. `TraceRow.role_title` sudah nullable di skema (`src/db/models.py`). Memperbaiki ini butuh menyentuh instrumentasi di banyak titik (beda sifat dari perbaikan bertarget Keputusan 2), di luar cakupan literal milestone ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tambahkan `role_title` sebagai span attribute di `invoke_agent` sekarang, sekalian dengan perbaikan Keputusan 2** — ditolak, scope creep di luar apa yang KK1 wajibkan, dan menambah risiko ke Checkpoint 2 yang sudah py tanggung jawab sendiri (perbaikan parenting).

**Dampak**
Dicatat sebagai entri baru `docs/keterbatasan-diterima.md` saat penutupan milestone (Checkpoint 11), bukan blocker KK1/KK2.

---

### Keputusan 8: Algoritma Pemetaan `layer_name`/`operation_name`

**Sumber Paksaan**
Kontrak instrumentasi existing PIC 1-4/7 — grep `_TRACER_NAME`/`_RETRIEVER_TRACER_NAME` di `src/` menemukan 29 nilai unik, SELURUHNYA mengikuti pola `"<layer_name>"` atau `"<layer_name>.<modul>"`, identik dengan 10 nilai `layer_name` yang SUDAH dipakai `SpanRow`/dashboard M5.1-5.4. `span.name()` (mis. `"chat"`) TERBUKTI dipakai ulang ≥13 lokasi lintas layer, TIDAK bisa jadi sumber `layer_name`.

**Keputusan yang Diikuti**
`layer_name` = `InstrumentationScope.Name` (nama tracer, `scope_spans[].scope.name` di OTLP) dipotong di titik pertama. `operation_name` = `span.Name()` apa adanya.

**Catatan Ketergantungan**
Kalau algoritma ini diubah sepihak, seluruh panel M5.1 (Latency per Layer)/M5.4 (Latency per Layer, Distribusi Status) yang mengelompokkan by `layer_name` akan salah kelompok untuk data asli.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by bukti langsung kode instrumentasi existing (bukan asumsi).

---

### Keputusan 9: Driver Postgres Go — `pgx`

**Sumber Paksaan**
Standar de-facto ekosistem Go modern untuk Postgres (analog `psycopg3` di Python project ini, `postgres` npm di `dashboard/`).

**Keputusan yang Diikuti**
`pgx` (`github.com/jackc/pgx`) dipakai untuk koneksi+query Checkpoint 5.

**Catatan Ketergantungan**
Tidak ada — pilihan library murni internal Checkpoint 5, tidak berdampak kontrak lintas-milestone.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif nyata dipertimbangkan — tidak ada driver Postgres Go lain yang punya kematangan/adopsi sebanding untuk project baru.

---

### Keputusan 10: Encoding `trace_id`/`span_id` — Hex String Standar OTel

**Sumber Paksaan**
Wire protocol OTLP merepresentasikan `trace_id` sebagai 16 byte, `span_id` sebagai 8 byte — skema Supabase (Bagian 4) menyimpan keduanya sebagai `text`. Encoding hex lowercase (32 karakter trace_id, 16 karakter span_id) adalah representasi standar yang SAMA dipakai Jaeger UI.

**Keputusan yang Diikuti**
`hex.EncodeToString()` atas raw bytes trace_id/span_id — memungkinkan `trace_id`/`span_id` di Supabase dicocokkan langsung ke tampilan Jaeger UI untuk keperluan debugging silang.

**Catatan Ketergantungan**
Data sample M5.2/M5.3 (`sample-6d7f5cea8dfd-root` dst.) TIDAK mengikuti format ini (string sintetis bebas) — begitu data asli mengalir, format ID akan berbeda bentuk dari data sample lama (kedua bentuk tetap valid sebagai `text`, tidak ada constraint format, jadi tidak breaking, hanya kosmetik).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by konvensi standar OTel/Jaeger yang sudah dipakai project ini di jalur privat.

---

### Keputusan 11: `builder-config.yaml` Wajib Mendaftarkan Seluruh Komponen Existing

**Sumber Paksaan**
`ocb` menghasilkan SATU distribusi Collector utuh yang MENGGANTIKAN image `otel/opentelemetry-collector-contrib:latest` resmi (`docker-compose.yml` saat ini) — bukan komponen tempel ke image existing. `infra/observability/otel-collector-config.yaml` existing memakai `otlpreceiver`, `batchprocessor`, `memory_limiter`, `attributes` processor, `otlp_grpc` exporter (Jaeger), `prometheus` exporter, `span_metrics` connector (M5.1).

**Keputusan yang Diikuti**
`builder-config.yaml` (Checkpoint 8 Task 14) mendaftarkan SELURUH komponen di atas PLUS modul lokal `supabaseexporter` baru — bukan cuma exporter custom sendirian.

**Catatan Ketergantungan**
Kalau komponen apa pun terlewat, mengganti image Collector (Checkpoint 9) akan meregresi pipeline M5.1 (Jaeger/Prometheus/Grafana berhenti terima data) — diverifikasi eksplisit Checkpoint 10 Task 18 sebelum milestone ditutup.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by cara kerja `ocb` (menggantikan distribusi, bukan menempel).

### Keputusan 12 (Addendum): `role_title` Diperbaiki + Strategi Buffering Dirombak Total (Bug FK Ganda Ditemukan+Diperbaiki Verifikasi Produksi)

**Status:** Ditemukan+diperbaiki setelah M6.1 dinyatakan selesai (2026-08-21), dipicu pertanyaan user "kenapa role title tidak pernah jadi span? ... role tittle ini adalah komponen yang sangat penting untuk access rules" dan persetujuan eksplisit ("yaa") untuk memperbaikinya sekarang — MEMBATALKAN Keputusan 7 di atas. Perbaikan `role_title` kemudian membuka rangkaian verifikasi produksi yang menemukan (dan memperbaiki) DUA bug independen di strategi buffering Keputusan 6, keduanya luput dari unit test Checkpoint 7 asli.

**Latar Belakang**

*Bagian A — role_title.* User menegaskan `role_title` bukan sekadar metadata tampilan, melainkan komponen inti audit-trail RBAC (Lapis 1 project ini). Span `authorization.check` (M2.2) dan `domain_gate.cakupan_individu.check` (M2.3) — titik keputusan RBAC yang sesungguhnya — TIDAK PERNAH merekam `role_title` sendiri, hanya `invoke_agent` yang akhirnya diberi atribut `role_title` (bukan `rbac.role_title` — beda namespace, `invoke_agent` mengikuti pola bare-attribute matching nama kolom Supabase `session.id`/`turn.index`, sedangkan span RBAC memakai prefix `rbac.*`).

*Bagian B — Bug FK #1 (urutan insert).* Verifikasi nyata skenario `gop_margin` (trace `f831b5b7df9e903f1eb5b5095bf9fcde`) menunjukkan `rbac.role_title` benar di Jaeger, TAPI 0 baris tersimpan di Supabase — `docker logs` menunjukkan `spans_parent_span_id_fkey` terlanggar berulang. Akar masalah: `flushLocked()` (Checkpoint 7 asli) menulis span tertahan dalam urutan KEDATANGAN mentah, bukan urutan topological (induk-sebelum-anak) — trace multi-level (mis. `invoke_agent` → `domain_gate.periksa_otorisasi_semua` → `authorization.check`) py induk NON-ROOT yang SENDIRI berakhir belakangan anaknya, sehingga cucu bisa ter-buffer sebelum induk langsungnya.

**Rangkaian percobaan perbaikan Bug FK #1** (didokumentasikan lengkap, bukan disembunyikan — "log adalah catatan peristiwa"):
1. **Percobaan 1**: urutkan span pending berdasar `StartedAt` menaik sebelum insert (span anak selalu MULAI setelah induknya, walau bisa BERAKHIR/ter-buffer duluan). Lolos unit test baru, TAPI verifikasi produksi ulang (trace baru) MASIH menunjukkan FK error — trace sudah "dikenal" (anchor sudah tiba di batch sebelumnya) menyebabkan span berikutnya di-insert LANGSUNG tanpa pernah dicek ulang lewat sort ini.
2. **Percobaan 2**: rombak `Buffer` total — `written map[string]bool` (span_id yang sudah tertulis) + `insertableLocked()` (trace dikenal DAN (akar ATAU induk sudah `written`)) + `drainLocked()` kaskade (fixpoint loop, menangani kedalaman nesting berapa pun). Lolos unit test skenario cross-batch, TAPI verifikasi produksi MASIH menunjukkan FK error (2 kejadian, bukan 14 seperti Percobaan 1 — jelas ADA perbaikan, tapi belum tuntas) dan Supabase menunjukkan 0 span sama sekali untuk trace itu.
3. **Diagnosis root cause sesungguhnya**: ditambahkan logging span_id/parent_span_id ke setiap kegagalan `InsertSpan` (`zap.Logger` diteruskan ke `Buffer`, `factory.go` diteruskan `set.TelemetrySettings.Logger`) DAN `pushTraces()` diubah TIDAK lagi `return err` di span pertama yang gagal (satu batch `chat` processor Collector bisa membawa span dari BEBERAPA trace_id, berhenti di kegagalan pertama membuang SISA batch yang genuinely tidak bermasalah — `errors.Join` dipakai mengumpulkan seluruh kegagalan tanpa mengorbankan sibling yang insertable). Log baru menunjukkan `InsertSpan gagal (anchor)` untuk DUA `span_id` BERBEDA pada trace yang SAMA.

**Bug FK #2 (akar masalah sesungguhnya) — konflasi `isAnchor()` dengan "span akar".** Dump lengkap trace `eadc58b474e238446e8e6b95a9e663ec` ke Jaeger menemukan EMPAT span berbeda membawa `session.id`+`turn.index`: `invoke_agent` (akar sejati), `input.validate` (M1.2), span `chat` penyusun narasi (M4.4), dan `riwayat.simpan` (M7.18) — SEMUA independen men-set kedua atribut ini untuk kebutuhan observability masing-masing, TIDAK ADA yang mendokumentasikan ini sebagai "hanya `invoke_agent`". Desain Checkpoint 7 ASLI (dan kedua percobaan perbaikan di atas) mengasumsikan `isAnchor()` (=py `session.id`+`turn.index`) SAMA DENGAN "span akar, selalu insertable" — salah: cabang `if ms.isAnchor()` di `Ingest()` meng-`InsertSpan` LANGSUNG tanpa pernah memeriksa `ParentSpanID`-nya sendiri, sehingga `input.validate`/`riwayat.simpan`/`chat` narasi (SEMUA non-root) melanggar FK persis saat tiba sebelum induk langsungnya (paling sering `invoke_agent`) sempat ter-INSERT.

**Keputusan yang Dipilih**
1. `role_title` direkam sebagai `rbac.role_title` di span `authorization.check` (`otorisasi.py`) dan `domain_gate.cakupan_individu.check` (`cakupan_individu.py`), DAN sebagai `role_title` (bare) di span `invoke_agent` (`turn_pipeline.py`) — diekstrak exporter Go (`mapping.go`) ke `mappedSpan.RoleTitle`, diteruskan sampai `TraceRow.RoleTitle` (`buffer.go`).
2. `isAnchor()` (mapping.go, TIDAK diubah — tetap murni deteksi atribut) DIPISAHKAN perannya di `Buffer`: memicu `UpsertTrace`+`known[traceID]=true` TETAP boleh dari span mana pun yang membawa `session.id`+`turn.index` (aman dipanggil berkali-kali, `traceUpsertArgs` sudah `ON CONFLICT DO UPDATE`+`COALESCE`) — TAPI keputusan "boleh insert langsung atau harus ditahan" SEKARANG SELALU lewat `insertableLocked()` yang sesungguhnya (akar sejati = `ParentSpanID == nil`, bukan lagi disamakan dengan `isAnchor()`).
3. `pushTraces()` tidak lagi berhenti di kegagalan span pertama (`errors.Join`), dan setiap kegagalan `InsertSpan`/`UpsertTrace` dicatat via `zap.Logger` dengan `trace_id`/`span_id`/`parent_span_id` — kegagalan residual (mis. dependency yang genuinely tidak pernah tiba) sekarang terlihat di `docker logs`, bukan silently menjatuhkan seluruh batch.

**Alasan**
`role_title` adalah input LANGSUNG ke keputusan `periksa_domain()`/deteksi constraint (Lapis 1 RBAC project ini) — merekamnya di titik keputusan itu sendiri (bukan cuma `invoke_agent`) memberi audit-trail yang genuinely bisa menjelaskan KENAPA suatu domain ditolak/diizinkan per role, sesuai penegasan user. Perbaikan Buffer BUKAN pilihan desain baru, melainkan koreksi bug — verifikasi produksi (bukan cuma unit test sintetis) adalah satu-satunya cara menemukan pola nesting nyata (span yang SAMA-SAMA membawa `session.id`+`turn.index` tapi berbeda kedalaman) yang tidak pernah terpikirkan saat menulis Checkpoint 7/unit test aslinya.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menghentikan diagnosis di Percobaan 1 (StartedAt-sort saja)** — ditolak, verifikasi produksi ulang MEMBUKTIKAN masih gagal; berhenti di sini akan mengulang pola "menganggap perubahan benar tanpa bukti" yang dilarang `CLAUDE.md`.
- **Menganggap 2 error residual Percobaan 2 sebagai keterbatasan diterima, bukan bug** — ditolak, jumlahnya kecil TAPI konsisten (bukan flaky), dan investigasi lanjutan (logging diagnostik) membuktikan itu genuinely bug desain (konflasi `isAnchor()`/akar), bukan noise infrastruktur.
- **Menandai `isAnchor()` di mapping.go sebagai yang salah, mengubah kriterianya jadi `ParentSpanID==nil`** — ditolak; `isAnchor()` justru BENAR mendeteksi "span pembawa metadata trace" (tujuan aslinya di `MapTraces()`), yang SALAH adalah `Buffer` menyamakannya dengan "aman insert tanpa cek induk". Memperbaiki di `Buffer` (bukan `mapping.go`) menjaga `isAnchor()` tetap dipakai benar untuk kedua perannya (trigger UpsertTrace vs insertability).

**Dampak**
`docs/keterbatasan-diterima.md` #19 (role_title tidak pernah jadi span) diperbarui status jadi DIPERBAIKI. Keputusan 6 di atas (strategi buffering) TETAP DIPERTAHANKAN sebagai catatan sejarah desain awal (bukan dihapus) — implementasi aktualnya sekarang mengikuti addendum ini. Keputusan 7 di atas (role_title tidak diperbaiki) DIBATALKAN oleh addendum ini. 4 unit test baru di `buffer_test.go` mereplikasi persis kedua bug (`TestBuffer_CucuSebelumIndukNonRoot`, `TestBuffer_CucuTibaSetelahAnchorSebelumIndukNonRoot`, `TestBuffer_SpanNonRootJugaBawaSessionTurnIndex`, plus assertion role_title di `mapping_test.go`). Verifikasi akhir (trace `0767cf9b32464b44cca43e8d5d810295`, real production turn skenario `gop_margin`, nesting 4 level) membuktikan 39/39 span tersimpan, nol FK error, `traces.role_title='Front Office Staff'` DAN `traces.status='ditolak_otorisasi'` terisi benar dari data asli — pertama kalinya KEDUA kolom itu terisi dari eksekusi nyata (sebelumnya hanya seed manual M5.2/M5.3).

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Arsitektur Exporter — Native OTel Collector Component via `ocb` | A | Plan |
| 2 | Perbaikan Gap Parenting `riwayat.simpan` — di Sumbernya, Sekarang | A | Plan / Checkpoint 2 |
| 3 | Toolchain Go — Instal Lokal | A | Plan / Checkpoint 3 |
| 4 | Nama Folder — `custom-exporter/` | A | Plan |
| 5 | Struktur Repo — Bagian `nirwana-chatbot` yang Sama | A | Plan |
| 6 | Strategi Buffering untuk Trace Belum Dikenal (lihat Addendum 12) | A | Plan / Checkpoint 7 |
| 7 | `role_title` Tidak Diperbaiki di Milestone Ini (DIBATALKAN, lihat Addendum 12) | A | Plan |
| 8 | Algoritma Pemetaan `layer_name`/`operation_name` | B | Checkpoint 6 |
| 9 | Driver Postgres Go — `pgx` | B | Checkpoint 5 |
| 10 | Encoding `trace_id`/`span_id` — Hex String Standar OTel | B | Checkpoint 6 |
| 11 | `builder-config.yaml` Wajib Mendaftarkan Seluruh Komponen Existing | B | Checkpoint 8 |
| 12 | Addendum: `role_title` diperbaiki + Bug FK ganda ditemukan+diperbaiki verifikasi produksi | A | Addendum 2026-08-21 |
