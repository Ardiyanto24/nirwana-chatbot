# Decisions — Milestone 7.4: Menyambungkan Query Engine (Susun Request → Verifikasi Bentuk Request)

Dokumen ini mencatat keputusan desain untuk Milestone 7.4, ditentukan sebelum implementasi dimulai (Plan Mode), direncanakan dalam satu sesi bersama Milestone 7.5 (urutan berurutan, bukan paralel) atas permintaan user. Berbeda dari Milestone 7.2/7.3 (kode penyambung sudah ada), investigasi mengonfirmasi Milestone 7.4 genuinely butuh kode orkestrator baru — tidak ada fungsi mana pun di `src/` yang menyambungkan `susun_request_atomic_intent()` (M3.4) ke `verifikasi_bentuk_request_atomic_intent()` (M3.5) untuk jalur utama.

---

### Keputusan 1: Orkestrator baru di file terpisah `query_engine.py`, bukan disisipkan ke file sub-langkah

**Sumber Paksaan**
Preseden 2/2 layer multi-langkah yang sudah ada di codebase: `src/layers/domain_gate/domain_gate.py::identifikasi_domain_atomic_intent()` (M2.1) dan `src/layers/decomposition/decompose.py::decompose_question()` (M1.6) — keduanya menempatkan fungsi orkestrator di file BARU terpisah dari file sub-langkah (`identifikasi.py`/`verifikasi_titik_buta.py`, `klasifikasi.py`/`pemecahan.py`/`verifikasi.py`), tidak pernah disisipkan ke salah satu file sub-langkah yang sudah ada.

**Keputusan yang Diikuti**
Fungsi baru `susun_dan_verifikasi_request_atomic_intent()` ditempatkan di `src/layers/query_engine/query_engine.py` (file baru), terpisah dari `penyusunan_request.py` dan `verifikasi_bentuk_request.py`.

**Catatan Ketergantungan**
Menyisipkan ke salah satu file sub-langkah akan memecah preseden konsisten yang sudah dipakai 2 layer sebelumnya tanpa alasan kuat.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden yang konsisten di seluruh codebase.

---

### Keputusan 2: Nama fungsi `susun_dan_verifikasi_request_atomic_intent()`

**Sumber Paksaan**
Preseden penamaan gabungan `verifikasi_dan_susun_visualisasi()` (M4.5, `src/layers/interpretation/verifikasi_kesetiaan.py`) — dipilih dari dua pola penamaan orkestrator yang sudah ada di codebase (`<verb>_dan_<verb>_...` vs `<verb_tunggal>_..._atomic_intent` seperti `identifikasi_domain_atomic_intent`). Pola `dan` dipakai karena Susun dan Verifikasi adalah dua aksi konseptual yang berbeda (bukan satu aksi dengan langkah verifikasi terlipat di dalamnya, seperti framing "identifikasi domain (dengan verifikasi titik buta)").

**Keputusan yang Diikuti**
Nama fungsi final: `susun_dan_verifikasi_request_atomic_intent()`.

**Catatan Ketergantungan**
Murni penamaan, dampak rendah — dicatat di sini untuk jejak konsistensi, bukan karena mahal diubah.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`proses_request_atomic_intent()`** — ditolak, nama generik "proses" tidak menyebutkan dua aksi konkret yang terjadi, tidak konsisten dengan pola penamaan deskriptif yang dipakai di seluruh codebase.

---

### Keputusan 3: Parameter `view_name_tervalidasi_retriever` terpisah dari `view_name`, default ke `view_name`

**Sumber Paksaan**
Kutipan literal Kriteria Keberhasilan M7.4 di `rancangan-orkestrasi-api.md`: "Request yang sengaja dibuat tidak sesuai hasil Retriever (skenario uji yang sudah dipakai Milestone 3.5) berhasil ditangkap saat mengalir dari langkah Susun ke langkah Verifikasi secara berurutan nyata." Ditemukan lewat investigasi: `request.view_name` (M3.4) di-set deterministik dari parameter `view_name` fungsi `susun_request_atomic_intent()` itu sendiri (`src/layers/query_engine/penyusunan_request.py`, `QueryEngineRequest(view_name=view_name, ...)` — bukan dari jawaban LLM). Kalau orkestrator baru cuma menerima satu parameter `view_name` yang dipakai untuk kedua pemanggilan (seperti satu-satunya caller nyata yang sudah ada, `_revisi_request()` di `klasifikasi_respons.py`), maka `request.view_name` hasil Susun dan `view_name_tervalidasi_retriever` yang diterima Verifikasi akan SELALU sama by construction — skenario mismatch KK1 M3.5 jadi mustahil direproduksi lewat chain nyata orkestrator ini.

**Keputusan yang Diikuti**
Fungsi baru mengekspos `view_name_tervalidasi_retriever: str | None = None` sebagai parameter terpisah dari `view_name: str`. Kalau `None`, default ke nilai `view_name` (mempertahankan perilaku satu-satunya caller nyata yang ada sekarang, yang secara implisit memakai nilai identik). Kalau diisi eksplisit dengan nilai berbeda, memungkinkan skenario mismatch KK1 M3.5 dibuktikan lewat chain nyata.

**Alasan**
Ini satu-satunya bentuk yang memenuhi KK M7.4 (butuh kemungkinan nilai berbeda untuk menguji mismatch) SEKALIGUS mempertahankan perilaku default yang konsisten dengan pemakaian nyata yang sudah ada (`_revisi_request`, yang akan tetap bekerja sama persis kalau suatu saat direfactor memakai fungsi ini — meski refactor itu di luar cakupan M7.4, lihat Keputusan 6).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Satu parameter `view_name` saja, dipakai untuk kedua pemanggilan** — ditolak karena membuat KK M7.4 secara struktural mustahil dibuktikan lewat chain nyata (lihat Sumber Paksaan di atas), bukan soal preferensi gaya.
- **Konstruksi input Verifikasi secara manual terpisah dari output Susun untuk skenario test** — ditolak eksplisit oleh teks KK M7.4 sendiri: "bukan diuji dengan input Verifikasi yang disusun manual terpisah dari output Susun."

---

### Keputusan 4: `tanggal_referensi` dan `feedback` diteruskan apa adanya (pass-through) ke `susun_request_atomic_intent`

**Sumber Paksaan**
Kelengkapan API — `susun_request_atomic_intent()` (M3.4) sudah py kedua parameter opsional ini (`tanggal_referensi: date | None = None`, `feedback: str | None = None`), tidak ada alasan menyembunyikannya dari orkestrator baru.

**Keputusan yang Diikuti**
Fungsi baru mengekspos `tanggal_referensi: date | None = None` dan `feedback: str | None = None`, diteruskan langsung ke `susun_request_atomic_intent()`.

**Catatan Ketergantungan**
Kalau tidak diekspos, caller yang butuh kedua parameter ini (mis. jalur revisi yang mungkin suatu saat mengadopsi orkestrator ini) harus memanggil `susun_request_atomic_intent()` secara terpisah, menghilangkan gunanya orkestrator.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by kelengkapan API, tidak ada trade-off nyata.

---

### Keputusan 5: Return type `tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]` — tanpa skema baru

**Sumber Paksaan**
Genuinely terbuka sebelum plan ditulis — diajukan ke user lewat `AskUserQuestion`. Konflik skema ditemukan lewat investigasi: `HasilVerifikasiBentukRequest.request` (`src/schemas/query_engine.py`) wajib terisi (non-null, ditegakkan `model_validator`), sehingga saat `susun_request_atomic_intent()` gagal (status `GAGAL_TEKNIS`, `request=None`), orkestrator baru TIDAK BISA mengembalikan instance valid dari tipe M3.5 — beda dari preseden `domain_gate.py` yang bisa mendegradasi ke tipe gabungannya sendiri (`AtomicIntentDomains(domains=[], status=GAGAL_TEKNIS)`) karena field gabungannya cuma `list` kosong, bukan objek bersarang wajib.

**Keputusan yang Diikuti**
User memilih Opsi A: `tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]` — elemen kedua `None` kalau langkah Susun gagal/tidak menghasilkan request. Tidak ada skema baru ditambahkan ke `src/schemas/query_engine.py`.

**Alasan**
Meniru pola `verifikasi_dan_susun_visualisasi()` (M4.5, `src/layers/interpretation/verifikasi_kesetiaan.py`) persis — bentuk "langkah 2 cuma jalan/ada kalau gate langkah 1 lolos" yang sama, dengan analogi struktural terdekat yang sudah ada di codebase. Reuse penuh kedua tipe yang sudah ada, tanpa skema ketiga yang harus disinkronkan tiap kali M3.4/M3.5 berubah.

**Dampak**
Kontrak ini akan dipakai M7.6+ (Level 2, belum dibangun) sebagai bentuk pemanggilan Query Engine dari orkestrasi antar-layer. Kalau nanti M7.6 menemukan bentuk tuple ini menyulitkan, dicatat sebagai revisit di `docs/keputusan-tertunda.md` sebelum kode Level 2 banyak bergantung padanya (lihat Risiko & Mitigasi plan).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Skema baru gabungan gaya `HasilQueryEngineRequest`** (meniru `DecompositionResult` M1.6) — ditolak karena kedua skema yang sudah ada (`HasilPenyusunanRequest`, `HasilVerifikasiBentukRequest`) sudah mencakup seluruh info yang caller butuhkan (atomic_intent, request, status, lolos, alasan); skema baru cuma jadi reshuffling field yang sudah tersedia, menambah maintenance surface tanpa nilai ekspresif baru. Beda dari `DecompositionResult` yang justru merangkum 3 langkah jadi 1 bentuk flat yang TIDAK direpresentasikan skema manapun sebelumnya.

---

### Keputusan 6: `_revisi_request()` (M4.2) TIDAK direfactor untuk memakai orkestrator baru

**Sumber Paksaan**
Lingkup M7.4 di `rancangan-orkestrasi-api.md` hanya menyebut "Menyambungkan dua pemanggilan LLM berurutan Query Engine (Milestone 3.4-3.5)" — tidak menyebut refactor caller lain yang sudah ada. Cakupan pekerjaan PIC 7 secara umum: "Tidak termasuk: Logic internal kesembilan layer itu sendiri... pekerjaan ini memanggil mekanisme yang sudah ada, bukan menulis ulang."

**Keputusan yang Diikuti**
`_revisi_request()` di `src/layers/execution/klasifikasi_respons.py` (M4.2, jalur revisi HTTP 400) dibiarkan seperti sekarang — tidak diubah untuk memanggil `susun_dan_verifikasi_request_atomic_intent()` yang baru, meski secara logic keduanya melakukan hal serupa.

**Catatan Ketergantungan**
Merefactor M4.2 di luar Lingkup M7.4 yang eksplisit, berisiko menyentuh kode Execution layer (PIC 4) yang sudah selesai dan teruji tanpa alasan bug.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Merefactor `_revisi_request()` memakai orkestrator baru** — ditolak, di luar Lingkup dokumen sumber M7.4; dicatat sebagai follow-up potensi deduplikasi di `report.md`, bukan dikerjakan sekarang.

---

### Keputusan 7: Tidak ada span baru dibuka di level orkestrator

**Sumber Paksaan**
`docs/01-architecture/rancangan-observability-ai-chatbot.md` §2, baris kontrak Query Engine: tepat 2 span `chat`, sudah terpenuhi penuh oleh instrumentasi `susun_request_atomic_intent()` dan `verifikasi_bentuk_request_atomic_intent()` masing-masing (diverifikasi langsung di kedua file). Preseden: `identifikasi_domain_atomic_intent()` (domain_gate.py) dan `decompose_question()` (decompose.py) — orkestrator level-atomic-intent-tunggal keduanya, sama-sama TIDAK membuka span pembungkus sendiri, murni mengandalkan span sub-langkah masing-masing.

**Keputusan yang Diikuti**
`susun_dan_verifikasi_request_atomic_intent()` adalah fungsi Python murni tanpa `tracer.start_as_current_span()` sendiri — hanya memanggil dua fungsi yang sudah terinstrumentasi.

**Catatan Ketergantungan**
Menambah span baru di sini akan menyimpang dari kontrak §2 (yang secara eksplisit hanya mensyaratkan 2 span, bukan 3) tanpa dasar.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by kontrak observability §2 + preseden konsisten.

---

### Keputusan 8: File test baru `tests/layers/query_engine/test_query_engine.py`, connectivity test memakai LLM sungguhan

**Sumber Paksaan**
Belum ada file test orkestrator untuk layer ini (`test_penyusunan_request.py`/`test_verifikasi_bentuk_request.py` masing-masing hanya menguji sub-langkahnya sendiri, full-mock). Filosofi pengujian M7 (preseden M7.2/M7.3 Keputusan 2, instruksi eksplisit user: "uji hanya dilakukan untuk memastikan antar llm call saling terhubung dan request bisa mengalir") mensyaratkan test connectivity memakai LLM sungguhan, bukan mock, dengan spy (`side_effect`/`wraps`) untuk membuktikan identity objek di boundary.

**Keputusan yang Diikuti**
File baru `tests/layers/query_engine/test_query_engine.py`. Test connectivity KK (Checkpoint 3) memanggil LLM sungguhan untuk langkah Susun, `skipif` tanpa `OPENROUTER_API_KEY` (konsisten preseden M7.1-7.3). Aman dipakai di sini karena skenario KK1 M3.5 bersifat deterministik (bergantung `view_name` yang di-set kode, bukan isi jawaban LLM) — tidak ada risiko flaky dari konten LLM.

**Catatan Ketergantungan**
Sama seperti M7.2/M7.3 Keputusan 2 — risiko klaim keliru dimitigasi lewat assersi identity objek langsung, bukan cuma kecocokan hasil akhir.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Test dengan mock/manual di kedua langkah** — ditolak, bertentangan langsung dengan filosofi pengujian M7 dan teks KK M7.4 sendiri ("bukan diuji dengan input Verifikasi yang disusun manual terpisah dari output Susun").

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Orkestrator baru di file terpisah `query_engine.py` | B | Plan |
| 2 | Nama fungsi `susun_dan_verifikasi_request_atomic_intent()` | B | Plan |
| 3 | Parameter `view_name_tervalidasi_retriever` terpisah, default ke `view_name` | B | Plan |
| 4 | `tanggal_referensi`/`feedback` pass-through | B | Plan |
| 5 | Return type tuple, tanpa skema baru | A | Plan |
| 6 | `_revisi_request()` (M4.2) tidak direfactor | B | Plan |
| 7 | Tidak ada span baru di level orkestrator | B | Plan |
| 8 | File test baru, connectivity pakai LLM sungguhan | B | Plan |
