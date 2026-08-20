# Decisions — Milestone 1.6: Membangun Decomposition (Klasifikasi, Pemecahan, Verifikasi)

## Keputusan 1: Model Langkah 4 (Klasifikasi) & Langkah 5 (Pemecahan) — Qwen3-32B (Reuse)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
M1.6 adalah pemanggilan LLM pertama sejak M1.4 yang butuh keputusan model baru. Klasifikasi (3-way categorization) dan Pemecahan (structuring Bahasa Indonesia jadi atomic intent list) punya profil kesulitan mirip tugas M1.4 (rewrite/structuring), beda dari Langkah 6 (Verifikasi) yang butuh peran "critic" independen.

**Keputusan yang Dipilih**
Qwen3-32B via OpenRouter (`qwen/qwen3-32b`), reuse model M1.4.

**Alasan**
Sudah terbukti bekerja baik di project ini (eval M1.4: 11/12 skenario benar, termasuk kasus nuansa), thinking-mode aktif secara default (reasoning internal, dikonfirmasi di audit M1.4), SEA-HELM Indonesian leader, termurah dari seluruh kandidat yang pernah diriset project ini ($0.08/$0.28 per 1M token).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Model lain untuk Klasifikasi/Pemecahan** — tidak dieksplorasi lebih jauh karena tidak ada bukti/kebutuhan nyata Qwen3-32B tidak cukup untuk kedua peran ini (beda dari Verifikasi yang punya alasan spesifik butuh keragaman model, lihat Keputusan 2).

**Dampak**
Konstanta `OPENROUTER_MODEL_DECOMPOSITION` di `src/config/llm.py`, terisolasi dari `OPENROUTER_MODEL_REWRITE` (M1.4) meski nilainya kebetulan sama — lihat Keputusan 7.

---

## Keputusan 2: Model Langkah 6 (Verifikasi) — DeepSeek V4 Pro

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion` + riset web, 2 putaran riset).

**Latar Belakang**
Langkah 6 adalah pemanggilan LLM **generate-lalu-verify penuh pertama** di proyek (M1.3/M1.4 verifikasinya deterministik ruang-tertutup) — menanggung bobot lebih besar sebagai satu-satunya gerbang penangkap kesalahan Pemecahan. Riset pertama (model non-China: Gemini 2.5 Flash $0.30/$2.50, GPT-5-mini $0.25/$2 — disebut eksplisit sebagai "cost-balanced judge workhorse" di sumber judge-model 2026) ditolak user, diarahkan riset ke model China. Riset kedua menemukan QwQ-32B (reasoning model Qwen lain) ternyata model lama (Maret 2025, kalah relevan dari Qwen3-32B yang sudah py thinking-mode bawaan) — tidak layak dipertimbangkan serius.

**Keputusan yang Dipilih**
DeepSeek V4 Pro (`deepseek/deepseek-v4-pro`), $0.4138/$0.8275 per 1M token (harga diskon 76%), reasoning effort "high" dikonfigurasi eksplisit saat pemanggilan.

**Alasan**
Satu keluarga dengan model M1.3 (DeepSeek), rilis terbaru (April 2026) dengan mode reasoning "high/xhigh" yang bisa dikonfigurasi eksplisit — cocok untuk peran verifier yang butuh penilaian ulang independen. Keragaman model (verifier TIDAK memakai "otak" yang sama dengan yang diverifikasi, Qwen3-32B vs DeepSeek) mengurangi risiko blind spot berkorelasi. Jauh lebih murah dari alternatif non-China yang sempat dipertimbangkan (~7-9x lebih murah dari GPT-5-mini/Gemini 2.5 Flash).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Qwen3-32B untuk ketiga langkah (termasuk Verifikasi)** — opsi termurah/paling sederhana, sempat direkomendasikan awal. Ditolak user demi keragaman model untuk peran verifier.
- **Gemini 2.5 Flash / GPT-5-mini untuk Verifikasi** — disebut eksplisit sebagai "judge workhorse" 2026, tapi ditolak user (bukan model China) meski secara riset legitimate.
- **QwQ-32B** — dicek, ternyata model lama (Maret 2025) yang sudah kalah relevan dari kapabilitas thinking-mode Qwen3-32B sendiri; tidak diajukan sebagai opsi serius ke user.
- **DeepSeek R1** — dicek pricing ($0.70/$2.50), lebih mahal dari V4 Pro dan model generasi lebih lama (pra-V4).

**Dampak**
Konstanta `OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI` di `src/config/llm.py`. `verifikasi_pemecahan()` perlu eksplisit set parameter reasoning effort "high" saat memanggil API (bukan default provider).

---

## Keputusan 3: Kebijakan Verifikasi Gagal — Retry Maksimal 3 Kali Total (1 Awal + 2 Retry)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`; interpretasi angka dikonfirmasi implisit lewat review+approval plan yang eksplisit menyatakan interpretasi ini).

**Latar Belakang**
Langkah 6 (Verifikasi) genuinely LLM independen (Keputusan 2) — perlu kebijakan eksplisit soal apa yang terjadi kalau hasil Langkah 5 dinilai tidak valid. Precedent yang tersedia: M1.3 (`forced_independent_reason`, flag anomali tanpa retry, karena punya nilai fallback aman `is_dependent=False`) dan M4.5 Verifikasi Kesetiaan Data (`rancangan-execution-interpretation.md`: "lolos atau perlu revisi dengan alasan spesifik", tanpa auto-block eksplisit didokumentasikan). Tidak ada precedent retry-loop eksplisit di dokumen manapun untuk kasus M1.6.

**Keputusan yang Dipilih**
`decompose_question()` retry Langkah 5→6 (bukan Langkah 4) maksimal **3 kali total** — 1 percobaan awal + hingga 2 retry, alasan invalid dari Langkah 6 disisipkan ke prompt Langkah 5 di tiap retry. Kalau percobaan ke-3 masih invalid: span attribute anomali (`decomposition.verification_exhausted=True`), hasil percobaan TERAKHIR tetap diteruskan (`verifikasi_valid=False` tetap tercatat apa adanya di `DecompositionResult`, TIDAK disamarkan jadi `True`).

**Alasan**
User eksplisit meminta retry (bukan langsung flag-and-pass-through atau hard-fail seperti dua opsi lain yang diajukan) — kebijakan "self-healing" dengan feedback loop. Batas maksimal (bukan retry tanpa henti) mencegah biaya/latensi tak terbatas. Fallback akhir (flag + teruskan, bukan blocking) tetap konsisten prinsip "Kejujuran terhadap keterbatasan" — M1.6 belum punya akses ke kosakata `status` penuh (`gagal_teknis` dst., baru relevan mulai M1.7/Execution) untuk memutuskan pipeline berhenti total, jadi flag+teruskan adalah pilihan paling aman yang tersedia di titik ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Flag anomali, tetap teruskan hasil asli tanpa retry** — direkomendasikan awal (paling sederhana, mirror M1.3 murni), ditolak user demi self-healing lewat retry.
- **Tandai `gagal_teknis`, hentikan turn ini langsung** — ditolak, dan secara struktural bermasalah karena M1.6 belum punya akses ke kosakata status penuh di titik pipeline ini.
- **Retry tanpa batas (sampai valid)** — tidak diajukan sebagai opsi karena risiko biaya/latensi tak terbatas jelas tidak wajar.

**Dampak**
`pecah_atomik()` (Langkah 5) perlu parameter `feedback: str | None` opsional untuk menyisipkan alasan invalid dari percobaan sebelumnya. `DecompositionResult` perlu field `retry_count` untuk observability/debugging.

---

## Keputusan 4 (Forced): Tiga Pemanggilan LLM Terpisah

**Sumber Paksaan:** Output Milestone 1.6 (`rancangan-context-decomposition.md` baris 121): "tiga pemanggilan model AI terpisah".

**Keputusan yang Diikuti:** `klasifikasi_kebutuhan()`, `pecah_atomik()`, `verifikasi_pemecahan()` — tiga fungsi/pemanggilan LLM terpisah, bukan digabung jadi satu prompt majemuk.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by dokumen sumber.

---

## Keputusan 5 (Forced): Langkah 6 Wajib LLM Independen, Bukan Deterministik

**Sumber Paksaan:** Prinsip Arsitektur #3 `CLAUDE.md` (ruang-kesalahan-terbuka wajib LLM independen) + diagram arsitektur `arsitektur-ai-chatbot-rbac.md` baris 154 eksplisit: "6. Verifikasi Pemecahan ← LLM, independen dari Langkah 5".

**Keputusan yang Diikuti:** Verifikasi kesesuaian pemecahan (apakah benar-benar menangkap seluruh kebutuhan + relasi yang tepat) dinilai LLM independen kedua, bukan aturan deterministik — beda dari M1.3/M1.4 yang verifikasinya murni struktural (bounds-check) karena Output-nya eksplisit "satu pemanggilan".

**Catatan Ketergantungan:** Ini precedent generate-lalu-verify PENUH pertama di proyek — pola yang sama kemungkinan berulang di milestone LLM berikutnya yang punya sifat serupa (ruang kesalahan terbuka, bukan sekadar validasi bentuk output).

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced ganda oleh prinsip arsitektur DAN diagram eksplisit.

---

## Keputusan 6 (Forced): Relasi 2 Nilai (`independen`/`bergantung`)

**Sumber Paksaan:** Taksonomi Langkah 4 sendiri yang sudah dikunci (`arsitektur-ai-chatbot-rbac.md` baris 143): "Tunggal / majemuk-independen / majemuk-bergantung" — tidak ada taksonomi relasi lain yang disebut di dokumen manapun.

**Keputusan yang Diikuti:** `RelasiKebutuhan` Enum 2 nilai: `independen`, `bergantung`. Tidak mengarang taksonomi lebih granular (mis. jenis-jenis dependency) yang tidak diminta dokumen sumber.

**Catatan Ketergantungan:** Konsisten prinsip "jangan menambah fitur di luar yang diminta" (`CLAUDE.md`).

**Opsi yang Dipertimbangkan tapi Ditolak:** Taksonomi relasi lebih granular — tidak dipertimbangkan serius karena tidak ada dasar dokumen sumber, akan jadi pengarangan scope yang tidak diminta.

---

## Keputusan 7 (Forced): `atomic_intent_id` Digenerate Kode (UUID4), Bukan LLM

**Sumber Paksaan:** Preseden identik Keputusan 6 `milestones/1.3-pemetaan-ketergantungan-turn/decisions.md` — LLM tidak boleh membuat ID granular sendiri, risiko halusinasi/duplikasi.

**Keputusan yang Diikuti:** LLM (Langkah 5) mereferensikan kebutuhan lain lewat index lokal (integer posisi dalam responsnya sendiri, mis. `bergantung_pada_index: [1]`). Kode men-generate `atomic_intent_id` (UUID4) SETELAH respons LLM diterima, lalu menerjemahkan index lokal jadi `atomic_intent_id` sungguhan. Bounds-check deterministik: index lokal yang dirujuk harus benar-benar ada dalam list yang sama direspons LLM itu — kalau dangling (index tidak ada), referensi di-drop + dicatat span attribute anomali. Mirror pola bounds-check M1.3 (Keputusan 9 M1.3) — closed error space murni struktural, tidak butuh LLM kedua untuk cek ini secara spesifik (beda dari Langkah 6 yang menilai kesesuaian MAKNA keseluruhan, bukan struktur index).

**Opsi yang Dipertimbangkan tapi Ditolak:** LLM diminta generate ID sendiri — ditolak, forced by preseden M1.3.

---

## Keputusan 8 (Forced): `LabelBentukJawaban` Reuse dari `src/schemas/session_memory.py`

**Sumber Paksaan:** `CLAUDE.md` Prinsip Arsitektur — "Skema paket Session Memory... adalah kontrak yang dipakai bersama PIC 1 (membaca) dan PIC 4 (menulis) — perubahan wajib disepakati kedua pemilik, tidak diubah sepihak."

**Keputusan yang Diikuti:** `AtomicIntent.label_bentuk_jawaban` mengimpor `LabelBentukJawaban` langsung dari `src/schemas/session_memory.py` (M1.5) — tidak didefinisikan ulang di `decomposition.py`.

**Catatan Ketergantungan:** Kalau `LabelBentukJawaban` perlu berubah nanti, perubahan berdampak ke M1.5 DAN M1.6 sekaligus — perlu koordinasi.

**Opsi yang Dipertimbangkan tapi Ditolak:** Definisikan ulang Enum terpisah di `decomposition.py` dengan nilai yang sama — ditolak, akan menciptakan dua sumber kebenaran yang berpotensi drift (anti-pattern yang sama yang dihindari di M1.5 Keputusan 9 soal `roles.yaml`).

---

## Keputusan 9 (Forced): Klasifikasi (Langkah 4) Tidak Ikut Retry Loop

**Sumber Paksaan:** Kriteria Keberhasilan sumber sendiri — eksplisit soal "verifikasi hasil **pemecahan**" (Langkah 5), bukan klasifikasi.

**Keputusan yang Diikuti:** Retry (Keputusan 3) hanya mengulang Langkah 5↔6. Langkah 4 dipanggil sekali di awal, hasilnya jadi konteks/input tetap untuk seluruh percobaan Langkah 5 berikutnya (termasuk saat retry).

**Opsi yang Dipertimbangkan tapi Ditolak:** Retry juga mengulang dari Langkah 4 — ditolak, scope creep di luar apa yang diminta Kriteria Keberhasilan (yang spesifik soal Pemecahan, bukan Klasifikasi).

---

## Keputusan 10 (Forced): Struktur Kode `src/layers/decomposition/` Subpackage

**Sumber Paksaan:** Preseden `src/layers/context_resolution/` (Keputusan 10 M1.3) — 1 layer arsitektur berisi >1 mekanisme/milestone jadi subpackage, bukan file tunggal. Decomposition sendiri 1 milestone tapi berisi 3 mekanisme berbeda (Klasifikasi/Pemecahan/Verifikasi) + 1 orkestrator — pola yang sama berlaku.

**Keputusan yang Diikuti:** `src/layers/decomposition/{klasifikasi.py, pemecahan.py, verifikasi.py, decompose.py}`.

**Opsi yang Dipertimbangkan tapi Ditolak:** Satu file tunggal `decomposition.py` berisi keempat fungsi — dipertimbangkan tapi ditolak demi konsistensi pola subpackage-per-multi-mekanisme yang sudah dipakai proyek, dan supaya tiap langkah bisa diuji/di-mock terpisah dengan jelas (terutama Langkah 6 yang butuh dipanggil terisolasi untuk Kriteria Keberhasilan skenario deliberately-wrong).

---

## Keputusan 11 (Forced): Konstanta Model Terisolasi per Milestone

**Sumber Paksaan:** Preseden Keputusan 9 `milestones/1.4-rewrite-mandiri/decisions.md` — satu konstanta model per konsumen/milestone, meski nilainya kebetulan sama dengan konstanta lain.

**Keputusan yang Diikuti:** `OPENROUTER_MODEL_DECOMPOSITION` (Qwen3-32B) dan `OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI` (DeepSeek V4 Pro) — konstanta baru, terisolasi dari `OPENROUTER_MODEL_REWRITE` (M1.4) meski `OPENROUTER_MODEL_DECOMPOSITION` kebetulan bernilai sama (Qwen3-32B).

**Opsi yang Dipertimbangkan tapi Ditolak:** Reuse langsung `OPENROUTER_MODEL_REWRITE` untuk Langkah 4/5 M1.6 — ditolak, akan menciptakan coupling tak sengaja antara M1.4 dan M1.6 (ganti model salah satu berisiko memengaruhi yang lain tanpa disadari).

---

## Keputusan 12 (Forced): Span `chat` ×3, Atribut per Langkah

**Sumber Paksaan:** `rancangan-observability-ai-chatbot.md` Bagian 2 baris 37 — "Decomposition (Klasifikasi, Pemecahan, Verifikasi) | `chat` ×3 | + `intent.count`, `intent.relation_type`".

**Keputusan yang Diikuti:** Tiap langkah emit span `chat` sendiri. Atribut: Langkah 4 → `decomposition.classification`; Langkah 5 → `intent.count`, `intent.relation_type`; Langkah 6 → `decomposition.verification_valid`; span retry TERAKHIR di orkestrator → `decomposition.retry_count`, dan (kalau exhausted) `decomposition.verification_exhausted`.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by kontrak observability.

---

## Keputusan 13 (Forced): `evals/1.6-decomposition/` Mengikuti Konvensi Nyata M1.3/M1.4, Jumlah Skenario Tidak Dipatok

**Sumber Paksaan:** Preseden project (`evals/1.3-.../`, `evals/1.4-.../`) + memory `feedback-eval-workflow-mirror-precedent` + koreksi eksplisit user saat review plan ("12 yang ada pada bagian bagian sebelumnya hanyalah kebetulan... prioritas adalah membuat skenario yang bisa mengcover seluruh skenario yang mungkin terjadi").

**Keputusan yang Diikuti:** `rancangan.md` → `run_eval.py` (reuse fungsi internal produksi) → `payloads/` → `audit.md`. Jumlah skenario ditentukan oleh cakupan ruang kegagalan yang genuinely relevan untuk mekanisme 3-langkah+retry ini, BUKAN dipatok ke angka tertentu (12 di M1.3/M1.4 murni kebetulan, bukan konvensi).

**Opsi yang Dipertimbangkan tapi Ditolak:** Mematok jumlah skenario ke 12 (mengikuti pola M1.3/M1.4 secara literal) — ditolak eksplisit oleh user, karena kebetulan pola sebelumnya bukan aturan yang harus diulang.

---

## Keputusan 14 (Forced): `decisions.md` sebagai Task Pertama

**Sumber Paksaan:** Preferensi eksplisit user, ditetapkan sejak Milestone 1.4, berlaku seluruh milestone berikutnya.

**Keputusan yang Diikuti:** Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode apa pun.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by instruksi eksplisit user.

---

## Keputusan 15 (Addendum): `klasifikasi_kebutuhan()` Diberi Guard `response.choices` Kosong/`None` — Fallback Aman Sama Seperti Kegagalan `APIError`

**Status:** Ditemukan di Milestone 7.18 (2026-08-20, saat eksekusi nyata Checkpoint 7 — endpoint `POST /v1/turns` crash HTTP 500), diperbaiki di sini — bukan ditutup di M7.18 sendiri, karena perbaikan logic internal M1.6 adalah tanggung jawab milestone pemilik layer ini, bukan milestone penyambung/pengguna. Pemicu peninjauan ulang yang sudah tercatat lebih dulu di `docs/keterbatasan-diterima.md` #17 (ditemukan riset M7.17, 2026-08-20, "belum terbukti terjadi nyata") kini genuinely terpicu — entri itu sendiri sudah eksplisit mengarahkan "prioritaskan perbaikan di file pemilik masing-masing... mirror pola perbaikan M7.6/M7.7" begitu ini terjadi.

**Latar Belakang**
Eksekusi nyata `evals/7.18-database-percakapan/run_eval.py` (percobaan langsung ke server debug, session_id `eval-7.18-e01c`/`e01d`) menghasilkan HTTP 500 dua kali berturut-turut. Traceback (`uvicorn` stderr, sebelumnya dibuang ke `DEVNULL` di skrip eval — ditangkap ulang lewat pemanggilan manual `uv run python -m uvicorn` dengan stderr tertangkap) menunjukkan `TypeError: 'NoneType' object is not subscriptable` di `klasifikasi_kebutuhan()` (`src/layers/decomposition/klasifikasi.py:69`, baris `response.choices[0].message.content`) — `response.choices` bernilai `None`. Ini PERSIS kelas celah yang sudah didokumentasikan `docs/keterbatasan-diterima.md` #17 sebagai salah satu dari 5 titik ("3 sub-langkah Decomposition M1.6"), ditemukan saat riset M7.17 tapi sengaja diterima tanpa perbaikan karena "belum pernah terjadi nyata". Fungsi ini SUDAH punya mekanisme fallback aman untuk `openai.APIError` (Keputusan 4/9 di atas), tapi respons HTTP 200 dengan body malformed (`choices=None`) tidak raise `APIError` sama sekali — tidak tertangkap `except APIError` yang sudah ada.

**Keputusan yang Dipilih**
Tambah guard `if not response.choices:` SEBELUM baris indexing, REUSE persis mekanisme fallback `_FALLBACK` (`KlasifikasiKebutuhan.MAJEMUK_BERGANTUNG`) yang sudah ada untuk `APIError` — mencatat span attribute `decomposition.forced_fallback_reason=f"empty_response: choices={response.choices!r}"`, TANPA mengubah skema `KlasifikasiKebutuhan` atau signature fungsi.

**Alasan**
Konsisten filosofi Keputusan 3 (retry+fallback aman) — respons API yang tidak bisa dipercaya (baik karena exception maupun karena body malformed) sama-sama diperlakukan sebagai sinyal "tidak bisa menentukan klasifikasi, fallback ke asumsi paling konservatif" (`MAJEMUK_BERGANTUNG` dipilih sebagai fallback di Keputusan awal karena mendorong verifikasi lebih ketat di langkah berikutnya, bukan melewatkan begitu saja). Span attribute tetap membedakan alasan (`empty_response: ...` vs alasan `api_error: ...` yang sudah ada di jalur except), menjaga observability tanpa mengubah kontrak tipe.

**Cakupan perbaikan — SENGAJA DIBATASI hanya `klasifikasi.py`, BUKAN seluruh 5 titik di `keterbatasan-diterima.md` #17.** `pemecahan.py`/`verifikasi.py` (2 sub-langkah Decomposition lain) dan `detect_turn_dependency()` (M1.3) TIDAK disentuh — mirror pola M7.6/M7.7 yang memperbaiki tepat SATU fungsi yang genuinely terbukti crash, bukan seluruh fungsi serupa yang "kemungkinan besar" py celah sama tapi belum terbukti. `susun_narasi()` (M4.4) SENGAJA TIDAK disentuh sama sekali — desain M4.4 eksplisit "tanpa fallback, biarkan menjalar" (lihat `milestones/4.4-penyusunan-narasi/decisions.md`), guard serupa di sana berarti mengubah keputusan desain yang sudah dikunci, bukan sekadar mem-fix bug, di luar wewenang satu temuan insidental untuk memutuskan sepihak.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Memperbaiki seluruh 5 titik `keterbatasan-diterima.md` #17 sekaligus** — ditolak, hanya `klasifikasi.py` yang genuinely terbukti crash lewat eksekusi nyata; 4 titik lain tetap berstatus "diterima, belum terbukti" sampai masing-masing genuinely terpicu, konsisten prinsip precedent M7.6/M7.7 (fix yang terbukti, bukan fix preventif borongan).
- **Guard serupa untuk `susun_narasi()` (M4.4)** — ditolak, bertentangan langsung dengan keputusan desain M4.4 yang sudah dikunci ("tanpa fallback" adalah pilihan sadar, bukan celah).
- **Membiarkan exception menjalar apa adanya (status quo)** — ditolak, sudah terbukti crash HTTP 500 nyata di M7.18, blocking eksekusi eval Checkpoint 7.

**Dampak**
`tests/layers/decomposition/test_klasifikasi_kegagalan.py` (baru, mocked, mirror pola `test_turn_dependency_kegagalan.py` M1.3) membuktikan fallback ini. `docs/keterbatasan-diterima.md` #17 diperbarui — titik "klasifikasi.py" ditandai DIPERBAIKI, 4 titik lain tetap AKTIF/diterima.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Model Langkah 4/5: Qwen3-32B (reuse) | A | Plan |
| 2 | Model Langkah 6: DeepSeek V4 Pro | A | Plan |
| 3 | Kebijakan verifikasi gagal: retry maks 3 kali total | A | Plan |
| 4 | Tiga pemanggilan LLM terpisah | B | Plan |
| 5 | Langkah 6 wajib LLM independen | B | Plan |
| 6 | Relasi 2 nilai (independen/bergantung) | B | Plan |
| 7 | `atomic_intent_id` digenerate kode, bukan LLM | B | Checkpoint 5 |
| 8 | `LabelBentukJawaban` reuse dari session_memory.py | B | Checkpoint 2 |
| 9 | Klasifikasi tidak ikut retry loop | B | Plan |
| 10 | Struktur `src/layers/decomposition/` subpackage | B | Plan |
| 11 | Konstanta model terisolasi per milestone | B | Checkpoint 3 |
| 12 | Span `chat` ×3, atribut per langkah | B | Plan |
| 13 | Konvensi `evals/`, jumlah skenario tidak dipatok | B | Checkpoint 9 |
| 14 | `decisions.md` sebagai Task pertama | B | Plan |
| 15 | Addendum M7.18: guard `response.choices` kosong/`None` di `klasifikasi_kebutuhan()` | A | Addendum 2026-08-20 |
