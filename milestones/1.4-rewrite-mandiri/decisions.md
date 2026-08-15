# Decisions — Milestone 1.4: Membangun Penulisan Ulang Pertanyaan Jadi Mandiri

## Keputusan 1: Model LLM — Qwen3-32B via OpenRouter

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion` + riset web komparatif).

**Latar Belakang**
Milestone 1.4 adalah pemanggilan LLM kedua di proyek (setelah M1.3), untuk tugas yang beda sifat — generatif (menyusun kalimat Bahasa Indonesia baru), bukan klasifikasi ringan seperti M1.3. `CLAUDE.md` "Status Saat Ini" eksplisit menyatakan model per-langkah boleh berbeda dari M1.3 kalau kebutuhannya beda, bukan otomatis dianggap final untuk seluruh proyek.

**Keputusan yang Dipilih**
`qwen/qwen3-32b` (OpenRouter), $0.08/$0.28 per 1M token input/output.

**Alasan**
Riset komparatif (WebSearch/WebFetch, Agustus 2026) terhadap kandidat dari beberapa provider menunjukkan Qwen3-32B satu-satunya kandidat dengan bukti benchmark Bahasa Indonesia **langsung** — keluarga Qwen3 (varian VL-32B) memuncaki **SEA-HELM** (benchmark bahasa Asia Tenggara) untuk Indonesian di kalangan model open-source, skor 68.41. Harga input setara DeepSeek V4 Flash 0731 (model M1.3), dan model sudah beredar cukup lama (bukan rilis baru) sehingga risiko perilaku API tak terduga lebih rendah.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **DeepSeek V4 Flash 0731 (reuse model M1.3)** — $0.08/$0.16 per 1M token, termurah dari seluruh kandidat. Ditolak karena tidak ada sinyal benchmark Bahasa Indonesia spesifik yang ditemukan untuk tugas generatif seperti rewrite — model ini terbukti bekerja baik untuk klasifikasi ringan (M1.3), tapi kualitasnya untuk menyusun kalimat Indonesia yang natural/setia makna belum terverifikasi.
- **Gemini 2.5 Flash Lite** — $0.10/$0.40 per 1M token. Sempat jadi rekomendasi awal (harga hampir setara DeepSeek, keluarga Google umumnya kuat di bahasa low-resource). Ditolak setelah user meminta eksplorasi kandidat dari provider China — bukan ditolak karena kualitas, tapi karena Qwen3-32B ditemukan setara harga dengan bukti benchmark Indonesian yang lebih langsung (SEA-HELM vs sinyal keluarga umum).
- **Gemini 3 Flash (Preview)** — $0.50/$3.00 per 1M token. Skor Indonesian tertinggi di Artificial Analysis Multilingual Index (94, setara model flagship Gemini Pro). Ditolak karena ~6x lebih mahal dari Qwen3-32B untuk tugas yang masih tahap testing proyek — tidak sepadan untuk klasifikasi/generasi ringan yang dipanggil tiap turn bukan-pertama.
- **Qwen3-Next-80B-A3B Instruct** — $0.09/$1.10 per 1M token. Peringkat #2 SEA-HELM Indonesian (67.11), kapasitas model lebih besar (MoE 80B). Ditolak karena output ~4x lebih mahal dari Qwen3-32B tanpa kebutuhan kapasitas ekstra yang jelas untuk tugas rewrite sederhana ini.
- **Gemini 3.7 Flash** — $0.375/$1.875 per 1M token (harga promo 50% off, normal ~$0.75/$3.75). Ditolak karena rilis baru 2 hari sebelum riset ini (13 Agustus 2026) — belum ada skor benchmark Indonesian spesifik untuk versi ini, harga promo berisiko berubah, dan didesain untuk "agentic workflows, coding, complex multi-step reasoning" — kapasitas reasoning berlebih untuk tugas rewrite yang sederhana.

**Dampak**
Konstanta model baru `OPENROUTER_MODEL_REWRITE` diisolasi di `src/config/llm.py`, terpisah dari `OPENROUTER_MODEL` (M1.3) — mengganti model nanti tidak menyentuh logic `rewrite.py` maupun `turn_dependency.py`.

---

## Keputusan 2: Pendekatan Verifikasi — Deterministik Ruang-Tertutup

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Ada tegangan nyata antara dua sumber: Prinsip Arsitektur #3 `CLAUDE.md`/`arsitektur-ai-chatbot-rbac.md` mewajibkan "generate lalu verify independen" untuk keputusan yang menyentuh makna bahasa, kecuali ruang kesalahannya tertutup — sementara menilai apakah hasil rewrite benar-benar mandiri dan setia makna adalah judgment semantik terbuka. Tapi dokumen sumber Milestone 1.4 (`rancangan-context-decomposition.md` baris 87) dan tabel kontrak observability (`rancangan-observability-ai-chatbot.md` baris 34, "sama seperti di atas") eksplisit mendesain langkah ini sebagai **satu** pemanggilan LLM (`chat`), tanpa span verify terpisah — identik pola Langkah 2 (M1.3).

**Keputusan yang Dipilih**
Verifikasi deterministik ruang-tertutup: scan hasil rewrite terhadap daftar frasa tetap penanda rujukan sisa (bukan LLM kedua). Murni flag observability (span attribute anomali), TIDAK memaksa fallback/mengubah hasil LLM.

**Alasan**
Mirror preseden M1.3 (Keputusan 7: single-call forced by dokumen sumber, verifikasi murni struktural bukan LLM kedua) — dokumen sumber M1.4 sudah membuat trade-off desain ini secara eksplisit saat arsitektur ditulis, sehingga diperlakukan sebagai keputusan yang sudah dipaksa (forced), bukan dibuka ulang. Yang tersisa untuk diputuskan adalah SEBERAPA JAUH verifikasi struktural bisa membantu tanpa melanggar batas single-call — jawabannya: heuristic ruang-tertutup (daftar frasa tetap), konsisten prinsip "verifikasi boleh deterministik hanya jika ruang kesalahan bisa didaftar eksplisit di depan".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tanpa verifikasi tambahan (murni single-call passthrough)** — paling literal mengikuti dokumen sumber. Ditolak karena tidak ada pengaman struktural sama sekali, berbeda dari preseden M1.3 yang selalu punya bounds-check minimal; mengurangi observability tanpa alasan kuat mengingat biayanya (satu fungsi scan sederhana) rendah.
- **LLM verifier independen kedua** — paling ketat mengikuti Prinsip Arsitektur #3 secara literal. Ditolak karena bertentangan langsung dengan desain eksplisit dokumen sumber M1.4 dan tabel kontrak observability (single `chat` span) — memilih ini berarti merevisi kontrak yang sudah dikunci di dokumen arsitektur, bukan sekadar keputusan implementasi, dan tidak ada permintaan eksplisit dari user untuk melakukan revisi sebesar itu.

**Dampak**
Daftar frasa tetap (mis. "dibanding itu", "seperti tadi", "sama seperti sebelumnya", "hal itu", "hal tersebut", "yang disebutkan sebelumnya") dipakai — BUKAN kata tunggal ambigu seperti "itu"/"nya" saja, karena suffix "-nya" dan kata ganti tunggal terlalu umum dipakai legit dalam Bahasa Indonesia (mis. "harganya", "labanya") dan akan menghasilkan banyak false-positive. Hasil deteksi dicatat sebagai span attribute `rewrite.residual_reference_detected` + `rewrite.residual_reference_phrases`, tidak pernah mengubah `rewritten_question`.

---

## Keputusan 3 (Forced): Satu Pemanggilan LLM Tunggal

**Sumber Paksaan:** Output Milestone 1.4 (`rancangan-context-decomposition.md` baris 87: "Mekanisme (satu pemanggilan model AI)") + tabel kontrak observability (`rancangan-observability-ai-chatbot.md` baris 34: "Context Resolution — Langkah 3a (Rewrite) | `chat` | sama seperti di atas").

**Keputusan yang Diikuti:** Satu span `chat`, satu pemanggilan LLM — tidak dipecah jadi generate+verify berpasangan lewat LLM kedua.

**Catatan Ketergantungan:** Preseden langsung Keputusan 7 `milestones/1.3-pemetaan-ketergantungan-turn/decisions.md`.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by dokumen sumber + kontrak observability.

---

## Keputusan 4 (Forced): Input = `payload.question` + `payload.history` Penuh, Tidak Mengonsumsi Output M1.3

**Sumber Paksaan:** (a) Sifat independen/paralel M1.4 yang dinyatakan eksplisit di `rancangan-context-decomposition.md` ("berjalan paralel dengan Milestone 1.5... keduanya benar-benar independen"); (b) Kriteria Keberhasilan M1.4 sendiri butuh histori penuh untuk resolusi eksplisit (skenario "satu tahun sebelumnya" hanya bisa diresolusi kalau tahu bulan/tahun turn sebelumnya, yang cuma tersedia di `history`).

**Keputusan yang Diikuti:** `rewrite_to_standalone(payload: TurnPayload)` membaca `payload.question` + `payload.history` langsung dari payload M1.2/M1.3 — tidak menerima `TurnDependencyResult` sebagai parameter.

**Catatan Ketergantungan:** Konsisten dengan revisi payload M1.3 (`history: list[HistoryTurn]`) yang sudah menyediakan seluruh konteks yang dibutuhkan.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by independensi eksplisit yang dinyatakan dokumen sumber.

---

## Keputusan 5 (Forced): Output Schema Minimal `RewriteResult{rewritten_question: str}`, Teks Polos (Bukan JSON)

**Sumber Paksaan:** Output milestone doc ("menghasilkan satu kalimat pertanyaan yang utuh dan bisa dipahami tanpa konteks tambahan apa pun").

**Keputusan yang Diikuti:** `RewriteResult` hanya berisi satu field `rewritten_question: str`. Panggilan LLM TIDAK memakai `response_format={"type": "json_object"}` (beda dari M1.3) — hasil LLM diambil sebagai teks polos, dibungkus `RewriteResult` di sisi kode untuk konsistensi tipe.

**Catatan Ketergantungan:** M1.3 butuh JSON karena punya 2 field (`is_dependent`+`referenced_turn_index`) yang perlu dibedakan. M1.4 cuma 1 field string — JSON wrapper tidak menambah manfaat struktural, hanya menambah mode kegagalan parsing (mis. LLM membungkus jawaban dengan markdown code fence) yang tidak perlu untuk output sesederhana ini.

**Opsi yang Dipertimbangkan tapi Ditolak:** `response_format=json_object` mirror M1.3 — ditolak karena tidak ada manfaat struktural untuk output 1 field, hanya menambah risiko kegagalan parsing.

---

## Keputusan 6 (Forced): Span `chat`, Atribut `gen_ai.*` dari `genai_semconv.py`

**Sumber Paksaan:** `rancangan-observability-ai-chatbot.md` Bagian 2.

**Keputusan yang Diikuti:** Konstanta diimpor dari `src/observability/genai_semconv.py` (Milestone 1.1) — tidak hardcode string baru, identik pola M1.3.

**Catatan Ketergantungan:** Konsistensi lintas-layer untuk dashboard observability (Milestone 5.x).

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada.

---

## Keputusan 7 (Forced): Lokasi Kode `src/layers/context_resolution/rewrite.py`, Tracer `context_resolution.rewrite`

**Sumber Paksaan:** Keputusan 10 `milestones/1.3-.../decisions.md` — 1 layer arsitektur (Context Resolution) = 4 milestone implementasi (1.3/1.4/1.5/1.7), subpackage `src/layers/context_resolution/` sudah ada dari M1.3.

**Keputusan yang Diikuti:** Modul baru `rewrite.py` di subpackage yang sama, tracer name `context_resolution.rewrite` (mirror `context_resolution.turn_dependency`).

**Catatan Ketergantungan:** Konsisten konvensi "per-layer" M1.2/M1.3.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — perluasan wajar dari struktur yang sudah ada.

---

## Keputusan 8 (Forced): Fallback Kegagalan API → Kembalikan `payload.question` Asli, Ditandai Anomali

**Sumber Paksaan:** Prinsip "Kejujuran terhadap keterbatasan" (`CLAUDE.md`) + preseden safety-first Keputusan 9 `milestones/1.3-.../decisions.md`.

**Keputusan yang Diikuti:** Kalau panggilan API gagal atau respons kosong, `rewritten_question` diisi `payload.question` asli tanpa modifikasi (bukan exception, bukan string kosong), span attribute `rewrite.forced_fallback_reason` diisi alasan.

**Catatan Ketergantungan:** Rewrite tidak punya nilai "aman" pasti setara `is_dependent=False` M1.3 — mengembalikan teks asli tanpa modifikasi adalah pilihan paling tidak merusak (langkah berikutnya tetap menerima kalimat yang valid secara gramatikal, meski belum tentu mandiri).

**Opsi yang Dipertimbangkan tapi Ditolak:** Melempar exception ke pemanggil — ditolak karena akan menghentikan pipeline turn sepenuhnya untuk kegagalan yang mestinya bisa degradasi dengan baik (best-effort), bertentangan dengan prinsip kejujuran-terhadap-keterbatasan yang minta status non-normal *tersurat*, bukan sistem berhenti total.

---

## Keputusan 9 (Forced): Konstanta Model Baru Terisolasi, Tidak Mengubah `OPENROUTER_MODEL` Existing

**Sumber Paksaan:** `turn_dependency.py` (M1.3) masih bergantung pada `OPENROUTER_MODEL`; `CLAUDE.md` "Status Saat Ini" eksplisit menyatakan model per-langkah boleh beda dari M1.3.

**Keputusan yang Diikuti:** `OPENROUTER_MODEL_REWRITE = "qwen/qwen3-32b"` ditambahkan sebagai konstanta baru di `src/config/llm.py`, terpisah dari `OPENROUTER_MODEL = "deepseek/deepseek-v4-flash-0731"`.

**Catatan Ketergantungan:** Mengganti model M1.4 di masa depan tidak menyentuh `turn_dependency.py`, dan sebaliknya.

**Opsi yang Dipertimbangkan tapi Ditolak:** Mengganti `OPENROUTER_MODEL` existing jadi Qwen3-32B untuk kedua langkah — ditolak karena akan diam-diam mengubah model M1.3 yang sudah terverifikasi bekerja (Keputusan 3 M1.3), tanpa permintaan eksplisit untuk migrasi itu.

---

## Keputusan 10 (Forced): Workflow Pengujian Dua Lapis (`tests/` + `evals/`) Mirror Preseden Nyata M1.3

**Sumber Paksaan:** Instruksi eksplisit user untuk milestone ini ("untuk pengujian tolong lakukan dengan workflow yang sama seperti pada milestone 1.3") + konvensi project-wide `evals/README.md`.

**Keputusan yang Diikuti:** Checkpoint 2 (`tests/`, skenario minimal sesuai 2 Kriteria Keberhasilan sumber + verifikasi span nyata di Jaeger) dan Checkpoint 3 (`evals/1.4-rewrite-mandiri/`, skenario lebih luas: `rancangan.md` sebelum eksekusi → `run_eval.py` reuse `_call_llm()` produksi langsung → `payloads/*.json` → `audit.md` setelah eksekusi dengan analisis mendalam) — struktur identik `evals/1.3-pemetaan-ketergantungan-turn/`.

**Catatan Ketergantungan:** Bukan cuma mengikuti nama konvensi `evals/README.md` secara abstrak, tapi mereplikasi kedalaman nyata yang sudah terbukti berguna di M1.3 (menemukan temuan S07/S12 yang tidak akan ketahuan dari 2-3 skenario minimal saja).

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by instruksi eksplisit user.

---

## Keputusan 11 (Forced): `decisions.md` Ditulis Sebagai Task Pertama, Sebelum Implementasi Kode

**Sumber Paksaan:** Instruksi eksplisit user untuk milestone ini ("task pertama haruslah selalu menulis file decisions"), merevisi pola M1.3 yang menulisnya di checkpoint penutupan.

**Keputusan yang Diikuti:** Dokumen ini (`decisions.md`) ditulis sebagai Task 1, Checkpoint 1 — sebelum `src/schemas/rewrite.py` atau file kode lain mana pun dibuat.

**Catatan Ketergantungan:** Seluruh keputusan (model + verifikasi) sudah final lewat `AskUserQuestion` sebelum plan ditulis, sehingga tidak ada risiko mendokumentasikan keputusan yang belum matang di titik ini.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by instruksi eksplisit user.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Model LLM: Qwen3-32B via OpenRouter | A | Plan |
| 2 | Pendekatan verifikasi: deterministik ruang-tertutup | A | Plan |
| 3 | Satu pemanggilan LLM tunggal | B | Plan |
| 4 | Input `payload.question`+`payload.history`, tidak konsumsi output M1.3 | B | Plan |
| 5 | Output schema minimal, teks polos (bukan JSON) | B | Plan |
| 6 | Span `chat`, atribut `gen_ai.*` | B | Plan |
| 7 | Lokasi kode `rewrite.py`, tracer `context_resolution.rewrite` | B | Plan |
| 8 | Fallback kegagalan API → teks asli + anomali | B | Plan |
| 9 | Konstanta model baru terisolasi | B | Plan |
| 10 | Workflow pengujian dua lapis mirror M1.3 | B | Plan |
| 11 | `decisions.md` sebagai Task pertama | B | Plan |
