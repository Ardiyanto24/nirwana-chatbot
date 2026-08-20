# Decisions — Milestone 4.5: Membangun Verifikasi Kesetiaan Data dan Penyusunan Visualisasi

Dokumen ini mencatat setiap keputusan desain untuk Milestone 4.5, seluruhnya ditentukan sebelum implementasi dimulai (Plan Mode), sesuai urutan kemunculan di plan. Tidak ada Jenis A (genuinely terbuka) — seluruh 14 keputusan Jenis B (forced/preseden), dikonfirmasi eksplisit di plan section "Keputusan yang Ditanyakan ke User".

---

## Keputusan 1: Model verifikasi `deepseek/deepseek-v4-pro`, `reasoning="high"`

**Sumber Paksaan**
Preseden model verifier TIDAK TERPUTUS di 5 milestone berturut-turut: M1.6 Langkah 6 (Verifikasi Pemecahan), M2.1 Langkah 2 (Verifikasi Titik Buta), M2.3 Langkah 2 (Verifikasi Cakupan Individu), M3.2 Langkah 2 (Kecocokan Makna Verifikasi), M3.5 Langkah 2 (Verifikasi Bentuk Request) — seluruhnya reuse `deepseek/deepseek-v4-pro` + `reasoning="high"` TANPA perbandingan empiris baru, masing-masing dengan alasan "satu konstanta per konsumen, tidak perlu perbandingan empiris baru".

**Keputusan yang Diikuti**
Konstanta baru `OPENROUTER_MODEL_VERIFIKASI_KESETIAAN = "deepseek/deepseek-v4-pro"`, dipakai dengan `extra_body={"reasoning": {"effort": "high"}}`.

**Catatan Ketergantungan**
Sengaja TIDAK diajukan ulang ke user via `AskUserQuestion` (beda dari M4.4 yang mengajukan pertanyaan model untuk `susun_narasi()`) — tugas verifier di sini tetap berbentuk SAMA (menilai independen, mengembalikan `lolos`/`alasan`) seperti 5 preseden sebelumnya, beda dari M4.4 yang genuinely tugas baru (generate teks bebas tanpa preseden persis manapun). Risiko residual (verifier mungkin kurang piawai menangkap klaim sebab-akibat halus dalam PROSA, beda dari menilai struktur terstruktur seperti 5 preseden) dicatat eksplisit di Risiko & Mitigasi plan, dimitigasi lewat eval yang secara khusus menguji skenario klaim sebab-akibat (KK sumber paling eksplisit).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Mengajukan ulang pertanyaan model ke user (mirror M4.4)** — dipertimbangkan mengingat penekanan user soal kehati-hatian di area Interpretation. Ditolak karena tugas verifier (menilai keputusan lolos/tidak + alasan) BUKAN tugas baru seperti generate teks bebas — sudah py 5 preseden identik yang tidak pernah dipertanyakan ulang; mengajukan pertanyaan di sini berisiko jadi pola "tanya model tiap milestone" yang bertentangan dengan prinsip CLAUDE.md "jangan tanya ulang keputusan yang sudah dipaksa preseden".

---

## Keputusan 2: TIDAK membangun retry loop balik ke `susun_narasi()` (M4.4)

**Sumber Paksaan**
Preseden PERSIS M3.5 (`milestones/3.5-verifikasi-bentuk-request/report.md` Bagian 5-6): "Jalur perbaikan/retry (baik ke M3.4 maupun ke Execution `400`) TETAP di luar cakupan — dokumen sumber sendiri eksplisit menyatakan ini 'perlu disepakati... sebelum diimplementasikan di kedua sisi' dengan pemilik `rancangan-execution-interpretation.md`." Retry loop M3.4↔M3.5 baru dibangun BELAKANGAN oleh M4.2, dipicu kebutuhan nyata (`400` dari `chatbot_api`), bukan oleh M3.5 sendiri.

**Keputusan yang Diikuti**
`verifikasi_kesetiaan_narasi()` mengembalikan `lolos=False`+`alasan` apa adanya, TANPA memanggil ulang `susun_narasi()` dengan feedback. Tidak ada parameter `feedback` di `susun_narasi()` M4.4 yang perlu ditambah sekarang.

**Catatan Ketergantungan**
Membangun retry sekarang berarti mengasumsikan bentuk orkestrator masa depan (belum ada wiring end-to-end di project ini) — berisiko salah tebak persis seperti alasan M3.5 tidak membangunnya, dan berpotensi perlu dirombak ulang begitu kebutuhan nyata (kalau ada) muncul dari pemanggil sesungguhnya.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden M3.5 persis (kasus paling analog di seluruh project — sama-sama split generate-verify lintas dua milestone).

---

## Keputusan 3: `temperature=0`, `response_format={"type": "json_object"}`

**Sumber Paksaan**
Preseden SELURUH verifier project (M1.6/M2.1/M2.3/M3.2/M3.5) yang mengembalikan keputusan terstruktur (`lolos`/`alasan`) — beda dari M4.4 (Narasi) yang outputnya teks bebas sehingga TIDAK memakai `response_format`.

**Keputusan yang Diikuti**
`verifikasi_kesetiaan_narasi()` memanggil LLM dengan `temperature=0`, `response_format={"type": "json_object"}`.

**Catatan Ketergantungan**
Output verifier ADALAH keputusan terstruktur (`lolos: bool`, `alasan: str|null`) — beda mendasar dari M4.4 yang outputnya prosa bebas. `response_format=json_object` di sini forced oleh BENTUK TUGAS, bukan preferensi implementasi.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden + bentuk tugas.

---

## Keputusan 4: Skema `HasilVerifikasiNarasi` mencetak `HasilVerifikasiBentukRequest`

**Sumber Paksaan**
`HasilVerifikasiBentukRequest` (M3.5, `src/schemas/query_engine.py`): `lolos: bool | None`, `alasan: str | None`, `status: StatusEksekusi` (`BERHASIL`/`GAGAL_TEKNIS`), validator (gagal_teknis→lolos/alasan None; lolos=True→alasan None; lolos=False→alasan wajib). Bentuk output yang diminta Lingkup M4.5 sendiri ("mengembalikan keputusan lolos atau perlu revisi dengan alasan spesifik") SAMA PERSIS bentuknya dengan output M3.5.

**Keputusan yang Diikuti**
`HasilVerifikasiNarasi(BaseModel)`: `narasi: str` (disalin utuh dari input, jejak audit), `status: StatusEksekusi`, `lolos: bool | None`, `alasan: str | None`, validator identik `HasilVerifikasiBentukRequest`.

**Catatan Ketergantungan**
Menyimpang dari pola ini (mis. menambah field granular per-kriteria) akan menciptakan bentuk baru tanpa alasan kuat, padahal Lingkup sumber sendiri hanya minta SATU keputusan lolos/tidak + SATU alasan, persis M3.5.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Field terpisah per 5 kriteria verifikasi (mis. `data_lengkap: bool`, `sebab_akibat_valid: bool`, dst.)** — ditolak: Lingkup/KK sumber hanya minta SATU keputusan lolos/perlu-revisi + SATU alasan spesifik, bukan breakdown per-kriteria; menambah field granular tanpa diminta melanggar prinsip "jangan menambah fitur di luar yang diminta" (`CLAUDE.md`).

---

## Keputusan 5: Reuse `_build_user_prompt()` (`narasi.py`, M4.4) untuk konteks ground-truth verifier

**Sumber Paksaan**
Verifier butuh PERSIS data yang sama yang dipakai `susun_narasi()` untuk menyusun narasi (daftar kebutuhan+status+sumber+nilai_hasil+catatan_interpretasi+relasi `bergantung_pada`), supaya bisa menilai "angka yang disebutkan benar-benar berasal dari data yang diterima". Mirror pola reuse `DEFINISI_LENGKAP_VIEW` (M3.2→M3.5) — data yang sama dipakai generate DAN verify, bukan diduplikasi.

**Keputusan yang Diikuti**
`verifikasi_kesetiaan.py` mengimpor `_build_user_prompt()` dari `narasi.py` langsung, menyisipkan narasi yang dinilai sebagai bagian tambahan user prompt.

**Catatan Ketergantungan**
Kalau `_build_user_prompt()` di `narasi.py` berubah bentuk (mis. menambah field baru), verifier otomatis ikut menerima konteks yang sama — konsisten, TIDAK bisa drift diam-diam seperti kalau logic dirakit ulang terpisah.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menulis ulang logic perakitan konteks terpisah khusus verifier** — ditolak: duplikasi logic murni, berisiko drift kalau salah satu diubah tanpa yang lain ikut diperbarui; tidak ada alasan substantif kenapa verifier butuh representasi data yang berbeda dari yang dipakai generate.

---

## Keputusan 6: Span `chat` untuk verifikasi

**Sumber Paksaan**
`rancangan-observability-ai-chatbot.md` Bagian 2, baris "Interpretation (Narasi, Verifikasi Kesetiaan)": `chat` ×2 — satu untuk M4.4 (Narasi, sudah selesai), satu untuk M4.5 (Verifikasi Kesetiaan).

**Keputusan yang Diikuti**
`verifikasi_kesetiaan_narasi()` membuka span `chat` dengan atribut `gen_ai.request.model`, `gen_ai.usage.*`, `prompt.id`/`prompt.version`.

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang — kontrak lintas-PIC yang perubahannya wajib dikomunikasikan ke seluruh pemilik pekerjaan lain.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kontrak observability Bagian 2.

---

## Keputusan 7: Penyusunan Data Visualisasi murni deterministik, TANPA model AI

**Sumber Paksaan**
Lingkup M4.5 sumber eksplisit: "digabung dalam milestone yang sama dengan penyusunan data terstruktur untuk visualisasi (**transformasi struktur data murni, tanpa model AI**, menyesuaikan label bentuk jawaban dari Decomposition)".

**Keputusan yang Diikuti**
`susun_data_visualisasi()` (`src/layers/interpretation/visualisasi.py`) adalah fungsi Python murni, TIDAK memanggil `get_openrouter_client()`/LLM apa pun.

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang — dinyatakan eksplisit di dokumen sumber, bukan pilihan implementasi.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by Lingkup M4.5 sumber secara eksplisit.

---

## Keputusan 8: Skema `DataVisualisasi` — `nilai_tunggal` (scalar) vs `deret` (list)

**Sumber Paksaan**
Kriteria Keberhasilan sumber M4.5 secara eksplisit: "kebutuhan berlabel tren benar-benar berbentuk **deret** yang bisa digambar sebagai grafik garis, dan untuk kebutuhan berlabel nilai tunggal berbentuk **angka tunggal** yang sesuai." Ini bentuk minimum yang MENGIKAT, diturunkan langsung dari teks KK — bukan invensi bebas.

**Keputusan yang Diikuti**
`DataVisualisasi(BaseModel)`: `atomic_intent_id: str`, `label_bentuk_jawaban: LabelBentukJawaban`, `nilai_tunggal: float | int | str | None`, `deret: list[dict] | None` — validator memastikan tepat satu terisi sesuai label (`nilai_tunggal` label → field `nilai_tunggal` terisi, field `deret`=None; 4 label lain → sebaliknya).

**Catatan Ketergantungan**
Perluasan `deret` ke 3 label SELAIN `tren` (`perbandingan`/`peringkat`/`komposisi`) adalah penalaran-dianalogikan (ketiganya secara inheren multi-nilai/multi-kategori, sama seperti `tren`), BUKAN forced langsung dari teks KK yang hanya eksplisit menyebut `tren` dan `nilai_tunggal` — dicatat PROVISIONAL (lihat Keputusan 9), direkonsiliasi begitu PIC 5 (dashboard) benar-benar mulai dan tahu kebutuhan chart library-nya nyata.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Skema terpisah per-label (5 Pydantic model berbeda, mis. `DataTren`, `DataPeringkat`, dst.)** — dipertimbangkan untuk type-safety lebih ketat. Ditolak: tanpa konsumen nyata (PIC 5 belum mulai), tidak ada bukti bentuk detail apa yang genuinely dibutuhkan tiap label; skema tunggal `scalar-vs-list` sudah cukup memenuhi KK sumber literal, lebih murah diubah nanti (satu tempat, bukan 5 model terpisah) begitu kebutuhan nyata diketahui.

---

## Keputusan 9: Perluasan `deret` ke `perbandingan`/`peringkat`/`komposisi` dicatat PROVISIONAL

**Sumber Paksaan**
Tidak ada kontrak/preseden eksplisit — PIC 5 (Observability Dashboard, konsumen sesungguhnya) belum mulai sama sekali. Mirror pola provisional lain di project: `PARAM_WHITELIST_VIEW` (M3.4, `docs/keputusan-tertunda.md` #3), `BM25_SKOR_MINIMUM` (M3.1, `docs/keputusan-tertunda.md` #2) — keduanya "keputusan pragmatis terbaik yang tersedia SEKARANG, didokumentasikan jujur sebagai provisional, direkonsiliasi nanti begitu konsumen nyata tersedia."

**Keputusan yang Diikuti**
Dicatat eksplisit di `docs/keputusan-tertunda.md` (entri baru) — 3 label (`perbandingan`/`peringkat`/`komposisi`) memakai bentuk `deret` yang SAMA dengan `tren`, TANPA bukti nyata kebutuhan frontend, direvisit begitu M5.x mulai.

**Catatan Ketergantungan**
Biaya perubahan SEKARANG rendah (belum ada konsumen yang bergantung pada bentuk ini) — beda dari kalau perubahan ini terjadi SETELAH M5.x mengonsumsinya.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menunda seluruh Penyusunan Data Visualisasi sampai PIC 5 mulai dan bentuk kontraknya jelas** — ditolak: bertentangan langsung dengan Lingkup M4.5 sumber yang eksplisit meminta ini dibangun SEKARANG sebagai bagian milestone ini, dan KK sumber sudah memberi bentuk minimum yang cukup mengikat untuk 2 dari 5 label.

---

## Keputusan 10: Visualisasi HANYA dijalankan untuk `lolos=True`, orkestrator dibangun DI M4.5

**Sumber Paksaan**
Lingkup M4.5 sumber eksplisit: "Untuk narasi yang lolos, dilanjutkan dengan penyusunan data terstruktur..." — sekuens verify→visualisasi dideskripsikan sebagai SATU Lingkup/milestone yang sama (beda dari retry M4.4↔M4.5 yang LINTAS milestone, Keputusan 2).

**Keputusan yang Diikuti**
`verifikasi_dan_susun_visualisasi()` (orkestrator, di `verifikasi_kesetiaan.py`) memanggil `verifikasi_kesetiaan_narasi()` dulu; kalau `lolos=True`, lanjut `susun_data_visualisasi_semua(packages)`; kalau tidak, visualisasi `None`.

**Catatan Ketergantungan**
Beda dari Keputusan 2 (TIDAK membangun retry ke M4.4) — di sini sekuensingnya EKSPLISIT dalam satu Lingkup yang sama, bukan lintas-milestone, sehingga membangunnya di M4.5 BUKAN pelanggaran prinsip "jangan asumsikan bentuk orkestrator masa depan".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Membangun `verifikasi_kesetiaan_narasi()` dan `susun_data_visualisasi()` sebagai dua fungsi lepas TANPA orkestrator gabungan** — dipertimbangkan untuk konsistensi dengan Keputusan 2 (tidak membangun sekuensing). Ditolak: beda kasus — Lingkup sumber EKSPLISIT mendeskripsikan sekuens "verify lalu (kalau lolos) visualisasi" sebagai SATU alur kerja milestone ini sendiri, bukan lintas-milestone seperti retry M4.4→M4.5.

---

## Keputusan 11: Prompt disimpan `src/prompts/interpretation/verifikasi_kesetiaan.md`

**Sumber Paksaan**
`rancangan-manajemen-prompt.md` Bagian 2 (lokasi mirror `src/layers/`). Subpackage `src/layers/interpretation/` SUDAH ADA (dibuat M4.4).

**Keputusan yang Diikuti**
File baru `src/prompts/interpretation/verifikasi_kesetiaan.md` — TIDAK memicu update tabel Struktur Repository `CLAUDE.md`/`AGENT.md` (aturan proyek: file baru di subpackage yang SUDAH tercatat tidak perlu update tabel, beda dari M4.4 yang membuat subpackage BARU).

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by `rancangan-manajemen-prompt.md` Bagian 2 + struktur yang sudah ada.

---

## Keputusan 12: `prompt_reliability/interpretation/verifikasi_kesetiaan.promptfooconfig.yaml` dibangun native

**Sumber Paksaan**
Preseden M2.3/M3.2/M3.4/M3.5/M4.4 — sejak M2.3, tiap milestone LLM baru membangun config Promptfoo sendiri sebagai bagian checkpoint milestone.

**Keputusan yang Diikuti**
Checkpoint 9 membangun config, reuse skenario dari `evals/4.5-.../rancangan.md`, `response_format: json_object` (beda `narasi.promptfooconfig.yaml` M4.4 yang tanpa itu).

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden M2.3/M3.2/M3.4/M3.5/M4.4.

---

## Keputusan 13: Gap taksonomi `label_bentuk_jawaban` (`docs/keterbatasan-diterima.md` #4) dicatat, TIDAK diperbaiki

**Sumber Paksaan**
`label_bentuk_jawaban` adalah kontrak bersama PIC 1 (Decomposition)/PIC 4 (Execution/Interpretation), dikunci `arsitektur-ai-chatbot-rbac.md` §7 — `CLAUDE.md` eksplisit "perubahan wajib disepakati kedua pemilik", satu milestone tidak berwenang mengubahnya sepihak.

**Keputusan yang Diikuti**
Dicek eksplisit sebelum plan ditulis (pemicu peninjauan ulang `docs/keterbatasan-diterima.md` #4 secara eksplisit menyebut M4.5): gap TIDAK memblokir implementasi (input `label_bentuk_jawaban` yang sampai ke M4.5 selalu salah satu dari 5 nilai sah, dipaksa skema Pydantic sejak M1.6) — dicatat sebagai keterbatasan kualitas yang diwariskan M1.6, bukan cakupan M4.5 untuk diperbaiki.

**Catatan Ketergantungan**
Kalau M4.5 (atau tahap produksi berikutnya) menemukan gap yang SAMA relevan untuk kebutuhan visualisasi (mis. kebutuhan deskriptif yang dipaksa `nilai_tunggal` menghasilkan visualisasi scalar yang menyesatkan), itu jadi bukti tambahan untuk mengajukan revisi taksonomi bersama pemilik kontrak — bukan diputuskan sepihak di sini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menunda M4.5 sampai taksonomi direvisi** — ditolak: gap TIDAK memblokir implementasi secara struktural (input selalu valid enum), menunda tanpa alasan kuat.

---

## Keputusan 14: Closure M4.5 wajib konfirmasi status "Catatan Serah Terima ke Pekerjaan Lain"

**Sumber Paksaan**
Template `report.md` (`docs/00-project-governance/template-report.md`): "konfirmasi eksplisit di report apakah kontrak yang diwariskan ke pekerjaan lain benar-benar terpenuhi sesuai bentuk yang dijanjikan" untuk milestone yang py "Catatan Serah Terima" di dokumen plan-nya. M4.5 adalah milestone TERAKHIR di `rancangan-execution-interpretation.md`.

**Keputusan yang Diikuti**
`report.md` Checkpoint 10 mengonfirmasi status ketiga item Catatan Serah Terima dokumen sumber: (a) jalur revisi `400`→Query Engine — TERPENUHI (M4.2); (b) skema Session Memory M4.3=M1.5 — TERPENUHI (KK1 M4.3); (c) sinyal `403`/`404` prioritas tinggi ke dashboard observability — BELUM terpenuhi (PIC 5 belum mulai), dicatat statusnya jujur sebagai tertunda menunggu PIC 5, BUKAN kegagalan M4.4/M4.5.

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang — aturan template mengikat untuk milestone terakhir dokumen sumber manapun.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by aturan template `report.md`.

---

## Keputusan 15 (Addendum): Migrasi Model Verifikasi Kesetiaan — DeepSeek V4 Pro 0423 → DeepSeek V4 Pro 0813

**Status:** Diputuskan 2026-08-20, di luar siklus milestone ini (sudah closed) — perubahan cross-cutting terhadap 6 titik verifier DeepSeek V4 Pro project sekaligus, diinisiasi permintaan user, dikonfirmasi lewat `AskUserQuestion`.

**Latar Belakang**
User meminta migrasi biaya untuk 6 titik verifier project yang semula seragam `deepseek/deepseek-v4-pro` (versi `0423`, dikunci Keputusan 1 milestone ini): kombinasi antara `deepseek/deepseek-v4-flash-0731` (jauh lebih murah/cepat) dan `deepseek/deepseek-v4-pro-0813` (rilis resmi 2026-08-13, upgrade dari versi preview `0423`). Riset menemukan Artificial Analysis Intelligence Index kedua model nyaris identik (Flash 0731 = 52, Pro 0813 = 53), sementara lompatan skor Pro 0813 terkonsentrasi di benchmark coding/agentic/cyber yang tidak relevan untuk tugas verifier project ini. Pro 0813 juga LEBIH MAHAL dari Pro 0423 lama (+26% input, +90% output) — migrasi bukan downgrade seragam, melainkan realokasi berdasar risiko per titik.

**Keputusan yang Dipilih**
Konstanta `OPENROUTER_MODEL_VERIFIKASI_KESETIAAN` (`verifikasi_kesetiaan.py`) diubah dari `deepseek/deepseek-v4-pro` menjadi `deepseek/deepseek-v4-pro-0813` — **tetap tier Pro**, hanya upgrade versi.

**Alasan**
Titik ini adalah garda TERAKHIR sebelum narasi sampai ke user (verifier independen atas hasil `susun_narasi()` M4.4), langsung terikat prinsip "Kejujuran terhadap keterbatasan" `CLAUDE.md` — mencegah klaim sebab-akibat/data yang mengada-ada lolos ke output final (KK1 M4.5, dibuktikan nyata Checkpoint 6-8 milestone ini). Karena tidak ada verifikasi lain setelahnya (beda dari titik-titik yang masih tersaring layer berikutnya), margin keamanan di sini paling perlu dijaga — tetap tier Pro, upgrade ke 0813 meski lebih mahal dari 0423.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Migrasi ke Flash 0731 (ikut 3 titik simetris lain)** — ditolak, ini garda hilir terakhir sebelum output ke user, tidak ada layer verifikasi berikutnya yang bisa menangkap kesalahan kalau verifier di sini melemah.
- **Tetap di Pro 0423 (status quo)** — ditolak, versi preview lama tidak lagi jadi rilis utama DeepSeek per 2026-08-13.

**Dampak**
`src/config/llm.py` konstanta `OPENROUTER_MODEL_VERIFIKASI_KESETIAAN` diubah nilainya (docstring diperbarui, pointer ke keputusan ini). Tidak ada perubahan skema/signature/`reasoning="high"`/kontrak fungsi. `susun_data_visualisasi()` (deterministik, tanpa AI) tidak tersentuh.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Model verifikasi `deepseek/deepseek-v4-pro` reasoning=high | B | Plan |
| 2 | TIDAK membangun retry loop balik ke `susun_narasi()` | B | Plan |
| 3 | `temperature=0`, `response_format=json_object` | B | Plan |
| 4 | Skema `HasilVerifikasiNarasi` mencetak `HasilVerifikasiBentukRequest` | B | Plan |
| 5 | Reuse `_build_user_prompt()` (`narasi.py`) untuk verifier | B | Plan |
| 6 | Span `chat` untuk verifikasi | B | Plan |
| 7 | Penyusunan Data Visualisasi murni deterministik, tanpa AI | B | Plan |
| 8 | Skema `DataVisualisasi` — `nilai_tunggal` vs `deret` | B | Plan |
| 9 | Perluasan `deret` ke 3 label lain — PROVISIONAL | B | Plan |
| 10 | Visualisasi hanya untuk `lolos=True`, orkestrator di M4.5 | B | Plan |
| 11 | Prompt `src/prompts/interpretation/verifikasi_kesetiaan.md` | B | Plan |
| 12 | `prompt_reliability` config native | B | Plan |
| 13 | Gap taksonomi `label_bentuk_jawaban` dicatat, tidak diperbaiki | B | Plan |
| 14 | Closure wajib konfirmasi Catatan Serah Terima | B | Plan |
| 15 | Addendum: migrasi model verifikasi kesetiaan Pro 0423 → Pro 0813 | A | Addendum 2026-08-20 |
