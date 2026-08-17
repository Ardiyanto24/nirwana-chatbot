# Prompt Reliability Testing

Folder ini menampung pengujian reliability **berkelanjutan** untuk system prompt di `src/prompts/` — beda dari `evals/`, yang mengevaluasi perilaku LLM **sekali** di titik pengembangan satu milestone tertentu. Konvensi lengkap ada di `docs/01-architecture/rancangan-manajemen-prompt.md` Bagian 5-6; ringkasannya di sini.

Perbedaan mendasar dengan `evals/`:

| | `evals/<milestone>/` | `prompt_reliability/` |
|---|---|---|
| Kapan dijalankan | Sekali, saat milestone dikembangkan | Berkali-kali, setiap kali file di `src/prompts/**/*.md` berubah — tidak terikat siklus milestone |
| Alat | Skrip Python manual (`run_eval.py`) | Promptfoo (CLI, config `promptfooconfig.yaml`) |
| Penyimpanan hasil | `payloads/*.json` **di-commit ke git** | Tabel Supabase `prompt_eval_runs` (append-only, payload penuh) — **tidak di-commit**, supaya repo tidak membengkak seiring waktu |
| Sumber kebenaran prompt | Ditulis manual per skenario | Dibaca langsung dari frontmatter+body `src/prompts/<layer>/<nama>.md` — tidak menyimpan prompt sendiri |

## Konvensi Struktur

Satu subfolder per layer, mirror `src/prompts/`:

```
prompt_reliability/
├── README.md
├── context_resolution/
│   ├── turn_dependency.promptfooconfig.yaml
│   ├── rewrite.promptfooconfig.yaml
│   └── matching.promptfooconfig.yaml
├── decomposition/
│   ├── klasifikasi.promptfooconfig.yaml
│   ├── pemecahan.promptfooconfig.yaml
│   └── verifikasi.promptfooconfig.yaml
└── domain_gate/
    ├── identifikasi.promptfooconfig.yaml
    ├── verifikasi_titik_buta.promptfooconfig.yaml
    ├── deteksi_cakupan_individu.promptfooconfig.yaml
    └── verifikasi_cakupan_individu.promptfooconfig.yaml
```

## Kapan Dipakai

Setiap kali prompt di `src/prompts/**/*.md` berubah (bump `version` di frontmatter), sebelum commit di-push — supaya reviewer prompt punya bukti konkret dampak perubahan (skenario yang tadinya lolos jadi gagal, atau sebaliknya), bukan hanya membaca teks prompt baru dan menebak dampaknya. Wajib terutama untuk prompt RBAC-sensitif (Domain Gate: `identifikasi.md`/`verifikasi_titik_buta.md`/`deteksi_cakupan_individu.md`/`verifikasi_cakupan_individu.md`) mengingat sensitivitasnya (lihat Prinsip 1, `rancangan-manajemen-prompt.md`).

**Menjalankan Promptfoo lokal**: provider Python (`provider.py`) butuh dependency proyek (`opentelemetry-exporter-otlp-proto-grpc`, dll.) yang hanya terpasang di virtualenv `uv` (`.venv/`), bukan Python sistem yang dipakai Promptfoo secara default. Set `PROMPTFOO_PYTHON` ke interpreter venv sebelum `npx promptfoo eval`, mis. (PowerShell): `$env:PROMPTFOO_PYTHON = "$(Resolve-Path ../../.venv/Scripts/python.exe)"`.

## Status

Terisi penuh — seluruh 8 prompt M1.3-M2.1 (`config` per call site, Fase 2) + 2 prompt M2.3 (`deteksi_cakupan_individu`/`verifikasi_cakupan_individu`, dibangun natif sejak awal milestone, bukan retrofit — lihat `milestones/2.3-deteksi-cakupan-individu/decisions.md` Keputusan 11) + 2 prompt M3.2 (`retriever/kecocokan_makna_{generate,verifikasi}`, natif sejak awal, diselaraskan penuh 8 skenario `evals/3.2-.../rancangan.md` — 7/8 lolos tiap config, lihat `milestones/3.2-kecocokan-makna/logs.md` Checkpoint 14 untuk detail dua temuan). `push_results.py` reuse untuk seluruh config.

## Referensi

`docs/01-architecture/rancangan-manajemen-prompt.md` — kontrak lengkap storage, versioning, templating, dan reliability testing prompt.
