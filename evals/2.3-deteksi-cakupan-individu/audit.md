# Audit — Deteksi Constraint Cakupan-Individu (Milestone 2.3)

Dieksekusi `uv run python evals/2.3-deteksi-cakupan-individu/run_eval.py <ID>` satu per satu (bukan batch — mirror mitigasi hang M2.1 Checkpoint 10). Payload lengkap tersimpan di `payloads/`.

## Ringkasan

| ID | Status | Deskripsi |
|---|---|---|
| S01 | LOLOS | Review kinerja individu by name (hr) |
| S02 | LOLOS | Beban kerja teknisi by name (facility) |
| S03 | LOLOS | Distractor: jumlah cuti agregat (hr) |
| S04 | LOLOS | Agregat facility tanpa kata staf |
| S05 | LOLOS | Ranking individu tanpa kata staf/karyawan (jebakan arah sebaliknya) |
| S06 | LOLOS | Watchlist individu (hr) |
| S07 | LOLOS | Kehadiran individu by name (hr) |
| S08 | LOLOS | Generalisasi role-differentiation ke teks baru |
| S09 | LOLOS | Titik-buta phrasing berbeda (retest) |
| S10 | LOLOS | Distractor over-triggering: durasi/waktu agregat (facility) |

**10/10 skenario lolos.** Tidak ada REVIEW.

## Analisis per Skenario

**S01-S02** — cakupan 4 dari 9 view yang belum pernah disentuh `tests/` (`v_hr_employee_performance_semester`/`v_lookup_employee_performance`, `v_maintenance_technician_daily`/`v_lookup_maintenance_tickets`) sekarang terbukti terdeteksi benar untuk kueri by-name konkret.

**S03-S04** — dua bentuk distractor "kata ada, makna agregat" (S03: kata "staf" hadir tapi hasilnya angka gabungan; S04: bahkan tanpa kata "staf" sama sekali) sama-sama tidak memicu false-positive. Prompt (`CATATAN_INDIVIDU_VS_AGREGAT` poin 2-3) bekerja sesuai desain di kedua arah.

**S05** — pengujian INTI generalisasi (mirror pola S01 `evals/2.1-.../rancangan.md`): "Siapa yang paling banyak menangani tiket maintenance bulan ini?" TIDAK menyebut kata "staf"/"karyawan"/"teknisi" sama sekali, tapi genuinely ranking per-teknisi. LOLOS — mengonfirmasi prompt mengajarkan pemahaman makna, bukan cocok kata kunci literal semata.

**S06-S07** — 2 view `hr` tambahan (`v_hr_watchlist_monthly`, `v_lookup_staff_shifts`) terdeteksi benar. Bersama S01, ini menuntaskan cakupan seluruh 5 view `hr` yang tersentuh minimal sekali oleh kombinasi `tests/`+eval (KK1/KK3 sudah menyentuh `facility`, S01/S06/S07 menyentuh 3 dari 5 view `hr`; `v_hr_employee_monthly` masih belum tersentuh eksplisit tapi termasuk kategori sama seperti S01/S06/S07 — pola sudah terbukti konsisten lintas 3 view berbeda).

**S08** — role-differentiation (KK2) terbukti generalisasi ke teks yang SAMA SEKALI berbeda dari teks asli KK1/KK2 ("Teknisi mana yang paling sering menangani perbaikan AC bulan ini?", bukan "siapa staf tercepat"). Role A (`Maintenance Staff`) → `terdeteksi=True` dengan `alasan`; Role B (`Maintenance Manager`) → `terdeteksi=False` tanpa `alasan`, keduanya dari `atomic_intent_id` yang SAMA (dua panggilan `deteksi_constraint_atomic_intent()` terpisah, bukan fixture ganda) — membuktikan pre-filter role bukan hasil hardcode kebetulan terhadap satu teks spesifik.

**S09** — titik-buta dengan phrasing berbeda dari `tests/test_verifikasi_cakupan_individu.py` ("Bandingkan kecepatan kerja tiap staf housekeeping minggu ini", bukan "siapa staf tercepat bulan ini"), `terdeteksi_awal` dipaksa `False`. Langkah 2 menangkapnya (`terdeteksi_tambahan=True`) — verifier titik-buta generalisasi ke phrasing baru, bukan hanya bekerja untuk satu kalimat spesifik yang kebetulan sudah diuji.

**S10** — skenario dengan toleransi eksplisit (kandidat over-triggering mirip `docs/keterbatasan-diterima.md` #6 M2.1, kata bertema durasi/waktu). **Hasil: TIDAK over-trigger** (`terdeteksi=False` sesuai ekspektasi) — berbeda dari pola M2.1 yang konsisten over-trigger pada tema serupa. Kemungkinan penyebab: teks S10 ("rata-rata waktu penyelesaian... apakah melebihi SLA") eksplisit menyebut "rata-rata" (penanda agregat kuat), sementara temuan M2.1 #6 tidak selalu py penanda agregat literal sekuat itu di teksnya. **Tidak dijadikan entri baru `docs/keterbatasan-diterima.md`** — satu temuan positif belum cukup bukti pola berulang seperti kriteria M2.1 (yang diverifikasi konsisten di beberapa skenario sebelum dicatat sebagai keterbatasan diterima); dicatat di sini sebagai observasi untuk pemantauan berkelanjutan lewat `prompt_reliability/` (Checkpoint 10), bukan diterima sebagai keterbatasan permanen prematur.

## Kesimpulan

Tidak ada temuan REVIEW/gagal di eval ini — berbeda dari pola M1.6/M1.7/M2.1 yang masing-masing menemukan minimal satu isu nyata. Ini dibaca sebagai sinyal desain grounding context (`CATATAN_INDIVIDU_VS_AGREGAT`, disusun eksplisit dengan 3 poin termasuk jebakan kata kunci di KEDUA arah) cukup robust untuk 10 dimensi yang diuji — BUKAN berarti mekanisme bebas keterbatasan sama sekali. Pemantauan berkelanjutan (Promptfoo, Checkpoint 10) tetap diperlukan karena non-determinisme `temperature=0` pada model (pola sudah terdokumentasi `docs/keterbatasan-diterima.md` #3 lintas M1.3/M1.4/M1.7) berarti satu run yang lolos tidak menjamin lolos di run berikutnya dengan input yang sama persis.
