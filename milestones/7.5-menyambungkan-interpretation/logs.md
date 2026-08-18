# Logs — Milestone 7.5: Menyambungkan Interpretation (Narasi → Verifikasi Kesetiaan Data)

## Checkpoint 1 — Persiapan & Keputusan

- Investigasi (dilanjutkan dari investigasi M7.4 sesi yang sama): dikonfirmasi TIDAK ADA fungsi produksi di `src/` yang menyambungkan `susun_narasi()` (M4.4) ke `verifikasi_dan_susun_visualisasi()` (M4.5) untuk jalur utama.
- Ditemukan tegangan desain: Rule 5 prompt `src/prompts/interpretation/narasi.md` (baris 20) melarang LLM mengarang klaim sebab-akibat, sehingga skenario S01 M4.5 (klaim kausal tak berdasar) kemungkinan besar tidak tereproduksi lewat `susun_narasi()` sungguhan. Diajukan ke user lewat `AskUserQuestion` — dipilih Opsi A (mock hanya return value `susun_narasi()`, verifikasi tetap LLM sungguhan penuh).
- Tulis `decisions.md` — 7 keputusan (6 Jenis B/forced, 1 Jenis A/genuinely terbuka).
- Commit hash: `d666058`.

## Checkpoint 2 — Implementasi Orkestrator

- Implementasi `src/layers/interpretation/interpretation.py::susun_dan_verifikasi_narasi()` — file baru, meniru pola M7.4 (`query_engine.py`) yang baru saja dikerjakan dalam sesi yang sama.
- Tulis 2 unit test mocked (tanpa LLM) di `tests/layers/interpretation/test_interpretation.py`: identity narasi diteruskan ke verifikasi, visualisasi=None diteruskan apa adanya saat lolos=False.

**Hasil run nyata (unit test mocked):**
```
$ .venv/Scripts/python.exe -m pytest tests/layers/interpretation/test_interpretation.py -v
tests/layers/interpretation/test_interpretation.py::test_narasi_diteruskan_identik_ke_verifikasi PASSED
tests/layers/interpretation/test_interpretation.py::test_visualisasi_none_saat_verifikasi_tidak_lolos PASSED
2 passed in 3.40s
```

- Commit hash: `0445d6f` (feat), `0cf3ed7` (test).

## Checkpoint 3 — Test Connectivity Sesuai Kriteria Keberhasilan

- `OPENROUTER_API_KEY` tersedia — kedua test connectivity dijalankan dengan LLM sungguhan, bukan di-skip.
- Ditambahkan `test_konektivitas_jalur_normal_narasi_verifikasi_nyata` (tanpa mock sama sekali, membuktikan wiring dasar) dan `test_konektivitas_klaim_sebab_akibat_tertangkap_verifikasi_nyata` (reuse skenario S01 M4.5, `susun_narasi()` dipaksa sesuai Keputusan 7, verifikasi tetap LLM sungguhan) ke file yang sama dalam satu edit.

**Hasil run nyata:**
```
$ .venv/Scripts/python.exe -m pytest tests/layers/interpretation/test_interpretation.py -v --durations=0
tests/layers/interpretation/test_interpretation.py::test_narasi_diteruskan_identik_ke_verifikasi PASSED
tests/layers/interpretation/test_interpretation.py::test_visualisasi_none_saat_verifikasi_tidak_lolos PASSED
tests/layers/interpretation/test_interpretation.py::test_konektivitas_jalur_normal_narasi_verifikasi_nyata PASSED
tests/layers/interpretation/test_interpretation.py::test_konektivitas_klaim_sebab_akibat_tertangkap_verifikasi_nyata PASSED

slowest durations
73.12s call     test_konektivitas_jalur_normal_narasi_verifikasi_nyata
15.77s call     test_konektivitas_klaim_sebab_akibat_tertangkap_verifikasi_nyata
4 passed in 92.29s (0:01:32)
```

- `hasil_verifikasi.lolos is False` untuk skenario S01, alasan menyebut klaim sebab-akibat, `visualisasi is None` (short-circuit `lolos is not True` di `verifikasi_kesetiaan.py` yang sudah ada).
- **Catatan proses**: kedua test connectivity ditulis dalam satu `Edit` (satu diff), sehingga hanya menghasilkan SATU commit test (`7933905`, "buktikan konektivitas jalur normal nyata") alih-alih dua commit terpisah seperti direncanakan plan. Sempat dibuat commit kedua kosong (`--allow-empty`) untuk test klaim sebab-akibat, lalu dikoreksi dengan `git reset --soft HEAD~1` sebelum mendokumentasikan di sini — bukan `git commit --amend` (dihindari sesuai aturan Git project), commit kosong yang salah dihapus dari HEAD sebelum ada commit lain di atasnya. Riwayat final: 1 commit `test` mencakup kedua test Checkpoint 3.

Commit hash: `7933905` (test, mencakup kedua test connectivity Checkpoint 3).
