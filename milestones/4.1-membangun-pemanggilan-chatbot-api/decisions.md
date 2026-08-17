# Decisions — Milestone 4.1: Membangun Pemanggilan chatbot_api

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 4.1 — pekerjaan pertama PIC 4 (Execution & Interpretation), satu-satunya titik dalam seluruh sistem yang benar-benar memanggil `chatbot_api`.

---

## Keputusan 1: Konvensi Risiko #10 — Tetap Kirim `employee_id`, Menunggu Tim Database Menambahkan Filter

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Genuinely terbuka — riset sebelum plan ditulis (membaca `whitelist_facility.py`+`whitelist_hr.py` di repo bertetangga `../nirwana-database/scripts/chatbot_api/`, read-only) mengonfirmasi `docs/keterbatasan-diterima.md` entri #10 sebagai gap NYATA (bukan lagi risiko teoretis): dari 9 view cakupan-individu M2.3, hanya 2 (`v_lookup_staff_shifts`, `v_lookup_employee_performance`) yang benar-benar menerapkan `employee_id` sebagai filter baris di whitelist `chatbot_api`. 7 lainnya (`v_housekeeping_staff_daily`, `v_maintenance_technician_daily`, `v_lookup_housekeeping_log`, `v_lookup_maintenance_tickets` di `facility`; `v_hr_employee_monthly`, `v_hr_employee_performance_semester`, `v_hr_watchlist_monthly` di `hr`) tidak mendeklarasikan `employee_id`/`staff_id` sebagai filter sama sekali — parameter M2.3/M2.4 kirim tapi diabaikan server-side (`main.py` baris 71-77: hanya filter yang dideklarasikan eksplisit di `entry["filters"]` yang pernah diterapkan).

**Proses**
Temuan disampaikan lengkap ke user (tabel 9 view vs status filter) lewat `AskUserQuestion` sebelum plan difinalisasi. User awalnya bertanya detail 7 view mana saja (dijawab), lalu menjawab arah keputusan.

**Keputusan yang Dipilih**
Tetap kirim `employee_id` sesuai desain M2.3/M2.4 yang sudah ada — TIDAK diubah. Parameter ini "diperlakukan seolah punya filter `employee_id`" — akan ditambahkan sebagai filter oleh tim database engineering di kemudian hari, di luar cakupan proyek ini untuk memperbaikinya (`chatbot_api` tidak boleh dimodifikasi, `CLAUDE.md`).

**Alasan**
`chatbot_api` adalah sistem eksternal yang sudah final dan di luar cakupan revisi — memperbaiki whitelist-nya bukan opsi. Mengirim `employee_id` tetap benar dari sisi kontrak Lapis 1 (parameter yang benar, sesuai konvensi resmi yang ada); ketidakcukupan penegakan server-side adalah tanggung jawab tim yang memiliki `chatbot_api`, bukan proyek ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menambahkan penanda observability khusus saat request menyentuh salah satu dari 7 view gap** — ditawarkan sebagai opsi eksplisit di `AskUserQuestion`, tidak dipilih user.
- **Menjeda pekerjaan M4.1 untuk diskusi lebih dalam** — ditawarkan sebagai opsi eksplisit, tidak dipilih user; user memilih lanjut dengan arah "tetap kirim, tunggu tim database".

---

## Keputusan 2: Verifikasi Nyata (Checkpoint 5) Ditunda Sampai Ada Kabar Filter `employee_id` Diterapkan

**Status:** Diputuskan sebelum implementasi (dari plan, arahan langsung user di chat).

**Latar Belakang**
Genuinely terbuka — dokumen sumber tidak mengatur kapan verifikasi nyata harus dijalankan relatif terhadap perbaikan eksternal yang sedang ditunggu.

**Keputusan yang Dipilih**
Checkpoint 1-4 (dokumentasi, konfigurasi, implementasi, unit test mocked) berjalan sekarang. Checkpoint 5 (start `chatbot_api` lokal, panggilan HTTP nyata KK1/KK2, verifikasi span Jaeger nyata) dan Checkpoint 6 (penutupan: `report.md`, update status `CLAUDE.md`/`AGENT.md`) DITUNDA sampai ada kabar filter `employee_id` sudah diterapkan tim database engineering untuk 7 view gap (Keputusan 1).

**Alasan**
Menghindari menjalankan verifikasi nyata dua kali (sekali sekarang, sekali lagi setelah perbaikan server-side) — instruksi eksplisit user.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Jalankan verifikasi nyata sekarang juga** — tidak dipilih; KK1/KK2 M4.1 sendiri tidak menyentuh 7 view gap secara langsung, tapi user memilih menunggu demi konsolidasi satu putaran verifikasi.

---

## Keputusan 3: Lingkup M4.1 — HTTP Client Murni, Tanpa LLM, Passthrough Tanpa Interpretasi

**Sumber Paksaan**
`rancangan-execution-interpretation.md` Lingkup Milestone 4.1: "Pekerjaan ini murni teknis, tanpa keterlibatan model AI sama sekali" dan Output: "mengembalikan responsnya apa adanya... tanpa interpretasi apa pun."

**Keputusan yang Diikuti**
`panggil_chatbot_api()` menerima `QueryEngineRequest` yang sudah `lolos=True` dari `HasilVerifikasiGate` (M2.4) dan mengembalikan `{status_code, body}` mentah — TANPA klasifikasi status (`berhasil`/`sebagian`/dst, itu kerja M4.2), tanpa retry, tanpa panggilan LLM.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced langsung oleh teks Lingkup dan Output dokumen sumber, tidak ada ambiguitas.

---

## Keputusan 4: `role_title` dan `employee_id` sebagai Parameter Fungsi Eksplisit, Terpisah dari `request.params`

**Sumber Paksaan**
`api-chatbot.md`: `role_title` selalu wajib di setiap request; `employee_id` wajib untuk `access_scope == own_property` (dipakai resolve `property_id` server-side) — berbeda dari `params["employee_id"]` yang HANYA dipaksa M2.4 untuk 9 view cakupan-individu M2.3. `TurnPayload` (M1.2, `src/schemas/turn_payload.py`) sudah membawa `role_title`+`employee_id` sebagai field top-level sejak turn pertama masuk sistem. Preseden: `verifikasi_gate()` M2.4 sudah menerima `employee_id: str` eksplisit dengan pola identik.

**Keputusan yang Diikuti**
`panggil_chatbot_api(request: QueryEngineRequest, role_title: str, employee_id: str)` — keduanya parameter fungsi terpisah, digabung ke query string bersama `request.params` saat membangun request, BUKAN diasumsikan sudah ada di dalam `request.params`.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Asumsikan `role_title`/`employee_id` selalu ada di `request.params`** — ditolak: `request.params` diisi Query Engine (M3.4) lewat ekstraksi LLM dari kebutuhan data user, yang secara alami TIDAK akan pernah spontan menyertakan identitas caller sebagai "filter data" — caller identity dan filter data adalah dua kategori data yang berbeda sumber sepanjang pipeline ini.

---

## Keputusan 5: Tabel Pemetaan `view_name` → Slug URL `chatbot_api` (67 Entri, Transkripsi Manual)

**Sumber Paksaan**
Temuan audit plan: `view_name` internal (nama SQL, `src/config/katalog_view.py`, mis. `v_housekeeping_staff_daily`) TIDAK SAMA dengan slug URL yang dipakai `chatbot_api` sebagai key `WHITELIST` di tiap `whitelist_<domain>.py` (mis. `housekeeping-staff-daily`). Dicek 4 dari 10 file whitelist (`reservation`, `facility`, `hr`, `financial`) — transformasinya TIDAK KONSISTEN antar view (`v_lookup_housekeeping_log`→`housekeeping-log` strip `lookup_`; `v_hr_attendance_daily`→`attendance-daily` strip `hr_`; `v_lookup_financial_summary`→`financial-summary` strip `lookup_` TAPI PERTAHANKAN `financial_`; `v_financial_departmental_margin`→`departmental-margin` strip `financial_`) — tidak bisa diturunkan otomatis lewat regex.

**Keputusan yang Diikuti**
`src/config/slug_view_chatbot_api.py` — `VIEW_NAME_KE_SLUG_CHATBOT_API: dict[str, str]`, ditranskripsi manual dari 10 file `whitelist_<domain>.py` (repo bertetangga, read-only), mirror preseden `katalog_view.py` (transkripsi eksplisit dari sumber eksternal final, ruang kesalahan tertutup diaudit sumbernya, bukan dikarang/diturunkan otomatis).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Regex/transformasi otomatis dari nama SQL** — ditolak dengan bukti konkret: pola berbeda-beda per view (kadang strip nama domain, kadang strip `lookup_`, kadang keduanya, kadang tidak ada yang di-strip), tidak ada aturan tunggal yang menjelaskan seluruh 67 kasus.
- **Minta Retriever (M3.1-3.3) langsung menghasilkan slug, bukan nama SQL** — ditolak, `view_name` nama SQL adalah kontrak yang sudah dipakai lintas SELURUH layer M2.4-M3.5 (Verification Gate, Query Engine); mengubahnya sekarang berarti merombak kontrak yang sudah stabil di banyak milestone lain demi kebutuhan M4.1 saja — translasi slug lebih tepat jadi tanggung jawab titik terakhir (M4.1) yang memang satu-satunya tahu detail koneksi `chatbot_api`.

---

## Keputusan 6: Subpackage Baru `src/layers/execution/` dan Skema `src/schemas/execution.py`

**Sumber Paksaan**
Preseden struktur per-layer `CLAUDE.md`: layer yang mencakup lebih dari satu milestone (Execution = M4.1-4.3) jadi subpackage tersendiri, mirror `retriever/`, `query_engine/`, `verification_gate/`. Preseden penamaan `Hasil<X>` di SETIAP skema output layer lain, dan preseden `model_validator` konsistensi di SETIAP skema `Hasil<X>` lain (`HasilVerifikasiGate`, `HasilPenyusunanRequest`, `HasilVerifikasiBentukRequest`, `DomainAuthorization`, dst).

**Keputusan yang Diikuti**
`src/layers/execution/pemanggilan_chatbot_api.py` (fungsi `panggil_chatbot_api()`); `src/schemas/execution.py` — `HasilPemanggilanChatbotAPI {status_code: int | None, body: Any = None, kegagalan_transport: str | None = None}` dengan `model_validator` yang menjamin `status_code is None` ⇔ `kegagalan_transport` terisi.

Field diberi nama `kegagalan_transport` — BUKAN `error_type` — untuk menghindari tabrakan makna dengan kosakata `error.type` di kontrak observability, yang merujuk klasifikasi status project (`berhasil`/`sebagian`/`ditolak_otorisasi`/`gagal_teknis`/`terblokir_ketergantungan`) dan secara eksplisit jadi tanggung jawab Output M4.2 ("Atribut `error.type`... ter-emit ke span sesuai kontrak observability"), bukan M4.1.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Nama field `error_type`** — ditolak: berpotensi disalahartikan sebagai kosakata status project yang sebenarnya kerja M4.2, bukan M4.1.
- **Tanpa `model_validator`** — ditolak: menyimpang dari preseden konsisten seluruh skema `Hasil<X>` lain di project yang selalu menjaga invarian lewat validator, bukan dipercaya begitu saja ke pemanggil.

---

## Keputusan 7: Span `execute_tool` — Hanya `http.response.status_code`, Bukan `error.type`

**Sumber Paksaan**
`rancangan-observability-ai-chatbot.md` Bagian 2: Output M4.1 sendiri hanya menyebut "mencatat `http.response.status_code`" — sedangkan Output Milestone 4.2 eksplisit terpisah: "Atribut `error.type` dan jumlah percobaan ulang ter-emit ke span sesuai kontrak observability." Preseden span diberi nama PERSIS sesuai nilai `gen_ai.operation.name`/tipe operasi dari tabel kontrak (`"chat"` di `identifikasi.py`, `"memory.retrieve"` di `session_memory.py`) — bukan nama dotted custom.

**Keputusan yang Diikuti**
Span dengan nama literal `"execute_tool"` (tracer `execution.pemanggilan_chatbot_api`), HANYA set atribut `http.response.status_code`. Atribut `error.type` TIDAK diset M4.1 — akan diset M4.2 (di luar cakupan milestone ini) saat klasifikasi respons dilakukan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **M4.1 juga men-set `error.type`** — ditolak: melanggar pembagian tanggung jawab eksplisit M4.1 (passthrough tanpa interpretasi) vs M4.2 (klasifikasi) yang dikunci dokumen sumber.

---

## Keputusan 8: HTTP Client Sinkron, Library `httpx`, Timeout Eksplisit

**Sumber Paksaan**
Preseden `get_openrouter_client()` (`src/config/llm.py`) — client SINKRON (`OpenAI`, bukan `AsyncOpenAI`) meski aplikasi FastAPI-nya `async def`, satu-satunya preseden pemanggilan jaringan keluar yang sudah ada di project. Pelajaran `docs/keterbatasan-diterima.md` #7 (insiden hang OpenRouter M2.1 tanpa timeout eksplisit, root cause tidak teridentifikasi penuh) — diterapkan proaktif di sini, bukan menunggu insiden serupa.

**Keputusan yang Diikuti**
`httpx.Client` sinkron (context manager), timeout eksplisit dengan nilai default wajar (dikonfigurasi di `src/config/chatbot_api.py`, starting point bukan hasil kalibrasi empiris). Library `httpx` dipilih sebagai derived decision (bukan diajukan `AskUserQuestion`) — idiom ekosistem FastAPI/Python async modern, sudah ada transitif di dependency graph project (dipakai `openai` SDK), biaya mengganti nanti (satu fungsi, satu file) rendah, tidak memenuhi ambang "berdampak material/mahal diubah" `CLAUDE.md` untuk perlu ditanyakan ke user.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`httpx.AsyncClient`** — ditolak, tidak konsisten preseden sinkron project; tidak ada milestone lain yang butuh async bridging saat ini (belum ada wiring FastAPI end-to-end, lihat Keputusan 9).
- **Library `requests`** — dipertimbangkan sebagai alternatif populer, tidak dipilih: `httpx` lebih idiomatik untuk ekosistem FastAPI/async modern dan sudah tersedia transitif, tidak menambah dependency benar-benar baru secara konseptual.

---

## Keputusan 9: 403/404 Diteruskan Apa Adanya; Tanpa Fungsi Batch; Tanpa Wiring ke `src/main.py`

**Sumber Paksaan**
KK2 M4.1 sumber eksplisit: "menghasilkan respons `403` yang tertangkap dan diteruskan apa adanya... tanpa memodifikasi atau menyembunyikannya." Kesempitan Lingkup M4.1: "satu-satunya titik... yang melakukan panggilan HTTP" (orkestrasi multi-atomic-intent/retry alami jadi kerja M4.2 yang memang butuh state per-item). Preseden M1.3-M3.5: seluruh layer tetap fungsi standalone, `src/main.py` masih persis kondisi M1.2 (echo validasi saja) — komposisi end-to-end sembilan layer belum eksplisit jadi tanggung jawab milestone manapun di 8 dokumen sumber.

**Keputusan yang Diikuti**
`panggil_chatbot_api()` meneruskan 403/404 (dan status lain) apa adanya tanpa modifikasi/eskalasi (itu kerja M4.2). Tidak ada fungsi `panggil_chatbot_api_semua()` untuk banyak request sekaligus. Tidak ada perubahan `src/main.py` di milestone ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **M4.1 langsung eskalasi 403/404 sebagai bug prioritas tinggi** — ditolak, itu eksplisit Lingkup M4.2, bukan M4.1.
- **Tambah fungsi batch di M4.1** — ditolak, forced by kesempitan Lingkup + kebutuhan state per-item retry yang lebih tepat tinggal di M4.2.
- **Rangkai `panggil_chatbot_api()` ke endpoint `src/main.py`** — ditolak untuk saat ini, konsisten preseden seluruh milestone sebelumnya belum ada yang melakukan wiring end-to-end; bukan keputusan permanen, hanya belum jadi tanggung jawab milestone manapun sejauh ini.

---

## Keputusan 10: `decisions.md` sebagai Task Pertama, `logs.md` Diisi per Checkpoint

**Sumber Paksaan**
`CLAUDE.md` Workflow Wajib bagian "1. Rencanakan sebelum mengimplementasikan" dan "3. Implementasikan per checkpoint" — preseden konsisten milestone-milestone sebelumnya (mis. M2.4 Keputusan 9).

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis. `logs.md` diisi entri baru di setiap checkpoint selesai, bukan satu task besar dikumpulkan di akhir.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit `CLAUDE.md`/preseden konsisten milestone sebelumnya. (Draf plan pertama M4.1 sempat keliru menaruh `decisions.md` di checkpoint terakhir — dikoreksi saat audit plan sebelum implementasi dimulai.)

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Konvensi risiko #10: tetap kirim employee_id, tunggu tim database | A | Checkpoint 1 |
| 2 | Verifikasi nyata (Checkpoint 5) ditunda | A | Checkpoint 5-6 |
| 3 | Lingkup M4.1: HTTP client murni, tanpa LLM, passthrough | B | Checkpoint 3 |
| 4 | role_title + employee_id sebagai parameter eksplisit | B | Checkpoint 3 |
| 5 | Tabel pemetaan view_name → slug URL (67 entri) | B | Checkpoint 2-3 |
| 6 | Subpackage execution/ + skema HasilPemanggilanChatbotAPI | B | Checkpoint 2-3 |
| 7 | Span execute_tool: hanya http.response.status_code | B | Checkpoint 3 |
| 8 | Client sinkron, httpx, timeout eksplisit | B | Checkpoint 2-3 |
| 9 | 403/404 apa adanya, tanpa batch, tanpa wiring main.py | B | Checkpoint 3 |
| 10 | decisions.md Task pertama, logs.md per checkpoint | B | Plan |
