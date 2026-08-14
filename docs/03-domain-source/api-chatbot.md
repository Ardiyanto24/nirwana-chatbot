# API Query Interface — AI Chatbot

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dihasilkan oleh** | Milestone 4.4 (`milestones/4.4-api-query-interface-chatbot/`) |
| **Kode** | `scripts/chatbot_api/` |
| **Input utama** | `docs/09-serving-ai-chatbot/{pemetaan-akses-teknis-chatbot.md,view-query-pattern-chatbot.md,kredensial-chatbot.md}` (M4.1/4.2/4.3) |
| **Status** | Selesai |

---

## Penanda Stabil vs Berpotensi Berubah

Dokumen sumber (`05-serving-ai-chatbot.md`) menandai skema API ini **eksplisit belum final**. Pembagiannya di project ini:

| Bagian | Status | Kenapa |
|---|---|---|
| Logic akses: view `chatbot_views` (M4.2) + kredensial per domain (M4.3) + otorisasi via `role_permissions` (§2 di bawah) | **Stabil** | Sudah terverifikasi berlapis (M4.2 KK1-3, M4.3 KK1-2), tidak bergantung bentuk request/response |
| Bentuk request/response, nama parameter (`role_title`, `employee_id`, dst), struktur URL `/chatbot/{domain}/{view_name}` | **Berpotensi berubah** | Bentuk integrasi sesungguhnya dengan sistem chatbot pihak lain belum ditentukan — desain saat ini adalah kontrak awal yang masuk akal, bukan hasil negosiasi dengan tim chatbot sungguhan (project solo) |

Kalau bentuk request/response berubah nanti, `authz.py` dan `connections.py` (logic akses) tidak perlu dibongkar — hanya `main.py`/`whitelist_*.py` (bentuk API) yang perlu menyesuaikan.

## Cara Kerja

```
1. Request masuk: GET /chatbot/{domain}/{view_name}?role_title=...&employee_id=...&<filter lain>
2. authorize(role_title, domain) -- lookup mart_cleaned.role_permissions via
   kredensial chatbot_authz_reader (M4.4, SELECT-only ke tabel itu SAJA).
   -> role_title tidak dikenal ATAU domain di luar cakupan role -> 403, TIDAK ada query data yang jalan.
3. Whitelist lookup: view_name harus ada di whitelist_<domain>.py -> kalau tidak, 404.
4. access_scope == 'own_property' -> employee_id wajib -> resolve_property_id()
   lookup chatbot_views.v_employees_directory (kredensial employees_directory_chatbot_reader)
   -> property_id yang DIKLAIM caller diabaikan, diganti hasil resolve.
   access_scope == 'all_properties' -> property_id caller dipakai apa adanya sebagai filter opsional.
5. Query dieksekusi lewat kredensial domain M4.3 yang sesuai (mis. reservation_chatbot_reader)
   -- BUKAN admin -- terhadap chatbot_views.<view_name> saja.
6. Response JSON dikembalikan.
```

## Endpoint

Satu pola per domain: `GET /chatbot/{domain}/{view_name}`. 10 domain, 67 `view_name` total (cocok persis jumlah view M4.2).

| Domain | Jumlah `view_name` | File whitelist |
|---|---|---|
| `reservation` | 10 | `whitelist_reservation.py` |
| `fnb` | 11 | `whitelist_fnb.py` |
| `facility` | 12 | `whitelist_facility.py` |
| `spa_event` | 9 | `whitelist_spa_event.py` |
| `hr` | 10 | `whitelist_hr.py` |
| `financial` | 11 | `whitelist_financial.py` |
| `properties_ref` | 1 | `whitelist_properties_ref.py` |
| `employees_directory` | 1 | `whitelist_employees_directory.py` |
| `guests_pii` | 1 | `whitelist_guests_pii.py` |
| `guests_profile` | 1 | `whitelist_guests_profile.py` |

## Parameter

| Parameter | Wajib? | Keterangan |
|---|---|---|
| `role_title` | **Selalu wajib** | Klaim identitas dari Lapis 1, divalidasi terhadap `role_permissions` sebelum apa pun — tidak dipercaya buta. |
| `employee_id` | Wajib **hanya** kalau `access_scope` role untuk domain itu `own_property` | Dipakai resolve `property_id` sebenarnya — nilai `property_id` yang dikirim caller tidak pernah dipercaya untuk kasus `own_property`. |
| `property_id` (dan filter lain per whitelist domain) | Opsional | Untuk `own_property`: diabaikan, di-override. Untuk `all_properties`: dipakai apa adanya sebagai penyempitan opsional. |
| `limit`/`offset` | Opsional | Default 100/0, maks `limit` 1000. |

## Mekanisme Penolakan (KK2)

- `role_title` tidak dikenal di `role_permissions`, atau domain yang diminta di luar cakupan role itu → **403**, sebelum query data apa pun dijalankan.
- `view_name` tidak ada di whitelist domain → **404**.
- `access_scope == own_property` tanpa `employee_id`, atau `employee_id` tidak ditemukan → **400**.
- `role_permissions`/tabel `mart_cleaned` di luar peta M4.1 → **tidak pernah punya endpoint sama sekali** (bukan ditolak saat runtime, tapi secara struktural tidak terdaftar — mencoba path apa pun ke situ selalu 404 "not in whitelist").

## Bukti Verifikasi (ringkasan, detail penuh di `milestones/4.4-.../logs.md`)

Seluruh bukti di bawah dari HTTP call nyata (`uvicorn` + `curl`/`requests`), bukan baca kode:

- **KK1** (sampel 3 tingkat): Front Office Staff/F&B Staff/Housekeeping Staff/Spa & Event Staff/HR Staff (Staff), Finance Manager (Manager), Corporate Revenue Director + CEO (Korporat) — semua menghasilkan data sesuai cakupan `role_permissions` masing-masing.
- **KK2**: Front Office Staff → domain `fnb` ditolak 403; HR Staff → domain `financial`/`guests_pii`/`guests_profile` ditolak 403; role_title tak dikenal ditolak 403. Uji krusial: pemisahan `guests_pii`/`guests_profile` tetap tertegakkan di layer API (independen dari deny DB M4.3) — dibuktikan dengan role yang tidak permitted keduanya (HR Staff), karena **tidak ada satu pun dari 20 persona nyata yang punya `guests_profile` tanpa `guests_pii`** (temuan RBAC, dicatat di `logs.md`).
- **KK3**: `role_permissions` tidak pernah terdaftar sebagai `view_name` apa pun di whitelist manapun — percobaan mengaksesnya selalu 404 struktural. Setiap query benar-benar dieksekusi lewat kredensial domain M4.3 (bukan admin), yang sudah terbukti terisolasi penuh dari `mart_cleaned`/`mart_aggregated` mentah (M4.3 report.md).
- **`own_property`**: Front Office Staff (E0071, P01) mengklaim `property_id=P02`/`P04` di request — hasil tetap 100% P01 di seluruh domain yang diuji (reservation, facility). Finance Manager (E0452, P03) — override berhasil ke P03 (bukan P01), membuktikan resolve per-`employee_id` yang sesungguhnya, bukan konstanta.
- **`all_properties`**: Corporate Revenue Director — bebas akses `property_id` apa pun tanpa `employee_id` sama sekali; filter `property_id` yang dikirim dipakai sebagai penyempitan opsional, bukan dipaksa.

## Cara Menjalankan

```bash
pip install -r requirements.txt
cd scripts/chatbot_api
uvicorn main:app --reload
```

Auto-docs Swagger di `http://127.0.0.1:8000/docs`. Manual-only, tidak dideploy, tidak ada di workflow terjadwal manapun — sama klasifikasi `scripts/data_analyst_api/` (M3.4).
