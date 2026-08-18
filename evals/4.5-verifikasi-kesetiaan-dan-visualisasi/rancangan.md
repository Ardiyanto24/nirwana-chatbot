# Rancangan Pengujian — Verifikasi Kesetiaan Data dan Penyusunan Visualisasi (Milestone 4.5)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — skenario dan ekspektasi ditetapkan dulu. Struktur mirror `evals/4.4-.../rancangan.md`, tapi cakupan LEBIH SEMPIT — hanya `verifikasi_kesetiaan_narasi()` yang diuji di sini (LLM), karena `susun_data_visualisasi()` murni deterministik sudah dibuktikan penuh lewat 10 unit test (Checkpoint 7, `tests/layers/interpretation/test_visualisasi.py`) — tidak butuh eval perilaku LLM.

**Jumlah skenario TIDAK dipatok** — 10 skenario di sini disusun mencakup KEDUA Kriteria Keberhasilan sumber (walau KK2 sudah dibuktikan unit test) plus kelima kriteria prompt `verifikasi_kesetiaan.md` secara merata.

## Yang Diuji

`verifikasi_kesetiaan_narasi()` (`src/layers/interpretation/verifikasi_kesetiaan.py`) — sudah dibuktikan manual sekali (Checkpoint 4, `logs.md`) untuk skenario klaim sebab-akibat (KK paling kritis) dan narasi jujur, plus 13 unit test mocked (Checkpoint 7) untuk logic deterministik (parse, span, fallback `APIError`). Pengujian ini menutup dimensi PERILAKU LLM lain yang belum tersentuh:

| Dimensi (kriteria prompt) | Sudah diuji? | Skenario di sini |
|---|---|---|
| Klaim sebab-akibat tidak berdasar (Kriteria 3, KK sumber) | Sebagian (Checkpoint 4, manual sekali) | S01 (formal), S02 (kontrol negatif) |
| Data hilang dari narasi (Kriteria 1) | Tidak | S03 |
| Angka dikarang/salah (Kriteria 4) | Tidak | S04 |
| Status `sebagian` disamarkan sebagai normal (Kriteria 2) | Tidak | S05 (harus tertangkap), S06 (kontrol - disampaikan jujur) |
| Status `terblokir_ketergantungan` digeneralisasi (Kriteria 5) | Tidak | S07 (harus tertangkap), S08 (kontrol - spesifik) |
| Status `ditolak_otorisasi` disamarkan sebagai kegagalan teknis (Kriteria 2, varian) | Tidak | S09 |
| Narasi kompleks multi-status, semua jujur (stress test kontrol) | Tidak | S10 |

## Cara Baca Skenario

Tiap skenario: daftar `AtomicIntent` + `SessionMemoryPackage` pasangannya (data sumber "kebenaran"), narasi yang diberikan ke verifier (SENGAJA dibuat mengandung pelanggaran tertentu, atau sengaja jujur sebagai kontrol), ekspektasi (`lolos=True`/`False` + alasan yang diharapkan disebut kalau `False`).

---

### S01 — Klaim Sebab-Akibat Tidak Berdasar (KK Sumber, Paling Kritis)

**Data sumber:** [a] occupancy naik 10%, [b] revenue F&B naik 8% — dua data deskriptif independen, TIDAK ada hubungan kausal di data.

**Narasi diuji:** "...Kenaikan occupancy ini MENYEBABKAN revenue F&B juga naik 8%."

**Ekspektasi:** `lolos=False`, alasan menyebut klaim sebab-akibat tidak berdasar.

---

### S02 — Kontrol Negatif: Dua Data Deskriptif TANPA Klaim Kausal

**Data sumber:** Sama seperti S01.

**Narasi diuji:** "...Occupancy naik 10%. Revenue F&B juga naik 8% pada periode yang sama." (tanpa kata penghubung kausal)

**Ekspektasi:** `lolos=True`.

---

### S03 — Data Hilang dari Narasi

**Data sumber:** [a] occupancy rate 82% (berhasil), [b] revenue F&B Rp300jt (berhasil) — DUA kebutuhan.

**Narasi diuji:** "Occupancy rate bulan ini 82%." (HANYA menyebut [a], [b] sama sekali tidak disinggung)

**Ekspektasi:** `lolos=False`, alasan menyebut kebutuhan revenue F&B hilang/tidak disinggung.

---

### S04 — Angka Dikarang/Salah

**Data sumber:** occupancy rate = 82% (`nilai_hasil={"rows":[{"occupancy_rate":0.82}]}`).

**Narasi diuji:** "Occupancy rate bulan ini 95%." (angka BEDA dari data sumber)

**Ekspektasi:** `lolos=False`, alasan menyebut ketidaksesuaian angka (95% vs 82%).

---

### S05 — Status `sebagian` Disamarkan sebagai Normal

**Data sumber:** jumlah reservasi 120, `status=sebagian`, `catatan_interpretasi=["data ditandai perlu perhatian tim database"]`.

**Narasi diuji:** "Jumlah reservasi bulan ini 120." (disajikan seolah final/pasti, tidak menyebut keterbatasan kualitas data sama sekali)

**Ekspektasi:** `lolos=False`, alasan menyebut status sebagian/keterbatasan tidak disampaikan.

---

### S06 — Kontrol: Status `sebagian` Disampaikan Jujur

**Data sumber:** Sama seperti S05.

**Narasi diuji:** "Jumlah reservasi bulan ini tercatat 120, namun data ini ditandai perlu perhatian tim database sehingga mungkin belum akurat sepenuhnya."

**Ekspektasi:** `lolos=True`.

---

### S07 — Status `terblokir_ketergantungan` Digeneralisasi

**Data sumber:** [a] revenue reservasi Maret (`gagal_teknis`), [b] "bandingkan dengan Februari" (`terblokir_ketergantungan`, bergantung ke [a]).

**Narasi diuji:** "Beberapa data tidak dapat ditampilkan saat ini." (generalisasi, TIDAK menyebut [a]/[b] spesifik atau relasi ketergantungannya)

**Ekspektasi:** `lolos=False`, alasan menyebut generalisasi/tidak spesifik.

---

### S08 — Kontrol: Status `terblokir_ketergantungan` Disampaikan Spesifik

**Data sumber:** Sama seperti S07.

**Narasi diuji:** "Sistem mengalami kendala mengambil data revenue reservasi Maret, sehingga permintaan membandingkan dengan Februari juga tidak dapat diproses karena bergantung pada data itu."

**Ekspektasi:** `lolos=True`.

---

### S09 — Status `ditolak_otorisasi` Disamarkan sebagai Kegagalan Teknis

**Data sumber:** gaji staff Budi, `status=ditolak_otorisasi`.

**Narasi diuji:** "Terjadi kendala teknis saat mengambil data gaji Budi." (menyamarkan PENOLAKAN AKSES sebagai KEGAGALAN TEKNIS biasa — beda makna, KK M4.4 sendiri menuntut nada berbeda antara keduanya)

**Ekspektasi:** `lolos=False`, alasan menyebut status sebenarnya (penolakan otorisasi) disamarkan sebagai kegagalan teknis.

---

### S10 — Kontrol: Narasi Kompleks Multi-Status, Seluruhnya Jujur (Stress Test)

**Data sumber:** [a] occupancy 80% (berhasil), [b] gaji Budi (`ditolak_otorisasi`), [c] revenue reservasi (`gagal_teknis`), [d] "bandingkan dg bulan lalu" (`terblokir_ketergantungan`, bergantung ke [c]).

**Narasi diuji:** Narasi lengkap yang jujur menyampaikan keempatnya dengan nada tepat (mirror S04 `evals/4.4-.../audit.md`, yang sudah terbukti bersih).

**Ekspektasi:** `lolos=True` — stress test bahwa kompleksitas (4 status berbeda sekaligus) tidak membuat verifier over-triggering false-positive.

---

## Ringkasan Ekspektasi

| ID | Kriteria Diuji | Ekspektasi |
|---|---|---|
| S01 | Larangan klaim sebab-akibat (KK sumber) | `lolos=False` |
| S02 | Kontrol negatif S01 | `lolos=True` |
| S03 | Data tidak boleh hilang | `lolos=False` |
| S04 | Angka harus sesuai data asli | `lolos=False` |
| S05 | Status sebagian tidak boleh disamarkan | `lolos=False` |
| S06 | Kontrol S05 | `lolos=True` |
| S07 | Status terblokir tidak boleh digeneralisasi | `lolos=False` |
| S08 | Kontrol S07 | `lolos=True` |
| S09 | Ditolak_otorisasi tidak boleh disamarkan jadi gagal_teknis | `lolos=False` |
| S10 | Stress test kompleks, kontrol menyeluruh | `lolos=True` |
