# Decisions — Milestone 7.14: Sambungan 9 (Verification Gate → Execution, termasuk uji wave berulang)

Dokumen ini mencatat keputusan desain untuk Milestone 7.14, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: Instance lokal `chatbot_api` yang benar adalah `nirwana-database/scripts/chatbot_api/`, BUKAN `nirwana-database/api/`

**Status:** Ditemukan di tengah riset plan (sebelum implementasi dimulai)

**Latar Belakang**
User mengarahkan mengaktifkan `chatbot_api` lokal dengan mengakses `nirwana-database/api`. Riset plan (agen Explore) menemukan `nirwana-database/api/` adalah proyek **berbeda** — "Nirwana Monitoring API" (Milestone 1.6 project database, deployed Render), route-nya `/health`, `/api/status/tables`, `/api/dq/*`, `/api/warehouse/*` — TIDAK py satu pun route `/chatbot/...`. Kontrak yang benar-benar dibutuhkan `nirwana-chatbot` (`GET /chatbot/{domain}/{view_name}`) ada di file terpisah: `nirwana-database/scripts/chatbot_api/main.py`, dikonfirmasi `docs/09-serving-ai-chatbot/api-chatbot.md` (dokumen sumber tim database) dan `CLAUDE.md` proyek `nirwana-database` sendiri.

**Keputusan yang Dipilih**
Jalankan `nirwana-database/scripts/chatbot_api/` (`python -m uvicorn main:app --reload` dari dalam folder itu), BUKAN `nirwana-database/api/`.

**Alasan**
Kontrak endpoint (`/chatbot/{domain}/{view_name}`, 10 domain, `/…/_meta`) hanya diimplementasikan di `scripts/chatbot_api/main.py` — `api/` sama sekali tidak relevan untuk kebutuhan M7.14 meskipun sama-sama FastAPI dan sama-sama default port 8000. `nirwana-chatbot/.env` sudah py `CHATBOT_API_BASE_URL=http://127.0.0.1:8000`, cocok default uvicorn `scripts/chatbot_api/`. Kredensial 10 domain `*_CHATBOT_READER_DB_URL` + `CHATBOT_AUTHZ_READER_DB_URL` sudah terisi di `nirwana-database/.env` (dikonfirmasi tanpa membuka nilai sungguhan, hanya cek populated/tidak).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menjalankan `nirwana-database/api/` sesuai instruksi literal user** — ditolak: bukan salah tafsir gaya, tapi fakta objektif folder itu tidak mengimplementasikan kontrak yang dibutuhkan sama sekali (0 route `/chatbot/...`). Dikoreksi ke user sebagai temuan riset, bukan diam-diam diganti.

**Dampak**
Checkpoint 1 Task 2 menjalankan `scripts/chatbot_api/`, bukan `api/`. Tidak ada dampak ke milestone lain.

---

### Keputusan 2: Wave = urutan eksekusi murni, TANPA passing data hasil wave 1 ke wave 2

**Status:** Diputuskan sebelum implementasi (dikonfirmasi user via diskusi chat setelah penjelasan konkret, bukan `AskUserQuestion` formal — user diberi contoh nyata skenario `gop_margin` lalu setuju)

**Latar Belakang**
KK M7.14 (`rancangan-orkestrasi-api.md` baris 138-142) menyebut "kebutuhan majemuk-bergantung yang memicu lebih dari satu wave, memastikan wave kedua benar-benar menunggu **hasil** wave pertama sebelum Verification Gate-nya sendiri dipanggil ulang." Frasa "menunggu hasil" bisa dibaca dua cara: (a) murni urutan waktu (wave 2 tidak boleh dieksekusi SEBELUM wave 1 selesai), atau (b) wave 2 butuh NILAI hasil wave 1 dimasukkan ke parameter request-nya sendiri. Tidak ada satu baris kode pun di `src/` (Query Engine M3.4, Decomposition M1.6, atau layer manapun) yang mendukung passing data antar-atomic-intent — genuinely terbuka, berdampak material (menentukan apakah M3.4 perlu diubah).

**Keputusan yang Dipilih**
Wave murni soal URUTAN — `susun_request_atomic_intent()` (M3.4) TIDAK diubah sama sekali (signature, prompt, logic internal tetap persis). Yang berubah HANYA orkestrator: `verifikasi_gate_semua()` (M7.13) dipanggil PER WAVE (bukan sekali borongan), diselang-seling `eksekusi_atomic_intent_semua()` (baru) per wave — wave 2 baru diproses setelah `eksekusi_atomic_intent_semua()` wave 1 selesai dipanggil, dibuktikan lewat urutan span di Jaeger.

**Alasan**
Bukti empiris dari SELURUH skenario "bergantung"/"perbandingan" yang sudah dijalankan nyata M7.9-M7.13 (skenario `gop_margin`: "Bagaimana perbandingan gop_margin sebelum vs sesudah deviasi harga?"): request Query Engine yang dihasilkan SELALU self-sufficient — `params={"property_name": "Bali", "period_date_from": "2026-07-01", "period_date_to": "2026-08-01"}` — rentang tanggal lebar mencakup kedua periode dalam SATU request, tidak pernah butuh angka hasil eksekusi wave sebelumnya. Mengubah M3.4 untuk kasus yang belum pernah terbukti dibutuhkan akan melanggar batasan `rancangan-orkestrasi-api.md` baris 19 (PIC 7 tidak py wewenang mengubah logic internal layer, hanya menyambungkan). Bacaan literal KK juga mendukung: "dua wave yang benar-benar berurutan lewat Verification Gate dan Execution **yang sama**" menekankan REUSE mekanisme yang sama dipanggil dua kali secara berurutan (bukti struktural), bukan soal transformasi data antar-wave.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Wave 2 menerima hasil wave 1 sebagai konteks tambahan** (tambah parameter baru ke `susun_request_atomic_intent()`, ubah prompt M3.4 supaya LLM bisa "melihat" nilai hasil wave 1) — ditolak: memperluas cakupan M7.14 ke logic internal M3.4 (di luar batasan PIC 7), tidak didukung bukti nyata manapun bahwa ini genuinely dibutuhkan, dan menambah kerumitan penanganan dependensi yang "hilang" (bergantung_pada merujuk intent yang sudah tersaring upstream) tanpa manfaat yang terbukti.

**Dampak**
Merestrukturisasi CARA `turn_pipeline.py` memanggil `verifikasi_gate_semua()` (dari 1 panggilan flat menjadi loop per-wave) — pertama kalinya Sambungan Level 2 mengubah cara pemanggilan milestone sebelumnya, bukan murni menambah langkah baru di akhir. `KeadaanTurn.verification_gate` tetap bentuk/kontrak sama (flat list), hanya cara pengisiannya berubah.

---

### Keputusan 3: Fungsi pengelompokan wave baru ditempatkan di `src/orchestration/wave.py`

**Sumber Paksaan**
Tidak murni forced — keputusan teknik yang masuk akal berdasar kompleksitas: algoritma topological leveling (Keputusan 2) cukup rumit untuk butuh unit test standalone sendiri (5+ kasus edge: independen, dependensi sederhana, multi-dependensi, dependensi hilang, siklus), mirror alasan tiap fungsi `_semua()` baru di layer lain selalu punya modul sendiri (M7.11-7.13).

**Keputusan yang Diikuti**
File baru `src/orchestration/wave.py` — di dalam subpackage `src/orchestration/` yang SUDAH tercatat di `CLAUDE.md` (dari M7.6), jadi TIDAK memicu update tabel Struktur Repository (aturan proyek: file baru dalam subpackage yang sudah tercatat cukup didokumentasikan di `report.md`, bukan `CLAUDE.md`).

**Catatan Ketergantungan**
Kalau logic ini dipaksa inline di `turn_pipeline.py`, sulit diuji standalone tanpa mock berlapis — mengurangi kualitas test edge-case.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Inline di `turn_pipeline.py`** — dipertimbangkan untuk minimalkan file baru, ditolak: kompleksitas algoritma (5+ edge case) butuh test standalone yang sulit dicapai kalau logic tercampur langsung di badan `proses_turn()`.

**Dampak**
`turn_pipeline.py` mengimpor `kelompokkan_wave` dari modul baru ini.

---

### Keputusan 4: `verifikasi_gate_semua()` (M7.13) dipanggil PER WAVE, bukan sekali untuk seluruh `query_engine_result`

**Sumber Paksaan**
Konsekuensi langsung Keputusan 2 — kalau wave adalah soal urutan yang harus terbukti di span Jaeger, `verifikasi_gate_semua()` (dan `eksekusi_atomic_intent_semua()`) HARUS benar-benar dipanggil ulang per wave secara sekuensial, bukan sekali borongan lalu difilter belakangan (yang tidak akan menghasilkan urutan span yang berbeda untuk dibuktikan).

**Keputusan yang Diikuti**
`turn_pipeline.py` memanggil `kelompokkan_wave(query_engine_result)` lalu loop tiap wave: `verifikasi_gate_semua(wave_slice, ...)` → `eksekusi_atomic_intent_semua(...)` → lanjut ke wave berikutnya. `retriever_result`/`cakupan_individu_result` TETAP diteruskan utuh (full-set) di setiap panggilan wave (bukan di-slice) — fungsi `verifikasi_gate_semua()` sudah melakukan lookup via `atomic_intent_id` secara internal (M7.13 Keputusan 7), aman menerima superset.

**Catatan Ketergantungan**
Fungsi `verifikasi_gate_semua()` SENDIRI tidak diubah satu baris pun — hanya CARA `turn_pipeline.py` memanggilnya yang berubah. `KeadaanTurn.verification_gate` diisi dari hasil `extend()` seluruh wave, mempertahankan bentuk `list[tuple[AtomicIntent, HasilVerifikasiGate]]` flat yang sama seperti M7.13.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by Keputusan 2 (kalau wave harus terbukti via urutan span nyata, tidak ada cara lain selain benar-benar memanggil ulang secara sekuensial).

---

### Keputusan 5: `eksekusi_atomic_intent_semua()` ditempatkan di `src/layers/execution/klasifikasi_respons.py`, mengembalikan `list[HasilEksekusiAtomicIntent]` TANPA tuple pembungkus

**Sumber Paksaan**
Lokasi: preseden `_semua()` di layer package sendiri (M7.11 Keputusan 3, M7.12 Keputusan 2, M7.13 Keputusan 3) — dikonfirmasi konsisten 3x berturut-turut. Bentuk return: `HasilEksekusiAtomicIntent` (skema M4.2, `src/schemas/execution.py`) SUDAH membawa field `atomic_intent: AtomicIntent` sendiri (dikonfirmasi lewat investigasi) — BEDA dari kasus M7.13 (`HasilVerifikasiGate` tidak membawa `atomic_intent`, forced tuple). Di sini tidak ada asosiasi identitas yang hilang, jadi tuple pembungkus tidak dibutuhkan.

**Keputusan yang Diikuti**
`eksekusi_atomic_intent_semua(verification_gate_wave, cakupan_individu_result, role_title, employee_id) -> list[HasilEksekusiAtomicIntent]` di file yang sama dengan `eksekusi_atomic_intent()`.

**Catatan Ketergantungan**
Kalau `HasilEksekusiAtomicIntent` di masa depan kehilangan field `atomic_intent`-nya (tidak mungkin tanpa breaking change skema M4.2), keputusan ini perlu ditinjau ulang mirror M7.13.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden lokasi + skema yang sudah lengkap.

---

### Keputusan 6: `eksekusi_atomic_intent_semua()` butuh parameter tambahan `cakupan_individu_result` untuk lookup `constraint`

**Sumber Paksaan**
Signature `eksekusi_atomic_intent(atomic_intent, view_name, request, constraint: ConstraintCakupanIndividu, role_title, employee_id)` (non-Optional `constraint`) — dikonfirmasi lewat baca ulang `klasifikasi_respons.py` baris 160-172: `constraint`/`view_name` HANYA dipakai `_revisi_request()` kalau jalur `400` terpicu (tidak dipakai di percobaan pertama), TAPI tetap wajib parameter karena revisi bisa terjadi kapan saja selama eksekusi berjalan.

**Keputusan yang Diikuti**
`eksekusi_atomic_intent_semua()` menerima `cakupan_individu_result: list[AtomicIntentConstraint]` sebagai parameter tambahan, membangun lookup dict `constraint_by_id` (key `atomic_intent_id`) — mirror pola lookup M7.13 Keputusan 7. `view_name` diambil dari `hasil_vg.request_final.view_name` (sudah tersedia, sumber tunggal, tidak perlu parameter terpisah).

**Catatan Ketergantungan**
Tanpa parameter ini, `eksekusi_atomic_intent()` tidak bisa dipanggil sama sekali (TypeError - missing argument) begitu jalur revisi 400 genuinely terpicu saat eksekusi nyata.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by signature `eksekusi_atomic_intent()` yang sudah final sejak M4.2.

---

### Keputusan 7: `KeadaanTurn` bertambah field `execution: list[HasilEksekusiAtomicIntent]`, FLAT (bukan nested per-wave)

**Sumber Paksaan**
Preseden konsisten M7.6-7.13 (field flat per unit tersambung). Downstream (M7.15, titik pertemuan Pencocokan-selesai + Execution → Interpretation) hanya butuh hasil eksekusi + sumbernya (`sumber="eksekusi_baru"` vs `session_memory`, kontrak M4.4), TIDAK butuh tahu nomor wave — dikonfirmasi lewat baca `rancangan-orkestrasi-api.md` M7.15 dan kontrak paket Session Memory di `CLAUDE.md`.

**Keputusan yang Diikuti**
`execution: list[HasilEksekusiAtomicIntent]`, non-Optional, diisi dari `extend()` seluruh wave — nomor wave TIDAK disimpan di `KeadaanTurn` (kalau dibutuhkan untuk debugging, tersedia lewat span `orchestration.wave` di Jaeger, bukan lewat skema).

**Catatan Ketergantungan**
Kalau M7.15/M7.16 ternyata butuh tahu nomor wave (belum ada bukti ini dibutuhkan), field ini perlu direvisi — dicatat sebagai potensi follow-up, bukan diasumsikan sekarang.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`execution: list[list[HasilEksekusiAtomicIntent]]` (nested per-wave)** — ditolak: melanggar prinsip desain `KeadaanTurn` sendiri ("BUKAN tuple/struktur yang terus bersarang", `src/schemas/orchestration.py` docstring), dan tidak ada bukti downstream membutuhkannya.

**Dampak**
M7.15 akan mengonsumsi field ini sebagai list flat, konsisten field lain.

---

### Keputusan 8: Pengelompokan wave menangani dependensi hilang dan siklus secara defensif (fail-open)

**Status:** Diputuskan sebelum implementasi (dari plan, forced by realita pipeline — bukan genuinely dipertimbangkan sebagai pilihan gaya)

**Latar Belakang**
`bergantung_pada` suatu atomic intent bisa merujuk `atomic_intent_id` yang TIDAK ADA lagi di `query_engine_result` — tersaring di layer manapun sebelumnya (Domain Gate/Otorisasi/Cakupan Individu/Retriever/Query Engine, seluruhnya sudah terbukti bisa memfilter sejak M7.10-7.13). Tidak ada validator manapun di `AtomicIntent`/Decomposition yang menjamin `bergantung_pada` bebas siklus.

**Keputusan yang Dipilih**
(a) Dependensi hilang (tidak ada di `query_engine_result`) dianggap "sudah terpenuhi" — TIDAK menghalangi penempatan wave, level dihitung dari dependensi yang MASIH ADA saja; kalau semua dependensinya hilang, atomic intent itu masuk wave 1. (b) Siklus: algoritma dibatasi iterasi maksimum (= jumlah item); sisa yang tak terselesaikan setelah itu di-force masuk wave terakhir dengan span/log peringatan — fail-open, bukan crash seluruh turn.

**Alasan**
Konsisten prinsip "Kejujuran terhadap keterbatasan" TANPA mengorbankan ketahanan (`proses_turn()` tidak boleh crash total karena satu atomic intent bermasalah) — mirror preseden M7.11 Keputusan 7/M7.12 Keputusan 4 (item yang tidak bisa diproses di-skip/ditangani aman, bukan meruntuhkan seluruh turn).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Raise exception kalau dependensi hilang/siklus terdeteksi** — ditolak: satu atomic intent bermasalah (kemungkinan besar non-determinisme LLM di layer manapun sebelumnya) tidak seharusnya menggagalkan SELURUH turn ketika atomic intent lain dalam turn yang sama valid dan bisa dieksekusi.

**Dampak**
`kelompokkan_wave()` (Checkpoint 2) mengimplementasikan kedua penanganan ini, diuji eksplisit di unit test.

---

### Keputusan 9: Span baru `orchestration.wave` membungkus tiap iterasi wave

**Sumber Paksaan**
Kebutuhan pembuktian KK M7.14 sendiri (span harus menunjukkan urutan wave 2 setelah wave 1) + preseden `invoke_agent` sebagai satu-satunya span level-orkestrasi sejauh ini (M7.6) — pola serupa perlu diperluas untuk unit observability baru (wave) yang genuinely span dua layer sekaligus (Verification Gate + Execution), tidak cocok jadi tanggung jawab span salah satu layer saja.

**Keputusan yang Diikuti**
Tracer `orchestration` (sama dengan `invoke_agent`), span `orchestration.wave` per wave, atribut `wave.index` (mulai 1), `wave.intent_count`.

**Catatan Ketergantungan**
Tanpa span ini, pembuktian KK M7.14 di Jaeger (urutan wave 2 setelah wave 1) hanya bisa dilihat lewat span `execute_tool`/`verification_gate.check` individual yang tersebar tanpa pengelompokan eksplisit — lebih sulit diverifikasi manual di Checkpoint 7.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kebutuhan pembuktian KK sendiri.

---

### Keputusan 10: Prasyarat reachability `chatbot_api` diverifikasi di Checkpoint 1 (awal), bukan ditunda ke akhir

**Sumber Paksaan**
`docs/keterbatasan-diterima.md` #13, kutip langsung: *"Milestone 7.14... WAJIB mengulang percobaan reachability sebelum dianggap selesai... prioritaskan sebelum Milestone 7.14 dimulai."*

**Keputusan yang Diikuti**
Checkpoint 1 Task 2 menjalankan `scripts/chatbot_api/` dan membuktikan `GET /health` + satu panggilan nyata 200 (reuse skenario M4.1 Checkpoint 5: `role_title="Front Office Staff"`, `employee_id="E0071"`, `view_name="v_lookup_daily_occupancy"`) SEBELUM checkpoint implementasi manapun dimulai. Entri #13 diperbarui statusnya begitu terbukti.

**Catatan Ketergantungan**
Kalau prasyarat ini gagal (server tidak bisa dijalankan/kredensial ternyata tidak valid), SELURUH milestone terblokir sejak awal — lebih baik diketahui di Checkpoint 1 daripada di Checkpoint 7 setelah 6 checkpoint kerja lain selesai.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced eksplisit oleh teks `keterbatasan-diterima.md` #13 sendiri.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Instance lokal benar `scripts/chatbot_api/`, bukan `api/` | B (temuan riset) | Plan |
| 2 | Wave = urutan eksekusi murni, tanpa passing data | A | Plan |
| 3 | Fungsi wave baru di `src/orchestration/wave.py` | B | Plan |
| 4 | `verifikasi_gate_semua()` dipanggil per wave | B | Plan |
| 5 | `eksekusi_atomic_intent_semua()` di `klasifikasi_respons.py`, tanpa tuple | B | Plan |
| 6 | Parameter tambahan `cakupan_individu_result` untuk lookup constraint | B | Plan |
| 7 | Field `execution` flat, bukan nested per-wave | B | Plan |
| 8 | Penanganan dependensi hilang + siklus, fail-open | B | Plan |
| 9 | Span baru `orchestration.wave` | B | Plan |
| 10 | Verifikasi reachability chatbot_api di Checkpoint 1 | B | Plan |
