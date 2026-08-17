# Logs — Milestone 4.1: Membangun Pemanggilan chatbot_api

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | *(belum commit)* | `docs(milestone-4.1): decisions dan tutup verifikasi risiko employee_id` |
| 2 | *(pending)* | |
| 3 | *(pending)* | |
| 4 | *(pending)* | |
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

**Commit:** lihat Task 2 (satu commit gabungan checkpoint ini)

### Task 2 — Perbarui `docs/keterbatasan-diterima.md` #10

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri #10 diperbarui: judul ditambah "TERVERIFIKASI: Gap Dikonfirmasi untuk 7 dari 9 View", ditambahkan section "Status Verifikasi" berisi tabel 9 view vs status filter `employee_id` (hasil baca langsung `whitelist_facility.py`+`whitelist_hr.py`), kesimpulan 2 aman/7 gap, dan keputusan user (tetap kirim `employee_id`, tunggu tim database). Ketiga poin "Pemicu peninjauan ulang" asli ditandai selesai/terkonfirmasi, ditambah poin (d) baru untuk verifikasi ulang setelah kabar filter diterapkan.

**Temuan**
Premis asli entri #10 ("file `whitelist_<domain>.py`... tidak ada di repo ini") ternyata TIDAK akurat lagi — repo `chatbot_api` bisa diakses read-only dari repo bertetangga `../nirwana-database/scripts/chatbot_api/`. Ini bukan salah tulis M2.4 (saat itu memang belum ditelusuri), tapi temuan baru yang mengubah status dari "tidak bisa diverifikasi" jadi "sudah diverifikasi, gap dikonfirmasi nyata untuk 7/9 view".

**Error/Kegagalan (jika ada)**
Tidak ada.

**Selesai:** 2026-08-17

**Commit:** *(lihat Ringkasan commit per checkpoint di atas setelah commit dibuat)*
