# Logs — Milestone 3.2: Pemeriksaan Kecocokan Makna

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Dokumentasi Keputusan

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/3.2-kecocokan-makna/decisions.md`: 14 keputusan (3 Jenis A hasil `AskUserQuestion` dalam sesi perencanaan — mekanisme verifikasi generate+verifikator independen dengan koreksi dua arah, granularitas batch per kebutuhan atomik, cakupan orkestrator menyertakan `_semua()`; 11 Jenis B forced/preseden — termasuk reuse model Qwen3-32B/DeepSeek V4 Pro, transkripsi verbatim corpus definisi lengkap, injeksi sekali `Catatan Lintas-Domain`, dua fallback gagal-teknis, jaminan struktural anti-drop-kandidat, validator satu-arah `HasilKecocokanMakna`, nama span literal `"chat"`). Riset mendalam (3 agen Explore paralel + 1 agen Plan) dan verifikasi langsung terhadap kode sumber (`src/config/llm.py`, `domain_gate.py`, `matching.py`, `retriever.py` schemas, `katalog-data-chatbot.md`) dilakukan sebelum plan ditulis, memastikan tiap keputusan forced benar-benar bisa ditelusuri ke preseden/kontrak nyata, bukan asumsi.

**Temuan**
Plan draft pertama (format bebas, bukan mengikuti `template-plan-milestone-lengkap.md`) ditolak user lewat `ExitPlanMode` dengan instruksi eksplisit mengikuti template — plan ditulis ulang penuh mengikuti struktur template persis (Context dengan Temuan Penting/Batasan Mengikat/Klarifikasi → Keputusan Desain Turunan → Keputusan yang Ditanyakan ke User → Checkpoint & Task Breakdown Task 1-25 berurutan → Kriteria Keberhasilan → Commit → Risiko & Mitigasi) sebelum diajukan ulang dan disetujui. Verifikasi silang terhadap kode nyata (bukan hanya laporan agen) menemukan satu detail penting yang mengoreksi rekomendasi awal agen Plan: nama span pemanggilan LLM adalah literal `"chat"` (dibuktikan dari `context_resolution/matching.py`), bukan nama custom `retriever.nilai_kecocokan_makna_semua` seperti sempat diusulkan — dikoreksi sebelum plan final ditulis (Keputusan 11).

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Review manual — seluruh keputusan di plan yang disetujui (Keputusan Desain Turunan + Keputusan yang Ditanyakan ke User) punya entri `decisions.md` yang sesuai dengan "Opsi yang Dipertimbangkan tapi Ditolak", tidak ada yang diam-diam jadi asumsi implisit.

**Commit:** `4c46591` — `docs(milestone-3.2): keputusan desain kecocokan makna`

---

---

## Checkpoint 2 — Corpus Definisi Lengkap View

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 2 — Bangun `definisi_view.py`

**Kesesuaian dengan plan:** Sesuai plan, dengan penyesuaian metode kerja (bukan penyimpangan hasil): 67 entri DIBANGKITKAN lewat skrip Python sekali-pakai (parse regex atas `katalog-data-chatbot.md`, tulis dict Python) alih-alih diketik ulang manual satu per satu — menjamin byte-identik dengan sumber tanpa risiko salah ketik manual pada teks sepanjang ini (67 blok × ~10-20 baris). Hasil akhirnya tetap file Python statis hardcoded (bukan file yang dibaca runtime), sama seperti preseden `korpus_view.py`.

**Apa yang dilakukan**
Menulis skrip (`scratchpad/gen_definisi_view.py`, tidak di-commit) yang: (1) memisahkan bagian `## Catatan Lintas-Domain` dari body 67 view, (2) meregex tiap blok `#### \`view_name\`` s.d. batas berikutnya, (3) mengelompokkan entri per domain via `DAFTAR_VIEW_PER_DOMAIN` (bukan re-parse header `## Domain` — dihindari karena satu domain, `guests_pii`/`guests_profile`, py header gabungan non-standar), (4) menulis `src/layers/retriever/definisi_view.py` dengan `DEFINISI_LENGKAP_VIEW: dict[str, str]` (67 entri) dan `CATATAN_LINTAS_DOMAIN: str` (7 butir, transkripsi verbatim).

**Temuan**
Dua putaran percobaan regex gagal sebelum benar: (1) percobaan pertama hanya menemukan 65/67 entri — dua view (`guests_contact_view`, `guests_profile_view`) py header dengan teks tambahan setelah backtick penutup (`` #### `guests_contact_view` (domain `guests_pii`) ``), tidak cocok pola `` `#### \`([^\`]+)\`\n` `` yang mengasumsikan newline persis setelah backtick. (2) perbaikan pertama (`.*` sebelum `\n`) salah menambah `re.DOTALL` implisit ke bagian header sehingga `.*` melahap seluruh dokumen sampai ujung — regex akhirnya hanya menemukan 1 entri. Diperbaiki dengan `[^\n]*` (bukan `.*`) khusus untuk sisa baris header, mempertahankan `re.DOTALL` hanya untuk grup body. Setelah kedua perbaikan, tepat 67 entri ditemukan, diverifikasi bijective dengan `DAFTAR_VIEW_PER_DOMAIN`.

**Error/Kegagalan**
`AssertionError: expected 67, got 65` (percobaan 1), lalu `AssertionError: expected 67, got 1` (percobaan 2) — keduanya di skrip generator, sebelum file final ditulis. Tidak ada error di file akhir.

**Diagnosis dan Perbaikan**
Lihat "Temuan" di atas — root cause diisolasi dengan debug terpisah (`missing = all_views - set(entries.keys())`) yang langsung menunjuk `guests_contact_view`/`guests_profile_view`, dikonfirmasi dengan membaca baris 971/983 dokumen sumber langsung.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -c "from src.layers.retriever.definisi_view import DEFINISI_LENGKAP_VIEW, CATATAN_LINTAS_DOMAIN"` — import sukses, `len(DEFINISI_LENGKAP_VIEW) == 67`. Spot-check manual isi `guests_contact_view` dan `v_hr_turnover_snapshot` dibaca lewat tool `Read` (bukan terminal, yang menampilkan em-dash/× sebagai mojibake akibat codepage konsol Windows, bukan korupsi data nyata) — konten UTF-8 benar.

**Commit:** `735735c` — `feat(milestone-3.2): corpus definisi lengkap 67 view`

---

### Task 3 — Tulis Test Drift-Detection

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `tests/layers/retriever/test_definisi_view.py` — regex independen (didefinisikan ulang di file test, bukan impor dari skrip generator, supaya benar-benar independen) mem-parse ulang dokumen sumber, dibandingkan `==` terhadap `DEFINISI_LENGKAP_VIEW`. 8 test: kesamaan persis dokumen sumber, prasyarat regex menemukan 67 entri, 67-count langsung, bijective dengan `DAFTAR_VIEW_PER_DOMAIN`, kesamaan `CATATAN_LINTAS_DOMAIN`, spot-check marker "Kolom turunan" (`v_maintenance_ticket_daily`), spot-check jebakan snapshot (`v_hr_turnover_snapshot`), spot-check butir 5 Catatan Lintas-Domain ("di-join dari").

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -m pytest tests/layers/retriever/ tests/config/ -v` — 43 test lolos (8 baru + 35 sisa M3.1 tanpa regresi). Catatan operasional: `python -m pytest` dengan Python sistem (bukan `.venv/`) gagal `ModuleNotFoundError: rank_bm25` untuk 2 file test M3.1 yang sudah ada — bukan bug dari perubahan checkpoint ini, murni salah lingkungan (dependency proyek ada di `.venv/`, bukan Python sistem, sesuai catatan `prompt_reliability/README.md` soal `PROMPTFOO_PYTHON`); pengujian ulang dengan `.venv/Scripts/python.exe` mengonfirmasi seluruh 43 test lolos.

**Commit:** `733b191` — `test(milestone-3.2): drift-detection corpus definisi lengkap view`

---

---

## Checkpoint 3 — Skema Kecocokan Makna

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 4 — Tambah Skema ke `src/schemas/retriever.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambah `LabelKecocokanMakna` (enum ditemukan/sebagian/tidak_ditemukan), `KecocokanKandidat` (kandidat: KandidatView utuh, label, alasan), `HasilKecocokanMakna` (atomic_intent, kecocokan, status) ke `src/schemas/retriever.py` yang sudah ada (M3.1) — bukan file baru, sesuai preseden satu modul skema per layer. Docstring modul diperluas menjelaskan perbedaan cakupan status M3.1 vs M3.2 dan validator satu-arah.

**Temuan**
Tidak ada temuan di luar dugaan — implementasi persis mengikuti bentuk yang sudah dirancang di plan/decisions.md.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -m pytest tests/layers/retriever/test_kecocokan_makna_schema.py tests/layers/retriever/test_retriever_schema.py -v` — 14 test lolos (8 baru + 6 M3.1 tanpa regresi).

**Commit:** `78d1891` — `feat(milestone-3.2): skema kecocokan makna`

---

### Task 5 — Tulis Test Skema

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `tests/layers/retriever/test_kecocokan_makna_schema.py` — 8 test: `GAGAL_TEKNIS`+`kecocokan` non-kosong ditolak, `DITOLAK_OTORISASI`/`TERBLOKIR_KETERGANTUNGAN` ditolak, `GAGAL_TEKNIS`+kosong valid, **`BERHASIL`+kosong valid** (pembeda utama dari `AtomicIntentDomains` — Keputusan 10), `SEBAGIAN`/`BERHASIL`+non-kosong valid, dan `KandidatView` utuh (bukan `view_name` str) terbawa di `KecocokanKandidat`.

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Sama seperti Task 4 di atas (dijalankan bersamaan) — 14/14 lolos.

**Commit:** `e2a3016` — `test(milestone-3.2): skema kecocokan makna`

---

---

## Checkpoint 4 — Konstanta Model

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 6 — Tambah Konstanta Model M3.2

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambah `OPENROUTER_MODEL_KECOCOKAN_MAKNA_GENERATE = "qwen/qwen3-32b"` dan `OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI = "deepseek/deepseek-v4-pro"` ke `src/config/llm.py`, dengan entri docstring baru mengikuti gaya entri lama (rujuk milestone, model, dan alasan reuse — termasuk penjelasan kenapa Langkah 2 di sini MENGGANTIKAN Langkah 1, beda dari pola union aditif M2.1/M2.3).

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -c "from src.config.llm import OPENROUTER_MODEL_KECOCOKAN_MAKNA_GENERATE, OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI"` — import sukses, nilai sesuai (`qwen/qwen3-32b`, `deepseek/deepseek-v4-pro`).

**Commit:** `6ff410d` — `feat(milestone-3.2): konstanta model kecocokan makna`

---

---

## Checkpoint 5 — Prompt Langkah 1 (Generate)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 7 — Tulis `kecocokan_makna_generate.md`

**Kesesuaian dengan plan:** Menyimpang dari plan pada Task 8 (bukan Task 7 ini) — lihat catatan di bawah.

**Apa yang dilakukan**
Menulis `src/prompts/retriever/kecocokan_makna_generate.md` (frontmatter id=`retriever.kecocokan_makna_generate`, version=1, milestone="3.2", model_compat=["qwen/qwen3-32b"]) — instruksi menilai tiap kandidat terhadap definisi lengkap, jebakan grain-mismatch dan "Kolom turunan" eksplisit disebut, `{{ catatan_lintas_domain }}` diinject sebagai variabel Jinja2 (mirror `catatan_pola_jebakan` M2.1). Format keluaran JSON `{"penilaian": [{"view_name", "label", "alasan"}, ...]}`. `CLAUDE.md`/`AGENT.md` diperbarui (baris `src/`, `src/prompts/`, `tests/`) mencatat folder baru `src/prompts/retriever/` dan file-file M3.2 yang sudah ada sejauh ini, disinkronkan identik (`diff` kosong).

**Temuan**
**Penyimpangan dari plan ditemukan saat menulis Task 8** (Promptfoo config untuk prompt ini, direncanakan di checkpoint yang sama): konvensi `render_context` (dicontohkan `prompt_reliability/domain_gate/deteksi_cakupan_individu.promptfooconfig.yaml`) mensyaratkan dotted-path ke fungsi `_render_context()` TANPA ARGUMEN di modul layer terkait (mis. `src.layers.domain_gate.deteksi_cakupan_individu._render_context`) — fungsi ini belum bisa ada karena `src/layers/retriever/kecocokan_makna.py` (Checkpoint 7) belum ditulis. Menulis Promptfoo config sekarang akan merujuk fungsi yang belum ada. **Task 8 (dan simetris Task 10 di Checkpoint 6) dipindah ke Checkpoint 7/8** (implementasi Langkah 1/2), dieksekusi bersamaan dengan `_render_context_generate()`/`_render_context_verifikasi()` yang jadi target rujukannya — konsisten preseden M2.3 ("Promptfoo dibangun NATIF sebagai bagian checkpoint [implementasi]", bukan checkpoint prompt terpisah). Task TIDAK dihapus atau dikonsolidasi — nomor/isi Task 8 dan 10 tetap sama persis, hanya checkpoint eksekusinya berpindah. Tidak mengubah jumlah total atomic task milestone ini.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -c "from src.prompts.loader import load_prompt; from src.layers.retriever.definisi_view import CATATAN_LINTAS_DOMAIN; p = load_prompt('retriever.kecocokan_makna_generate'); print(p.render(catatan_lintas_domain=CATATAN_LINTAS_DOMAIN))"` — parse frontmatter + render Jinja2 sukses, 4662 karakter keluaran, `catatan_lintas_domain` ter-inject benar.

**Commit:** `83023b7` — `feat(milestone-3.2): prompt Langkah 1 kecocokan makna (generate)`

---

---

## Checkpoint 6 — Prompt Langkah 2 (Verifikasi)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 9 — Tulis `kecocokan_makna_verifikasi.md`

**Kesesuaian dengan plan:** Sesuai plan untuk Task 9 ini. Task 10 (Promptfoo config verifikasi) TETAP dipindah ke Checkpoint 8, konsisten deviasi yang sudah dicatat di logs Checkpoint 5.

**Apa yang dilakukan**
Menulis `src/prompts/retriever/kecocokan_makna_verifikasi.md` (frontmatter id=`retriever.kecocokan_makna_verifikasi`, version=1, milestone="3.2", model_compat=["deepseek/deepseek-v4-pro"]) — instruksi eksplisit re-derivasi independen SEBELUM melihat label Langkah 1 (mitigasi anchoring, per decisions.md Keputusan 1 dan Risiko baris 2 di plan), dua arah kesalahan diinstruksikan eksplisit sebagai daftar bernomor (terlalu longgar vs terlalu ragu), keluaran dinyatakan eksplisit sebagai "penilaian FINAL yang akan MENGGANTIKAN penilaian awal sepenuhnya". `CLAUDE.md`/`AGENT.md` diperbarui (baris `src/prompts/`) mencatat kedua prompt M3.2 sudah terisi, disinkronkan identik.

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -c "from src.prompts.loader import load_prompt; ...; load_prompt('retriever.kecocokan_makna_verifikasi').render(catatan_lintas_domain=...)"` — parse frontmatter + render Jinja2 sukses, 5216 karakter keluaran.

**Commit:** `b7116b2` — `feat(milestone-3.2): prompt Langkah 2 kecocokan makna (verifikasi)`

---

---
