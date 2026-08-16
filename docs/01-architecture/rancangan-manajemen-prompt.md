# Rancangan Arsitektur Manajemen Prompt — AI Chatbot RBAC

**Nirwana Hospitality Group — AI Chatbot Serving Layer**

| | |
|---|---|
| **Dokumen induk** | `arsitektur-ai-chatbot-rbac.md` |
| **Tujuan dokumen** | Mengunci kontrak penyimpanan, versioning, templating, dan reliability testing untuk seluruh system prompt yang dipakai delapan-plus titik pemanggilan LLM di PIC 1-4 — sebagai rujukan bersama SEBELUM prompt diiterasi lebih lanjut, karena prompt yang sudah terlanjur hardcode per-modul (M1.3-M2.1) tidak py versioning maupun mekanisme pengujian reliability sama sekali |
| **Status** | Rancangan awal — kontrak storage/versioning `[SOLID]`, retrofit ke call site yang sudah ada `[KERANGKA AWAL]` (dikerjakan terpisah sebagai Fase 2, di luar cakupan dokumen ini) |
| **Standar yang diikuti** | Markdown + YAML frontmatter untuk isi prompt, Jinja2 untuk templating, Promptfoo untuk reliability testing (CLI, git-native), skema tabel mengikuti pola SQLModel `table=True` yang sudah dipakai `src/db/models.py` |

---

## 1. Prinsip Fondasi

1. **Prompt adalah kode, bukan konten yang bisa diedit lepas dari review.** Prinsip arsitektur induk "AI hanya penulis rencana, bukan pengeksekusi langsung" (`arsitektur-ai-chatbot-rbac.md` Bagian 1) berlaku juga ke instruksi yang dipakai berulang di setiap turn — terutama dua prompt Domain Gate (`identifikasi.py`, `verifikasi_titik_buta.py`) yang secara langsung menentukan domain apa yang dianggap relevan untuk sebuah kebutuhan, sebelum dicocokkan ke `role_permissions`. Perubahan pada prompt ini setara dampaknya dengan perubahan pada kode `otorisasi.py` — **wajib lewat commit git yang direview**, tidak boleh py jalur perubahan lain (mis. lewat UI/API layanan pihak ketiga) yang lolos dari proses review yang sama.
2. **Generate-lalu-verify tidak berubah karena prompt sekarang bisa diversion.** Mekanisme versioning di dokumen ini murni soal *di mana* dan *bagaimana* prompt disimpan/diuji — tidak menggantikan atau melonggarkan kebutuhan verifier independen (M1.6, M2.1, dst.) yang sudah dikunci di dokumen arsitektur induk.
3. **Default aman tetap berlaku.** Selaras `rancangan-observability-ai-chatbot.md` Bagian 1 Prinsip 3 — identitas/versi prompt boleh direkam sebagai metadata terstruktur di span, isi prompt **tidak pernah** direkam di span maupun di tempat lain yang tidak sengaja jadi log permanen berisi teks mentah.
4. **Reliability testing adalah kebutuhan berkelanjutan, bukan sekali per milestone.** Berbeda dari `evals/<milestone>/` yang mengevaluasi perilaku LLM sekali di titik pengembangan milestone tertentu, prompt akan terus diiterasi setelah milestone selesai — mekanisme pengujian di dokumen ini didesain untuk dijalankan berulang kali kapan pun prompt berubah, tanpa terikat siklus milestone.

---

## 2. Struktur Penyimpanan & Versioning

**Lokasi**: `src/prompts/<nama-layer>/<nama>.md`, mirror struktur `src/layers/` yang sudah dipakai konsisten di `src/`, `tests/`, dan `evals/` (lihat tabel Struktur Repository `CLAUDE.md`). Contoh pemetaan dari 8 call site yang sudah ada:

| Call site sekarang | File prompt baru |
|---|---|
| `context_resolution/turn_dependency.py` | `src/prompts/context_resolution/turn_dependency.md` |
| `context_resolution/rewrite.py` | `src/prompts/context_resolution/rewrite.md` |
| `context_resolution/matching.py` | `src/prompts/context_resolution/matching.md` |
| `decomposition/klasifikasi.py` | `src/prompts/decomposition/klasifikasi.md` |
| `decomposition/pemecahan.py` | `src/prompts/decomposition/pemecahan.md` |
| `decomposition/verifikasi.py` | `src/prompts/decomposition/verifikasi.md` |
| `domain_gate/identifikasi.py` | `src/prompts/domain_gate/identifikasi.md` |
| `domain_gate/verifikasi_titik_buta.py` | `src/prompts/domain_gate/verifikasi_titik_buta.md` |

**Format file** — Markdown dengan YAML frontmatter, dipilih dibanding YAML murni atau modul Python karena prompt multi-baris jauh lebih enak dibaca/di-diff sebagai teks Markdown daripada block scalar YAML, sekaligus memisahkan konten prompt dari kode Python secara nyata (dibanding modul `.py` yang tetap mencampur keduanya):

```markdown
---
id: domain_gate.identifikasi_awal
version: 1
milestone: "2.1"
model_compat: ["qwen/qwen3-32b"]
description: "Identifikasi domain awal dari kebutuhan atomik"
---

<isi prompt sebagai template Jinja2 di sini>
```

**Skema frontmatter**:

| Field | Tipe | Keterangan |
|---|---|---|
| `id` | string | Dot-separated, mirror path modul Python (mis. `domain_gate.identifikasi_awal`) — dipakai sebagai key lookup di loader dan sebagai nilai `prompt.id` di span |
| `version` | integer | Naik 1 setiap perubahan material pada isi prompt (bukan whitespace/typo). Bukan semver — prompt bukan API publik dengan konsumen eksternal yang butuh makna major/minor/patch |
| `milestone` | string | Milestone asal (mis. `"2.1"`) — jejak audit ke dokumen `rancangan-*.md` sumber |
| `model_compat` | list[string] | Konstanta model (dari `src/config/llm.py`) yang dimaksudkan kompatibel dengan prompt ini |
| `description` | string | Satu kalimat, untuk manusia yang scan daftar prompt |

**Versi historis** = histori git pada file itu sendiri (`git log`/`git blame`) — tidak perlu sistem versioning terpisah, karena `version` di frontmatter + commit yang mengubahnya sudah cukup untuk menjawab "versi berapa, kapan berubah, siapa yang mengubah, kenapa" (pesan commit).

---

## 3. Templating (Jinja2)

Dipilih dibanding `string.Template` karena beberapa prompt butuh logic, bukan sekadar substitusi:

- **Kondisional** — mis. `pemecahan.py` (M1.6) menyisipkan blok `feedback` hanya saat retry, sekarang jadi `{% if feedback %}...{% endif %}` di template.
- **Loop** — mis. `identifikasi.py`/`verifikasi_titik_buta.py` (M2.1) merender daftar domain dari `DESKRIPSI_DOMAIN` (saat ini di `konteks_domain.py`), jadi `{% for domain, deskripsi in daftar_domain %}...{% endfor %}`.

**Konvensi variabel**: nama variabel Jinja2 memakai `snake_case` Bahasa Indonesia mengikuti konvensi penamaan kode yang sudah dipakai di seluruh `src/` (mis. `riwayat_percakapan`, `daftar_domain`, `catatan_feedback`), bukan Bahasa Inggris — konsisten dengan gaya penamaan fungsi/variabel proyek ini.

Data yang dipakai untuk keperluan sinkronisasi lintas-prompt (mis. `konteks_domain.py` dipakai dua call site M2.1) tetap disuplai dari kode Python ke context Jinja2 saat render — bukan diduplikasi ke dalam tiap file prompt, supaya drift seperti yang sudah dicegah `konteks_domain.py` tidak muncul kembali dalam bentuk baru.

---

## 4. Loader

Kontrak fungsi (dibangun Fase 2, dikontrakkan di sini supaya seluruh call site retrofit mengikuti bentuk yang sama):

```python
# src/prompts/loader.py

def load_prompt(id: str) -> PromptTemplate:
    """Baca file src/prompts/<path>.md sesuai id, parse frontmatter+body.
    Return objek berisi metadata (id, version, dll.) + method render(**kwargs)
    yang mengembalikan teks prompt jadi (setelah Jinja2 render)."""
```

`load_prompt()` dipanggil sekali per proses (hasil bisa di-cache seperti pola `@lru_cache` pada `load_valid_roles()`/`role_permissions.py`, karena isi file tidak berubah selama proses hidup) — prompt di-*render* ulang tiap pemanggilan (variabel per-request), tapi file hanya dibaca dari disk sekali.

Loader **tidak** melakukan network call apa pun — murni baca file lokal, konsisten dengan keputusan storage di Bagian 2 (tanpa dependency runtime ke layanan eksternal).

---

## 5. Reliability Testing (Promptfoo)

**Alat**: [Promptfoo](https://www.promptfoo.dev/) — CLI open-source, config `promptfooconfig.yaml` per prompt, membaca langsung file prompt di `src/prompts/` (bukan sumber kebenaran sendiri, hanya pembaca).

**Lokasi**: `prompt_reliability/` di root repo, terpisah dari `evals/<milestone>/` — `evals/` tetap dipakai untuk evaluasi milestone (sekali di titik pengembangan), `prompt_reliability/` untuk pengujian yang berjalan **setiap kali prompt berubah**, lintas waktu, tidak terikat siklus milestone (lihat Prinsip 4 di atas).

**Struktur** (kerangka, diisi Fase 2 per call site):
```
prompt_reliability/
├── README.md
├── domain_gate/
│   ├── identifikasi_awal.promptfooconfig.yaml
│   └── verifikasi_titik_buta.promptfooconfig.yaml
└── ... (satu subfolder per layer, mirror src/prompts/)
```

**Kapan wajib dijalankan**: setiap kali file di `src/prompts/**/*.md` berubah (bump `version` di frontmatter), sebelum commit di-push — mengikuti prinsip "jangan menganggap perubahan benar tanpa bukti" (`CLAUDE.md`, Workflow Wajib). Diff hasil eval (skenario yang tadinya lolos jadi gagal, atau sebaliknya) idealnya terlihat di review PR, sehingga reviewer prompt RBAC-sensitif (Bagian 1 Prinsip 1) punya bukti konkret, bukan hanya membaca teks prompt baru dan menebak dampaknya.

**Integrasi CI**: opsional, didefer ke Fase 2 (lihat Bagian 9) — Promptfoo mendukung GitHub Actions bawaan bila proyek ini nanti pindah ke remote dengan CI aktif.

---

## 6. Penyimpanan Hasil Eval

**Masalah yang dihindari**: pola `evals/<milestone>/payloads/` yang sudah ada saat ini **men-commit payload mentah ke git** — cocok untuk evaluasi sekali per milestone (volume kecil, finite), tapi tidak cocok untuk reliability testing berkelanjutan (Bagian 5) yang volumenya bertumbuh terus tanpa batas — git bukan tempat yang didesain untuk data yang terus bertambah.

**Solusi**: tabel Supabase baru `prompt_eval_runs`, **append-only**, payload penuh (bukan ringkasan) — reuse infra yang sudah ada (pola sama `session_memory_packages`/`role_permissions`, M1.5/M2.2), bukan tambah database baru. SQLModel `table=True` di `src/db/models.py`, mengikuti pola `SessionMemoryPackageRow`/`RolePermissionRow`.

**Skema**:

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | uuid, primary key | |
| `prompt_id` | text | Merujuk `id` di frontmatter prompt |
| `prompt_version` | int | Merujuk `version` di frontmatter saat run dilakukan |
| `git_commit_hash` | text | Commit tempat versi ini diuji — jejak audit balik ke kode |
| `scenario_id` | text | Dari config Promptfoo (Bagian 5) |
| `input_payload` | jsonb | Payload lengkap yang dikirim ke LLM |
| `output_payload` | jsonb | Output lengkap dari LLM |
| `verdict` | text | Hasil assertion Promptfoo (lolos/gagal, alasan singkat) |
| `model` | text | Konstanta model yang dipakai saat run |
| `created_at` | timestamptz, default now() | |

**Cara push**: skrip kecil (dibangun Fase 2, mis. `prompt_reliability/push_results.py`) mem-parsing output JSON Promptfoo lalu insert baris ke tabel ini lewat SQLModel — dijalankan setelah tiap `promptfoo eval`, baik manual maupun (nanti) dari CI.

---

## 7. Integrasi Observability

Identitas dan versi prompt yang dipakai pada satu pemanggilan LLM direkam sebagai atribut span **metadata terstruktur saja** (bukan isi prompt), konsisten Prinsip 3 di atas: `prompt.id`, `prompt.version` — tanpa prefix `gen_ai.` karena bukan bagian OpenTelemetry GenAI Semantic Conventions resmi (`src/observability/genai_semconv.py` mengekspos `GEN_AI_*` hanya untuk atribut yang benar-benar ada di paket resmi; `PROMPT_ID`/`PROMPT_VERSION` ditulis tangan sebagai konstanta project-custom, mengikuti pola atribut custom lain seperti `rbac.domain`). Kontrak lengkapnya ada di addendum `rancangan-observability-ai-chatbot.md` Bagian 2 (ditambahkan bersamaan dengan dokumen ini) — atribut ini memungkinkan korelasi trace production ke versi prompt spesifik yang menghasilkannya, melengkapi (bukan menggantikan) `prompt_eval_runs` di Bagian 6 yang mencatat hasil pengujian pre-deployment.

---

## 8. Keputusan Desain dan Alternatif yang Dipertimbangkan tapi Ditolak

*(Dicatat di sini, bukan `milestones/<id>/decisions.md` terpisah — pekerjaan ini bukan salah satu dari 22 milestone, dikonfirmasi user sebagai bagian dari dokumen arsitektur ini sendiri.)*

### Keputusan 1 — Storage & versi prompt: file di git

**Opsi dipertimbangkan**:
- **Tabel database (Supabase), mirip `role_permissions`** — ditolak karena membuka jalur perubahan prompt RBAC-sensitif (Domain Gate) lewat write langsung ke DB, di luar review PR — bertentangan dengan Prinsip 1 di atas. Kalau prompt yang menentukan domain relevan bisa diedit tanpa lewat commit yang direview, itu setara melonggarkan RBAC tanpa jejak audit yang sama seperti perubahan `otorisasi.py`.
- **Langfuse (self-hosted)** — dipertimbangkan serius (open-source MIT, self-host gratis, native OpenTelemetry, py fitur prompt versioning+label+link-ke-trace bawaan). Ditolak karena tiga alasan konkret: (1) prompt bisa diubah lewat UI/API Langfuse di luar review PR — risiko sama seperti opsi database di atas; (2) butuh infra tambahan (Postgres+ClickHouse+Redis+opsional S3) di luar 2 database yang sudah dipakai proyek ini (Supabase, Postgres lokal untuk observability privat); (3) menambah satu network call runtime tambahan per pemanggilan LLM (fetch prompt dari Langfuse sebelum panggil OpenRouter) — proyek ini baru saja menambah mitigasi timeout eksplisit untuk masalah hang `get_openrouter_client()` (`docs/keterbatasan-diterima.md` #7), menambah titik kegagalan serupa dinilai kontraproduktif.
- **LangSmith** — ditolak lebih awal: self-hosting hanya tersedia di plan Enterprise berbayar, tidak sesuai proyek portfolio self-hosted.
- **Portkey** — dipertimbangkan (open-source Apache 2.0 sejak Gateway 2.0). Ditolak karena perannya utamanya AI gateway (proxy routing provider), mengadopsinya berarti mengalihkan seluruh pemanggilan LLM proyek lewat gateway baru — perubahan arsitektur jauh lebih besar daripada sekadar kebutuhan penyimpanan prompt. Juga baru diakuisisi Palo Alto Networks (selesai Mei 2026) — ketidakpastian arah roadmap open-source jangka panjang.
- **Hybrid (git + Langfuse sebagai mirror read-only)** — dipertimbangkan sebagai jalan tengah (dapat UI Langfuse tanpa lepas kontrol review). Ditolak karena kompleksitas tertinggi dari semua opsi (dua tempat harus tetap sinkron) untuk manfaat yang sebagian sudah dicakup rencana dashboard M5.x (Next.js+Supabase) — berpotensi tumpang tindih fungsi.

**Dipilih**: file di git, alasan lengkap di Prinsip 1.

### Keputusan 2 — Reliability testing: Promptfoo

**Opsi dipertimbangkan**:
- **Braintrust** — dataset versioning dan experiment tracking dinilai terkuat di kelasnya, tapi **cloud-only, tidak ada opsi self-host sama sekali** — tereliminasi langsung, proyek ini portfolio individu yang seluruh infranya self-hosted.
- **Langfuse (untuk eval, bukan storage prompt)** — Langfuse py fitur dataset+evaluation, tapi kedalaman eval-nya dinilai "limited dibanding platform khusus eval" (Braintrust), dan tiga downside di Keputusan 1 (infra tambahan, dependency runtime, risiko edit-di-luar-review — meski untuk kasus eval risiko terakhir ini lebih kecil) tetap berlaku kalau dipakai murni untuk fitur ini.
- **Promptfoo** — dipilih. CLI-first, git-native (baca langsung file prompt yang sudah lewat review, bukan sumber kebenaran sendiri), tanpa service/database tambahan, tanpa dependency runtime saat serving request (jalan di dev/CI time, bukan saat aplikasi FastAPI melayani request). Trade-off yang diterima sadar: tidak ada production monitoring bawaan (tidak masalah — sudah dicakup kontrak span OTel) dan tidak ada managed prompt registry terpusat (tidak masalah — itu peran `src/prompts/` di git).

### Keputusan 3 — Hasil eval: Supabase, payload penuh

**Opsi dipertimbangkan**:
- **Commit ke git** (pola `evals/*/payloads/` yang sudah ada) — ditolak untuk penggunaan berkelanjutan (Prinsip 4) karena akan membuat repo membengkak tanpa batas seiring waktu; git bukan tempat yang didesain untuk data yang terus bertambah.
- **Supabase, ringkasan saja (tanpa payload mentah)** — dipertimbangkan sebagai opsi paling hemat storage. Tidak dipilih (payload penuh lebih diprioritaskan) karena kalau nanti perlu audit ulang "kenapa skenario X gagal beberapa bulan lalu", detail lengkapnya sudah hilang jika hanya skor yang disimpan.
- **CI artifact ephemeral** (mis. GitHub Actions, retensi terbatas) — dipertimbangkan untuk kebutuhan debugging jangka pendek. Tidak dipilih karena user secara eksplisit ingin analisis tren jangka panjang seiring prompt sering diiterasi ke depan, bukan cuma debugging per-perubahan.
- **Supabase, payload penuh** — dipilih, detail skema di Bagian 6.

### Keputusan 4 — Governance: bagian dari dokumen arsitektur, bukan milestone baru

**Opsi dipertimbangkan**:
- **Folder `milestones/<id>-manajemen-prompt/` baru**, mengikuti workflow milestone penuh (`decisions.md`/`logs.md`/`report.md`) — dipertimbangkan karena pekerjaan ini py bentuk yang sama (keputusan → implementasi → verifikasi → commit) seperti milestone lain, dan ada preseden M1.1 (fondasi Collector) sebagai infra lintas-milestone. Tidak dipilih oleh user — dianggap dokumen arsitektur cross-cutting, bukan unit kerja yang dieksekusi-diverifikasi seperti milestone biasa.
- **Bagian dari dokumen arsitektur ini sendiri** — dipilih. Keputusan tercatat di Bagian 8 ini (menggantikan fungsi `decisions.md`), tanpa `logs.md`/`report.md` terpisah — histori kerja cukup lewat pesan commit dan isi dokumen ini.

---

## 9. Bagian yang Masih Terbuka

Didefer ke Fase 2 (eksekusi retrofit ke 8 call site yang sudah ada), bukan diputuskan sekarang:

1. **Mekanisme exact skrip push Promptfoo → Supabase** (`prompt_reliability/push_results.py`) — format parsing output JSON Promptfoo, penanganan error saat insert gagal.
2. **Urutan retrofit 8 call site** — apakah per-milestone (M1.3 dulu, dst.) atau dikelompokkan cara lain; belum diputuskan, akan diajukan ke user saat Fase 2 dimulai.
3. **Isi konkret `promptfooconfig.yaml` per prompt** (skenario, assertion) — kerangka folder saja yang disiapkan Fase 1, isinya menyusul bersamaan retrofit tiap call site.
4. **Integrasi CI** (Bagian 5) — proyek ini belum py remote/CI aktif; keputusan pindah ke CI penuh ditunda sampai relevan.
