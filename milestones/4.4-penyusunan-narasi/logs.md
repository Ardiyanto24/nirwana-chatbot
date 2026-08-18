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
