# Decisions — Milestone 7.3: Menyambungkan Domain Gate (Identifikasi → Verifikasi Titik Buta)

Dokumen ini mencatat keputusan desain untuk Milestone 7.3, ditentukan sebelum implementasi dimulai (Plan Mode), berdasarkan investigasi menyeluruh yang sama dengan Milestone 7.2 (satu sesi kerja, urutan berurutan).

---

### Keputusan 1: Kode penyambung sudah ada sejak Milestone 2.1 Checkpoint 7-8 — M7.3 tidak menulis kode baru

**Sumber Paksaan**
Investigasi langsung sebelum plan ditulis: `src/layers/domain_gate/domain_gate.py::identifikasi_domain_atomic_intent()` sudah memanggil `identifikasi_domain()` lalu meneruskan `hasil_awal.domains` (return value apa adanya, tanpa rekonstruksi) ke `verifikasi_titik_buta()` sebagai `domain_awal`. `git log --follow -- src/layers/domain_gate/domain_gate.py` menunjukkan **satu commit tunggal** (`91abe27 feat(milestone-2.1): orkestrator identifikasi domain gate`). `milestones/2.1-identifikasi-domain/logs.md` Checkpoint 7 mencatat real-LLM verification (`test_kelompok_a_union_domain_berhasil`, 161.93s, PASSED) dan Checkpoint 8 mencatat live Jaeger trace end-to-end (`trace_id=ed0a755f...` KK1, `trace_id=6fed6752...` KK3) — dibangun DAN dibuktikan nyata sejak saat itu.

**Keputusan yang Diikuti**
M7.3 tidak menulis fungsi/logic penyambung baru. Sama seperti M7.2, premis Lingkup M7.3 di `rancangan-orkestrasi-api.md` tidak akurat untuk kondisi kode saat ini — dicatat sebagai koreksi temuan, bukan diperbaiki di dokumen sumber.

**Catatan Ketergantungan**
Sama seperti M7.2 Keputusan 1 — risiko klaim keliru sudah dimitigasi lewat verifikasi langsung (pembacaan source + `git log` + `logs.md` M2.1), bukan asumsi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Merefactor `identifikasi_domain_atomic_intent()`** — ditolak karena kode sudah bekerja dan teruji, tidak boleh diubah tanpa alasan bug (forced "Tidak termasuk" `rancangan-orkestrasi-api.md`).

---

### Keputusan 2: Pendekatan test connectivity — spy pada boundary call, LLM tetap dipanggil nyata (mirror M7.2)

**Sumber Paksaan**
Sama persis dengan M7.2 Keputusan 2 — filosofi pengujian M7 (instruksi user) + preseden M7.1 Keputusan 5.

**Keputusan yang Diikuti**
Spy (`unittest.mock.patch(..., side_effect=fungsi_asli)`) pada `identifikasi_domain` dan `verifikasi_titik_buta` di namespace `src.layers.domain_gate.domain_gate` — merekam argumen yang diterima `verifikasi_titik_buta()` SAMBIL tetap menjalankan LLM sungguhan.

**Catatan Ketergantungan**
Sama seperti M7.2 Keputusan 2.

**Opsi yang Dipertimbangkan tapi Ditolak**
- Sama seperti M7.2 Keputusan 2 (kutip ulang test lama / mock seluruh chain) — ditolak dengan alasan sama.

---

### Keputusan 3: Satu checkpoint test saja (bukan dua seperti M7.2) — Domain Gate tidak py mekanisme retry

**Sumber Paksaan**
`milestones/2.1-identifikasi-domain/decisions.md` Keputusan 2: Identifikasi → Verifikasi Titik Buta dirancang **union aditif TANPA retry** — beda struktural dari Decomposition (M1.6) yang py retry-dengan-feedback (Keputusan 3 M1.6). Domain Gate cuma 2 pemanggilan LLM tetap (tidak ada loop), sehingga tidak ada "jalur retry" terpisah untuk diuji.

**Keputusan yang Diikuti**
M7.3 hanya py 1 checkpoint test connectivity (jalur normal/union) — beda dari M7.2 yang py 2 (normal + retry/feedback).

**Catatan Ketergantungan**
Memaksakan checkpoint "retry" untuk M7.3 akan menguji sesuatu yang tidak ada di desain M2.1 — bukan kekurangan cakupan, melainkan ketidaksesuaian struktural.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by desain M2.1 sendiri (tidak ada retry loop untuk diuji).

---

### Keputusan 4: Skenario test wajib pakai kasus `gop_margin`, bukan skenario lain yang sudah ada

**Sumber Paksaan**
Kutipan literal Kriteria Keberhasilan M7.3 di `rancangan-orkestrasi-api.md`: "Kasus domain 'bocor' lewat kolom turunan (skenario uji `gop_margin` yang sudah dipakai Milestone 2.1)..." — KK sumber secara eksplisit menyebut skenario spesifik ini, bukan skenario lain yang kebetulan sudah ada di `test_domain_gate.py` (mis. RESERVATION+FINANCIAL di `test_kelompok_a_union_domain_berhasil`).

**Keputusan yang Diikuti**
Test connectivity M7.3 (Checkpoint 2) memakai/reuse skenario `gop_margin` — teks kebutuhan yang menyebut metrik turunan finansial (`gop_margin`) yang berpotensi tidak tertangkap identifikasi domain awal, memicu Verifikasi Titik Buta menambahkan domain `FINANCIAL` yang terlewat.

**Catatan Ketergantungan**
Kalau skenario lain dipakai (mis. skenario yang sudah ada di test_domain_gate.py), KK sumber M7.3 secara literal tidak terpenuhi persis — prinsip "salin persis Kriteria Keberhasilan, jangan ditulis ulang dengan kata sendiri" (`CLAUDE.md`) berlaku juga untuk skenario yang dirujuk eksplisit di dalamnya.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Pakai skenario RESERVATION+FINANCIAL yang sudah ada di `test_kelompok_a_union_domain_berhasil`** — ditolak karena tidak match literal KK sumber M7.3 (yang eksplisit menyebut `gop_margin`), meski secara teknis sama-sama membuktikan union aditif.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Kode penyambung sudah ada sejak M2.1 CP7-8 — tidak menulis kode baru | B | Plan |
| 2 | Pendekatan test connectivity: spy + LLM nyata | B | Plan |
| 3 | Satu checkpoint test saja (tanpa retry, beda dari M7.2) | B | Plan |
| 4 | Skenario test wajib pakai kasus `gop_margin` | B | Plan |
