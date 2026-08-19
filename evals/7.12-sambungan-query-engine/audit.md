# Audit — Sambungan 7: Retriever → Query Engine (Milestone 7.12)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-19), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap kejadian ada di `payloads/<ID>.json`. Docker Compose (Jaeger+Collector+Prometheus) berjalan lokal sepanjang eksekusi (sudah `up` dari sesi M7.11).

**Catatan operasional**: percobaan eksekusi PERTAMA mengalami hang (~24.7 menit tanpa progres, terdeteksi via laporan langsung user + verifikasi query Jaeger API), dihentikan dan dijalankan ulang — lihat `milestones/7.12-sambungan-query-engine/logs.md` Checkpoint 6 untuk detail lengkap insiden. Hasil di bawah adalah dari eksekusi KEDUA (berhasil).

## Ringkasan

**3/3 kejadian LOLOS — `view_name` yang dikirim Query Engine PERSIS SAMA dengan `view_name_final` hasil Retriever di SELURUH 5 atomic intent** (E01: 3 intent, E03: 1 intent) yang diteruskan, dan item dengan `view_name_final=None` (E02: 1 intent) TERBUKTI di-skip, tidak pernah mencapai Query Engine sama sekali. KK literal M7.12 terbukti PALING JELAS di E01: ketiga atomic intent (termasuk replikasi persis skenario `gop_margin` M2.1/M7.3) menghasilkan `view_name_final=v_reservation_gop_impact_monthly`, dan `request.view_name` yang benar-benar dikirim ke `susun_request_atomic_intent()` — dikonfirmasi lewat inspeksi langsung return value Python DAN span `chat` M3.4/M3.5 di Jaeger — PERSIS sama, tanpa satu pun penyimpangan.

**Penyimpangan dari rencana (non-determinisme Decomposition, pola berulang M7.9→M7.12)**: E01 menghasilkan 3 atomic intent yang KETIGANYA `view_name_final=v_reservation_gop_impact_monthly` — berbeda komposisi dari run M7.11 asli (yang menghasilkan 3 intent dengan HANYA 1 memakai view ini, 1 lainnya `view_name_final=None`). Dicatat transparan, TIDAK di-retry untuk memaksa reproduksi persis — komposisi berbeda ini justru memberi 3 bukti independen sekaligus untuk KK literal M7.12 di satu kejadian, bukan melemahkan verdict.

| ID | `role_title` | Jumlah atomic intent | `view_name_final` terisi | Diteruskan ke Query Engine | `view_name` persis sama | Verdict |
|---|---|---|---|---|---|---|
| E01 | Front Office Staff | 3 | 3/3 | 3/3 | 3/3 | ✅ **LOLOS — bukti KK literal utama (3x independen)** |
| E02 | F&B Staff | 1 | 0/1 (`None`) | 0/1 (di-skip) | — | ✅ LOLOS — bukti skip bekerja |
| E03 | HR Staff | 1 | 1/1 | 1/1 | 1/1 | ✅ LOLOS — bukti kedua independen |

## Analisis Per Kejadian

### E01 — `view_name` persis sama, replikasi gop_margin (LOLOS — bukti KK literal utama)

`trace_id=0463a32203101e9256672c0fa87cc6f7`. Payload: `role_title="Front Office Staff"`, pertanyaan "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?" (teks identik `evals/7.11-.../E01`, `session_id` baru `eval-7.12-e01`). Decomposition menghasilkan 3 atomic_intents — SEMUA 3 diidentifikasi Domain Gate menyentuh kombinasi domain yang membawa hasil Retriever `view_name_final=v_reservation_gop_impact_monthly` (view domain `reservation` dengan kolom turunan `financial`, persis pola KK literal M2.1/M7.3).

Untuk KETIGA atomic intent: `susun_dan_verifikasi_request_semua()` menerima `view_name_final` terisi, TIDAK di-skip, dipanggil `susun_dan_verifikasi_request_atomic_intent(atomic_intent, "v_reservation_gop_impact_monthly")`. Hasil: `request.view_name == "v_reservation_gop_impact_monthly"` untuk KETIGANYA — `view_name_persis_sama=True` di seluruh 3 intent. Span Jaeger mengonfirmasi: `query_engine.susun_dan_verifikasi_request_semua` (`intent.count=3`), 6 span `chat` (2 per intent — M3.4 Penyusunan Request + M3.5 Verifikasi Bentuk Request) SEMUA membawa tag `request.view_name="v_reservation_gop_impact_monthly"`, `request.domain="reservation"`.

**Kesimpulan: Kriteria Keberhasilan literal Milestone 7.12 TERPENUHI PENUH, dibuktikan TIGA KALI independen dalam satu kejadian** — view hasil Retriever mengalir ke Query Engine dan menghasilkan request dengan `view_name` yang persis sama, dibuktikan lewat inspeksi return value real-execution DAN span Jaeger yang menunjukkan data nyata (bukan dicocokkan manual).

### E02 — Item `view_name_final=None` di-skip (LOLOS — bukti skip bekerja)

`trace_id=3f1c27f67c469e42a5208ebac35515c5`. Payload: `role_title="F&B Staff"`, "Berapa GOP (gross operating profit) properti bulan ini?" (teks identik `evals/7.11-.../E03`, `session_id` baru `eval-7.12-e02`). Decomposition `tunggal`, 1 atomic_intent — PERSIS sesuai prediksi (berbeda dari E01, kejadian ini reproduksi bersih). Domain `financial` teridentifikasi, DITOLAK seluruhnya untuk F&B Staff (mewarisi hasil M7.11 Checkpoint-nya sendiri), `domain_diizinkan=[]`, Retriever mengembalikan `view_name_final=None`.

`susun_dan_verifikasi_request_semua()` menerima item ini (span `intent.count=1`, dihitung SEBELUM filter — sesuai desain Keputusan 8), TAPI filter internal (`view_name_final is not None`) meng-exclude-nya — `susun_dan_verifikasi_request_atomic_intent()` TIDAK PERNAH terpanggil untuk intent ini, dikonfirmasi: `diteruskan_ke_query_engine=False`, `KeadaanTurn.query_engine` kosong untuk kejadian ini, DAN tidak ada span `chat` dengan tag `request.view_name` muncul di trace sama sekali (0 span, sesuai `span_info`).

**Kesimpulan: mekanisme skip (Keputusan 4) terbukti bekerja nyata** — item tanpa view yang cukup tidak pernah mencapai Query Engine, `proses_turn()` selesai normal tanpa exception.

### E03 — Bukti kedua independen (LOLOS)

`trace_id=ae70c85c82b35c3e1a31f6cdcb722e7b`. Payload: `role_title="HR Staff"`, "Bagaimana hasil review kinerja Budi semester ini?" (teks identik `evals/7.11-.../E04`, `session_id` baru `eval-7.12-e03`). Decomposition `tunggal`, 1 atomic_intent — PERSIS sesuai prediksi. Domain `hr` teridentifikasi dan diizinkan, Retriever menghasilkan `view_name_final=v_hr_employee_performance_semester` (identik hasil M7.11 E04).

`request.view_name` yang dikirim = `v_hr_employee_performance_semester`, PERSIS sama dengan `view_name_final` — `view_name_persis_sama=True`. Span `chat` ×2 (M3.4+M3.5) mengonfirmasi `request.view_name`/`request.domain="hr"` konsisten.

**Kesimpulan: bukti KEDUA independen untuk KK literal M7.12**, di domain berbeda (`hr` vs `reservation` E01) dan role berbeda — memperkuat generalisasi klaim "kepatuhan sumber" melampaui satu domain/skenario tunggal.

## Temuan Metodologi

**Non-determinisme Decomposition (E01)**: komposisi 3 atomic_intent E01 (ketiganya bermuara ke `view_name_final` yang sama) berbeda dari run M7.11 asli (campuran, hanya 1 dari 3) — data point tambahan untuk `docs/keterbatasan-diterima.md` #3, konsisten pola M7.9→M7.10→M7.11→M7.12. Tidak memengaruhi verdict KK — justru memperkuatnya lewat replikasi 3x independen dalam satu kejadian.

**Insiden hang eksekusi (percobaan pertama)**: lihat `logs.md` Checkpoint 6 untuk kronologi lengkap. Ringkasan: proses hang ~24.7 menit pada trace E01 (terdeteksi lewat laporan user + verifikasi Jaeger, BUKAN dari output `run_eval.py` sendiri yang stdout-nya ter-buffer penuh saat dijalankan via background process — pelajaran operasional: monitoring progres eval jangka panjang sebaiknya via query Jaeger langsung, bukan menunggu buta output proses). Insiden ini melampaui klaim mitigasi `docs/keterbatasan-diterima.md` #7 ("~180s terburuk per panggilan") secara signifikan — dicatat sebagai temuan baru yang layak jadi follow-up peninjauan ulang entri itu (lihat `report.md` Bagian 6), TIDAK diperbaiki di M7.12 sendiri (di luar cakupan — bukan bug logic kode M7.12, murni observasi operasional infrastruktur/provider LLM).
