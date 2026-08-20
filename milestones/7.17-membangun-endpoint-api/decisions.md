# Decisions — Milestone 7.17: Membangun Endpoint API

Dokumen ini mencatat keputusan desain untuk Milestone 7.17, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: Narasi yang gagal verifikasi kesetiaan (`lolos=False` ATAU `lolos=None`) diganti pesan generik aman, bukan dikirim apa adanya

**Status:** Diputuskan sebelum implementasi (dikonfirmasi user via `AskUserQuestion` — user minta contoh konkret dulu sebelum memutuskan)

**Latar Belakang**
`HasilVerifikasiNarasi` (M4.5) bisa mengembalikan `lolos=False` (narasi terdeteksi mengandung klaim tidak berdasar data — mis. LLM menambahkan penjelasan sebab-akibat yang tidak didukung `nilai_hasil` yang diambil) atau `lolos=None` (status `GAGAL_TEKNIS`, verifikasi ITU SENDIRI gagal dijalankan). Tidak ada mekanisme retry balik ke M4.4 (sengaja, M7.5 Keputusan 4-5) — begitu verifikasi gagal, narasi ASLI tetap ada di `HasilNarasi.narasi`, tidak pernah diperbaiki otomatis. Genuinely terbuka: endpoint (titik pertama yang benar-benar mengirim narasi ke KLIEN NYATA) harus memutuskan apa yang ditampilkan.

**Keputusan yang Dipilih**
Kapan pun `terverifikasi=False` (lihat definisi di bawah, mencakup `lolos=False` DAN `lolos=None`), field `narasi` di response DIGANTI pesan generik aman (konstanta, belum diklaim mengandung informasi jawaban), BUKAN mengirim `HasilNarasi.narasi` yang asli. `terverifikasi: bool` = `True` hanya kalau `lolos=True` persis. `catatan_verifikasi: str | None` diisi `HasilVerifikasiNarasi.alasan` kapan pun `terverifikasi=False` (termasuk `GAGAL_TEKNIS`, mis. "verifikasi tidak dapat dijalankan").

**Alasan**
User memilih pendekatan konservatif untuk fase awal — mencegah klaim yang berpotensi tidak berdasar (contoh konkret yang dibahas: narasi "revenue turun 18.75% [BENAR] disebabkan penurunan wisatawan asing [karangan LLM, tidak didukung data]") sampai ke user sama sekali, walau konsekuensinya bagian narasi yang sebenarnya VALID juga ikut terbuang.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Kirim narasi asli + metadata jujur (`terverifikasi:false`, biarkan klien yang menampilkan)** — sempat direkomendasikan (konsisten prinsip "kejujuran, tidak menyembunyikan"), TAPI TIDAK dipilih user untuk fase ini — risiko klaim tidak berdasar sampai ke user dinilai lebih penting dihindari dulu daripada mempertahankan bagian narasi yang valid.

**Dampak**
(a) Bagian narasi yang sebenarnya valid ikut terbuang saat verifikasi gagal karena SATU klaim tambahan — dicatat sebagai keterbatasan diterima (`docs/keterbatasan-diterima.md`, entri baru, lihat Keputusan 3 di bawah). (b) Strategi lebih halus (mis. strip hanya klaim yang gagal, bukan buang seluruh narasi) dicatat sebagai keputusan tertunda (`docs/keputusan-tertunda.md`, entri baru #5).

---

### Keputusan 2: Celah defensif laten (IndexError/KeyError) yang ditemukan saat riset TIDAK diperbaiki di file layer manapun

**Status:** Diputuskan sebelum implementasi (dikonfirmasi user — mengikuti rekomendasi)

**Latar Belakang**
Riset plan (pembacaan kode menyeluruh, BUKAN reproduksi nyata) menemukan 2 kelas celah defensif laten: (a) `IndexError` kalau LLM merespons SUKSES (HTTP 200) tapi `response.choices` kosong — 5 titik (`detect_turn_dependency`, 3 sub-langkah Decomposition, `susun_narasi`), TIDAK tertangkap `try/except APIError` yang sudah ada karena bukan `APIError`; (b) `KeyError` kalau invarian fan-in ID meleset (`verifikasi_gate_semua`/`eksekusi_atomic_intent_semua`, dict indexing langsung `dict[id]` bukan `.get(id)`). Keduanya BELUM PERNAH terjadi nyata di eval/produksi manapun sepanjang project — beda dari preseden M7.6 (`detect_turn_dependency` tanpa `try/except` sama sekali) dan M7.7 (`retrieve_session_memory` serupa), yang KEDUANYA ditemukan lewat REPRODUKSI NYATA (skenario eval yang benar-benar crash).

**Keputusan yang Dipilih**
TIDAK mengubah `src/layers/`/`src/orchestration/` manapun untuk menutup celah ini. Endpoint M7.17 tetap aman lewat exception handler catch-all generik (`Exception` → 500, `{"detail": "<pesan aman>"}`) yang otomatis menangkap celah ini KALAU genuinely terjadi. Dicatat sebagai entri baru `docs/keterbatasan-diterima.md` (Keputusan 3 di bawah).

**Alasan**
M7.17 sendiri py batasan mengikat eksplisit "Tidak termasuk: Logic internal kesembilan layer itu sendiri" (`rancangan-orkestrasi-api.md`). Beda kualitatif dari preseden M7.6/M7.7: di sana bug SUDAH TERBUKTI nyata menyebabkan crash (dibuktikan payload eval spesifik), sehingga user secara eksplisit menginstruksikan perbaikan segera SEBAGAI PENGECUALIAN dari batasan tersebut. Di sini celah masih hipotetis/laten — user memilih TIDAK membuat pengecualian yang sama untuk kasus yang belum terbukti terjadi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Perbaiki sekarang, mirror preseden M7.6/M7.7** — dipertimbangkan (perubahan kecil+rendah risiko: guard `if not response.choices`, ganti `.get()`), TAPI TIDAK dipilih user — mengikuti rekomendasi menjaga cakupan M7.17 tetap sesuai batasan mengikat tertulis, mengingat celah belum terbukti nyata.

**Dampak**
Tidak ada dampak fungsional (catch-all sudah menutup risiko kegagalan tak aman) — hanya berarti kalau celah ini genuinely terpicu suatu saat, klien menerima 500 generik (bukan detail spesifik penyebabnya) sampai ada investigasi manual lewat Jaeger/log.

---

### Keputusan 3: Entri baru `docs/keterbatasan-diterima.md` dan `docs/keputusan-tertunda.md`

**Sumber Paksaan**
Konsekuensi langsung Keputusan 1 (dampak bagian narasi valid terbuang + follow-up strategi lebih halus) dan Keputusan 2 (celah laten diterima, bukan diperbaiki) — instruksi eksplisit user untuk mencatat KEDUANYA di backlog project-wide, bukan hanya di `decisions.md` milestone ini.

**Keputusan yang Diikuti**
Dua entri baru `docs/keterbatasan-diterima.md`: (a) narasi gagal verifikasi diganti pesan generik — konteks, dampak (bagian valid ikut terbuang), pemicu peninjauan (revisit begitu ada bukti pola ini sering terjadi/strategi lebih baik tersedia); (b) celah laten IndexError/KeyError — konteks penemuan, kenapa diterima, pemicu peninjauan (begitu genuinely terjadi sekali, prioritaskan perbaikan di file pemilik). Satu entri baru `docs/keputusan-tertunda.md` (#5): strategi lebih halus penanganan narasi gagal verifikasi (mis. strip klaim spesifik, retry bertarget), pemicu peninjauan (bukti nyata pola ini sering terjadi, atau kapasitas untuk redesain M4.4/M4.5).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by instruksi eksplisit user.

---

### Keputusan 4: Upgrade `/v1/turns` existing, bukan endpoint baru terpisah

**Sumber Paksaan**
Komentar eksplisit `src/orchestration/turn_pipeline.py` baris 9-10: *"src/main.py SENGAJA belum memanggil fungsi ini - penyambungan endpoint ditunda ke Milestone 7.17"* — menandakan `/v1/turns` (M1.2) SELALU dimaksudkan sebagai endpoint yang sama, ditingkatkan bertahap, bukan endpoint sekali-pakai untuk Input Layer semata.

**Keputusan yang Diikuti**
`src/main.py::submit_turn()` (route `POST /v1/turns`) diubah memanggil `proses_turn()` penuh, menggantikan perilaku echo-payload M1.2.

**Catatan Ketergantungan**
Handler `ValidationError` → 422 existing DIPERTAHANKAN apa adanya (kontrak M1.2/1.3 tidak berubah — `proses_turn()` sendiri memanggil `validate_turn_payload()` sebagai langkah pertama, exception yang sama tetap menjalar ke handler yang sama).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Endpoint baru terpisah (mis. `/v1/turns/full`), `/v1/turns` lama dipertahankan echo** — tidak dipertimbangkan serius, bertentangan langsung dengan intent eksplisit yang sudah ditandai kode `turn_pipeline.py`.

---

### Keputusan 5: Skema response baru `TurnResponse` di `src/schemas/api_response.py`

**Sumber Paksaan**
Preseden satu-file-per-concern di `src/schemas/` (`orchestration.py`, `interpretation.py`, dst.). Tidak ada schema response API yang sudah ada (`grep "class.*Response" src/` nol hasil, dikonfirmasi riset plan) — genuinely perlu dibangun baru, bukan reuse.

**Keputusan yang Diikuti**
`TurnResponse(BaseModel)`: `session_id: str`, `turn_index: int`, `narasi: str`, `terverifikasi: bool`, `catatan_verifikasi: str | None`, `visualisasi: list[DataVisualisasi] | None` — `DataVisualisasi` di-reuse dari `src/schemas/interpretation.py` (M4.5), tidak didefinisikan ulang.

**Catatan Ketergantungan**
`src/main.py` mengimpor `TurnResponse` dari file ini untuk `response_model=` FastAPI.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Definisikan `TurnResponse` langsung di `src/main.py`** — dipertimbangkan (file kecil, hanya dipakai di sana), TAPI ditolak untuk konsistensi preseden `src/schemas/` sebagai satu-satunya lokasi definisi Pydantic model project.

---

### Keputusan 6: Pemetaan status HTTP untuk kegagalan tak tertangani

**Sumber Paksaan**
Konvensi REST standar — forced karena TIDAK ada spesifikasi status code untuk kasus gagal di dokumen manapun (`rancangan-orkestrasi-api.md` M7.17 hanya menyebut "response 200" untuk kasus sukses; riset plan mengonfirmasi nol hasil pencarian status code lain).

**Keputusan yang Diikuti**
`openai.APIError` → **503 Service Unavailable** (dependency LLM eksternal tidak tersedia, mengisyaratkan klien boleh coba lagi). `sqlalchemy.exc.SQLAlchemyError` / `RuntimeError` → **500 Internal Server Error** (kegagalan internal/DB). Catch-all `Exception` generik → **500** (mencakup celah laten Keputusan 2 KALAU genuinely terjadi). Seluruh body `{"detail": "<pesan aman>"}` — kunci `detail` konsisten handler 422 existing, isi pesan TIDAK memuat tipe/pesan exception asli (defense-in-depth, diverifikasi lewat test Checkpoint 4).

**Catatan Ketergantungan**
Urutan registrasi handler FastAPI penting — handler lebih spesifik (`ValidationError`, `APIError`, `SQLAlchemyError`) harus terdaftar SEBELUM catch-all `Exception` supaya tidak "ditelan" duluan oleh catch-all.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by konvensi REST standar + tidak ada spesifikasi lain yang mengikat.

---

### Keputusan 7: Verifikasi KK1 dibuktikan 2 lapis (kesetaraan field persis via mock + kesetaraan struktural via eval nyata), BUKAN kesamaan teks literal

**Sumber Paksaan**
Realitas non-determinisme LLM (`docs/keterbatasan-diterima.md` #3, dikonfirmasi berulang M7.9-7.16) — dua pemanggilan `proses_turn()` terpisah (satu langsung, satu lewat HTTP) TIDAK akan pernah menghasilkan teks narasi identik meski payload sama persis.

**Keputusan yang Diikuti**
KK1 ("response... sesuai dengan hasil yang sama... membuktikan endpoint tidak mengubah makna") dibuktikan: (a) Checkpoint 4, test deterministik — `proses_turn()` di-mock mengembalikan `KeadaanTurn` TETAP, `_build_turn_response()` dibuktikan TIDAK kehilangan/mengubah field apa pun (kesetaraan PERSIS valid di sini karena input dikontrol penuh); (b) Checkpoint 6, eval nyata — panggilan langsung `proses_turn()` vs panggilan lewat HTTP (payload sama, `session_id` beda) dibandingkan secara STRUKTURAL (status/kategori hasil sama), BUKAN teks identik.

**Catatan Ketergantungan**
`rancangan.md` (Checkpoint 5) WAJIB menyatakan eksplisit standar ini SEBELUM eksekusi, mencegah verdict keliru "gagal" karena menuntut kesamaan teks literal yang mustahil.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by realitas teknis non-determinisme LLM yang sudah berulang kali dikonfirmasi project ini.

---

### Keputusan 8: Port aplikasi sendiri diubah ke 8001

**Sumber Paksaan**
Bentrok port: docstring `main.py` existing (M1.2) menyarankan port 8000, TAPI `chatbot_api` (dipanggil `proses_turn()` internal saat Execution, WAJIB jalan bersamaan) JUGA memakai port 8000 (`CHATBOT_API_BASE_URL`, `src/config/chatbot_api.py`).

**Keputusan yang Diikuti**
Docstring `main.py` diperbarui menyarankan `--port 8001` untuk app milik proyek ini sendiri.

**Catatan Ketergantungan**
`evals/7.17-.../run_eval.py` (Checkpoint 6) memakai port 8001 secara eksplisit, dicek prasyarat sebelum eksekusi (mirror pola `_cek_prasyarat()` M7.14-7.16).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by bentrok port yang genuinely ditemukan riset plan.

---

### Keputusan 9: Tidak ada test unit terpisah khusus schema `TurnResponse`

**Sumber Paksaan**
Preseden `KeadaanTurn` (`src/schemas/orchestration.py`) — schema data murni 15 field tanpa validator kompleks, TIDAK py test file sendiri, diverifikasi tidak langsung lewat test konsumennya.

**Keputusan yang Diikuti**
`TurnResponse` (schema data murni, tanpa validator custom) diverifikasi via test `main.py`/`_build_turn_response()` (Checkpoint 4), bukan test schema berdiri sendiri.

**Catatan Ketergantungan**
Kalau di kemudian hari `TurnResponse` mendapat validator custom (mis. konsistensi `terverifikasi`/`catatan_verifikasi` mirror `HasilVerifikasiNarasi`), pertimbangkan ulang kebutuhan test khusus saat itu.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden konsisten `src/schemas/`.

---

### Keputusan 10: Autentikasi HTTP, Dockerfile, deployment produksi — di luar cakupan

**Sumber Paksaan**
`CLAUDE.md` "Batas Implementasi Saat Ini" — tidak membangun kapabilitas di luar cakupan 9 dokumen sumber kebenaran kecuali user memperluas. Riset plan mengonfirmasi nol hasil pencarian "API key"/"JWT"/"Bearer"/"autentikasi" di seluruh `docs/`, dan tidak ada `Dockerfile`/entrypoint deployment untuk `src/main.py` yang sudah ada.

**Keputusan yang Diikuti**
M7.17 TIDAK membangun mekanisme autentikasi/otorisasi di level HTTP (RBAC tetap sepenuhnya di Domain Gate + `chatbot_api`, sesuai prinsip arsitektur existing), TIDAK membangun `Dockerfile`/mekanisme deployment produksi.

**Catatan Ketergantungan**
Kalau user memperluas cakupan di kemudian hari (mis. sebelum endpoint benar-benar dipublikasikan ke frontend nyata), ini perlu direvisit sebagai milestone/task terpisah, bukan diam-diam ditambahkan di sini.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by batasan cakupan project yang eksplisit.

---

### Keputusan 11: Panduan integrasi frontend baru di `docs/panduan-integrasi-frontend.md`

**Sumber Paksaan**
Instruksi eksplisit user ("tambahkan juga dokumen panduan cara menggunakan api ini... tambakan juga template output dari api ini... jadi frontend harus punya panduan") — perluasan cakupan M7.17 di tengah Plan Mode.

**Keputusan yang Diikuti**
Dokumen baru di top-level `docs/` (bukan subfolder `01-architecture/`/`02-implementation-plan/`/`03-domain-source/` yang khusus dokumen fase desain final sebelum implementasi). Nama SENGAJA dibedakan dari `docs/03-domain-source/api-chatbot.md` (API BERBEDA — itu API Lapis 2 yang DIKONSUMSI sistem ini; dokumen baru ini soal API yang DISEDIAKAN sistem ini ke frontend). Contoh request/response WAJIB dikutip dari payload nyata `evals/7.17-.../payloads/*.json` (Checkpoint 6), bukan dikarang — kecuali ditandai eksplisit sebagai contoh terkonstruksi (lihat Risiko & Mitigasi plan soal kasus `terverifikasi=false` yang mungkin tidak muncul organik).

**Catatan Ketergantungan**
Checkpoint 7 (penulisan panduan) HARUS setelah Checkpoint 6 (eksekusi nyata) selesai — urutan checkpoint mencerminkan ketergantungan ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by instruksi eksplisit user (lokasi/nama file sendiri adalah keputusan turunan kecil, bukan hal yang diperdebatkan).

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Narasi gagal verifikasi diganti pesan generik | A | Plan |
| 2 | Celah laten TIDAK diperbaiki di layer manapun | A | Plan |
| 3 | Entri baru keterbatasan-diterima + keputusan-tertunda | B | 1 |
| 4 | Upgrade `/v1/turns` existing | B | Plan |
| 5 | Skema `TurnResponse` baru | B | Plan |
| 6 | Pemetaan status HTTP kegagalan | B | Plan |
| 7 | Verifikasi KK1 2 lapis, bukan teks literal | B | Plan |
| 8 | Port aplikasi sendiri ke 8001 | B | Plan |
| 9 | Tidak ada test schema terpisah | B | Plan |
| 10 | Autentikasi/Dockerfile di luar cakupan | B | Plan |
| 11 | Panduan integrasi frontend baru | B | Plan |
