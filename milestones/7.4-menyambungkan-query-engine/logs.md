# Logs — Milestone 7.4: Menyambungkan Query Engine (Susun Request → Verifikasi Bentuk Request)

## Checkpoint 1 — Persiapan & Keputusan

- Investigasi sebelum plan ditulis: dikonfirmasi TIDAK ADA fungsi produksi di `src/` yang menyambungkan `susun_request_atomic_intent()` (M3.4) ke `verifikasi_bentuk_request_atomic_intent()` (M3.5) untuk jalur utama — satu-satunya caller nyata adalah `_revisi_request()` (`src/layers/execution/klasifikasi_respons.py`, M4.2), helper privat khusus jalur revisi HTTP 400.
- Ditemukan konflik skema: `HasilVerifikasiBentukRequest.request` (M3.5) wajib terisi non-null, sehingga orkestrator baru tidak bisa mendegradasi ke tipe M3.5 saat M3.4 gagal (beda dari preseden `domain_gate.py`). Diajukan ke user lewat `AskUserQuestion` — dipilih Opsi A (tuple dari tipe yang sudah ada, tanpa skema baru).
- Ditemukan `view_name` ganda dipaksa oleh teks KK M7.4 sendiri — parameter tunggal akan membuat skenario mismatch mustahil direproduksi lewat chain nyata.
- Tulis `decisions.md` — 8 keputusan (7 Jenis B/forced, 1 Jenis A/genuinely terbuka).
- Commit hash: `4393b75`.

## Checkpoint 2 — Implementasi Orkestrator

- Implementasi `src/layers/query_engine/query_engine.py::susun_dan_verifikasi_request_atomic_intent()` — file baru, meniru preseden `domain_gate.py`/`decompose.py` (orkestrator selalu di file terpisah dari sub-langkah).
- Tulis 4 unit test mocked (tanpa LLM) di `tests/layers/query_engine/test_query_engine.py`: short-circuit saat susun gagal, identity request diteruskan ke verifikasi, default `view_name_tervalidasi_retriever` ke `view_name`, override eksplisit diteruskan apa adanya.
- **Catatan environment**: `python -m pytest` dari interpreter global gagal `ModuleNotFoundError: opentelemetry.exporter.otlp.proto.grpc` — project py virtualenv terpisah di `.venv/` yang belum diaktifkan secara default di shell kerja. Seluruh run test M7.4 memakai `./.venv/Scripts/python.exe -m pytest` secara eksplisit.

**Hasil run nyata (unit test mocked):**
```
$ .venv/Scripts/python.exe -m pytest tests/layers/query_engine/test_query_engine.py -v
tests/layers/query_engine/test_query_engine.py::test_short_circuit_susun_gagal_verifikasi_tidak_dipanggil PASSED
tests/layers/query_engine/test_query_engine.py::test_happy_path_request_diteruskan_identik_ke_verifikasi PASSED
tests/layers/query_engine/test_query_engine.py::test_view_name_tervalidasi_retriever_default_ke_view_name PASSED
tests/layers/query_engine/test_query_engine.py::test_view_name_tervalidasi_retriever_eksplisit_berbeda_diteruskan PASSED
4 passed in 2.70s
```

- Commit hash: `896528a` (feat), `6b2ac0a` (test).

## Checkpoint 3 — Test Connectivity Sesuai Kriteria Keberhasilan

- `OPENROUTER_API_KEY` tersedia di environment kerja — test connectivity dijalankan dengan LLM sungguhan, bukan di-skip.
- Ditambahkan `test_konektivitas_mismatch_view_name_tertangkap_verifikasi_nyata` — reuse skenario KK1 M3.5 (`test_pre_check_gagal_llm_tidak_pernah_dipanggil`), memanggil `susun_dan_verifikasi_request_atomic_intent()` dengan `view_name="v_reservation_room_type_daily"` dan `view_name_tervalidasi_retriever="v_reservation_channel_daily"` (berbeda), spy identity check di boundary Susun→Verifikasi.

**Hasil run nyata:**
```
$ .venv/Scripts/python.exe -m pytest tests/layers/query_engine/test_query_engine.py -v --durations=0
tests/layers/query_engine/test_query_engine.py::test_short_circuit_susun_gagal_verifikasi_tidak_dipanggil PASSED
tests/layers/query_engine/test_query_engine.py::test_happy_path_request_diteruskan_identik_ke_verifikasi PASSED
tests/layers/query_engine/test_query_engine.py::test_view_name_tervalidasi_retriever_default_ke_view_name PASSED
tests/layers/query_engine/test_query_engine.py::test_view_name_tervalidasi_retriever_eksplisit_berbeda_diteruskan PASSED
tests/layers/query_engine/test_query_engine.py::test_konektivitas_mismatch_view_name_tertangkap_verifikasi_nyata PASSED

slowest durations
22.68s call     test_konektivitas_mismatch_view_name_tertangkap_verifikasi_nyata
5 passed in 25.17s
```

Assertion boundary (`spy_verifikasi.call_args_list[0].args[2] is susun_returns[0].request`) lolos dengan LLM sungguhan untuk langkah Susun — membuktikan hand-off objek persis, bukan rekonstruksi manual. `hasil_verifikasi.lolos is False` dan alasan menyebut `v_reservation_channel_daily` (Kriteria 1 M3.5 short-circuit deterministik, tanpa LLM untuk langkah Verifikasi — sesuai kontrak M3.5 yang sudah ada).

- Commit hash: `e37b774`.
