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

## Checkpoint 7 — Implementasi Langkah 1

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 11 — Implementasi `_langkah_generate` dkk.

**Kesesuaian dengan plan:** Sesuai plan, plus Task 8 (Promptfoo config) dieksekusi di sini sesuai deviasi yang dicatat logs Checkpoint 5.

**Apa yang dilakukan**
Menulis `src/layers/retriever/kecocokan_makna.py`: `_render_context_generate()`/`_render_system_prompt_generate()` (inject `CATATAN_LINTAS_DOMAIN`), `_build_user_prompt_generate()` (kebutuhan + label_bentuk_jawaban + daftar kandidat dengan definisi lengkap dari `DEFINISI_LENGKAP_VIEW`), `_call_llm_generate()` (panggilan mentah, dipisah dari parsing - preseden `matching.py`), `_parse_generate()` (jaminan struktural: iterasi dari daftar kandidat GROUND-TRUTH, bukan dari respons LLM — kandidat hilang/label invalid diberi default aman via `_entri_aman_default()`, kandidat halusinasi di respons diabaikan), `_langkah_generate()` (span `"chat"` sesuai kontrak, atribut `retriever.kecocokan_makna.generate_forced_fallback_reason`/`generate_ditemukan_count`).

**Temuan**
Tidak ada temuan mengejutkan pada kode implementasi. `CLAUDE.md`/`AGENT.md` diperbarui mencatat `kecocokan_makna.py` (Langkah 1 selesai) di baris `src/`, disinkronkan identik.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -m pytest tests/layers/retriever/ tests/config/ -v` — 59 test lolos (8 baru Langkah 1 + 51 sisa tanpa regresi).

**Commit:** `29d90f1` — `feat(milestone-3.2): implementasi Langkah 1 kecocokan makna (generate)`

---

### Task 12 — Test Mocked Langkah 1

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `tests/layers/retriever/test_kecocokan_makna.py` — 5 test pure-function `_parse_generate` (respons valid, JSON rusak → gagal, kandidat hilang → default aman BUKAN drop, label invalid → default aman, `view_name` halusinasi diabaikan) + 3 test `_langkah_generate` dengan `get_openrouter_client`/`_call_llm_generate` di-monkeypatch (sukses normal, `APIError` → gagal=True bukan exception, `empty_choices` → gagal=True) — mirror pola `test_pencarian_embedding.py` (M3.1), TANPA network call nyata.

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Sama seperti Task 11 di atas (dijalankan bersamaan) — 59/59 lolos.

**Commit:** `24076b3` — `test(milestone-3.2): Langkah 1 kecocokan makna (generate)`

---

### Task 8 — Promptfoo Config Langkah 1 (dipindah dari Checkpoint 5)

**Kesesuaian dengan plan:** Menyimpang checkpoint eksekusi (dipindah dari Checkpoint 5 ke sini), SESUAI keputusan deviasi yang sudah dicatat eksplisit di logs Checkpoint 5 — bukan penyimpangan baru.

**Apa yang dilakukan**
Menulis `prompt_reliability/retriever/kecocokan_makna_generate.promptfooconfig.yaml` — 3 skenario awal (S01 KK1 grain-mismatch `v_reservation_property_daily` vs kebutuhan per-tipe-kamar, S02 KK2 cocok penuh `v_reservation_room_type_daily`, S03 jebakan "Kolom turunan" `sla_threshold_hours` dengan toleransi eksplisit — nuansa penuh divalidasi di eval Checkpoint 11-13, bukan smoke test ini). `render_context` merujuk `src.layers.retriever.kecocokan_makna._render_context_generate` yang baru dibuat Task 11 — dependency yang jadi alasan deviasi Checkpoint 5 sekarang terpenuhi.

**Temuan**
`user_prompt` di tiap skenario disusun manual mengikuti format PERSIS keluaran `_build_user_prompt_generate()` (dicek dengan menjalankan fungsi tersebut atas data uji nyata terlebih dahulu, lihat kutipan format di komentar commit) - bukan ditulis bebas, supaya reliability testing benar-benar mencerminkan payload runtime asli (prinsip `provider.py`: "prompt yang diuji selalu identik dengan yang benar-benar dikirim").

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -c "import yaml; yaml.safe_load(open(...))"` — YAML valid, 3 test terparse. Import `_render_context_generate` via `importlib` (mensimulasikan cara `provider.py` me-resolve `render_context`) sukses, mengembalikan `catatan_lintas_domain` (2479 karakter). **Belum dijalankan nyata terhadap OpenRouter** — eksekusi Promptfoo penuh ditunda ke Checkpoint 14 sesuai plan.

**Commit:** `82e87a0` — `chore(milestone-3.2): Promptfoo config Langkah 1 kecocokan makna`

---

---

## Checkpoint 8 — Implementasi Langkah 2

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 13 — Implementasi `_langkah_verifikasi` dkk.

**Kesesuaian dengan plan:** Sesuai plan, plus Task 10 (Promptfoo config) dieksekusi di sini sesuai deviasi yang dicatat logs Checkpoint 5.

**Apa yang dilakukan**
Extend `kecocokan_makna.py`: `_render_context_verifikasi()`/`_render_system_prompt_verifikasi()` (konstanta terpisah dari Langkah 1 meski isinya sama, mirror preseden `identifikasi.py`/`verifikasi_titik_buta.py` M2.1), `_build_user_prompt_verifikasi()` (definisi lengkap + penilaian awal Langkah 1 per kandidat), `_call_llm_verifikasi()` (DeepSeek V4 Pro, `extra_body={"reasoning": {"effort": "high"}}`), `_parse_verifikasi()` (SATU perbedaan penting dari `_parse_generate`: kandidat hilang/label-invalid di respons Langkah 2 fallback ke label Langkah 1 kandidat itu SAJA — bukan default generik SEBAGIAN — karena penilaian nyata untuk kandidat itu sudah ada dari Langkah 1, lebih aman dipakai daripada menebak; keputusan implementasi ini tidak butuh entri decisions.md baru, hanya generalisasi natural dari Keputusan 8 ke level per-kandidat), `_langkah_verifikasi()` (span `"chat"`, atribut `retriever.kecocokan_makna.verifikasi_dikoreksi_count` — sinyal observability langsung untuk mendeteksi anchoring: kalau count ini selalu 0 di produksi, Langkah 2 kemungkinan cuma menyalin Langkah 1).

**Temuan**
Tidak ada temuan mengejutkan. `CLAUDE.md`/`AGENT.md` diperbarui mencatat Langkah 2 selesai.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -m pytest tests/layers/retriever/ tests/config/ -v` — 66 test lolos (7 baru Langkah 2 + 59 sisa tanpa regresi).

**Commit:** `5166864` — `feat(milestone-3.2): implementasi Langkah 2 kecocokan makna (verifikasi)`

---

### Task 14 — Test Mocked Langkah 2

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Extend `tests/layers/retriever/test_kecocokan_makna.py` — 5 test pure-function `_parse_verifikasi` (koreksi arah turun ditemukan→sebagian, koreksi arah naik sebagian→ditemukan, konfirmasi tak berubah, JSON rusak → gagal, kandidat hilang → fallback ke label Langkah 1 PERSIS bukan default generik) + 2 test `_langkah_verifikasi` mocked (sukses koreksi dua arah sekaligus dalam satu batch, `APIError` → gagal=True).

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Sama seperti Task 13 di atas (dijalankan bersamaan) — 66/66 lolos.

**Commit:** `7698ebd` — `test(milestone-3.2): Langkah 2 kecocokan makna (verifikasi)`

---

### Task 10 — Promptfoo Config Langkah 2 (dipindah dari Checkpoint 6)

**Kesesuaian dengan plan:** Menyimpang checkpoint eksekusi (dipindah dari Checkpoint 6 ke sini), SESUAI keputusan deviasi yang sudah dicatat eksplisit di logs Checkpoint 5.

**Apa yang dilakukan**
Menulis `prompt_reliability/retriever/kecocokan_makna_verifikasi.promptfooconfig.yaml` — 3 skenario, tiap skenario menyuplai penilaian awal Langkah 1 yang SENGAJA salah arah (S01 terlalu longgar, S02 terlalu ragu, S03 sudah benar/harus dikonfirmasi bukan diubah) untuk menguji Langkah 2 benar-benar mengoreksi dua arah, bukan menyalin.

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -c "import yaml; yaml.safe_load(open(...))"` — YAML valid, 3 test terparse, `render_context` merujuk `_render_context_verifikasi` yang baru dibuat Task 13. **Belum dijalankan nyata** — eksekusi Promptfoo penuh ditunda ke Checkpoint 14.

**Commit:** `58b0e03` — `chore(milestone-3.2): Promptfoo config Langkah 2 kecocokan makna`

---

---

## Checkpoint 9 — Orkestrator Single-Item

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 15 — Implementasi `nilai_kecocokan_makna_atomic_intent`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Extend `kecocokan_makna.py`: `nilai_kecocokan_makna_atomic_intent()` — jalur pintas `kandidat=[]` (BERHASIL+kosong, nol panggilan LLM), lalu Langkah 1 → (kalau gagal: GAGAL_TEKNIS+kosong) → Langkah 2 → (kalau gagal: SEBAGIAN+hasil Langkah 1 utuh) → (sukses: BERHASIL+hasil Langkah 2, MENGGANTIKAN bukan menggabung Langkah 1).

**Temuan**
Tidak ada temuan di luar dugaan. `CLAUDE.md`/`AGENT.md` diperbarui.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -m pytest tests/layers/retriever/ tests/config/` — 70 test lolos (4 baru + 66 sisa tanpa regresi).

**Commit:** `826c3ca` — `feat(milestone-3.2): orkestrator single-item kecocokan makna`

---

### Task 16 — Test Orkestrator Single-Item

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Extend test — kandidat kosong dibuktikan NOL panggilan LLM via monkeypatch raise pada `_langkah_generate`/`_langkah_verifikasi` (pola pembuktian pre-filter M2.3, bukan hanya cek hasil akhir), sukses penuh memastikan keluaran = hasil Langkah 2 (bukan Langkah 1 — membuktikan replacement, bukan union), Langkah 1 gagal total → `_langkah_verifikasi` TIDAK dipanggil (dibuktikan monkeypatch raise juga) + status `GAGAL_TEKNIS`, Langkah 2 gagal → status `SEBAGIAN` + `kecocokan` persis sama objek hasil Langkah 1.

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Sama seperti Task 15 di atas (dijalankan bersamaan) — 70/70 lolos.

**Commit:** `2746b79` — `test(milestone-3.2): orkestrator single-item kecocokan makna`

---

---

## Checkpoint 10 — Orkestrator `_semua()`

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 17 — Implementasi `nilai_kecocokan_makna_semua`

**Kesesuaian dengan plan:** Menyimpang SEBAGIAN pada satu atribut span (bukan pada task/fungsi itu sendiri) — lihat catatan di bawah.

**Apa yang dilakukan**
Extend `kecocokan_makna.py`: `nilai_kecocokan_makna_semua()` — loop `[nilai_kecocokan_makna_atomic_intent(hp) for hp in daftar_hasil_pencarian]`, span `retriever.nilai_kecocokan_makna_semua` (tracer `retriever.kecocokan_makna`, mirror `domain_gate.identifikasi_domain_semua`), atribut `kecocokan_makna.intent_count`/`gagal_teknis_count`/`sebagian_count`. `CLAUDE.md`/`AGENT.md` diperbarui — `kecocokan_makna.py` M3.2 dinyatakan SELESAI.

**Temuan**
**Deviasi kecil dari plan ditemukan saat menulis fungsi ini**: plan Checkpoint 10 menyebut atribut agregat `kecocokan_makna.dikoreksi_count` ("jumlah kandidat yang labelnya berubah Langkah1→2") di span `_semua()`. Menghitung ini di level `_semua()` butuh akses ke `hasil_awal` (Langkah 1) DAN `hasil_verifikasi` (Langkah 2) tiap atomic intent secara bersamaan — tapi `nilai_kecocokan_makna_atomic_intent()` (Checkpoint 9) hanya mengembalikan `HasilKecocokanMakna` final (skema publik, TIDAK menyimpan state antara Langkah 1/2). Menambah field intermediate ke skema publik hanya untuk metrik ini dinilai tidak proporsional dan tidak diminta `decisions.md` manapun. **Data ini SUDAH tercatat lengkap** per-atomic-intent di atribut `retriever.kecocokan_makna.verifikasi_dikoreksi_count` pada span `"chat"` Langkah 2 (Checkpoint 8) — bisa diagregasi lewat query Jaeger/trace correlation antar span dalam satu trace, tanpa perlu duplikasi di span pembungkus. Atribut agregat `_semua()` disederhanakan jadi `intent_count`/`gagal_teknis_count`/`sebagian_count` saja (persis pola `domain_gate.identifikasi_domain_semua()`), TANPA `dikoreksi_count` di level ini. Bukan penghilangan data — hanya dipindah tanggung jawab pencatatannya ke span yang sudah tepat memilikinya.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -m pytest tests/layers/retriever/ tests/config/` — 73 test lolos (3 baru + 70 sisa tanpa regresi).

**Commit:** `51adcf1` — `feat(milestone-3.2): orkestrator _semua() kecocokan makna`

---

### Task 18 — Test Orkestrator `_semua()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Extend test — multi-intent loop dengan urutan dipertahankan (termasuk campuran satu intent kandidat-kosong di antara intent normal), list kosong tidak error, kombinasi 3 status berbeda (`GAGAL_TEKNIS`/`SEBAGIAN`/`BERHASIL`) dalam satu batch diverifikasi urutannya persis sesuai input.

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Sama seperti Task 17 di atas (dijalankan bersamaan) — 73/73 lolos.

**Commit:** `ff628b6` — `test(milestone-3.2): orkestrator _semua() kecocokan makna`

---

---

## Checkpoint 11 — Rancangan Eval

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 19 — Tulis `rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `evals/3.2-kecocokan-makna/rancangan.md` — 8 skenario (S01-S02 KK1/KK2 sumber persis; S03 kolom turunan anti-false-negative; S04-S05 pasangan snapshot-vs-tren + counter-case anti-over-triggering; S06 domain padat 10 kandidat mirror stress-test B5 M3.1; S07 kolom hasil join nullable, observasional; S08 dua view financial mirip beda filter bawaan), tiap skenario dengan kebutuhan+kandidat+ekspektasi+toleransi eksplisit SEBELUM eksekusi.

**Temuan**
Saat menyusun S03 (awalnya dirancang sebagai "kolom turunan = trap negatif"), disadari spec sumber `rancangan-retrieval-query.md` sebenarnya membedakan DUA jenis jebakan berbeda: "Kolom turunan" (kolom hasil HITUNG, mis. `sla_threshold_hours`) vs "kolom hasil JOIN dari tabel lain, berpotensi tidak selalu terisi" (mis. `property_id` di `v_housekeeping_staff_daily`). Awalnya kedua ini nyaris tercampur jadi satu skenario. Dipisah jadi S03 (kolom turunan — dirancang ULANG jadi kasus POSITIF/anti-false-negative, karena nilai kolom turunan tetap benar) dan S07 (kolom hasil join, observasional soal nullability) — pemisahan ini memperjelas apa sebenarnya yang diuji tiap skenario.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Review manual — setiap dimensi di tabel "Yang Diuji" punya skenario pembukti, KK1/KK2 sumber (S01-S02) tanpa toleransi sesuai statusnya sebagai kriteria wajib.

**Commit:** `b9b7dd0` — `test(milestone-3.2): rancangan eval kecocokan makna`

---

---

## Checkpoint 12 — Eksekusi Eval

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 20 — Tulis + Jalankan `run_eval.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `evals/3.2-kecocokan-makna/run_eval.py` (reuse `nilai_kecocokan_makna_atomic_intent()` produksi langsung, filter opsional per-skenario lewat argv mirror `evals/2.1-.../run_eval.py`). Sanity-check import module (tanpa panggilan LLM) lolos duluan. Dijalankan S02 sendirian dulu sebagai smoke test sebelum batch penuh (validasi wiring end-to-end dengan biaya minimal) — LOLOS. Baru kemudian seluruh 8 skenario dijalankan sekaligus.

**Temuan**
**8/8 skenario LOLOS** pada percobaan pertama, termasuk kedua kriteria wajib tanpa toleransi (S01 KK1, S02 KK2, S04, S08). S06 (domain padat 10 kandidat) hasil LEBIH BAIK dari toleransi yang diizinkan — 0 dari 9 kandidat non-fokus salah dilabel `ditemukan` (toleransi mengizinkan hingga 2), seluruhnya presisi: 1 `ditemukan` (`v_hr_watchlist_monthly`, benar), 2 `sebagian` (kandidat yang genuinely dekat), 7 `tidak_ditemukan`. S07 (observasional) menunjukkan bukti NYATA mekanisme koreksi dua arah bekerja — `alasan` payload eksplisit menyebut "Penilaian awal terlalu ragu, koreksi ke 'ditemukan'" (Langkah 1 sempat menilai `sebagian`, Langkah 2 mengoreksi naik ke `ditemukan`) — TAPI `alasan` final TIDAK menyinggung nuansa join/nullable `property_id` yang jadi fokus observasional S07, murni soal grain/kolom yang tersedia. Dicatat sebagai temuan kualitatif jujur di `audit.md` (Checkpoint 13), bukan disembunyikan meski skenario tetap `match=True` sesuai kriteria pass/fail yang didefinisikan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Console: `8/8 skenario lolos`. Payload lengkap tersimpan `evals/3.2-kecocokan-makna/payloads/{S01..S08}.json` — respons API nyata (bukan mock), termasuk `alasan` tekstual penuh tiap kandidat untuk audit kualitatif.

**Commit:** `985f7f9` — `test(milestone-3.2): eksekusi eval kecocokan makna`

---

---

## Checkpoint 13 — Audit Eval

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 21 — Tulis `audit.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `evals/3.2-kecocokan-makna/audit.md` — ringkasan 8/8 lolos per skenario, 4 temuan didokumentasikan jujur: (1) bukti nyata koreksi dua arah bekerja (S07, Langkah 2 eksplisit menyatakan mengoreksi Langkah 1), (2) nuansa join/nullable tidak muncul di `alasan` S07 meski `CATATAN_LINTAS_DOMAIN` diinject penuh — dicatat sebagai observasi netral, BUKAN keterbatasan formal (baru satu titik data), (3) presisi S06 melebihi ambang toleransi (0/9 vs toleransi 2), (4) KK1/KK2 sumber lolos tanpa retry.

**Temuan**
Diputuskan TIDAK menambah entri baru `docs/keterbatasan-diterima.md` — dipertimbangkan eksplisit (Temuan 2 di atas) tapi ditolak karena satu titik data tunggal, beda dari preseden M2.1 #6/M3.1 #11 yang berulang lintas beberapa skenario sebelum dicatat formal.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Review manual — tiap skenario `rancangan.md` py hasil match/toleransi tercatat, tidak ada yang diam-diam dihilangkan meski seluruhnya lolos.

**Commit:** `2035811` — `test(milestone-3.2): audit eval kecocokan makna`

---

---
