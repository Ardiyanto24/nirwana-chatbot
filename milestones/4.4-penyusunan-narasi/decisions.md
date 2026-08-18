# Decisions — Milestone 4.4: Membangun Penyusunan Narasi

Dokumen ini mencatat setiap keputusan desain untuk Milestone 4.4, seluruhnya ditentukan sebelum implementasi dimulai (Plan Mode), sesuai urutan kemunculan di plan.

---

## Keputusan 1: Model LLM untuk pemanggilan Narasi

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`)

**Latar Belakang**
Narasi (M4.4) adalah satu dari dua titik di seluruh sistem yang hasilnya langsung dibaca user tanpa gerbang lagi setelahnya (selain M4.5), dan harus menjaga 7 instruksi bernuansa halus sekaligus (kejujuran status non-normal, beda nada penolakan vs kegagalan teknis, larangan klaim sebab-akibat, dst.). Ini genuinely terbuka — `arsitektur-ai-chatbot-rbac.md` Bagian 8 butir 4 eksplisit menandai "model per langkah, provider routing" sebagai belum ditentukan, dan tidak ada preseden milestone manapun yang secara otomatis mengunci model untuk TUGAS narasi bebas (beda dari tugas ekstraksi/klasifikasi terstruktur yang mendominasi milestone lain).

**Keputusan yang Dipilih**
Reuse `qwen/qwen3-32b` — konstanta baru `OPENROUTER_MODEL_NARASI` di `src/config/llm.py`, terisolasi sendiri (bukan reuse langsung `OPENROUTER_MODEL_REWRITE` dkk.) mengikuti pola "satu konstanta per konsumen" (M1.4 Keputusan 9).

**Alasan**
Dikonfirmasi user lewat `AskUserQuestion` (dua opsi diajukan: reuse Qwen3-32B vs perbandingan empiris beberapa kandidat mirror M3.1). User memilih reuse. Argumen pendukung: Qwen3-32B sudah dibenchmark SEA-HELM untuk kualitas Bahasa Indonesia saat dipilih M1.4 (Rewrite) — tugas itu juga NLG (natural language generation), bukan cuma ekstraksi struktural seperti mayoritas milestone lain, sehingga rasionalnya lebih relevan untuk Narasi dibanding sekadar "reuse karena konsisten murah".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Perbandingan empiris 2-3 kandidat model (mirror M3.1 embedding)** — ditolak user. Argumen yang diajukan: biaya waktu lebih tinggi di awal milestone; ditolak demi kecepatan, mengandalkan preseden benchmark SEA-HELM M1.4 yang sudah relevan untuk tugas NLG Bahasa Indonesia. Risiko residual (Qwen3-32B mungkin kurang piawai menjaga 7 instruksi sekaligus) dicatat eksplisit di Risiko & Mitigasi plan, dimitigasi lewat eval 12-14 skenario (Checkpoint 6-7) yang menguji tiap instruksi terpisah.

**Dampak**
Menentukan `OPENROUTER_MODEL_NARASI` (Checkpoint 2). Kalau eval Checkpoint 7 menemukan pola kegagalan sistematis, jadi trigger revisit `docs/keputusan-tertunda.md` (mirror pola M3.1 entri #2, model embedding Retriever yang sengaja tidak ditutup permanen).

---

## Keputusan 2: `temperature=0`

**Sumber Paksaan**
Preseden SELURUH pemanggilan LLM project sejak M1.3 (`turn_dependency.py`, `rewrite.py`, `klasifikasi.py`/`pemecahan.py`/`verifikasi.py`, `matching.py`, `identifikasi.py`/`verifikasi_titik_buta.py`, `deteksi_cakupan_individu.py`/`verifikasi_cakupan_individu.py`, `kecocokan_makna.py`, `kecukupan_struktural.py`, `penyusunan_request.py`/`verifikasi_bentuk_request.py`) — seluruhnya memakai `temperature=0` tanpa pengecualian.

**Keputusan yang Diikuti**
`susun_narasi()` memanggil `OPENROUTER_MODEL_NARASI` dengan `temperature=0`.

**Catatan Ketergantungan**
Mengubah ini sepihak di M4.4 akan memutus konsistensi determinisme yang jadi dasar testability seluruh eval/unit test project (`docs/keterbatasan-diterima.md` #3 addendum sudah mencatat bahkan `temperature=0` TIDAK menjamin determinisme penuh di OpenRouter — menaikkan `temperature` akan memperparah, bukan memperbaiki, masalah itu).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden project-wide di atas.

---

## Keputusan 3: Output diambil sebagai teks bebas, tanpa `response_format=json_object`

**Sumber Paksaan**
Sifat tugas itu sendiri: Narasi menghasilkan JAWABAN (teks bebas berbahasa natural), bukan keputusan terstruktur (bool/enum/index) seperti seluruh layer LLM lain di project. Memaksa `response_format=json_object` untuk sebuah narasi akan memaksa LLM membungkus prosa ke dalam field JSON tanpa manfaat struktural apa pun.

**Keputusan yang Diikuti**
`susun_narasi()` mengambil `response.choices[0].message.content` langsung sebagai `HasilNarasi.narasi`, tanpa parsing JSON.

**Catatan Ketergantungan**
Ini murni konsekuensi dari bentuk tugas, bukan preferensi implementasi — tidak ada milestone lain yang punya tugas serupa (teks bebas sebagai output final) untuk dijadikan preseden pembanding, tapi juga tidak ada alasan menambah lapisan JSON yang tidak dibutuhkan konsumen (M4.5 hanya butuh teks narasi untuk dinilai).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Bungkus narasi dalam JSON (`{"narasi": "..."}`) via `response_format=json_object`** — ditolak: menambah kelas kegagalan baru (parse error) tanpa manfaat, mengingat field yang diekstrak toh cuma satu string utuh yang sama dengan seluruh isi respons.

---

## Keputusan 4: Tanpa parameter `feedback`/retry internal di `susun_narasi()`

**Sumber Paksaan**
Preseden persis `penyusunan_request.py` (M3.4): fungsi generate-only itu SENDIRI dibangun tanpa retry/`feedback` internal, docstring eksplisit menyatakan "loop revisi (kalau ada) sepenuhnya tanggung jawab pemanggil, bukan modul ini" — `feedback` baru ditambahkan belakangan oleh M4.2 saat kebutuhan revisi nyata (400 dari `chatbot_api`) muncul. Juga forced oleh Lingkup M4.4 sendiri (`rancangan-execution-interpretation.md`): "Ini langkah 'menghasilkan' dalam pola generate-verify — dipisah dari langkah verifikasinya (Milestone 4.5) agar keduanya independen".

**Keputusan yang Diikuti**
`susun_narasi()` adalah SATU pemanggilan LLM murni, tanpa parameter `feedback`, tanpa loop retry.

**Catatan Ketergantungan**
Menambahkan retry/feedback sekarang berarti mengasumsikan bentuk verdict M4.5 (belum dibangun) — berisiko salah tebak dan perlu dirombak ulang begitu M4.5 benar-benar didesain, persis pola `penyusunan_request.py`/M3.4→M4.2.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden `penyusunan_request.py` + Lingkup M4.4 sendiri.

---

## Keputusan 5: Kegagalan API diteruskan sebagai exception, tidak ditelan ke fallback aman

**Sumber Paksaan**
Konsekuensi Keputusan 3: tidak ada nilai default aman untuk sebuah narasi (beda dari `matching.py` yang punya `PERLU_EKSEKUSI` sebagai fallback aman terhadap kegagalan API/parse). Mirror pola `store_session_memory()` (M1.5/M4.3): "Kegagalan DB ditangkap... LALU di-raise ulang APA ADANYA".

**Keputusan yang Diikuti**
`APIError` dari pemanggilan LLM di `susun_narasi()` diteruskan apa adanya ke pemanggil (tidak ditelan jadi narasi kosong/default).

**Catatan Ketergantungan**
Menelan exception jadi narasi generik ("terjadi kesalahan") akan MELANGGAR prinsip kejujuran terhadap keterbatasan (`CLAUDE.md` Prinsip Arsitektur) dengan cara yang lebih halus — bukan menyembunyikan status, tapi memaksa modul ini membuat keputusan UX (pesan generik apa yang ditampilkan) yang bukan wewenangnya; itu keputusan orkestrator/pemanggil di masa depan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Fallback ke narasi generik hardcode saat API gagal** — ditolak: memindahkan keputusan UX ke modul yang salah, dan berisiko menyamarkan kegagalan teknis sebagai jawaban normal kalau pemanggil di masa depan tidak memeriksa exception dengan benar.

---

## Keputusan 6: Span `chat` dengan atribut kontrak observability Bagian 2

**Sumber Paksaan**
`rancangan-observability-ai-chatbot.md` Bagian 2, baris tabel "Interpretation (Narasi, Verifikasi Kesetiaan)": `gen_ai.usage.*`, `narrative.turn_reference` (mengacu field `sumber`), `prompt.id`/`prompt.version`. Ini kontrak mengikat seluruh PIC 1-4, bukan pilihan implementasi.

**Keputusan yang Diikuti**
`susun_narasi()` membuka span `chat`, mengisi `gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens`, `prompt.id`/`prompt.version`, dan `narrative.turn_reference` (daftar turn_index unik dari paket bersumber `"session_memory (turn N)"` dalam input).

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang — ini kontrak lintas-PIC yang perubahannya wajib dikomunikasikan ke seluruh pemilik pekerjaan lain (`rancangan-observability-ai-chatbot.md` Bagian 5), bukan diubah sepihak satu milestone.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kontrak observability Bagian 2.

---

## Keputusan 7: Prompt disimpan `src/prompts/interpretation/narasi.md`

**Sumber Paksaan**
`rancangan-manajemen-prompt.md` Bagian 2: lokasi `src/prompts/<nama-layer>/<nama>.md`, mirror struktur `src/layers/`.

**Keputusan yang Diikuti**
File `src/prompts/interpretation/narasi.md`, frontmatter `id: interpretation.narasi`, `version: 1`, `milestone: "4.4"`, `model_compat: ["qwen/qwen3-32b"]`.

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang — kontrak storage/versioning prompt sudah dikunci sebagai dokumen arsitektur cross-cutting, berlaku ke seluruh call site LLM baru sejak diterbitkan.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by `rancangan-manajemen-prompt.md` Bagian 2.

---

## Keputusan 8: Sistem prompt statis, konten dinamis dirakit Python (bukan Jinja2 loop)

**Sumber Paksaan**
Preseden `matching.py` (M1.7): satu-satunya pemakaian Jinja2 loop nyata di seluruh project ada di prompt Domain Gate (`identifikasi.md`/`verifikasi_titik_buta.md`, daftar 10 domain TETAP) — untuk data per-request yang jumlahnya variabel (daftar kandidat/paket), pola project konsisten merakitnya di Python lewat fungsi `_build_user_prompt()`, sistem prompt tetap statis.

**Keputusan yang Diikuti**
`narasi.md` adalah teks statis (7 instruksi wajib). Daftar atomic intent + paket + relasi ketergantungan dirakit `_build_user_prompt()` (Python) sebagai user prompt, bukan di-loop lewat Jinja2 di system prompt.

**Catatan Ketergantungan**
Mengubah ini akan menyimpang dari konvensi Bagian 3 `rancangan-manajemen-prompt.md` yang eksplisit mencatat (di Bagian 9, sebagai temuan Fase 2) bahwa Jinja2 loop HANYA dipakai untuk data tetap seperti daftar domain, bukan data per-request.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Jinja2 loop di `narasi.md` untuk merender daftar paket** — ditolak: jumlah atomic intent per turn variabel dan isinya (nilai_hasil, catatan_interpretasi) jauh lebih kompleks dari daftar domain statis; preseden project menaruh logic perakitan sekompleks ini di Python (`_build_user_prompt()`), bukan di template.

---

## Keputusan 9: Input menerima `list[SessionMemoryPackage]` DAN `list[AtomicIntent]`

**Sumber Paksaan**
Kalimat Output Milestone 4.4 di `rancangan-execution-interpretation.md`: "menerima kumpulan paket data (dari kedua sumber) beserta relasi antar-atomic-intent dari Decomposition" — eksplisit menyebut DUA hal berbeda: paket data (skema M1.5 §7) dan relasi (field `relasi`/`bergantung_pada` di `AtomicIntent`, skema M1.6).

**Keputusan yang Diikuti**
`susun_narasi(atomic_intents: list[AtomicIntent], packages: list[SessionMemoryPackage], session_id: str, turn_index: int) -> HasilNarasi`.

**Catatan Ketergantungan**
Tanpa `list[AtomicIntent]`, instruksi wajib ke-6 ("kebutuhan gagal karena bergantung pada kebutuhan lain yang juga gagal disampaikan spesifik penyebabnya") tidak bisa dipenuhi — `SessionMemoryPackage` sendiri TIDAK punya field relasi/ketergantungan (hanya `AtomicIntent` yang punya).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hanya `list[SessionMemoryPackage]`, tanpa relasi eksplisit** — ditolak: melanggar instruksi wajib ke-6 secara langsung, dan bertentangan dengan kalimat Output milestone sumber yang eksplisit menyebut "beserta relasi antar-atomic-intent".

---

## Keputusan 10: Return type `HasilNarasi` (Pydantic), bukan bare `str`

**Sumber Paksaan**
Preseden konsisten seluruh layer LLM project — setiap fungsi pemanggil LLM mengembalikan schema Pydantic (`TurnDependencyResult`, `RewriteResult`, `DecompositionResult`, `AtomicIntentMatch`, `HasilPenyusunanRequest`, dst.), bukan tipe primitif polos.

**Keputusan yang Diikuti**
`src/schemas/interpretation.py`: `HasilNarasi(BaseModel)` dengan satu field `narasi: str`.

**Catatan Ketergantungan**
Murni penamaan/struktur mekanis mengikuti konvensi project — tidak ada trade-off substantif untuk dipertimbangkan.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by konsistensi konvensi project-wide.

---

## Keputusan 11: Data uji status `ditolak_otorisasi`/`terblokir_ketergantungan` dikonstruksi manual

**Sumber Paksaan**
Tidak ada satu pun komponen di codebase saat ini yang memproduksi `SessionMemoryPackage` berstatus `ditolak_otorisasi` atau `terblokir_ketergantungan` (dikonfirmasi lewat grep — hanya muncul di definisi enum/docstring). Hanya `berhasil`/`sebagian`/`gagal_teknis` yang punya jalur produksi nyata lewat M4.2→M4.3 (dibatasi validator `HasilEksekusiAtomicIntent`). Tapi Kriteria Keberhasilan sumber M4.4 eksplisit menuntut skenario `ditolak_otorisasi` diuji. Preseden: M1.7 sudah menetapkan pola ini (`milestones/1.7-.../report.md` Bagian 5: "Verifikasi memakai data seed manual, bukan pipeline organik... Disepakati EKSPLISIT dengan user").

**Keputusan yang Diikuti**
Unit test (Checkpoint 5) dan eval (Checkpoint 6-7) mengonstruksi `SessionMemoryPackage(status=StatusEksekusi.DITOLAK_OTORISASI, ...)`/`(status=StatusEksekusi.TERBLOKIR_KETERGANTUNGAN, ...)` langsung sebagai fixture, TIDAK menunggu pipeline organik yang belum ada.

**Catatan Ketergantungan**
Menunda M4.4 sampai upstream (Domain Gate reject → simpan paket; dependency-block → simpan paket) benar-benar di-wiring akan memblokir milestone ini tanpa alasan kuat — kedua fungsi tersebut sudah didesain generik sejak M4.3 (`susun_dan_simpan_paket()` menerima `status` sebagai parameter eksplisit, bukan terikat ketat M4.2) justru untuk mengakomodasi pemanggil lain di masa depan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menunda pengujian `ditolak_otorisasi`/`terblokir_ketergantungan` sampai wiring end-to-end tersedia** — ditolak: bertentangan langsung dengan Kriteria Keberhasilan sumber yang eksplisit menuntut skenario `ditolak_otorisasi` diuji SEKARANG, dan preseden M1.7 sudah membuktikan pola fixture manual ini valid dan diterima.

---

## Keputusan 12: `prompt_reliability/interpretation/narasi.promptfooconfig.yaml` dibangun native

**Sumber Paksaan**
Preseden M2.3/M3.2/M3.4/M3.5 — sejak M2.3, tiap milestone LLM baru membangun config Promptfoo sendiri sebagai bagian checkpoint milestone (dikonfirmasi: folder `prompt_reliability/query_engine/`, `prompt_reliability/retriever/` sudah ada), bukan retrofit terpisah seperti Fase 2 lama (8 call site M1.3-M2.1).

**Keputusan yang Diikuti**
Checkpoint 8 membangun `prompt_reliability/interpretation/narasi.promptfooconfig.yaml`, reuse skenario dari `evals/4.4-.../rancangan.md`.

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang — ini sudah jadi praktik standar project sejak M2.3, menunda ke Fase 2 terpisah (seperti 8 call site pertama) akan jadi inkonsistensi dengan preseden yang sudah berjalan 4 milestone berturut-turut.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden M2.3/M3.2/M3.4/M3.5.

---

## Keputusan 13: Subpackage baru `src/layers/interpretation/`

**Sumber Paksaan**
`arsitektur-ai-chatbot-rbac.md` §3 (Peta Layer): layer ke-9 bernama "Interpretation". `CLAUDE.md` "Struktur Repository": aturan wajib memperbarui tabel begitu folder top-level/subpackage baru dibuat.

**Keputusan yang Diikuti**
Folder baru `src/layers/interpretation/` (Checkpoint 4), tabel Struktur Repository `CLAUDE.md`/`AGENT.md` diperbarui sebagai bagian Checkpoint 9 (penutupan) — bukan ditunda lebih jauh, karena kelengkapan tabel ini diverifikasi di penutupan milestone (Task 14).

**Catatan Ketergantungan**
Nama subpackage bukan pilihan bebas — harus konsisten dengan nama layer di dokumen arsitektur induk supaya pemetaan layer↔kode tetap jelas untuk pembaca/agen berikutnya.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by nama layer arsitektur §3.

---

## Keputusan 14: Bahasa Indonesia untuk narasi dan seluruh nama variabel/fungsi/prompt

**Sumber Paksaan**
Preseden project-wide — `rancangan-manajemen-prompt.md` Bagian 3 (konvensi variabel Jinja2 Bahasa Indonesia), seluruh nama fungsi/variabel `src/` project berbahasa Indonesia, dan seluruh narasi user-facing sistem ini (dokumen arsitektur, prompt Domain Gate, dst.) berbahasa Indonesia.

**Keputusan yang Diikuti**
`narasi.md`, `_build_user_prompt()`, dan narasi yang dihasilkan LLM seluruhnya berbahasa Indonesia.

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang — mengubah ini akan jadi satu-satunya penyimpangan bahasa di seluruh codebase.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden project-wide.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Model LLM untuk pemanggilan Narasi | A | Plan |
| 2 | `temperature=0` | B | Plan |
| 3 | Output teks bebas, tanpa `response_format=json_object` | B | Plan |
| 4 | Tanpa parameter `feedback`/retry internal | B | Plan |
| 5 | Kegagalan API diteruskan sebagai exception | B | Plan |
| 6 | Span `chat` + atribut kontrak observability Bagian 2 | B | Plan |
| 7 | Prompt disimpan `src/prompts/interpretation/narasi.md` | B | Plan |
| 8 | Sistem prompt statis, konten dinamis dirakit Python | B | Plan |
| 9 | Input menerima `list[SessionMemoryPackage]` + `list[AtomicIntent]` | B | Plan |
| 10 | Return type `HasilNarasi` (Pydantic) | B | Plan |
| 11 | Data uji `ditolak_otorisasi`/`terblokir_ketergantungan` dikonstruksi manual | B | Plan |
| 12 | `prompt_reliability/interpretation/narasi.promptfooconfig.yaml` native | B | Plan |
| 13 | Subpackage baru `src/layers/interpretation/` | B | Plan |
| 14 | Bahasa Indonesia untuk narasi dan kode | B | Plan |
