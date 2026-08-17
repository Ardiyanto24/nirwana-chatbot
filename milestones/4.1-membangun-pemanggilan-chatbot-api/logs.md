# Logs — Milestone 4.1: Membangun Pemanggilan chatbot_api

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `b3fe1d8` | `docs(milestone-4.1): decisions dan tutup verifikasi risiko employee_id` |
| 2 | `9b2dd50`, `e637389` | `chore(milestone-4.1): tambah dependency httpx` + `feat(milestone-4.1): konfigurasi chatbot_api, pemetaan slug view, skema hasil pemanggilan` |
| 3 | `6e2d71f` | `feat(milestone-4.1): implementasi pemanggilan chatbot_api` |
| 4 | `a203b10` | `test(milestone-4.1): unit test pemanggilan chatbot_api (mocked)` |
| 5 | **DITUNDA** — menunggu kabar filter `employee_id` diterapkan tim database | |
| 6 | **DITUNDA** — bergantung Checkpoint 5 | |

---

## Checkpoint 1 — Keputusan dan Penutupan Verifikasi Risiko #10

**Mulai:** 2026-08-17

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan. Dua keputusan genuinely terbuka (konvensi risiko #10, penundaan verifikasi nyata Checkpoint 5) dikonfirmasi lewat `AskUserQuestion` + arahan langsung user di chat SEBELUM plan difinalisasi.

**Apa yang dilakukan**
10 entri keputusan: 2 Jenis A genuinely terbuka (konvensi risiko #10 — tetap kirim `employee_id`, tunggu tim database; penundaan Checkpoint 5), 8 Jenis B forced/preseden (lingkup HTTP client murni, role_title+employee_id parameter eksplisit, tabel pemetaan slug URL 67 entri, subpackage execution/+skema, span execute_tool hanya status_code, client sinkron+httpx+timeout, 403/404 apa adanya+tanpa batch+tanpa wiring main.py, decisions.md task pertama).

**Temuan**
Audit plan sebelum implementasi (diminta eksplisit user: "coba audit apakah semua task sudah mencakup seluruh apa yang harus dilakukan") menemukan gap kritis baru yang tidak ada di draf plan pertama: `view_name` internal (nama SQL, `v_...`) TIDAK SAMA dengan slug URL yang dipakai `chatbot_api` (dicek langsung 4 dari 10 file `whitelist_<domain>.py` di repo bertetangga `../nirwana-database/scripts/chatbot_api/`, read-only) — tanpa tabel pemetaan eksplisit, KK1 M4.1 tidak mungkin lolos (selalu 404). Ditambahkan sebagai Keputusan 5 + Task baru Checkpoint 2. Audit juga menemukan draf plan pertama keliru menaruh `decisions.md` di checkpoint terakhir (melanggar `CLAUDE.md` "Task 1, sebelum kode") — dikoreksi sebelum implementasi dimulai.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `b3fe1d8` (satu commit gabungan checkpoint ini, lihat Task 2)

### Task 2 — Perbarui `docs/keterbatasan-diterima.md` #10

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri #10 diperbarui: judul ditambah "TERVERIFIKASI: Gap Dikonfirmasi untuk 7 dari 9 View", ditambahkan section "Status Verifikasi" berisi tabel 9 view vs status filter `employee_id` (hasil baca langsung `whitelist_facility.py`+`whitelist_hr.py`), kesimpulan 2 aman/7 gap, dan keputusan user (tetap kirim `employee_id`, tunggu tim database). Ketiga poin "Pemicu peninjauan ulang" asli ditandai selesai/terkonfirmasi, ditambah poin (d) baru untuk verifikasi ulang setelah kabar filter diterapkan.

**Temuan**
Premis asli entri #10 ("file `whitelist_<domain>.py`... tidak ada di repo ini") ternyata TIDAK akurat lagi — repo `chatbot_api` bisa diakses read-only dari repo bertetangga `../nirwana-database/scripts/chatbot_api/`. Ini bukan salah tulis M2.4 (saat itu memang belum ditelusuri), tapi temuan baru yang mengubah status dari "tidak bisa diverifikasi" jadi "sudah diverifikasi, gap dikonfirmasi nyata untuk 7/9 view".

**Error/Kegagalan (jika ada)**
Tidak ada.

**Selesai:** 2026-08-17

**Commit:** `b3fe1d8`

**Checkpoint 1 selesai:** 2026-08-17

---

## Checkpoint 2 — Konfigurasi, Skema, dan Pemetaan Slug URL

**Mulai:** 2026-08-17

### Task 3 — Tambah dependency `httpx`

**Kesesuaian dengan plan:** Sesuai plan. `uv add httpx` menginstal `httpx==0.28.1` + `httpcore==1.0.9` + `certifi` (57 total package resolved).

### Task 4 — `src/config/chatbot_api.py`

**Kesesuaian dengan plan:** Sesuai plan. `get_chatbot_api_base_url()` (pola identik `get_engine()`/`get_openrouter_client()`, env var + `RuntimeError`) + `CHATBOT_API_TIMEOUT_DETIK = 30.0` (starting point, bukan kalibrasi empiris). `.env.example` ditambah `CHATBOT_API_BASE_URL`.

### Task 5 — `src/config/slug_view_chatbot_api.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membaca LANGSUNG seluruh 10 file `whitelist_<domain>.py` di `../nirwana-database/scripts/chatbot_api/` (read-only), transkripsi manual `VIEW_NAME_KE_SLUG_CHATBOT_API` (67 entri, `entry["source"]` nama SQL -> key dict `WHITELIST` slug URL).

**Verifikasi nyata**
Dijalankan skrip cross-check terhadap `DAFTAR_VIEW_PER_DOMAIN` (`src/config/katalog_view.py`): jumlah 67=67, TIDAK ADA view yang hilang dari pemetaan slug, TIDAK ADA entri ekstra yang tidak dikenal katalog, TIDAK ADA slug duplikat (dua `view_name` berbeda menghasilkan slug sama). Hasil dijalankan nyata (`uv run python -c "..."`), bukan cuma dibaca.

**Temuan**
Konfirmasi pola transformasi TIDAK konsisten seperti diprediksi di plan (lihat `decisions.md` Keputusan 5) — beberapa contoh tambahan ditemukan saat transkripsi penuh: `v_lookup_recipe_bom` -> `recipe-bom` (strip "lookup_", TIDAK ada domain prefix "fnb_" untuk di-strip karena memang tidak ada di nama aslinya); `v_lookup_venues` -> `venues` (strip "lookup_" saja).

**Commit:** `e637389` (satu commit gabungan Task 4-6)

### Task 6 — `src/schemas/execution.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`HasilPemanggilanChatbotAPI {status_code: int | None, body: Any = None, kegagalan_transport: str | None = None}` dengan `model_validator` XOR (`status_code is None` ⇔ `kegagalan_transport` terisi).

**Verifikasi nyata**
Dijalankan 4 kasus nyata (`uv run python -c "..."`): valid `status_code` terisi, valid `kegagalan_transport` terisi, invalid keduanya `None` (raise `ValidationError`), invalid keduanya terisi (raise `ValidationError`) — seluruh 4 kasus sesuai ekspektasi.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Selesai:** 2026-08-17

**Commit:** `e637389` (satu commit gabungan Task 4-6)

**Checkpoint 2 selesai:** 2026-08-17

---

## Checkpoint 3 — Implementasi HTTP Client

**Mulai:** 2026-08-17

### Task 7 — `src/layers/execution/pemanggilan_chatbot_api.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`panggil_chatbot_api(request, role_title, employee_id) -> HasilPemanggilanChatbotAPI` — URL disusun dari `VIEW_NAME_KE_SLUG_CHATBOT_API[request.view_name]` (KeyError dibiarkan raise natural kalau terjadi — prasyarat request sudah lolos Verification Gate M2.4 menjamin `view_name` valid, bukan skenario yang perlu ditangani defensif), query params gabungan (filter `None`, tambah `role_title`+`employee_id`), `httpx.Client` sinkron context-managed dengan timeout dari config. Span `execute_tool` set `http.response.status_code`. Body di-parse `response.json()` dengan fallback `response.text` (`except ValueError`, mencakup `json.JSONDecodeError`). Exception `httpx.TimeoutException`/`httpx.TransportError` ditangkap, dipetakan `kegagalan_transport="timeout"`/`"connection_error"`.

**Verifikasi:** import sanity check nyata (`uv run python -c "from src.layers.execution.pemanggilan_chatbot_api import panggil_chatbot_api"`) berhasil tanpa error. Verifikasi fungsional penuh di Task 8 (Checkpoint 4).

**Commit:** `6e2d71f`

**Checkpoint 3 selesai:** 2026-08-17 (checkpoint ini digabung penutupannya dengan Checkpoint 4 di bawah, sesuai plan — implementasi tanpa bukti jalan bukan checkpoint valid)

---

## Checkpoint 4 — Test Unit (Mocked)

**Mulai:** 2026-08-17

### Task 8 — `tests/layers/execution/test_pemanggilan_chatbot_api.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
11 test, `httpx.Client.get` di-monkeypatch (tanpa dependency mock tambahan): (a) translasi `view_name`→slug URL (2 test, domain berbeda); (b) respons 200 diteruskan apa adanya; (c) respons 403/404 diteruskan apa adanya (parametrized, 2 test); (d) respons 500 non-JSON fallback ke `response.text`; (e) timeout dan connection error masing-masing menghasilkan `kegagalan_transport` benar tanpa crash (2 test); (f) `role_title`/`employee_id`/`params` masuk benar ke query string, nilai `None` di `params` tidak ikut terkirim (2 test); tambahan: span `execute_tool` mencatat `http.response.status_code` (fake tracer, bukan OTel SDK nyata — cukup untuk membuktikan `set_attribute` dipanggil dengan nilai benar).

**Verifikasi nyata**
`uv run pytest tests/layers/execution/ -v` — **11/11 PASSED**, dijalankan nyata (bukan dibaca kode saja).

**Temuan**
Tidak ada kejutan — implementasi Task 7 lolos seluruh skenario di percobaan pertama, tidak ada revisi Task 7 yang diperlukan setelah test ditulis.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Selesai:** 2026-08-17

**Commit:** `a203b10`

**Checkpoint 3+4 selesai:** 2026-08-17
