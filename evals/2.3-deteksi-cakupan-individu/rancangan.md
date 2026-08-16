# Rancangan Pengujian — Deteksi Constraint Cakupan-Individu (Milestone 2.3)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — skenario dan ekspektasi ditetapkan dulu. Struktur mirror `evals/2.1-identifikasi-domain/rancangan.md`. **Jumlah skenario TIDAK dipatok** — 10 skenario di sini murni hasil analisis dimensi yang belum tercakup `tests/`, bukan konvensi wajib.

## Yang Diuji

`deteksi_constraint_atomic_intent()` (`src/layers/domain_gate/cakupan_individu.py`) — Milestone 2.3 sudah lolos ketiga Kriteria Keberhasilan sumber lewat panggilan LLM nyata di `tests/layers/domain_gate/test_cakupan_individu.py` (Checkpoint 7) dan span nyata di Jaeger (Checkpoint 8): KK1 ("siapa staf tercepat" + Staff -> constraint), KK2 (kebutuhan sama + Manager -> tidak ada constraint, dari pre-filter), KK3 (domain relevan tapi genuinely bukan performa individu -> tidak ada constraint). `tests/` juga sudah menutup: kasus jelas-individu/jelas-agregat dasar (Checkpoint 4), skenario titik-buta terkontrol dengan phrasing "siapa staf tercepat" (Checkpoint 5), dan 3 pre-filter murni-mekanis (Checkpoint 6). Pengujian ini fokus pada dimensi yang **belum** tercakup: cakupan 9 view yang belum pernah disentuh (baru 1-2 dari 9 yang tersentuh `tests/`), distractor kata kunci di kedua arah, generalisasi role-differentiation ke teks baru, dan retest titik-buta dengan phrasing berbeda.

| Dimensi | Sudah diuji di `tests/`? | Skenario di sini |
|---|---|---|
| KK1-3 persis (teks "siapa staf tercepat") | Ya | — |
| Pre-filter role/domain murni-mekanis | Ya | — |
| Titik-buta terkontrol (phrasing "siapa staf tercepat") | Ya (1 phrasing) | S09 (phrasing berbeda) |
| `v_hr_employee_performance_semester`/`v_lookup_employee_performance` (review individu by name) | Tidak | S01 |
| `v_maintenance_technician_daily`/`v_lookup_maintenance_tickets` (teknisi by name) | Tidak | S02 |
| Distractor kata "staf" tapi genuinely agregat (arah keyword-hadir-tapi-agregat) | Sebagian (CP4: "berapa staf hadir") | S03 (leave count, view berbeda) |
| Agregat facility TANPA kata "staf" sama sekali | Tidak | S04 |
| Ranking individu TANPA kata "staf"/"karyawan" (jebakan arah sebaliknya) | Tidak | S05 |
| `v_hr_watchlist_monthly` (individu, sinyal risiko resign) | Tidak | S06 |
| `v_lookup_staff_shifts` (kehadiran individu by name) | Tidak | S07 |
| Generalisasi role-differentiation ke teks BARU (bukan "siapa staf tercepat") | Tidak | S08 |
| Titik-buta dengan phrasing berbeda dari `tests/` | Sebagian | S09 |
| Over-triggering verifier pada teks agregat bertema durasi/waktu (pola M2.1 keterbatasan #6) | Tidak | S10 |

## Cara Baca Skenario

Tiap skenario: teks kebutuhan (atomic intent tunggal), role pemanggil, domain yang diizinkan (hasil M2.2 disimulasikan), ekspektasi `terdeteksi`, status toleransi.

---

### S01 — Review Kinerja Individu by Name (`hr`)

**Kebutuhan:** "Bagaimana hasil review kinerja Budi semester ini?"
**Role:** `HR Staff` · **Domain diizinkan:** `hr`

**Ekspektasi:** `terdeteksi=True` — menyentuh `v_hr_employee_performance_semester`/`v_lookup_employee_performance`, skor review 1 karyawan tertentu by name.

**Toleransi:** Tidak ada — cakupan view yang belum pernah disentuh test manapun.

---

### S02 — Beban Kerja Teknisi by Name (`facility`)

**Kebutuhan:** "Berapa banyak tiket yang ditangani teknisi Andi bulan ini?"
**Role:** `Maintenance Staff` · **Domain diizinkan:** `facility`

**Ekspektasi:** `terdeteksi=True` — menyentuh `v_maintenance_technician_daily`/`v_lookup_maintenance_tickets`, beban kerja 1 teknisi tertentu.

**Toleransi:** Tidak ada.

---

### S03 — Distractor: Jumlah Cuti Agregat (`hr`)

**Kebutuhan:** "Berapa banyak staf yang mengambil cuti bulan ini?"
**Role:** `HR Staff` · **Domain diizinkan:** `hr`

**Ekspektasi:** `terdeteksi=False` — menyebut kata "staf" tapi hasilnya angka gabungan (`v_hr_attendance_daily.leave_count`), bukan granular per-orang.

**Toleransi:** Tidak ada — distractor kata kunci, beda view dari CP4 ("berapa staf hadir").

---

### S04 — Agregat Facility Tanpa Kata "Staf" (`facility`)

**Kebutuhan:** "Berapa rata-rata durasi pembersihan kamar tipe Villa dibanding baseline?"
**Role:** `Housekeeping Staff` · **Domain diizinkan:** `facility`

**Ekspektasi:** `terdeteksi=False` — `v_housekeeping_room_type_daily`, agregat per tipe kamar, tidak menyebut staf sama sekali dan tidak granular per-orang.

**Toleransi:** Tidak ada — baseline agregat murni tanpa kata kunci sama sekali.

---

### S05 — Ranking Individu Tanpa Kata "Staf"/"Karyawan" (Jebakan Arah Sebaliknya)

**Kebutuhan:** "Siapa yang paling banyak menangani tiket maintenance bulan ini?"
**Role:** `Maintenance Staff` · **Domain diizinkan:** `facility`

**Ekspektasi:** `terdeteksi=True` — genuinely ranking per-teknisi (`v_maintenance_technician_daily`) meski tidak menyebut kata "staf"/"karyawan"/"teknisi" secara eksplisit di pertanyaan.

**Toleransi:** Tidak ada — ini pengujian INTI apakah prompt (`CATATAN_INDIVIDU_VS_AGREGAT` poin 3) benar-benar mengajarkan generalisasi makna, bukan cocok kata kunci literal. Kalau gagal di sini, itu temuan signifikan terhadap desain grounding context — mirror pola pengujian S01 `evals/2.1-.../rancangan.md`.

---

### S06 — Watchlist Individu (`hr`)

**Kebutuhan:** "Karyawan mana saja yang pola absensinya menyimpang jauh dari kebiasaan pribadinya bulan ini?"
**Role:** `HR Staff` · **Domain diizinkan:** `hr`

**Ekspektasi:** `terdeteksi=True` — `v_hr_watchlist_monthly`, granular per-karyawan (deviasi dari baseline pribadi masing-masing).

**Toleransi:** Tidak ada.

---

### S07 — Kehadiran Individu by Name (`hr`)

**Kebutuhan:** "Apakah Budi sudah absen hari ini?"
**Role:** `HR Staff` · **Domain diizinkan:** `hr`

**Ekspektasi:** `terdeteksi=True` — `v_lookup_staff_shifts`, status kehadiran 1 karyawan spesifik.

**Toleransi:** Tidak ada.

---

### S08 — Generalisasi Role-Differentiation ke Teks Baru

**Kebutuhan:** "Teknisi mana yang paling sering menangani perbaikan AC bulan ini?" (IDENTIK dijalankan dua kali, role berbeda)
**Role A:** `Maintenance Staff` (ekspektasi `terdeteksi=True`) · **Role B:** `Maintenance Manager` (ekspektasi `terdeteksi=False`, dari pre-filter)
**Domain diizinkan:** `facility`

**Ekspektasi:** Role A `terdeteksi=True` dengan `alasan` terisi; Role B `terdeteksi=False` tanpa `alasan` — membuktikan pre-filter role bekerja pada teks yang BUKAN teks KK1/KK2 asli (generalisasi, bukan hasil hardcode kebetulan).

**Toleransi:** Tidak ada pada hasil akhir.

---

### S09 — Titik-Buta Phrasing Berbeda (Retest, Bukan Teks `tests/`)

**Kebutuhan:** "Bandingkan kecepatan kerja tiap staf housekeeping minggu ini."
**Role:** `Housekeeping Staff` · **Domain diizinkan:** `facility`
**Langkah 1 dipaksa keliru:** `verifikasi_cakupan_individu()` dipanggil langsung dengan `terdeteksi_awal=False` (disimulasikan sengaja salah, mirror teknik `tests/test_verifikasi_cakupan_individu.py` tapi teks BEDA dari yang sudah diuji di sana).

**Ekspektasi:** `terdeteksi_tambahan=True` — Langkah 2 menangkap kasus yang "terlewat" Langkah 1, dengan phrasing yang belum pernah diuji.

**Toleransi:** Tidak ada — kalau gagal, ini temuan nyata bahwa verifier titik-buta hanya bekerja untuk phrasing tertentu, bukan generalisasi genuine.

---

### S10 — Distractor Over-Triggering: Durasi/Waktu Agregat (`facility`)

**Kebutuhan:** "Berapa rata-rata waktu penyelesaian tiket maintenance bulan ini, dan apakah melebihi SLA?"
**Role:** `Maintenance Staff` · **Domain diizinkan:** `facility`

**Ekspektasi:** `terdeteksi=False` — `v_maintenance_ticket_daily`, agregat per area/jenis isu, TIDAK menyebut teknisi tertentu. Kata "waktu"/"durasi" bertema temporal berpotensi memicu over-triggering verifikasi titik buta, mirip pola `docs/keterbatasan-diterima.md` #6 (M2.1, kata bertema finansial/temporal).

**Toleransi eksplisit:** Kalau `terdeteksi=True` (verifier over-trigger), INI BUKAN otomatis dianggap fail keras — dicatat sebagai temuan pola over-triggering di `audit.md`, kandidat entri baru `docs/keterbatasan-diterima.md` kalau konsisten (mirror pola toleransi S04 `evals/2.1-.../rancangan.md`).

---

## Ringkasan Ekspektasi

| ID | Ekspektasi `terdeteksi` | Toleransi |
|---|---|---|
| S01 | `True` | Tidak |
| S02 | `True` | Tidak |
| S03 | `False` | Tidak |
| S04 | `False` | Tidak |
| S05 | `True` | Tidak — inti pengujian generalisasi |
| S06 | `True` | Tidak |
| S07 | `True` | Tidak |
| S08 | Role A `True`, Role B `False` | Tidak |
| S09 | `terdeteksi_tambahan=True` | Tidak |
| S10 | `False` | Ya — kalau `True`, dicatat temuan over-triggering, bukan fail keras |
