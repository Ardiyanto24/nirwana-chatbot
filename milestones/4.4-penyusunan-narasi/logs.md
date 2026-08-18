# Logs — Milestone 4.4: Membangun Penyusunan Narasi

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/4.4-penyusunan-narasi/decisions.md` berisi 14 keputusan (1 Jenis A — model LLM, dijawab user lewat `AskUserQuestion` saat Plan Mode; 13 Jenis B — forced/preseden), masing-masing merujuk sumber paksaan eksplisit (nama dokumen/milestone).

**Temuan**
Tidak ada temuan baru di luar yang sudah tercatat di plan (Context "Temuan penting sebelum plan ditulis") — seluruh 14 keputusan sudah teridentifikasi penuh sejak riset Plan Mode.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
Review manual: seluruh 14 entri menyebut sumber paksaan/rujukan eksplisit (nama dokumen/milestone), tidak ada butir tanpa rujukan. Daftar Isi Keputusan di akhir file konsisten dengan urutan penomoran entri.

**Commit:** `f1d60da` — `docs(milestone-4.4): keputusan desain penyusunan narasi`

---

## Checkpoint 2 — Skema dan Konstanta Model

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 2 — Buat `src/schemas/interpretation.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membuat `HasilNarasi(BaseModel)` dengan satu field `narasi: str`, docstring menjelaskan kenapa tanpa field tambahan (rujuk decisions.md Keputusan 10).

**Temuan**
Tidak ada.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`python -c "from src.schemas.interpretation import HasilNarasi; HasilNarasi(narasi='test')"` berhasil, output `narasi='test'`.

**Commit:** `c3d8b8c` — `feat(milestone-4.4): skema HasilNarasi + konstanta model narasi`

---

### Task 3 — Tambah `OPENROUTER_MODEL_NARASI` ke `src/config/llm.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambah `OPENROUTER_MODEL_NARASI = "qwen/qwen3-32b"` + entri docstring baru mengikuti pola persis entri model lain (alasan pemilihan + rujukan decisions.md Keputusan 1).

**Temuan**
Tidak ada.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`python -c "from src.config.llm import OPENROUTER_MODEL_NARASI; print(OPENROUTER_MODEL_NARASI)"` berhasil, output `qwen/qwen3-32b`. Kedua import (Task 2+3) diverifikasi bersamaan dalam satu pemanggilan.

**Commit:** `c3d8b8c` — `feat(milestone-4.4): skema HasilNarasi + konstanta model narasi`

---

## Checkpoint 3 — System Prompt Narasi

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 4 — Tulis `src/prompts/interpretation/narasi.md`

**Kesesuaian dengan plan:** Sesuai plan. Plan menyebut "6 instruksi wajib" di teks Task tapi rincinya sendiri menghitung 7 (5 arsitektur + rujukan lintas-turn + kontras nada) — konsisten dengan Kriteria Keberhasilan/Lingkup sumber M4.4 yang memang menyebut "5 ketentuan wajib... ditambah satu ketentuan yang lahir khusus dari kebutuhan multi-turn". Prompt final menulis 7 aturan bernomor eksplisit (status non-normal, parsial, ditolak_otorisasi, gagal_teknis dengan nada beda eksplisit dari ditolak_otorisasi, larangan klaim sebab-akibat, kebutuhan gagal karena dependency, rujukan lintas-turn) + instruksi tambahan soal catatan interpretasi.

**Apa yang dilakukan**
Menulis frontmatter (`id: interpretation.narasi`, `version: 1`, `milestone: "4.4"`, `model_compat: ["qwen/qwen3-32b"]`) + body: penjelasan peran, bentuk input yang akan diterima (daftar kebutuhan dengan status/nilai_hasil/catatan_interpretasi/sumber/prasyarat), instruksi format output (prosa Bahasa Indonesia biasa, BUKAN JSON), lalu 7 aturan bernomor.

**Temuan**
Tidak ada temuan tak terduga — isi prompt murni menerjemahkan 5+1 ketentuan dari `rancangan-execution-interpretation.md` Lingkup M4.4 + kontras nada ditolak_otorisasi vs gagal_teknis dari Kriteria Keberhasilan sumber, ke instruksi eksplisit bernomor.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`load_prompt("interpretation.narasi").render()` berhasil parse frontmatter YAML + body Jinja2 tanpa error (body statis, tidak ada variabel Jinja2 — konsisten Keputusan 8). Checklist manual: ketujuh aturan tersurat sebagai butir bernomor terpisah, kontras nada aturan 3 vs 4 eksplisit disebutkan dalam teks aturan 4 itu sendiri ("nada kalimatnya harus terasa BEDA dari... aturan 3").

**Commit:** `9ca96db` — `feat(milestone-4.4): system prompt penyusunan narasi`

---

## Checkpoint 4 — Implementasi `susun_narasi()`

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 5 — `_build_user_prompt()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Implementasi `_build_user_prompt(atomic_intents, packages)` di `src/layers/interpretation/narasi.py` — merakit daftar kebutuhan (teks, label bentuk jawaban, status, sumber, nilai_hasil, catatan_interpretasi) + relasi `bergantung_pada` (dicocokkan ke `atomic_intent_id` lain dalam daftar yang sama, ditampilkan sebagai teks kebutuhan+status prasyarat, bukan ID mentah — supaya LLM tidak perlu "menerka" makna ID). Menegakkan kontrak 1:1 atomic_intent<->package secara eksplisit lewat `ValueError` (Risiko & Mitigasi plan).

**Temuan**
Tidak ada temuan tak terduga.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Dua pemanggilan manual (bukan pytest, verifikasi cepat sebelum lanjut Task 6): (a) 2 atomic intent (1 independen, 1 bergantung) menghasilkan teks yang benar menyertakan baris "Bergantung pada" dengan status prasyarat; (b) atomic_intent tanpa package pasangan memicu `ValueError("atomic_intent tanpa package pasangan (kontrak 1:1 dilanggar): ['a1']")` — sesuai desain.

**Commit:** `9cca2f4` — `feat(milestone-4.4): implementasi susun_narasi()`

---

### Task 6 — `susun_narasi()` orkestrator

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Implementasi `susun_narasi(atomic_intents, packages, session_id, turn_index) -> HasilNarasi` — span `chat` dengan atribut kontrak (`session.id`, `turn.index`, `gen_ai.operation.name`, `gen_ai.request.model`, `prompt.id`/`prompt.version`, `narrative.turn_reference`, `gen_ai.usage.*`), panggilan `OPENROUTER_MODEL_NARASI` `temperature=0` tanpa `response_format`. Ditambah konstanta atribut custom `NARRATIVE_TURN_REFERENCE = "narrative.turn_reference"` di `src/observability/genai_semconv.py` (tidak eksplisit disebut di plan, tapi forced langsung oleh kontrak observability Bagian 2 — konsisten pola `REQUEST_DOMAIN`/`REQUEST_VIEW_NAME` M3.4). `APIError` ditangkap, `error.type=gagal_teknis` di-set pada span, lalu di-raise ulang apa adanya (mirror `store_session_memory()`).

**Temuan**
`_turn_reference()` menghasilkan `list[int]` (turn_index unik dari paket bersumber `"session_memory (turn N)"`) — di span OTel, list otomatis disimpan sebagai tuple immutable (`(3,)`) saat dibaca balik dari `InMemorySpanExporter`, bukan penyimpangan, murni perilaku OTel SDK menyimpan attribute sequence.

**Error/Kegagalan (jika ada)**
Percobaan pertama memanggil `python` (sistem, bukan venv proyek) gagal `ModuleNotFoundError: No module named 'opentelemetry.exporter.otlp.proto.grpc'` — bukan bug kode, environment sistem tidak punya dependency proyek terpasang.

**Diagnosis dan Perbaikan (jika ada error)**
Verifikasi diulang pakai `.venv/Scripts/python.exe` (virtualenv proyek, konsisten catatan `prompt_reliability/README.md` soal `PROMPTFOO_PYTHON`) — berhasil tanpa error.

**Hasil Verifikasi**
(1) Panggilan NYATA `susun_narasi()` (bukan mock) dengan 2 atomic intent campuran sumber (`session_memory (turn 3)` + `eksekusi_baru`) menghasilkan narasi yang secara manual dibaca masuk akal dan eksplisit membedakan "berdasarkan data yang telah dihitung sebelumnya (turn 3)" vs "hasil perhitungan terkini dari sistem" — memenuhi KK1 sumber di titik ini. (2) Docker Desktop TIDAK aktif sesi ini (`docker ps` gagal) — mirror keterbatasan M4.1-M4.3, verifikasi visual Jaeger TERTUNDA. Sebagai gantinya, dipakai `InMemorySpanExporter` (OTel SDK) langsung: span `chat` tunggal tercatat dengan seluruh 9 atribut kontrak terisi benar (`session.id='s1'`, `turn.index=5`, `gen_ai.operation.name='chat'`, `gen_ai.request.model='qwen/qwen3-32b'`, `prompt.id='interpretation.narasi'`, `prompt.version=1`, `narrative.turn_reference=(3,)`, `gen_ai.usage.input_tokens=1171`, `gen_ai.usage.output_tokens=248`).

**Commit:** `9cca2f4` — `feat(milestone-4.4): implementasi susun_narasi()`

---

## Checkpoint 5 — Unit Test

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 7 — `tests/layers/interpretation/test_narasi.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis 8 test: (a) `_turn_reference()` — kosong kalau seluruh `eksekusi_baru`, unik+terurut untuk campuran sumber; (b) `_build_user_prompt()` — memuat status/sumber/catatan_interpretasi, menyertakan relasi `bergantung_pada` (dengan status prasyarat), raise `ValueError` kalau package pasangan hilang; (c) `susun_narasi()` (mocked `_call_llm`, mirror pola `test_penyusunan_request.py` M3.4) — hasil sukses normal, atribut span lengkap sesuai kontrak (mocked tracer, mirror `_SpanRekam`/`_TracerRekam` `test_klasifikasi_respons.py` M4.2), `APIError` diteruskan ke pemanggil DAN `error.type=gagal_teknis` tercatat di span.

**Temuan**
Tidak ada temuan tak terduga — kedua pola precedent (mock `_call_llm` M3.4, mock tracer M4.2) langsung applicable tanpa penyesuaian struktural.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -m pytest tests/layers/interpretation/ -v` — 8/8 PASSED.

**Commit:** `ffa2e78` — `test(milestone-4.4): unit test susun_narasi()`

---

## Checkpoint 6 — Rancangan Eval

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 8 — Tulis `evals/4.4-penyusunan-narasi/rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan (13 skenario, sesuai target "~12-14" plan).

**Apa yang dilakukan**
Menulis 13 skenario (S01-S13) mencakup kedua KK sumber (S01 untuk KK1, S02-S04 untuk KK2) plus dimensi tambahan (sebagian+flagged/stale, berhasil murni baseline negatif, terblokir_ketergantungan 1 level + rantai 2 level, nullable-bermakna, jebakan sebab-akibat, kejujuran total kegagalan, lintas-turn ganda). Karena output `susun_narasi()` adalah teks bebas (beda dari SELURUH eval milestone sebelumnya yang menilai keputusan terstruktur), setiap skenario memakai heuristik ringan (kehadiran/ketiadaan kata kunci) SEBAGAI PELENGKAP, bukan pengganti audit manual — kolom "Audit Manual Wajib" ditambahkan eksplisit di ringkasan (tidak ada di preseden M1.6/M1.7 karena keduanya punya ekspektasi terstruktur yang bisa di-assert penuh otomatis).

**Temuan**
Penyesuaian struktural dari preseden: karena narasi adalah teks bebas, "check" otomatis tidak bisa jadi satu-satunya sumber kebenaran match/mismatch seperti M1.6/M1.7 — didesain sebagai lapis tambahan, verdict akhir tetap dari audit manual (dicatat eksplisit di rancangan.md, bukan penyimpangan diam-diam).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Tidak ada eksekusi di checkpoint ini (murni dokumen desain). Review manual: kedua KK sumber masing-masing punya ≥1 skenario pembukti eksplisit (S01 untuk KK1; S02, S03, S04 untuk KK2 — S04 paling representatif karena menguji kontras BERDAMPINGAN persis seperti kalimat KK2 sumber).

**Commit:** `3271209` — `docs(milestone-4.4): rancangan eval penyusunan narasi`

---
