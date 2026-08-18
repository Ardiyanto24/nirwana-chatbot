# Logs — Milestone 7.3: Menyambungkan Domain Gate (Identifikasi → Verifikasi Titik Buta)

## Checkpoint 1 — Persiapan & Keputusan

- Investigasi (bagian dari investigasi menyeluruh sebelum M7.2, dilanjutkan untuk M7.3) mengonfirmasi `identifikasi_domain_atomic_intent()` (`src/layers/domain_gate/domain_gate.py`) sudah menyambungkan kedua langkah sejak Milestone 2.1 Checkpoint 7 (commit `91abe27`), dengan real-LLM verification (Checkpoint 7, `test_kelompok_a_union_domain_berhasil` 161.93s) dan live Jaeger trace end-to-end (Checkpoint 8, `trace_id=ed0a755f...`/`6fed6752...`).
- Tulis `decisions.md` — 4 keputusan (semua Jenis B/forced): kode sudah terhubung, pendekatan test spy+LLM nyata, satu checkpoint saja (Domain Gate tidak py retry, beda dari M1.6), skenario wajib `gop_margin` sesuai KK sumber literal.
- Commit hash: `4fccc4a`.

## Checkpoint 2 — Test Connectivity: Skenario `gop_margin`

**Task 2.** Skenario `gop_margin` dicek ulang — ternyata SUDAH dipakai persis di `test_kelompok_a_union_domain_berhasil` (`tests/layers/domain_gate/test_domain_gate.py` baris 88: `"Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?"`), jadi teks kebutuhan yang sama di-reuse langsung untuk test connectivity baru — konsisten KK sumber M7.3 ("skenario uji `gop_margin` yang sudah dipakai Milestone 2.1").

Ditambahkan `test_konektivitas_identifikasi_verifikasi_titik_buta_skenario_gop_margin` ke `tests/layers/domain_gate/test_domain_gate.py`.

**Desain test:** fungsi recorder (`_rekam_identifikasi`) dipasang sebagai `side_effect` pada `patch()` untuk `identifikasi_domain` di namespace `src.layers.domain_gate.domain_gate` — LLM sungguhan tetap dipanggil, objek return-nya direkam ke list. `verifikasi_titik_buta` di-spy pakai `wraps=` murni.

**Assertion boundary:**
- `spy_verifikasi.call_args_list[0].args[1] is hasil_identifikasi.domains` — argumen `domain_awal` yang diterima `verifikasi_titik_buta()` adalah list PERSIS (identity check) yang dikembalikan `identifikasi_domain().domains`, bukan rekonstruksi/salinan baru.
- Sanity check tambahan: `result.status == BERHASIL`, `Domain.RESERVATION` dan `Domain.FINANCIAL` ada di union akhir (domain yang genuinely bocor lewat kolom turunan `gop_margin` berhasil ditangkap).

**Hasil run nyata:**
```
$ uv run pytest tests/layers/domain_gate/test_domain_gate.py::test_konektivitas_identifikasi_verifikasi_titik_buta_skenario_gop_margin -v
PASSED [100%]  (54.11s — konsisten 2 pemanggilan LLM berurutan sungguhan)

$ uv run pytest tests/layers/domain_gate/test_domain_gate.py -v   # regresi penuh file, 4 test
4 passed in 125.20s (0:02:05)
```

Assertion boundary lolos dengan LLM sungguhan — membuktikan hand-off nilai persis, bukan cuma "hasil akhir terlihat benar" (yang sudah dibuktikan `test_kelompok_a...` sejak M2.1/M7.1).
