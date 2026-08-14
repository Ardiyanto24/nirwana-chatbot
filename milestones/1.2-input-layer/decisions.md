# Decisions — Milestone 1.2: Membangun Input Layer

## Keputusan 1: Whitelist `role_title` Divalidasi (Bukan Sekadar Non-Empty)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Ditemukan konflik data: `rancangan-rbac-authorization.md` menyebut "19 role", tapi tabel aktual §2 `rancangan-rbac-ai-chatbot.md` punya 20 baris, dikonfirmasi independen oleh `api-chatbot.md` ("20 persona") dan cross-check internal dokumen yang sama ("7 Staff" cocok 7 baris berakhiran "Staff" di tabel). User mengonfirmasi 20 adalah angka benar. Pertanyaan lanjutan: dengan angka sudah pasti, apakah Input Layer benar-benar memvalidasi `role_title` terhadap daftar itu, atau cukup cek non-empty (delegasikan sepenuhnya ke `chatbot_api`/Domain Gate)?

**Keputusan yang Dipilih**
Divalidasi terhadap 20 role yang dikonfirmasi.

**Alasan**
User menekankan: meski `role_title` berasal dari sistem (bukan input user langsung), tetap perlu diverifikasi. Ini juga sejalan dengan semangat Milestone 1.2 sendiri: "kegagalan di titik ini selalu karena alasan struktural yang jelas" — role_title tidak dikenal adalah kegagalan struktural yang bisa ditangkap sedini mungkin.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tanpa whitelist, cukup non-empty** — didiskusikan sebagai opsi awal (lebih longgar, konsisten ketat prinsip Lapis 1 tidak menduplikasi keputusan otorisasi), tapi user memilih tetap divalidasi.
- **Tunda ke `keputusan-tertunda.md`** — tidak dipilih karena bukti sudah cukup kuat setelah verifikasi langsung ke sumber.

**Dampak**
Input Layer menolak `role_title` yang tidak dikenal dengan pesan spesifik, sebelum Domain Gate (Milestone 2.x) sempat memprosesnya.

---

## Keputusan 2: Endpoint HTTP Sungguhan Sekarang (Bukan Fungsi Murni)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Dokumen sumber menyebut "fungsi/endpoint" tanpa menegaskan, dan belum ada web framework yang dipilih proyek ini sama sekali.

**Keputusan yang Dipilih**
Endpoint HTTP sungguhan sekarang, bukan ditunda sebagai fungsi Python murni.

**Alasan**
Lebih dekat ke bentuk akhir sistem (yang memang API) — user memilih opsi ini alih-alih menunda keputusan framework.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Fungsi Python murni, tunda keputusan framework** — direkomendasikan awalnya (menghindari keputusan foundational diambil prematur), tapi user memilih sebaliknya.

**Dampak**
Milestone 1.2 jadi titik pertama proyek menyentuh web framework — keputusan itu (Keputusan 3) langsung mengikuti.

---

## Keputusan 3: FastAPI sebagai Web Framework

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Konsekuensi langsung Keputusan 2 — perlu framework konkret.

**Keputusan yang Dipilih**
FastAPI.

**Alasan**
Async native (cocok untuk proyek yang akan banyak memanggil LLM & `chatbot_api` secara async nanti), validasi request/response built-in via Pydantic, OpenAPI docs otomatis, standar de-facto backend API Python modern 2024-2026.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Flask** — lebih matang/lama dipakai luas, tapi sinkron secara default, lebih banyak boilerplate untuk kebutuhan async proyek ini.
- **Django REST Framework** — kemungkinan besar overkill (proyek tidak butuh ORM/database relasional sendiri untuk data platform, state ada di Session Memory + `chatbot_api` eksternal).

**Dampak**
`pydantic`, `uvicorn` jadi dependency turunan (lihat Keputusan 9-10). Seluruh 9 layer nantinya kemungkinan besar mengikuti pola FastAPI yang sama begitu dirangkai jadi satu API.

---

## Keputusan 4: Struktur `src/` — Per-Layer

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
`CLAUDE.md` eksplisit menyatakan keputusan struktur `src/` perlu diajukan ke user di awal implementasi Milestone 1.2.

**Keputusan yang Dipilih**
Per-layer: `src/layers/input_layer.py`, `src/layers/context_resolution.py`, dst — satu modul per salah satu dari 9 layer.

**Alasan**
Mirror langsung ke tabel "Peta Layer" §3 arsitektur induk — intuitif menelusuri kode ↔ dokumen arsitektur 1:1, sesuai model mental utama proyek (alur data 9-layer).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Per-PIC** (`src/pic1_context_decomposition/`, dst) — mirror ke pembagian dokumen `rancangan-*.md` per pemilik pekerjaan, tapi kurang relevan untuk runtime code (proyek solo, satu orang mengerjakan semua peran PIC secara berurutan) dan tidak searah alur data 9-layer.

**Dampak**
Folder pendukung non-layer (`schemas/`, `observability/`, `config/`) ditambahkan sebagai perluasan wajar konvensi ini (lihat Keputusan 8), bukan bagian dari konvensi per-layer itu sendiri.

---

## Keputusan 5: Penyimpanan Daftar Role — File Config YAML

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`, didiskusikan mendalam).

**Latar Belakang**
User menolak opsi awal (hardcode Python constant) karena dianggap rigid kalau role bertambah, dan mengusulkan proyek ini punya database sendiri (mengingat Milestone 1.5 Session Memory akan butuh storage juga). Dikonfirmasi secara arsitektur: proyek ini boleh punya database sendiri, terpisah dari database data platform (larangan "REST API bukan akses SQL" di `arsitektur-ai-chatbot-rbac.md` baris 7 hanya soal database data platform). Tapi baik hardcode/file config/database sama-sama tidak menyelesaikan masalah auto-sync (`role_permissions` tetap tanpa endpoint di manapun) — hanya beda mekanisme update manual.

**Keputusan yang Dipilih**
File config YAML (`src/config/roles.yaml` + loader `src/config/roles.py`).

**Alasan**
Jalan tengah: tidak menambah kompleksitas database sebelum kebutuhan Session Memory yang sesungguhnya diketahui (skema, TTL, pola akses — baru jelas di Milestone 1.5), tapi juga tidak serigid hardcode Python (daftar role bisa diedit tanpa sentuh kode Python).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hardcode Python constant** — rencana awal, ditolak user karena rigid kalau role bertambah (perlu edit kode + redeploy).
- **Database sekarang di Milestone 1.2** — menarik maju keputusan storage yang harusnya cakupan Milestone 1.5, berisiko keputusan teknologi diambil tanpa konteks kebutuhan Session Memory yang sesungguhnya (baru 20 baris statis, bukan representasi kebutuhan storage yang lebih luas).

**Dampak**
`docs/keputusan-tertunda.md` diinisialisasi (entri #1) dengan keputusan database utuh untuk proyek ditunda ke Milestone 1.5, termasuk evaluasi apakah `roles.yaml` sebaiknya dipindah ke database yang sama saat itu.

---

## Keputusan 6: Exception Handler `ValidationError` → `422` (Bukan Parameter Bertipe Model)

**Status:** Ditemukan di tengah implementasi pada Checkpoint 3, Task 10.

**Latar Belakang**
Plan menyatakan (keliru) bahwa FastAPI otomatis menangani `pydantic.ValidationError` jadi `422` tanpa custom exception handler. Ini salah: FastAPI hanya otomatis menangani `RequestValidationError` miliknya sendiri, yang hanya terpicu kalau parameter endpoint bertipe model Pydantic (FastAPI parse & validasi sendiri sebelum handler jalan). Karena `validate_turn_payload()` sengaja dirancang sebagai fungsi murni yang memanggil `TurnPayload.model_validate()` secara manual (supaya bisa diuji lepas dari HTTP, Checkpoint 2), exception yang menjalar adalah `pydantic.ValidationError` biasa — kalau dibiarkan, jadi `500` bukan `422`. Ditemukan lewat pengujian `curl` manual sebelum ditulis ke log.

**Keputusan yang Dipilih**
Daftarkan `@app.exception_handler(ValidationError)` yang mengonversi ke `422` dengan `exc.errors()` sebagai detail.

**Alasan**
Pola resmi yang didokumentasikan FastAPI untuk validasi Pydantic di luar parameter endpoint otomatis. Mempertahankan desain `validate_turn_payload()` sebagai fungsi murni testable (nilai penting dari Checkpoint 2) tanpa mengorbankan perilaku HTTP yang benar.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Endpoint dengan parameter bertipe `TurnPayload` langsung** (`async def submit_turn(payload: TurnPayload)`) — akan dapat `422` otomatis dari FastAPI tanpa exception handler, tapi menghilangkan span `input.validate` yang seharusnya dipancarkan `validate_turn_payload()` sendiri (FastAPI akan parse & validasi SEBELUM handler/fungsi kita jalan sama sekali) — bertentangan langsung dengan kontrak Output Milestone 1.2 yang mewajibkan span ini.

**Dampak**
Murni internal `src/main.py` — tidak berdampak ke kontrak yang dijanjikan ke milestone lain.

---

## Keputusan 7: Swap Dev Dependency `httpx` → `httpx2`

**Status:** Ditemukan di tengah implementasi pada Checkpoint 4, Task 12.

**Latar Belakang**
Run pertama `pytest` menampilkan `StarletteDeprecationWarning` menyarankan `httpx2`. Diverifikasi lewat web search: `httpx2` fork resmi tim Pydantic (development `httpx` asli mandek), Starlette resmi pindah untuk `TestClient` sejak rilis 1.2.0 (2026-05-25).

**Keputusan yang Dipilih**
`uv remove --dev httpx` + `uv add --dev httpx2`.

**Alasan**
Konsisten dengan preseden proyek memperbaiki deprecation begitu ditemukan (Milestone 1.1: `otlp`→`otlp_grpc`) — murah diperbaiki, menghindari technical debt di kode referensi yang akan dicontoh milestone lain.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Biarkan warning apa adanya** — ditolak, sama seperti preseden M1.1, warning bukan error fatal tapi murah diperbaiki dan berisiko jadi "pola yang dianggap benar" kalau dibiarkan.

**Dampak**
Hanya dev dependency (testing) — tidak berdampak ke runtime aplikasi.

---

## Keputusan 8 (Forced): Validasi Murni Mekanis, Tanpa LLM

**Sumber Paksaan:** `rancangan-context-decomposition.md` Milestone 1.2, baris 46 — "kontrak yang disengaja, karena seluruh layer di belakangnya berasumsi kegagalan di titik ini selalu karena alasan struktural yang jelas".

**Keputusan yang Diikuti:** Tidak ada pemanggilan model AI apa pun di Input Layer.

**Catatan Ketergantungan:** Layer 2-9 berasumsi Input Layer selalu gagal karena alasan struktural — melanggar ini merusak asumsi desain seluruh pipeline.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada alternatif dipertimbangkan karena forced by kontrak eksplisit.

---

## Keputusan 9 (Forced): Span `input.validate`, Atribut `session.id`+`turn.index`

**Sumber Paksaan:** `rancangan-observability-ai-chatbot.md` Bagian 2, baris 32.

**Keputusan yang Diikuti:** Span non-LLM `input.validate` dipancarkan dari `validate_turn_payload()`.

**Catatan Ketergantungan:** Kontrak lintas-PIC — PIC lain mengandalkan konvensi span yang sama untuk dashboard observability (Milestone 5.x).

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada.

---

## Keputusan 10 (Forced): Validasi `role_title` Tanpa Lookup Database/API Data Platform

**Sumber Paksaan:** `arsitektur-ai-chatbot-rbac.md` baris 65 (`role_permissions` tanpa endpoint, 404 struktural) + baris 7 (REST API, bukan akses SQL).

**Keputusan yang Diikuti:** Daftar role didapat dari sumber statis (`roles.yaml`, lihat Keputusan 5), tidak pernah query langsung ke `chatbot_api` atau database data platform.

**Catatan Ketergantungan:** Melanggar ini berarti proyek diam-diam membangun akses SQL langsung ke data platform — pelanggaran prinsip arsitektur paling mendasar proyek ini.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada alternatif dipertimbangkan karena forced by dua fakta arsitektur ini bersamaan.

---

## Keputusan 11 (Forced): Validasi Minimal untuk `session_id`/`employee_id`/`question`

**Sumber Paksaan:** Ketiadaan definisi format di `arsitektur-ai-chatbot-rbac.md` maupun `katalog-data-chatbot.md` (dikonfirmasi lewat pencarian menyeluruh — beda dari field lain seperti `room_number`/`review_period` yang memang didefinisikan formatnya eksplisit).

**Keputusan yang Diikuti:** Validasi minimal (tipe `str` benar + `min_length=1`), tanpa pattern/regex tambahan.

**Catatan Ketergantungan:** Mengarang aturan format yang tidak ada dasarnya berisiko menolak payload sah yang sebenarnya valid menurut kontrak yang benar-benar ada.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada alternatif dipertimbangkan karena forced by ketiadaan spesifikasi — interpretasi literal paling dekat dari "field wajib ada dan berformat benar".

---

## Keputusan 12 (Forced): `turn_index` Integer ≥ 1, `previous_turn` Wajib Jika `turn_index > 1`

**Sumber Paksaan:** Kriteria Keberhasilan sumber sendiri (membedakan `turn_index=1` tanpa histori vs `turn_index>1` dengan histori) + kalimat payload §4 arsitektur induk.

**Keputusan yang Diikuti:** `turn_index: int = Field(ge=1)`; `model_validator` menolak kalau `turn_index>1` tapi `previous_turn` kosong.

**Catatan Ketergantungan:** Kriteria Keberhasilan sumber secara eksplisit menguji kedua kasus ini sebagai satu-satunya dua kondisi yang diuji.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — inferensi langsung dari kriteria, bukan pengarangan bebas.

---

## Keputusan 13 (Forced): `previous_turn` Diabaikan (Bukan Ditolak) Kalau `turn_index=1` Tapi Tetap Terkirim

**Sumber Paksaan:** Tidak ada dasar dokumen untuk menolak data ekstra yang tidak berbahaya.

**Keputusan yang Diikuti:** `previous_turn: PreviousTurn | None = None` — kalau ada isinya saat `turn_index=1`, tetap diterima (tidak divalidasi/ditolak berdasarkan keberadaannya).

**Catatan Ketergantungan:** Menolaknya bukan "menangkap masalah struktural yang jelas", justru berlawanan dengan semangat pesan error yang jelas dan spesifik (Milestone 1.2 Output).

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada alternatif nyata dipertimbangkan — perilaku permisif adalah default yang lebih aman tanpa dasar eksplisit untuk memperketat.

---

## Keputusan 14 (Forced): Pindahkan `genai_semconv.py` ke `src/observability/`

**Sumber Paksaan:** `decisions.md` Milestone 1.1 Keputusan 6 sendiri — lokasi lama eksplisit disebut sementara ("supaya tidak diam-diam mengambil keputusan struktur `src/`").

**Keputusan yang Diikuti:** `git mv infra/observability/genai_semconv.py src/observability/genai_semconv.py`, referensi diperbarui di `smoke_test/send_dummy_span.py` dan `infra/observability/README.md`.

**Catatan Ketergantungan:** Struktur `src/` sekarang sudah diputuskan (Keputusan 4) — menunda lebih lanjut tidak lagi punya alasan.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by alasan keputusan M1.1 sendiri begitu prasyaratnya (struktur `src/`) terpenuhi.

---

## Keputusan 15 (Forced): Pydantic + `uvicorn` sebagai Konsekuensi FastAPI

**Sumber Paksaan:** Keputusan 3 (FastAPI) — Pydantic terintegrasi native, `uvicorn` pasangan ASGI server standar de-facto.

**Keputusan yang Diikuti:** `TurnPayload`/`PreviousTurn` sebagai model Pydantic; `uv run uvicorn src.main:app` untuk menjalankan server.

**Catatan Ketergantungan:** Tidak ada alasan memilih ASGI server lain setelah FastAPI dipilih.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada alternatif dipertimbangkan karena forced by Keputusan 3.

---

## Keputusan 16 (Forced): Perbaikan Referensi "19"→"20" Role di `rancangan-rbac-authorization.md`

**Sumber Paksaan:** Bukti yang dikonfirmasi user (lihat Keputusan 1) — tabel §2 `rancangan-rbac-ai-chatbot.md` (20 baris) + `api-chatbot.md` ("20 persona") + cross-check internal, melawan satu angka naratif "19" di dokumen implementasi PIC 2 yang tidak menghitung ulang tabelnya sendiri.

**Keputusan yang Diikuti:** Dua kemunculan "19 role" diubah jadi "20 role" di `rancangan-rbac-authorization.md`.

**Catatan Ketergantungan:** Ini koreksi angka rujukan naratif yang salah, bukan perubahan keputusan desain RBAC apa pun — tabel `role_permissions` sendiri (sumber kebenaran domain, di luar cakupan proyek ini) tidak disentuh.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by bukti yang sudah dikonfirmasi user secara eksplisit.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Whitelist `role_title` divalidasi (20 role) | A | Plan |
| 2 | Endpoint HTTP sungguhan sekarang | A | Plan |
| 3 | FastAPI sebagai web framework | A | Plan |
| 4 | Struktur `src/` per-layer | A | Plan |
| 5 | Penyimpanan daftar role: file config YAML | A | Plan |
| 6 | Exception handler `ValidationError`→`422` | A | Checkpoint 3 |
| 7 | Swap `httpx`→`httpx2` | A | Checkpoint 4 |
| 8 | Validasi murni mekanis, tanpa LLM | B | Plan |
| 9 | Span `input.validate` | B | Plan |
| 10 | Validasi `role_title` tanpa lookup DB/API data platform | B | Plan |
| 11 | Validasi minimal field tanpa pattern | B | Plan |
| 12 | `turn_index`≥1, `previous_turn` wajib jika `turn_index>1` | B | Plan |
| 13 | `previous_turn` diabaikan jika `turn_index=1` tapi terkirim | B | Plan |
| 14 | Pindahkan `genai_semconv.py` ke `src/observability/` | B | Checkpoint 1 |
| 15 | Pydantic + `uvicorn` sebagai konsekuensi FastAPI | B | Plan |
| 16 | Perbaikan referensi "19"→"20" role | B | Checkpoint 1 |
