# Decisions — Milestone 7.12: Sambungan 7 (Retriever → Query Engine)

Dokumen ini mencatat keputusan desain untuk Milestone 7.12, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: `KeadaanTurn.query_engine` mempertahankan bentuk tuple `list[tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]]` apa adanya, tanpa skema baru

**Status:** Diputuskan sebelum implementasi (dari plan)

**Latar Belakang**
`susun_dan_verifikasi_request_atomic_intent()` (M7.4) mengembalikan `tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]` — `decisions.md` M7.4 Keputusan 5 eksplisit mencatat ini sebagai keputusan yang sengaja belum ditutup permanen: "Kalau nanti M7.6 [Level 2] menemukan bentuk ini menyulitkan, dicatat sebagai revisit di `docs/keputusan-tertunda.md` sebelum kode Level 2 banyak bergantung padanya." M7.12 adalah konsumen Level 2 PERTAMA yang sesungguhnya memakai kontrak ini dalam konteks batch (`list[...]`) — genuinely terbuka apakah bentuk tuple tetap dipertahankan atau dibungkus skema baru bernama.

**Keputusan yang Dipilih**
`KeadaanTurn.query_engine: list[tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]]` — TIDAK ada skema baru ditambahkan ke `src/schemas/query_engine.py`.

**Alasan**
Ditelusuri dulu apakah ada blocker teknis nyata sebelum diputuskan: Pydantic v2 mendukung `tuple[X, Y]` sebagai field type tanpa masalah (serialisasi JSON otomatis jadi array), fungsi batch baru bisa langsung `[susun_dan_verifikasi_request_atomic_intent(...) for item in daftar]` tanpa kode pembungkus tambahan, dan M7.13 (konsumen berikutnya) bisa unpacking Python biasa (`for hasil_susun, hasil_verifikasi in keadaan_turn.query_engine`). Kompleksitas tri-state (susun gagal → verifikasi `None`; berhasil tapi `lolos=False`; keduanya berhasil `lolos=True`) tetap ada apa pun bentuknya — membungkus jadi named schema hanya mengganti cara akses (`.penyusunan`/`.verifikasi` vs `[0]`/`[1]`), tidak menghilangkan kerumitan itu. Bahasa "revisit kalau menyulitkan" di `decisions.md` M7.4 murni bahasa jaga-jaga (hedging) sebelum ada konsumen nyata, bukan prediksi pasti — karena riset tidak menemukan hambatan konkret, dipertahankan konsisten preseden M7.4 "tidak ada skema baru di `query_engine.py`".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Bungkus jadi skema baru `QueryEngineResult(penyusunan, verifikasi)`** — dipertimbangkan untuk keterbacaan (field bernama lebih self-documenting di payload JSON eval dan saat M7.13 mengakses field-nya), tapi ditolak: menyimpang dari preseden "tidak ada skema baru" M7.4 tanpa masalah teknis konkret yang mendasarinya, menambah satu lapis abstraksi untuk kasus yang belum terbukti butuh.

**Dampak**
M7.13 (Sambungan 8: Query Engine → Verification Gate) akan mengonsumsi `KeadaanTurn.query_engine` dalam bentuk tuple ini — kalau M7.13 nanti menemukan bentuk ini genuinely menyulitkan, itu jadi data point KEDUA (setelah M7.12 sendiri tidak menemukan masalah) untuk dipertimbangkan ulang, dicatat di `docs/keputusan-tertunda.md`.

---

### Keputusan 2: Fungsi batch baru `susun_dan_verifikasi_request_semua()` ditempatkan di `src/layers/query_engine/query_engine.py`

**Sumber Paksaan**
Preseden M7.11 Keputusan 3 (fungsi batch baru Retriever, `proses_retrieval_semua()`, ditempatkan di layer package sendiri `kecukupan_struktural.py`, bukan inline `turn_pipeline.py`) — dikonfirmasi user secara eksplisit satu milestone lalu. Diperkuat preseden SAMA-FOLDER: `verifikasi_bentuk_request_semua()` (`verifikasi_bentuk_request.py`) sudah ada di package `query_engine/` mengikuti pola identik ("span pembungkus non-LLM dengan statistik agregat, mirror `nilai_kecocokan_makna_semua()`/`identifikasi_domain_semua()`").

**Keputusan yang Diikuti**
Fungsi baru ditambahkan di `src/layers/query_engine/query_engine.py` (file yang sama dengan `susun_dan_verifikasi_request_atomic_intent()`, M7.4).

**Catatan Ketergantungan**
Menempatkan di `turn_pipeline.py` akan menyimpang dari konvensi arsitektur de facto proyek (setiap layer memiliki wrapper batch-nya sendiri) tanpa alasan teknis baru — preseden ini baru saja dikonfirmasi ulang di M7.11, tidak ada dasar untuk menyimpang lagi satu milestone kemudian.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden ganda (M7.11 + `verifikasi_bentuk_request_semua()` di folder yang sama) — tidak diajukan ulang ke user karena persis pertanyaan yang sudah dijawab eksplisit di M7.11.

---

### Keputusan 3: Fungsi batch memanggil `susun_dan_verifikasi_request_atomic_intent()` (M7.4) per item — bukan pola two-phase yang dipakai `_revisi_request()` (M4.2)

**Sumber Paksaan**
`decisions.md` M7.4 Keputusan 5 eksplisit: "Kontrak ini akan dipakai M7.6+ (Level 2, belum dibangun) sebagai bentuk pemanggilan Query Engine dari orkestrasi antar-layer." Fungsi ini SENGAJA dirancang untuk titik wiring seperti M7.12. Pola alternatif (`_revisi_request()` M4.2: panggil `susun_request_atomic_intent()` untuk batch, filter `BERHASIL`, baru batch-call `verifikasi_bentuk_request_semua()`) dirancang untuk tujuan BERBEDA (jalur revisi `400` dari Execution, bukan aliran segar pertama kali dari Retriever).

**Keputusan yang Diikuti**
`susun_dan_verifikasi_request_semua()` murni loop memanggil `susun_dan_verifikasi_request_atomic_intent(atomic_intent, view_name_final)` per item, TIDAK memanggil `verifikasi_bentuk_request_semua()` secara terpisah.

**Catatan Ketergantungan**
Memakai jalur `_revisi_request()` (two-phase) akan mengabaikan kontrak yang sudah sengaja disiapkan M7.4 untuk titik ini, dan menambah kompleksitas (dua tahap terpisah) tanpa manfaat — `susun_dan_verifikasi_request_atomic_intent()` sudah menangani short-circuit (Langkah 2 tidak dipanggil kalau Langkah 1 gagal) secara internal.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Reimplementasi pola two-phase `_revisi_request()`** — ditolak: dirancang untuk kasus revisi (`feedback` terisi, `view_name` sudah diketahui gagal sebelumnya), bukan aliran segar M7.12; forced by kontrak M7.4 Keputusan 5 yang eksplisit menyasar titik ini.

---

### Keputusan 4: Item dengan `HasilKecukupanStruktural.view_name_final=None` di-SKIP dari pemanggilan Query Engine

**Sumber Paksaan**
Signature `susun_request_atomic_intent(atomic_intent, view_name: str, ...)` (M3.4, `penyusunan_request.py`) — parameter `view_name` non-Optional (`str`, bukan `str | None`). Tidak ada jalur aman memanggil dengan `None`.

**Keputusan yang Diikuti**
`susun_dan_verifikasi_request_semua()` memfilter `daftar_retriever` ke item `view_name_final is not None` SEBELUM memanggil `susun_dan_verifikasi_request_atomic_intent()`.

**Catatan Ketergantungan**
Ini BEDA prinsip dari M7.11 Keputusan 7 (Retriever sengaja TIDAK memfilter, karena `proses_retrieval_atomic_intent()` terbukti aman menerima `domain_diizinkan=[]`) — di sini filtering bukan preferensi menghindari duplikasi logic, melainkan forced murni oleh tipe parameter yang tidak menerima `None` sama sekali. Filtering di level orkestrator adalah SATU-SATUNYA cara aman, bukan pilihan di antara alternatif.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by signature — memanggil dengan `view_name=None` akan menyebabkan `TypeError`/kegagalan validasi type-hint, bukan perilaku terdegradasi yang aman.

---

### Keputusan 5: `view_name` dan `view_name_tervalidasi_retriever` keduanya diisi dari `HasilKecukupanStruktural.view_name_final` yang SAMA

**Sumber Paksaan**
KK M7.12 sendiri (`rancangan-orkestrasi-api.md`): "View hasil Retriever untuk suatu kebutuhan mengalir ke Query Engine dan menghasilkan request dengan `view_name` yang persis sama [dengan hasil Retriever]."

**Keputusan yang Diikuti**
`susun_dan_verifikasi_request_atomic_intent(atomic_intent, view_name_final)` dipanggil dengan HANYA parameter `view_name` diisi (`view_name_tervalidasi_retriever` dibiarkan default `None`, yang menurut logic M7.4 sendiri otomatis di-set sama dengan `view_name`).

**Catatan Ketergantungan**
Parameter `view_name_tervalidasi_retriever` terpisah SENGAJA dirancang M7.4 untuk mereproduksi skenario MISMATCH (test M3.5 sendiri) — di titik wiring produksi M7.12, tidak ada sumber "nilai berbeda" yang valid untuk diisi di sana; memaksa nilai berbeda di titik ini akan menciptakan mismatch buatan yang tidak mencerminkan aliran data nyata.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by KK M7.12 + tidak ada sumber data lain yang valid untuk `view_name_tervalidasi_retriever` di titik wiring ini.

---

### Keputusan 6: `tanggal_referensi`/`feedback` dibiarkan default `None`

**Sumber Paksaan**
`feedback` (parameter M7.4) khusus dipakai jalur revisi balik dari Execution pada kegagalan `400` (`rancangan-retrieval-query.md` "Catatan Serah Terima": "Jalur perbaikan untuk request yang gagal di tahap Execution... kembali ke Milestone 3.4 untuk direvisi") — milestone TERPISAH (M7.14, Verification Gate → Execution, belum dikerjakan), bukan cakupan M7.12. `tanggal_referensi` tidak py sumber data di `TurnPayload` (dikonfirmasi: hanya `session_id`, `turn_index`, `role_title`, `employee_id`, `question`, `history`).

**Keputusan yang Diikuti**
Kedua parameter dibiarkan default `None` pada pemanggilan dari `susun_dan_verifikasi_request_semua()`.

**Catatan Ketergantungan**
Memaksa nilai untuk `feedback` di titik ini tidak masuk akal (belum ada percobaan sebelumnya yang gagal untuk direvisi — ini pemanggilan PERTAMA). `tanggal_referensi` diasumsikan ditangani default internal M3.4 sendiri (di luar cakupan M7.12 untuk diverifikasi/diubah).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by tidak adanya sumber data yang valid + `feedback` secara desain milik milestone lain (M7.14).

---

### Keputusan 7: `KeadaanTurn` bertambah field `query_engine`, non-Optional, panjang bisa lebih pendek dari `retriever`

**Sumber Paksaan**
Preseden konsisten M7.6-7.11: tiap unit yang disambungkan dapat field sendiri di `KeadaanTurn`, dipertahankan untuk observability/downstream. Panjang list yang lebih pendek dari input sudah dua kali terjadi sebelumnya (M7.10: `domain_gate` lebih pendek dari `matches`; M7.11: `otorisasi`/`cakupan_individu` bisa lebih pendek dari `domain_gate` untuk entri `GAGAL_TEKNIS`).

**Keputusan yang Diikuti**
`query_engine: list[tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]]` — wajib tanpa default, TIDAK dibungkus try/except baru (fungsi batch tidak pernah raise — filter murni, panggilan ke fungsi M7.4 yang sendiri sudah full-fallback).

**Catatan Ketergantungan**
Panjang `query_engine` BISA lebih pendek dari `retriever` (item `view_name_final=None` di-skip, Keputusan 4) — bukan indikasi kegagalan, desain yang forced.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden M7.6-7.11 + Keputusan 4 di atas.

---

### Keputusan 8: Fungsi batch baru membuka span pembungkus dengan atribut `intent.count`

**Sumber Paksaan**
Preseden SEKARANG 5-6x konsisten: `domain_gate.identifikasi_semua`, `domain_gate.periksa_otorisasi_semua`, `domain_gate.deteksi_constraint_semua`, `retriever.proses_semua` (M7.11), DAN `query_engine.verifikasi_bentuk_request_semua` yang sudah hidup di folder `query_engine/` yang SAMA dengan fungsi baru ini.

**Keputusan yang Diikuti**
`susun_dan_verifikasi_request_semua()` membuka span baru (nama mengikuti pola `query_engine.susun_dan_verifikasi_request_semua`), tracer yang sudah didefinisikan di `query_engine.py`, atribut `intent.count` = panjang `daftar_retriever` SEBELUM filter (mengikuti pola `identifikasi_domain_semua()`/`periksa_otorisasi_semua()` yang mencatat jumlah INPUT yang diproses, bukan jumlah OUTPUT).

**Catatan Ketergantungan**
Tidak ada atribut tambahan lain yang perlu — kontrak observability Query Engine (`request.domain`/`request.view_name`) sudah terpenuhi di span `chat` M3.4/M3.5 masing-masing per item.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by pola konsisten 5-6x preseden, termasuk contoh SAMA-FOLDER.

---

### Keputusan 9: Tidak ada instrumentasi span baru di luar wrapping span `_semua()`

**Sumber Paksaan**
`rancangan-orkestrasi-api.md` baris 10: "observability lintas-layer di luar span pembungkus (sudah tercakup instrumentasi masing-masing PIC 1-4)". Kontrak observability Query Engine (`request.domain`/`request.view_name` di M3.4, kepatuhan sumber M3.5) sudah lengkap dari span existing.

**Keputusan yang Diikuti**
M7.12 murni wiring — tidak menambah atribut/span baru di `penyusunan_request.py`/`verifikasi_bentuk_request.py`.

**Catatan Ketergantungan**
Menambah instrumentasi baru di logic internal M3.4/M3.5 akan melanggar batasan "Tidak termasuk: Logic internal kesembilan layer... memanggil mekanisme yang sudah ada, bukan menulis ulang."

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by batasan dokumen sumber.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Field `query_engine` mempertahankan bentuk tuple, tanpa skema baru | A | Plan |
| 2 | Fungsi batch baru di `query_engine.py` | B | Plan |
| 3 | Memanggil `susun_dan_verifikasi_request_atomic_intent()` per item, bukan pola two-phase | B | Plan |
| 4 | Item `view_name_final=None` di-skip | B | Plan |
| 5 | `view_name`/`view_name_tervalidasi_retriever` sama-sama dari `view_name_final` | B | Plan |
| 6 | `tanggal_referensi`/`feedback` default `None` | B | Plan |
| 7 | Field `query_engine` non-Optional, bisa lebih pendek dari `retriever` | B | Plan |
| 8 | Span pembungkus `intent.count` | B | Plan |
| 9 | Tidak ada instrumentasi span baru | B | Plan |
