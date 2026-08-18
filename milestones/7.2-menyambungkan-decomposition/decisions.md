# Decisions — Milestone 7.2: Menyambungkan Decomposition (Klasifikasi → Pemecahan → Verifikasi)

Dokumen ini mencatat keputusan desain untuk Milestone 7.2, ditentukan sebelum implementasi dimulai (Plan Mode), berdasarkan investigasi menyeluruh atas seluruh unit multi-langkah LLM di project (bukan hanya Decomposition).

---

### Keputusan 1: Kode penyambung sudah ada sejak Milestone 1.6 Checkpoint 7 — M7.2 tidak menulis kode baru

**Sumber Paksaan**
Investigasi langsung sebelum plan ditulis: `src/layers/decomposition/decompose.py::decompose_question()` sudah memanggil `klasifikasi_kebutuhan()` sekali, lalu loop `pecah_atomik(question, klasifikasi, feedback)` → `verifikasi_pemecahan(question, hasil)` hingga 3 kali — nilai `klasifikasi` (return `KlasifikasiKebutuhan` apa adanya), `hasil` (return `PemecahanResult` apa adanya), dan `feedback=verifikasi.alasan` pada retry, seluruhnya diteruskan tanpa modifikasi. `git log --follow -- src/layers/decomposition/decompose.py` menunjukkan **satu commit tunggal** (`33a53cf feat(milestone-1.6): orkestrator decompose_question + kebijakan retry`, Checkpoint 7 M1.6, 2026-08-15). `milestones/1.6-decomposition/logs.md` Checkpoint 7 mencatat smoke test end-to-end nyata ("bandingkan Maret dengan Februari", `retry_count=0`, 3 span `chat` berurutan terverifikasi di Jaeger) — dibangun DAN dibuktikan nyata sejak saat itu.

**Keputusan yang Diikuti**
M7.2 tidak menulis fungsi/logic penyambung baru. Premis Lingkup M7.2 di `rancangan-orkestrasi-api.md` ("ketiga langkah ini terbukti bekerja terisolasi... diuji dengan input buatan sendiri per langkah di Milestone 1.6") tidak akurat untuk kondisi kode saat ini — dicatat di sini sebagai koreksi temuan, bukan diperbaiki di dokumen sumber (di luar wewenang milestone ini untuk mengubah dokumen `rancangan-*.md`).

**Catatan Ketergantungan**
Kalau klaim ini keliru (mis. ditemukan kode yang ternyata berbeda saat implementasi checkpoint berjalan), seluruh checkpoint berikutnya (test connectivity) perlu dikaji ulang — tapi risiko ini kecil karena sudah diverifikasi langsung lewat pembacaan source + `git log`, bukan asumsi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menulis ulang/merefactor `decompose_question()` supaya "lebih eksplisit terhubung"** — ditolak karena kode yang sudah bekerja dan teruji tidak boleh diubah tanpa alasan bug (forced by "Tidak termasuk" `rancangan-orkestrasi-api.md`: logic internal 9 layer tidak dirombak ulang di M7.x).

---

### Keputusan 2: Pendekatan test connectivity — spy pada boundary call, LLM tetap dipanggil nyata

**Sumber Paksaan**
Filosofi pengujian M7 yang ditetapkan user secara eksplisit: "uji hanya dilakukan untuk memastikan antar llm call saling terhubung dan request bisa mengalir" — berbeda dari `evals/` yang menguji cakupan skenario/kualitas jawaban. Dikombinasikan preseden Milestone 7.1 Keputusan 5 (real trial call, reuse infrastruktur test yang ada, bukan mock penuh).

**Keputusan yang Diikuti**
Test baru memakai spy (`unittest.mock.patch(..., wraps=...)`) pada `klasifikasi_kebutuhan`, `pecah_atomik`, `verifikasi_pemecahan` di namespace `src.layers.decomposition.decompose` (tempat fungsi dipanggil) — merekam argumen yang benar-benar diterima tiap langkah SAMBIL tetap menjalankan implementasi asli (LLM sungguhan tetap dipanggil). Pembuktian ini lebih kuat dari test M1.6 yang sudah ada (`test_kelompok_a_majemuk_bergantung_relasi_benar`), yang hanya memeriksa hasil akhir konsisten (UUID silang cocok) — bukan nilai spesifik di titik sambung.

**Catatan Ketergantungan**
Kalau pendekatan spy tidak dipakai, buktinya tetap "hasil akhir terlihat benar" seperti yang sudah ada — tidak menambah nilai baru dibanding test M1.6/M7.1 yang sudah ada, sehingga M7.2 tidak akan menghasilkan apa pun yang genuinely baru.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Cukup mengutip ulang test M1.6 yang sudah ada sebagai bukti M7.2** — ditolak karena tidak menambah bukti connectivity-spesifik (hand-off nilai persis), hanya duplikasi bukti "hasil akhir benar" yang sudah ada sejak M1.6/M7.1.
- **Mock seluruh chain (klasifikasi+pemecahan+verifikasi semua di-mock)** — ditolak karena bertentangan langsung dengan filosofi "real trial call" M7 dan preseden M7.1 Keputusan 5; hasil test jadi tidak membuktikan apa pun tentang LLM sungguhan.

---

### Keputusan 3: Dua checkpoint test (jalur normal + jalur retry/feedback), bukan satu

**Sumber Paksaan**
`decompose.py::decompose_question()` py mekanisme retry-dengan-feedback (forced `milestones/1.6-decomposition/decisions.md` Keputusan 3) — dua jalur berbeda secara struktural: jalur normal (klasifikasi→pemecahan→verifikasi, `retry_count=0`) dan jalur retry (verifikasi gagal → `feedback` mengalir ke `pecah_atomik()` berikutnya). Investigasi menemukan **belum ada test otomatis sama sekali** untuk jalur retry — test yang ada (`test_kelompok_a...`) kebetulan `retry_count=0`, dan `evals/1.6-decomposition/audit.md` hanya menemukan retry "tidak terbukti memperbaiki hasil" (temuan kualitas, bukan pembuktian wiring).

**Keputusan yang Diikuti**
Checkpoint 2 (jalur normal) dan Checkpoint 3 (jalur retry/feedback, dipaksa deterministik lewat mock `verifikasi_pemecahan()` percobaan pertama) — dua bukti terpisah untuk dua jalur struktural berbeda.

**Catatan Ketergantungan**
Kalau hanya jalur normal diuji, klaim "seluruh mekanisme decompose_question() terbukti terhubung" tidak lengkap — jalur retry (bagian paling "connection-specific" dari desain M1.6 Keputusan 3) akan tetap tidak diverifikasi sama sekali.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menunggu LLM kebetulan retry secara natural** — ditolak karena `evals/1.6-decomposition/audit.md` sendiri menemukan retry natural jarang/tidak reliable terjadi; menunggu kejadian alami membuat test tidak deterministik dan berisiko flaky.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Kode penyambung sudah ada sejak M1.6 CP7 — tidak menulis kode baru | B | Plan |
| 2 | Pendekatan test connectivity: spy + LLM nyata | B | Plan |
| 3 | Dua checkpoint test: jalur normal + retry/feedback | B | Plan |
