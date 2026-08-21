# Decisions — Milestone 7.6: Sambungan 1 (Input Layer → Pemetaan Ketergantungan Turn)

Dokumen ini mencatat keputusan desain untuk Milestone 7.6, milestone Level 2 pertama PIC 7 — beda jenis pekerjaan dari Level 1 (M7.2-7.5) yang menyambungkan LLM call di dalam satu layer. M7.6 menyambungkan dua layer BERBEDA (Input Layer → Context Resolution) untuk pertama kalinya, sehingga tidak ada preseden lokasi kode/bentuk state lintas-layer yang bisa langsung ditarik — dua keputusan di bawah genuinely diajukan ke user lewat `AskUserQuestion` sebelum checkpoint ditulis final. Metodologi pengujian direvisi total setelah draf plan awal (berbasis fixture pytest `InMemorySpanExporter` buatan) ditolak eksplisit oleh user, diarahkan untuk meniru workflow `evals/` dengan unit "kejadian struktural", bukan variasi bahasa.

---

### Keputusan 1: Orkestrator baru di package `src/orchestration/`, `src/main.py` TIDAK disentuh sampai M7.17

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Level 1 (M7.2-7.5) selalu menempatkan orkestrator gabungan di dalam package layer yang bersangkutan (`domain_gate/domain_gate.py`, `query_engine/query_engine.py`, dst) karena tidak pernah melintasi package boundary. M7.6 memanggil `validate_turn_payload()` (`src/layers/input_layer.py`) DAN `detect_turn_dependency()` (`src/layers/context_resolution/`) — dua package berbeda, tidak ada satu pun yang jadi "rumah" alami. Keputusan ini berdampak ke seluruh 10 milestone Level 2 berikutnya (M7.7-7.16), yang semuanya akan memperluas fungsi orkestrator yang sama.

**Keputusan yang Dipilih**
Package baru `src/orchestration/` (sejajar `src/layers/`, bukan di dalamnya — karena bukan salah satu dari sembilan layer arsitektur, melainkan concern PIC 7 sendiri), berisi `turn_pipeline.py::proses_turn()`. `src/main.py::submit_turn()` TIDAK diubah sama sekali sampai Milestone 7.17 ("Membangun Endpoint API").

**Alasan**
Lingkup M7.17 sendiri eksplisit memisahkan "endpoint (antarmuka luar)" dari "orkestrator (alur kontrol internal)" dengan alasan tertulis "memungkinkan orkestrator diuji tanpa bergantung pada mekanisme HTTP". KK M7.6 sendiri tidak pernah menyebut HTTP/endpoint — hanya "span yang menunjukkan data mengalir". `tests/layers/test_input_layer.py` yang sudah menguji `submit_turn()` lewat `TestClient` (assert perilaku echo-only) tetap terjaga tanpa perubahan karena `main.py` memang tidak disentuh.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Wire `main.py` sekarang, endpoint tumbuh organik tiap Sambungan** — ditolak user: endpoint publik `POST /v1/turns` akan mengekspos pipeline yang genuinely belum lengkap (baru 2 dari 9 layer) selama 10 milestone berjalan, berisiko terlihat "rusak" tanpa alasan jelas bagi siapa pun yang mencoba endpoint tersebut di tengah proses.

**Dampak**
Menentukan bentuk seluruh Level 2 — M7.7-7.16 memperluas `src/orchestration/turn_pipeline.py::proses_turn()` yang sama, bukan membuat orkestrator baru per Sambungan.

---

### Keputusan 2: Skema akumulator `KeadaanTurn`, bukan tuple yang terus membesar

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
M7.6 menghasilkan 2 potongan state (`TurnPayload`, `TurnDependencyResult`). M7.7-7.16 akan terus menambah state baru (hasil Rewrite, paket Session Memory, atomic intents, domain, request, hasil eksekusi, narasi, dst) hingga mencakup seluruh 9 layer di M7.16. Preseden tuple Level 1 (M7.4 `tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]`, M7.5 serupa) hanya pernah didesain untuk SATU hop 2 elemen di dalam satu milestone — tidak pernah dimaksudkan dirantai 11 kali lintas milestone berbeda.

**Keputusan yang Dipilih**
Skema baru `KeadaanTurn {payload: TurnPayload, ketergantungan: TurnDependencyResult}` di `src/schemas/orchestration.py` (file baru di package `src/schemas/` yang sudah ada). Field bertambah satu-per-satu oleh `decisions.md` tiap milestone Sambungan berikutnya — bukan didesain penuh di muka di M7.6.

**Alasan**
11 langkah berurutan yang saling bergantung (Level 2 wajib berurutan sesuai nomor) secara alami memanggil akumulator tunggal, bukan tuple yang jadi 9+ elemen bersarang menjelang M7.16 — jauh lebih sulit dibaca/dipelihara. Kedua field M7.6 non-Optional: baik `ValidationError` (langkah 1) maupun `APIError` (langkah 2) adalah exception keras yang menjalar keluar `proses_turn()` (lihat Keputusan 6), bukan nilai terdegradasi yang perlu direpresentasikan di akumulator — tidak ada kebutuhan `Optional` untuk M7.6 spesifik.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tuple yang terus membesar/bersarang** — ditolak user: preseden Level 1 cuma untuk 1 hop, bukan 11 hop berantai; akan jadi tidak terbaca menjelang M7.16.

**Dampak**
Milestone Sambungan berikutnya (M7.7+) berhak menambah field `Optional` sendiri sesuai kebutuhan cabangnya masing-masing (mis. percabangan paralel Rewrite/Tarik Memory di M7.7) — otoritas penuh milestone masing-masing, tidak didikte di sini.

---

### Keputusan 3: `proses_turn(raw: dict) -> KeadaanTurn` — signature dan logic internal

**Sumber Paksaan**
Signature `raw: dict` (bukan `TurnPayload`) forced by mencerminkan kontrak `validate_turn_payload(raw: dict)` sendiri DAN bentuk yang sudah diterima `submit_turn(payload: dict)` di `main.py` — supaya M7.17 nanti tinggal memanggil satu baris `proses_turn(payload)` tanpa merombak entry point. Logic internal (panggil `validate_turn_payload()`, short-circuit alami via Python kalau exception, baru panggil `detect_turn_dependency()`) forced by KK M7.6 sendiri ("payload yang lolos validasi... benar-benar diteruskan").

**Keputusan yang Diikuti**
```python
def proses_turn(raw: dict) -> KeadaanTurn:
    with tracer.start_as_current_span("invoke_agent") as span:
        ...
        payload = validate_turn_payload(raw)
        ketergantungan = detect_turn_dependency(payload)
        return KeadaanTurn(payload=payload, ketergantungan=ketergantungan)
```
Short-circuit murni alami (exception Python menjalar keluar `with` block) — tidak ada `if`/`try` eksplisit yang menyembunyikan kegagalan.

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang — bentuk ini satu-satunya yang konsisten dengan Keputusan 1-2 di atas.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by Keputusan 1-2 + KK M7.6 sendiri.

---

### Keputusan 4: `invoke_agent` dibuka PERTAMA KALI di `src/` oleh `proses_turn()`

**Sumber Paksaan**
`docs/01-architecture/rancangan-observability-ai-chatbot.md` §2: `invoke_agent` didefinisikan sebagai span pembungkus "operasi orkestrasi keseluruhan" per turn — deskripsi yang persis `proses_turn()`, bukan salah satu dari dua fungsi yang dipanggilnya. `docs/02-implementation-plan/rancangan-orkestrasi-api.md` menyatakan eksplisit `invoke_agent` "belum py pemilik" (di header tabel dokumen) dan "dibangun bertahap sepanjang Milestone 7.6-7.16" (Catatan Serah Terima) — rentang yang MULAI dari 7.6, titik masuk pipeline paling awal (Input Layer = layer 1/9). `invoke_agent` sudah pernah dibuka di skrip verifikasi sekali-pakai (`milestones/1.1.../logs.md`, `2.1.../logs.md` Checkpoint 8, `2.2-2.4.../logs.md`, `3.1.../logs.md` — seluruhnya TIDAK di-commit, scratchpad) tapi TIDAK PERNAH di kode produksi `src/` — itu makna literal "belum py pemilik".

**Keputusan yang Diikuti**
`proses_turn()` membuka `tracer.start_as_current_span("invoke_agent")`, melekatkan atribut `session.id`/`turn.index` — preseden konsisten skrip-skrip verifikasi sebelumnya.

**Catatan Ketergantungan**
Level 1 (M7.2-7.5) TIDAK membuka span sendiri karena kontraknya beda (persis N span `chat` sub-langkah, sudah terpenuhi sub-fungsi) — tidak ada konflik preseden, `invoke_agent` adalah kontrak span turn-level yang berbeda sepenuhnya. Kalau dibuka lebih lambat (mis. ditunda ke M7.16), M7.6-7.15 tidak akan py span pembungkus untuk dijadikan acuan nesting pembuktian KK masing-masing — bertentangan langsung dengan KK M7.6 sendiri yang menuntut bukti span sejak hop pertama.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menunda pembukaan `invoke_agent` ke milestone Level 2 yang lain** — ditolak, tidak ada milestone lain yang lebih awal dari M7.6 di pipeline (Input Layer = entry point literal), dan menunda akan meninggalkan M7.6-7.15 tanpa span pembungkus untuk bukti nesting masing-masing KK.

---

### Keputusan 5: Metodologi pembuktian KK ("dibuktikan lewat span") — live Jaeger + `docker compose`, BUKAN fixture pytest buatan

**Status:** Ditemukan/dikoreksi di tengah perencanaan (draf plan awal ditolak eksplisit user, diarahkan ulang).

**Latar Belakang**
Draf plan pertama mengusulkan memasang `TracerProvider` + `InMemorySpanExporter` (OTel SDK) lewat fixture pytest `session`-scoped untuk memverifikasi nesting span in-process, tanpa mengecek dulu apakah project sudah py preseden pembuktian span sejenis. User menolak draf itu secara eksplisit dan meminta metodologi ditinjau ulang. Investigasi ulang menemukan `milestones/2.1-identifikasi-domain/logs.md` Checkpoint 8 SUDAH py preseden nyata untuk kasus "dibuktikan lewat span" persis: `docker compose up -d` (Jaeger+Collector+Prometheus lokal), skrip memanggil `setup_tracing()` + fungsi produksi nyata dibungkus `invoke_agent`, trace di-query LANGSUNG lewat Jaeger API (`curl http://localhost:16686/api/traces/<trace_id>`) — bukan asumsi dari kode, hasil (`trace_id`, struktur span, atribut) dicatat di `logs.md`.

**Keputusan yang Dipilih**
M7.6 mengikuti pola persis M2.1 Checkpoint 8 — Jaeger live via `docker compose`, query API nyata, `trace_id` dicatat sebagai bukti — BUKAN `InMemorySpanExporter`/fixture pytest.

**Alasan**
Preseden nyata yang sudah dipakai project untuk kasus serupa jauh lebih kuat sebagai dasar keputusan dibanding teknik baru yang belum pernah dipakai di project ini — konsisten prinsip "jangan mengasumsikan pola baru kalau preseden yang sudah terbukti bekerja tersedia".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`TracerProvider` + `InMemorySpanExporter` via fixture pytest** — ditolak user secara eksplisit; risiko tambahan yang ditemukan saat investigasi ulang: `set_tracer_provider()` cuma efektif dipanggil sekali per proses (panggilan kedua di-skip diam-diam OTel), sehingga fixture ini rapuh untuk dipakai ulang lintas 10 milestone Sambungan berikutnya tanpa disiplin ketat — preseden Jaeger live tidak py risiko ini karena tidak bergantung pemasangan provider spesifik-test.

**Dampak**
Menentukan struktur pengujian seluruh M7.6-7.16: tiap Sambungan yang butuh bukti span mengikuti pola Jaeger live yang sama, bukan membangun infrastruktur test terpisah.

---

### Keputusan 6: Pengujian kejadian mengikuti struktur `evals/`, unit skenario = kejadian struktural (bukan variasi bahasa)

**Status:** Arahan langsung user (bukan pertanyaan pilihan) setelah draf plan awal ditolak.

**Sumber Paksaan**
Arahan eksplisit user: "coba tiru cara testing real dari folder evals/... anda bisa tiru workflownya dengan penyesuaian bahwa testing kali ini adalah antar layer... testing pada milestone 7.x tidak bertujuan memilih prompt terbaik, tapi untuk memastikan setiap layer saling terhubung... rancangannya bukan berbasis mengcover kemungkinan input user apa saja yang bisa terjadi, tapi lebih ke memetakan kejadian apa saja yang mungkin saja terjadi. setiap kejadian itu harus bisa dipetakan kriteria keberhasilannya." Preseden struktur: `evals/README.md` (`rancangan.md` → `run_eval.py` → `payloads/` → `audit.md`, "ditulis SEBELUM eksekusi" lalu "SETELAH eksekusi") dan `evals/1.3-pemetaan-ketergantungan-turn/` sebagai contoh konkret formatnya.

**Keputusan yang Diikuti**
`evals/7.6-sambungan-input-layer-pemetaan-ketergantungan/{rancangan.md,run_eval.py,payloads/,audit.md}` — struktur identik preseden, TAPI unit skenario diberi prefix `E` (Kejadian) bukan `S` (Skenario), isinya kejadian struktural (payload valid/invalid, histori ada/tidak, kegagalan teknis), bukan variasi bahasa pertanyaan. `run_eval.py` M7.6 juga memanggil `setup_tracing()` (beda dari `run_eval.py` M1.3 yang tidak butuh ini — eval M1.3 murni soal kualitas jawaban LLM, tanpa kebutuhan span).

**Alasan**
Struktur `evals/` sudah py disiplin "tulis ekspektasi dulu sebelum eksekusi, baru audit ekspektasi-vs-aktual setelahnya" yang persis cocok untuk "tiap kejadian harus bisa dipetakan kriteria keberhasilannya" — tinggal mengganti UNIT skenarionya, bukan membangun mekanisme baru dari nol.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Draf awal: seluruhnya lewat pytest** (`tests/orchestration/` dengan `InMemorySpanExporter`) — ditolak user, tidak memisahkan bukti nyata (butuh LLM/Jaeger) dari regresi otomatis cepat (`tests/` murni deterministik), dan tidak mengikuti disiplin "tulis ekspektasi dulu, audit setelahnya" yang eksplisit diminta.

**Dampak**
`tests/orchestration/` (Checkpoint 3) tetap ada tapi cakupannya menyempit — hanya kejadian yang TIDAK butuh LLM/Jaeger nyata (short-circuit deterministik), sisanya (kejadian yang genuinely butuh eksekusi nyata) pindah ke `evals/7.6-.../`.

---

### Keputusan 7: `openai.APIError` di `detect_turn_dependency()` dibiarkan menjalar tanpa ditangkap orkestrator — dicatat sebagai keterbatasan diterima baru

**Sumber Paksaan**
Cakupan pekerjaan PIC 7: "Tidak termasuk: Logic internal kesembilan layer itu sendiri... pekerjaan ini memanggil mekanisme yang sudah ada, bukan menulis ulang" (`rancangan-orkestrasi-api.md`). Investigasi menemukan `detect_turn_dependency()` (M1.3) TIDAK py `try/except` sama sekali di sekitar pemanggilan LLM-nya — beda dari SEMUA layer LLM lain (yang menangkap `APIError` → `GAGAL_TEKNIS`), kecuali `susun_narasi()` (M4.4, sengaja, terdokumentasi). `milestones/1.3-.../decisions.md` hanya mendokumentasikan fallback untuk parse/bounds gagal, TIDAK untuk kegagalan API/jaringan — celah yang belum pernah terdokumentasi sebelumnya.

**Keputusan yang Diikuti**
`proses_turn()` TIDAK menambah `try/except APIError` baru untuk menutup celah ini. Dicatat sebagai entri baru `docs/keterbatasan-diterima.md` (Checkpoint 6).

**Catatan Ketergantungan**
Menambal celah ini di sini berarti mengubah logic internal M1.3 — di luar Lingkup M7.6, berisiko tidak konsisten dengan cara PIC lain menangani temuan serupa (dicatat, bukan langsung diperbaiki, kecuali milestone itu sendiri yang menyentuhnya untuk alasan lain).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menambahkan `try/except APIError` di `proses_turn()` sebagai mitigasi sementara** — ditolak, forced by "tidak dirombak ulang"; kalaupun ditambahkan di level orkestrator (bukan di `detect_turn_dependency()` sendiri), itu tetap mengubah kontrak/perilaku M1.3 yang sudah ada tanpa kesepakatan pemilik layer tersebut.

---

### Keputusan 8: File test deterministik `tests/orchestration/` untuk regresi otomatis, cakupan sempit (hanya kejadian tanpa LLM/Jaeger)

**Sumber Paksaan**
Belum ada test lintas-layer sama sekali di project. Pembagian tugas `tests/` vs `evals/` sudah dijelaskan `evals/README.md` sendiri: "Logic kode... assert otomatis, hasil pasti benar/salah" (`tests/`) vs "Perilaku model AI... kombinasi otomatis + audit manual" (`evals/`) — M7.6 py dua jenis kejadian: yang deterministik murni (short-circuit validasi gagal, tidak menyentuh LLM sama sekali) dan yang butuh eksekusi nyata (LLM + span).

**Keputusan yang Diikuti**
`tests/orchestration/test_turn_pipeline.py` HANYA mencakup kejadian E03 (short-circuit) + satu test wiring identity mocked — bukan kejadian yang butuh LLM/Jaeger nyata.

**Catatan Ketergantungan**
Kalau seluruh kejadian dipaksa masuk `tests/` (termasuk yang butuh LLM), akan bertentangan dengan preseden filosofi test M7 sebelumnya (M7.2-7.5) yang tetap memakai LLM sungguhan untuk connectivity test — dan tidak memenuhi disiplin `rancangan.md`/`audit.md` yang diminta eksplisit user.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by kombinasi preseden `evals/README.md` + arahan user (Keputusan 6).

---

### Keputusan 9: Struktur Repository `CLAUDE.md`/`AGENT.md` diperbarui di Checkpoint 2 (bukan ditunda ke penutupan)

**Sumber Paksaan**
Aturan eksplisit `CLAUDE.md`: "setiap kali sebuah checkpoint menghasilkan folder top-level baru atau subpackage baru... perbarui... sebagai bagian dari checkpoint itu sendiri, bukan ditunda ke penutupan milestone." `src/orchestration/` adalah subpackage top-level baru (dibuat Checkpoint 2), tidak sesuai baris manapun yang sudah tercatat.

**Keputusan yang Diikuti**
Update tabel Struktur Repository jadi bagian Task 2 (Checkpoint 2), bukan Task 8-10 (Checkpoint 7 penutupan). `src/schemas/orchestration.py` (file baru di package yang sudah tercatat) TIDAK memicu update terpisah.

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang — aturan eksplisit tanpa pengecualian untuk kasus ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by aturan `CLAUDE.md` sendiri.

---

---

### Keputusan 10 (Addendum M6.1): `KeadaanTurn` +2 field identitas `invoke_agent`, `proses_turn()` men-capture trace_id/span_id sebelum span exit

**Status:** Ditemukan di tengah implementasi Milestone 6.1 (PIC 6, Custom Exporter Go) — dicatat di sini karena kepemilikan kode (`KeadaanTurn`/`proses_turn()`) tetap M7.6, mengikuti preseden penulisan gap-fix di file pemilik (M7.6/M7.7/M7.11/M7.17/M7.18), bukan di `decisions.md` milestone penemunya.

**Latar Belakang**
Riset M6.1 menemukan span `riwayat.simpan` (M7.18) dibuka SETELAH `with`-block `invoke_agent` (baris ini) sudah exit — `riwayat.simpan` jadi trace akar terpisah (trace_id BEDA), bukan anak `invoke_agent`. Akibatnya exporter Go PIC 6 tidak akan pernah bisa mengisi `traces.status` untuk trace utama begitu data asli mengalir (satu-satunya sumber `riwayat.status` ada di trace lain). Lihat `milestones/6.1-membangun-exporter-dasar/decisions.md` Keputusan 2 untuk analisis lengkap+alternatif yang ditolak.

**Keputusan yang Dipilih**
`KeadaanTurn` (`src/schemas/orchestration.py`) ditambah 2 field `str` non-Optional: `invoke_agent_trace_id`, `invoke_agent_span_id` — diisi dari `span.get_span_context()` (`otel_trace.format_trace_id()`/`format_span_id()`) tepat sebelum `return KeadaanTurn(...)` di `proses_turn()`, MASIH di dalam `with`-block `invoke_agent` (span belum exit, `get_span_context()` valid).

**Alasan**
Menyimpan `trace_id`/`span_id` sebagai string (bukan objek `opentelemetry.context.Context` mentah) menghindari kebutuhan `arbitrary_types_allowed` di `KeadaanTurn` (Pydantic `BaseModel` biasa) — `main.py` (kepemilikan M7.18) merekonstruksi `SpanContext`/`NonRecordingSpan` dari kedua string ini, pola standar OTel untuk "link ke span yang sudah ditutup" (identik mekanisme W3C traceparent propagation).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Simpan objek `Context` OTel mentah di `KeadaanTurn`** — butuh `model_config = ConfigDict(arbitrary_types_allowed=True)`, mengubah karakter tipe-ketat schema yang dipakai 13+ milestone Sambungan lain. Ditolak, string hex jauh lebih ringan dan idiomatic.

**Dampak**
`KeadaanTurn` sekarang 15 field. Fixture test yang mengonstruksi `KeadaanTurn` manual (`tests/test_main.py`, `tests/layers/test_input_layer.py`) diperbarui menyertakan 2 field baru (dummy hex valid). Verifikasi Jaeger real (span `riwayat.simpan` genuinely bersarang di trace `invoke_agent`) — lihat `milestones/6.1-.../logs.md` Checkpoint 2 untuk status verifikasi.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Package `src/orchestration/`, `main.py` tidak disentuh sampai M7.17 | A | Plan |
| 2 | Skema akumulator `KeadaanTurn`, bukan tuple membesar | A | Plan |
| 3 | Signature `proses_turn(raw: dict) -> KeadaanTurn` | B | Plan |
| 4 | `invoke_agent` dibuka pertama kali di `proses_turn()` | B | Plan |
| 5 | Bukti span pakai live Jaeger, bukan fixture pytest buatan | B | Plan (revisi setelah plan awal ditolak) |
| 6 | Pengujian kejadian mengikuti struktur `evals/` | B | Plan (arahan langsung user) |
| 7 | `APIError` `detect_turn_dependency()` dibiarkan menjalar, dicatat keterbatasan diterima | B | Plan |
| 8 | `tests/orchestration/` cakupan sempit (tanpa LLM/Jaeger saja) | B | Plan |
| 9 | Update Struktur Repository di Checkpoint 2 | B | Plan |
| 10 | `KeadaanTurn` +2 field identitas `invoke_agent` (Addendum M6.1) | A | M6.1 Checkpoint 2 |
