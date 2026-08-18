# Decisions — Milestone 7.5: Menyambungkan Interpretation (Narasi → Verifikasi Kesetiaan Data)

Dokumen ini mencatat keputusan desain untuk Milestone 7.5, ditentukan sebelum implementasi dimulai (Plan Mode), direncanakan dalam satu sesi bersama Milestone 7.4 (urutan berurutan — 7.4 dituntaskan penuh termasuk commit sebelum 7.5 dimulai). Sama seperti M7.4, investigasi mengonfirmasi Milestone 7.5 genuinely butuh kode orkestrator baru — tidak ada fungsi mana pun di `src/` yang menyambungkan `susun_narasi()` (M4.4) ke `verifikasi_dan_susun_visualisasi()` (M4.5) untuk jalur utama.

---

### Keputusan 1: Orkestrator baru di file terpisah `interpretation.py`, bukan disisipkan ke file sub-langkah

**Sumber Paksaan**
Preseden yang sama dengan M7.4 Keputusan 1 — 2/2 layer multi-langkah yang sudah ada (`domain_gate.py`, `decompose.py`) menempatkan orkestrator di file baru terpisah dari sub-langkah. M7.4 (dikerjakan sebelum milestone ini dalam sesi yang sama) mengikuti pola yang sama untuk Query Engine.

**Keputusan yang Diikuti**
Fungsi baru `susun_dan_verifikasi_narasi()` ditempatkan di `src/layers/interpretation/interpretation.py` (file baru), terpisah dari `narasi.py`, `verifikasi_kesetiaan.py`, dan `visualisasi.py`.

**Catatan Ketergantungan**
Sama seperti M7.4 Keputusan 1.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden yang konsisten.

---

### Keputusan 2: Nama fungsi `susun_dan_verifikasi_narasi()`, return `HasilNarasi` penuh (bukan raw string)

**Sumber Paksaan**
Preseden penamaan `susun_dan_verifikasi_request_atomic_intent()` (M7.4, sesi yang sama) — pola `<verb>_dan_<verb>_...` untuk dua aksi konseptual berbeda. `susun_narasi()` mengembalikan `HasilNarasi{narasi: str}` (satu field) — mengembalikan objek penuh (bukan cuma `.narasi` string) menjaga parity dengan kedua elemen tuple lain yang juga tipe objek, dan caller (Level 2/M7.15, belum dibangun) kemungkinan butuh objek terstruktur untuk logging/tracing konsisten dengan langkah lain, bukan string lepas.

**Keputusan yang Diikuti**
Nama fungsi final: `susun_dan_verifikasi_narasi()`. Return type: `tuple[HasilNarasi, HasilVerifikasiNarasi, list[DataVisualisasi] | None]`.

**Catatan Ketergantungan**
Murni penamaan/bentuk return dampak rendah — dicatat untuk jejak konsistensi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Return `str` mentah untuk narasi** (bukan `HasilNarasi`) — ditolak, tidak konsisten dengan dua elemen tuple lain yang keduanya objek terstruktur, dan membuang informasi struktural tanpa keuntungan nyata (string tetap bisa diakses lewat `.narasi`).

---

### Keputusan 3: Tuple dari tipe yang sudah ada, tanpa skema baru — konsisten dengan keputusan M7.4

**Sumber Paksaan**
Tidak ada konflik skema seperti M7.4 (`HasilNarasi` tidak py field wajib bersarang yang menghalangi konstruksi kasus gagal, karena `susun_narasi()` justru tidak pernah mengembalikan hasil gagal — ia me-raise ulang `APIError`, lihat Keputusan 4). Rasional yang sama dengan M7.4 Keputusan 5 (dipilih user lewat `AskUserQuestion` untuk M7.4): reuse penuh tipe yang sudah ada tanpa skema ketiga yang harus disinkronkan.

**Keputusan yang Diikuti**
Return type `tuple[HasilNarasi, HasilVerifikasiNarasi, list[DataVisualisasi] | None]` — reuse penuh `HasilNarasi` (M4.4), `HasilVerifikasiNarasi` (M4.5), `list[DataVisualisasi]` (M4.5). Tidak ada skema baru ditambahkan ke `src/schemas/interpretation.py`.

**Catatan Ketergantungan**
Karena tidak ada konflik skema yang memaksa alternatif lain (beda dari M7.4), keputusan ini TIDAK diajukan ulang ke user via `AskUserQuestion` — cukup mengikuti preseden desain M7.4 yang baru saja dikonfirmasi dalam sesi yang sama, forced by konsistensi lintas kedua milestone Level 1 yang genuinely butuh kode baru.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Skema baru gabungan** — tidak dipertimbangkan serius, karena tidak ada dorongan struktural (konflik skema) yang memaksanya seperti di M7.4; mengikuti preseden M7.4 langsung adalah pilihan paling konsisten.

---

### Keputusan 4: `APIError` dari `susun_narasi()` dibiarkan menjalar tanpa `try/except`

**Sumber Paksaan**
`susun_narasi()` (`src/layers/interpretation/narasi.py`) secara eksplisit me-raise ulang `APIError` — didokumentasikan sebagai satu-satunya pemanggilan LLM di seluruh codebase tanpa fallback aman, keputusan sengaja Milestone 4.4 (lihat `milestones/4.4-penyusunan-narasi/decisions.md`). Cakupan pekerjaan PIC 7: "Tidak termasuk: Logic internal kesembilan layer itu sendiri... pekerjaan ini memanggil mekanisme yang sudah ada, bukan menulis ulang" (`rancangan-orkestrasi-api.md`).

**Keputusan yang Diikuti**
`susun_dan_verifikasi_narasi()` TIDAK membungkus pemanggilan `susun_narasi()` dengan `try/except` — `APIError` menjalar apa adanya ke caller orkestrator.

**Catatan Ketergantungan**
Menangkap exception ini lalu tidak berbuat apa-apa cuma menyamarkan kesengajaan M4.4; membungkusnya jadi hasil terdegradasi butuh field baru yang tidak py tempat di skema manapun (`HasilNarasi` tidak py varian gagal).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menangkap `APIError` dan mengembalikan hasil terdegradasi** — ditolak, bertentangan langsung dengan keputusan sengaja M4.4 dan batasan "tidak dirombak ulang" PIC 7; juga tidak ada skema yang bisa menampung hasil terdegradasi ini tanpa perubahan skema M4.4 (di luar cakupan).

---

### Keputusan 5: Tidak ada span baru dibuka di level orkestrator

**Sumber Paksaan**
`docs/01-architecture/rancangan-observability-ai-chatbot.md` §2, baris kontrak Interpretation: tepat 2 span `chat`, sudah terpenuhi penuh oleh instrumentasi `susun_narasi()` dan `verifikasi_kesetiaan_narasi()` masing-masing. Preseden yang sama dengan M7.4 Keputusan 7.

**Keputusan yang Diikuti**
`susun_dan_verifikasi_narasi()` adalah fungsi Python murni tanpa `tracer.start_as_current_span()` sendiri.

**Catatan Ketergantungan**
Sama seperti M7.4 Keputusan 7.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by kontrak observability §2 + preseden konsisten.

---

### Keputusan 6: File test baru `tests/layers/interpretation/test_interpretation.py`

**Sumber Paksaan**
Belum ada file test orkestrator untuk layer ini (`test_narasi.py`/`test_verifikasi_kesetiaan.py` masing-masing hanya menguji sub-langkahnya sendiri, full-mock).

**Keputusan yang Diikuti**
File baru `tests/layers/interpretation/test_interpretation.py`, mirror pola `test_query_engine.py` (M7.4): unit test dasar mocked (Checkpoint 2) + test connectivity LLM sungguhan (Checkpoint 3).

**Catatan Ketergantungan**
Sama seperti M7.4 Keputusan 8.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced karena belum ada file yang bisa dipakai ulang.

---

### Keputusan 7: Test connectivity klaim sebab-akibat — mock HANYA return value `susun_narasi()`, verifikasi tetap LLM sungguhan penuh

**Sumber Paksaan**
Genuinely terbuka sebelum plan ditulis — diajukan ke user lewat `AskUserQuestion`. Rule 5 prompt `src/prompts/interpretation/narasi.md` (baris 20) secara eksplisit melarang LLM mengarang klaim sebab-akibat dari data deskriptif: *"Jangan pernah mengarang klaim sebab-akibat dari data yang sifatnya deskriptif ... JANGAN simpulkan salah satu MENYEBABKAN yang lain kecuali data itu sendiri secara eksplisit menyatakan hubungan sebab-akibat."* Pemanggilan `susun_narasi()` sungguhan pada skenario S01 M4.5 (dua kenaikan yang sekadar berkorelasi) kemungkinan besar menghasilkan narasi yang PATUH terhadap Rule 5 ini (tanpa klaim kausal), bertentangan dengan tujuan skenario uji KK M7.5. M4.5 sendiri tidak pernah menyelesaikan masalah ini — eval dan test M4.5 memasok teks narasi langsung sebagai string ke `verifikasi_kesetiaan_narasi()`, tidak pernah lewat `susun_narasi()` sungguhan.

**Keputusan yang Dipilih**
User memilih Opsi A: mock HANYA `susun_narasi()` (`return_value` deterministik berisi teks klaim-kausal S01), sementara `verifikasi_dan_susun_visualisasi()` — yang sebenarnya sedang dibuktikan konektivitasnya — tetap panggilan LLM sungguhan penuh, tanpa mock sama sekali.

**Alasan**
Dipreseden langsung oleh `test_konektivitas_retry_feedback_mengalir_ke_pecah_atomik_berikutnya` (M7.2, `tests/layers/decomposition/test_decompose.py`), yang memaksa hasil langkah pertama (`verifikasi_pemecahan()` percobaan pertama) karena retry alami jarang terjadi dari LLM — dengan alasan eksplisit di docstring test itu sendiri: "Tujuan eksplisit BUKAN menguji kualitas [generation], melainkan menguji wiring." Penerapan yang sama di sini: memaksa HANYA bagian yang provably tidak reliable dipicu secara organik (generasi narasi kausal, yang justru dirancang untuk TIDAK terjadi), sambil menjaga bagian yang benar-benar sedang diuji (verifikasi menangkap klaim kausal, hand-off objek boundary) tetap 100% nyata.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Generasi sepenuhnya organik tanpa mock** — ditolak, melawan perilaku model yang memang sengaja dirancang (Rule 5), sehingga tidak reliable sebagai sinyal test yang bisa diulang; run LLM yang patuh aturan akan membuat test gagal membangun skenarionya sendiri, bukan soal apakah wiring orkestrator benar.

**Dampak**
Ini penyimpangan (didokumentasikan, dipreseden) dari konvensi "tidak pernah mock LLM" M7.2/M7.3 — alasan (Rule 5 `narasi.md`) dikutip eksplisit inline di kode test dan di sini, supaya pembaca berikutnya tidak salah paham sebagai kecerobohan.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Orkestrator baru di file terpisah `interpretation.py` | B | Plan |
| 2 | Nama fungsi `susun_dan_verifikasi_narasi()`, return `HasilNarasi` penuh | B | Plan |
| 3 | Tuple dari tipe yang sudah ada, tanpa skema baru | B | Plan |
| 4 | `APIError` dibiarkan menjalar tanpa `try/except` | B | Plan |
| 5 | Tidak ada span baru di level orkestrator | B | Plan |
| 6 | File test baru | B | Plan |
| 7 | Test klaim sebab-akibat: mock hanya `susun_narasi()` | A | Plan |
