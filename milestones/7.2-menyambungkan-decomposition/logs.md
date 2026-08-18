# Logs — Milestone 7.2: Menyambungkan Decomposition (Klasifikasi → Pemecahan → Verifikasi)

## Checkpoint 1 — Persiapan & Keputusan

- Investigasi menyeluruh (dipicu instruksi user) mengonfirmasi `decompose_question()` (`src/layers/decomposition/decompose.py`) sudah menyambungkan ketiga langkah sejak Milestone 1.6 Checkpoint 7 (commit `33a53cf`, 2026-08-15), dengan smoke test end-to-end nyata + span Jaeger dicatat di `milestones/1.6-decomposition/logs.md` saat itu.
- Tulis `decisions.md` — 3 keputusan (semua Jenis B/forced): kode sudah terhubung (tidak menulis kode baru), pendekatan test spy+LLM nyata, dua checkpoint test (normal+retry).
- Commit hash: `42c34b5`.

## Checkpoint 2 — Test Connectivity: Jalur Normal

**Task 2.** Ditambahkan `test_konektivitas_klasifikasi_pemecahan_verifikasi_jalur_normal` ke `tests/layers/decomposition/test_decompose.py`.

**Desain test:** dua fungsi recorder (`_rekam_klasifikasi`, `_rekam_pemecahan`) dipasang sebagai `side_effect` pada `patch()` untuk `klasifikasi_kebutuhan`/`pecah_atomik` di namespace `src.layers.decomposition.decompose` — LLM sungguhan tetap dipanggil (fungsi asli tetap dieksekusi di dalam recorder), sambil objek return-nya direkam ke list. `verifikasi_pemecahan` di-spy pakai `wraps=` murni (tanpa perlu rekam return, karena tidak ada langkah berikutnya yang menerima returnnya).

**Assertion boundary:**
- `spy_pecah.call_args_list[0].args[1] is klasifikasi_returns[0]` — argumen `klasifikasi` yang diterima `pecah_atomik()` adalah objek PERSIS (identity check, bukan cuma equality) yang dikembalikan `klasifikasi_kebutuhan()`.
- `spy_verifikasi.call_args_list[0].args[1] is pemecahan_returns[0]` — argumen `hasil` yang diterima `verifikasi_pemecahan()` adalah objek PERSIS yang dikembalikan `pecah_atomik()`.

**Hasil run nyata:**
```
$ uv run pytest tests/layers/decomposition/test_decompose.py::test_konektivitas_klasifikasi_pemecahan_verifikasi_jalur_normal -v
PASSED [100%]  (58.96s — konsisten 3 pemanggilan LLM berurutan sungguhan)

$ uv run pytest tests/layers/decomposition/test_decompose.py -v   # regresi penuh file
3 passed in 97.06s (0:01:37)
```

Kedua assertion boundary lolos dengan LLM sungguhan — membuktikan hand-off nilai persis, bukan cuma "hasil akhir terlihat benar" (yang sudah dibuktikan `test_kelompok_a...` sejak M1.6/M7.1).
