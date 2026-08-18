# Audit — Sambungan 3: Rewrite → Decomposition (Milestone 7.8)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-18), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap kejadian ada di `payloads/<ID>.json`. Docker Compose (Jaeger+Collector+Prometheus) dijalankan lokal sepanjang eksekusi.

## Ringkasan

**2/2 kejadian membuktikan KK M7.8 terpenuhi** — tapi E01 butuh koreksi penilaian di tengah audit (lihat "Temuan Metodologi" di bawah): verdict mekanis `lolos_konten=False` dari `run_eval.py` adalah **false negative** akibat asumsi `forbidden_phrases` yang keliru di `rancangan.md`, bukan kegagalan wiring/konten sungguhan. Verdict SUBSTANTIF (dinilai langsung terhadap teks KK M7.8, bukan lewat proxy mekanis yang keliru) untuk E01 adalah **LOLOS**.

| ID | Ekspektasi (mekanis, `rancangan.md`) | Aktual (mekanis) | Verdict Substantif (vs teks KK) |
|---|---|---|---|
| E01 | `required=[april,2025]` ada, `forbidden=[satu tahun sebelumnya,2026]` tidak ada | `required` ✅ ada; `forbidden`: "satu tahun sebelumnya" ✅ tidak ada, TAPI "2026" muncul (lihat Temuan Metodologi) | ✅ **Lolos** — bukti KK literal M7.8 |
| E02 | `required=[reservasi,maret,2026]` ada | ✅ Sesuai persis | ✅ Lolos — baseline kontras |

## Analisis Per Kejadian

### E01 — Kasus elipsis/koreferensi (bukti KK literal utama)

**Payload:** turn 2, "Bandingkan dengan occupancy satu tahun sebelumnya." + histori turn 1 "Occupancy April 2026 mencapai 78%."

**Rewrite:** `rewritten_question = "Bagaimana tingkat occupancy April 2026 dibandingkan dengan tingkat occupancy April 2025?"` — resolusi BENAR sesuai KK M1.4 asli ("satu tahun sebelumnya" dari April 2026 → April 2025, keduanya disebut eksplisit karena kalimat ini adalah PERBANDINGAN, bukan pernyataan tunggal).

**Decomposition** (`klasifikasi=majemuk_bergantung`, `retry_count=0`, `verifikasi_valid=true`):
1. "Berapa tingkat occupancy April 2025?" — `independen`
2. "Berapa tingkat occupancy April 2026?" — `independen`
3. "Bagaimana perbandingan tingkat occupancy April 2026 dengan April 2025?" — `bergantung`, `bergantung_pada=[intent 1, intent 2]`

**Temuan Metodologi (koreksi penilaian di tengah audit):** `rancangan.md` menetapkan `forbidden_phrases=["satu tahun sebelumnya", "2026"]` dengan asumsi keliru bahwa kalimat mandiri hasil resolusi HANYA akan menyebut tahun tujuan (2025). Asumsi ini salah — kalimat mandiri yang benar untuk pertanyaan PERBANDINGAN ("Bandingkan dengan...") secara linguistik WAJIB menyebut KEDUA sisi yang dibandingkan (April 2026 sebagai baseline dari histori, April 2025 hasil resolusi "satu tahun sebelumnya") supaya perbandingan itu sendiri bermakna. `rewrite_to_standalone()` (M1.4) sudah benar melakukan ini, dan `decompose_question()` (M1.6) benar mewarisinya — bahkan menghasilkan struktur `majemuk_bergantung` yang PERSIS mengikuti pola KK asli M1.6 sendiri ("bandingkan X dengan Y... menghasilkan lebih dari satu kebutuhan atomik dengan relasi ketergantungan yang benar").

Yang SEHARUSNYA jadi sinyal kegagalan (dan genuinely TIDAK muncul) adalah **teks ambigu asli** "satu tahun sebelumnya" bocor mentah ke Decomposition — itu satu-satunya `forbidden_phrase` yang benar dari sisi desain, dan itu terbukti **tidak pernah muncul** (`forbidden_phrases_ditemukan["satu tahun sebelumnya"] = false`). "2026" tidak seharusnya pernah masuk daftar forbidden untuk skenario perbandingan — kesalahan ada di perancangan `rancangan.md`, bukan di kode produksi.

**Kesimpulan:** **Kriteria Keberhasilan literal Milestone 7.8 TERPENUHI PENUH** — Decomposition menghasilkan pemecahan atomik yang konsisten dengan makna kalimat MANDIRI (perbandingan April 2026 vs April 2025, keduanya eksplisit), bukan makna kalimat ASLI sebelum di-rewrite (yang sama sekali tidak menyebut tahun/bulan apa pun — "satu tahun sebelumnya" tanpa referensi tereksplisit). Verdict mekanis `lolos_konten=False` di `payloads/E01.json` dikoreksi eksplisit di sini menjadi **LOLOS** berdasar teks KK sesungguhnya, bukan proxy `forbidden_phrases` yang keliru dirancang.

**Konfirmasi sekunder (span):** `trace_id=06c731a65a8103a9dfdbed8fa41373ff`, 5 span `chat` (Pemetaan Ketergantungan M1.3 ×1, Rewrite M1.4 ×1, Decomposition M1.6 ×3 — klasifikasi+pemecahan+verifikasi) SEMUA `parentSpanID` = span `invoke_agent`, dikonfirmasi lewat query Jaeger API langsung. Decomposition genuinely dipanggil sekuensial di thread utama yang sama (tanpa perlu propagasi context manual), spannya tetap tercatat sebagai bagian trace turn yang sama.

### E02 — Kasus sudah mandiri (baseline kontras, LOLOS)

**Payload:** turn 1, "Berapa revenue reservasi bulan Maret 2026?", tanpa histori.

**Rewrite:** diteruskan tanpa perubahan (`rewritten_question` identik `payload.question`) — turn pertama, tidak ada yang perlu diresolusi.

**Decomposition** (`klasifikasi=tunggal`, `retry_count=0`): satu `atomic_intent` — "Berapa revenue reservasi bulan Maret 2026?", `relasi=independen`.

**Kesimpulan:** Sesuai ekspektasi persis, mekanis DAN substantif. Berfungsi sebagai kontras terhadap E01 — membuktikan verdict E01 bukan kebetulan "selalu lolos terlepas dari isi Rewrite": di sini Decomposition tetap setia pada kalimat mandiri yang jauh lebih sederhana (satu kebutuhan tunggal, bukan majemuk), bukan pola tetap yang sama di semua kasus.

**Konfirmasi sekunder (span):** `trace_id=d9bf0ba3b5d28c2bff024d7d325b4290`, 5 span `chat` (Pemetaan Ketergantungan ×1, Rewrite ×1, Decomposition ×3), semua anak `invoke_agent`. Tidak ada span `memory.retrieve` (konsisten `is_dependent=false`, mewarisi perilaku M7.7).

## Temuan Metodologi

Kesalahan desain `forbidden_phrases` di `rancangan.md` E01 (menandai "2026" sebagai terlarang, padahal legitimately muncul di kalimat mandiri hasil perbandingan) adalah pelajaran untuk milestone Sambungan berikutnya yang memakai verdict berbasis konten (bukan span): **`forbidden_phrases` harus dipetakan dari kata/frasa yang SECARA LINGUISTIK mustahil muncul di kalimat mandiri yang benar** (mis. frasa rujukan mentah seperti "satu tahun sebelumnya", "itu", "tadi"), **bukan dari entitas/nilai spesifik** (seperti tahun) yang bisa jadi legitimately relevan tergantung struktur kalimat (perbandingan vs pernyataan tunggal). Dicatat di sini sebagai koreksi, bukan disembunyikan — `rancangan.md` TIDAK diubah retroaktif (tetap jadi catatan ekspektasi apa adanya sebelum eksekusi), koreksi penilaian didokumentasikan eksplisit di sini sesuai kejadian sesungguhnya.
