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
    └── verifikasi_titik_buta.promptfooconfig.yaml
```

## Kapan Dipakai

Setiap kali prompt di `src/prompts/**/*.md` berubah (bump `version` di frontmatter), sebelum commit di-push — supaya reviewer prompt punya bukti konkret dampak perubahan (skenario yang tadinya lolos jadi gagal, atau sebaliknya), bukan hanya membaca teks prompt baru dan menebak dampaknya. Wajib terutama untuk prompt Domain Gate (`identifikasi.md`, `verifikasi_titik_buta.md`) mengingat sensitivitas RBAC-nya (lihat Prinsip 1, `rancangan-manajemen-prompt.md`).

## Status

Skeleton — isi `promptfooconfig.yaml` per prompt dan skrip push hasil ke Supabase (`push_results.py`) menyusul di Fase 2, bersamaan retrofit tiap call site dari `_SYSTEM_PROMPT` hardcode ke `src/prompts/`.

## Referensi

`docs/01-architecture/rancangan-manajemen-prompt.md` — kontrak lengkap storage, versioning, templating, dan reliability testing prompt.
