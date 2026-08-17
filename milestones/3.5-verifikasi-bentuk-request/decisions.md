# Decisions — Milestone 3.5: Verifikasi Bentuk Request

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 3.5 — Langkah 2 (verifikasi independen) Query Engine, menilai ulang `QueryEngineRequest` hasil Milestone 3.4 terhadap kepatuhan sumber (`view_name`) dan kecukupan semantik parameter terhadap `label_bentuk_jawaban`, tanpa melihat proses generate-nya.

**Catatan penting:** Seluruh 13 keputusan di bawah adalah Jenis B (forced/turunan dari preseden atau kontrak yang sudah ada) — **tidak ada keputusan Jenis A** (genuinely terbuka lewat `AskUserQuestion`) di milestone ini. Ini dinyatakan eksplisit sesuai anjuran template plan ("Kalau seluruh keputusan di suatu milestone ternyata forced semua... itu sah terjadi, nyatakan eksplisit alih-alih menghapus section-nya") — bukan hasil section yang terlewat, melainkan hasil pengecekan sadar terhadap: (a) redaksi eksplisit `rancangan-retrieval-query.md` Milestone 3.5; (b) preseden model verifier independen yang sudah dipakai konsisten di 4 milestone lain (M1.6/M2.1/M2.3/M3.2); (c) preseden struktural langsung Milestone 3.4; (d) prinsip arsitektur ruang-kesalahan-tertutup-vs-terbuka `CLAUDE.md`.

---

## Keputusan 1: Mekanisme HYBRID — Pre-Check Deterministik (Kriteria 1) + Satu Pemanggilan LLM (Kriteria 2)

**Sumber Paksaan**
Prinsip arsitektur `CLAUDE.md`: "Verifikasi boleh murni deterministik (tanpa LLM) hanya jika seluruh ruang kesalahan yang mungkin terjadi bisa didaftar sebagai aturan eksplisit di depan (ruang kesalahan tertutup)." Kriteria 1 M3.5 (`view_name` request sama dengan `view_name` tervalidasi Retriever) adalah satu perbandingan string persis — ruang kesalahan TERTUTUP. Kriteria 2 (apakah `params` benar-benar cukup membentuk jawaban sesuai `label_bentuk_jawaban`) tidak bisa didaftar sebagai aturan tertutup karena bentuk `params` bebas per view — ruang kesalahan TERBUKA, sesuai redaksi sumber sendiri: "yang diperiksa di sini masih menyentuh soal kesesuaian makna terhadap kebutuhan asli, bukan sekadar kepatuhan struktural yang seluruh ruang kesalahannya bisa didaftar sebagai aturan tertutup di depan."

**Keputusan yang Diikuti**
`verifikasi_bentuk_request_atomic_intent()` menjalankan pre-check deterministik untuk Kriteria 1 TERLEBIH DAHULU; hanya memanggil LLM untuk Kriteria 2 kalau pre-check lolos.

**Catatan Ketergantungan**
Menentukan struktur seluruh Checkpoint 4 (pre-check dulu, LLM kedua sebagai langkah terpisah, bukan satu prompt menilai keduanya sekaligus).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Satu pemanggilan LLM menilai KEDUA kriteria sekaligus (termasuk kepatuhan sumber)** — ditolak, bertentangan langsung dengan prinsip "jangan minta LLM menilai yang ruang kesalahannya tertutup dan bisa dipastikan kode" yang sudah dipegang konsisten proyek ini (`_saring_params_tidak_dikenal` M3.4, rule table M3.3, `verifikasi_bentuk_request_statis` M2.4).

---

## Keputusan 2: Pre-Check Kriteria 1 — Perbandingan String Sederhana

**Sumber Paksaan**
Ruang kesalahan tertutup (Keputusan 1) — Kriteria 1 hanya butuh `request.view_name == view_name_tervalidasi_retriever`, tidak ada nuansa makna yang perlu dipertimbangkan.

**Keputusan yang Diikuti**
`_view_name_sesuai_retriever(request, view_name_tervalidasi_retriever) -> bool` — perbandingan string exact match, bukan fuzzy/substring.

**Catatan Ketergantungan**
Pemeriksaan ini SECARA SENGAJA redundan dengan `verifikasi_kepatuhan_sumber()` (Cek 2, M2.4 `verifikasi_gate.py`) — bukan duplikasi tidak sengaja. M2.4 adalah gerbang keamanan TERAKHIR yang tetap wajib menolak independen apa pun yang terjadi sebelumnya (defense in depth, prinsip `CLAUDE.md` "AI hanya penulis rencana, bukan pengeksekusi langsung"); M3.5 memberi sinyal revisi dengan alasan LEBIH AWAL dalam alur (di titik generate-verify Query Engine, sebelum request sampai ke Verification Gate sama sekali). Risiko drift antara dua implementasi rendah karena keduanya hanya perbandingan string atas dua nilai yang sama.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hilangkan pre-check M3.5, andalkan M2.4 saja** — ditolak, bertentangan langsung dengan Kriteria Keberhasilan sumber M3.5 sendiri yang eksplisit menuntut "berhasil ditangkap dan ditolak oleh verifikasi ini" (bukan oleh Verification Gate).

---

## Keputusan 3: Pre-Check Gagal → Short-Circuit, Tanpa Span `chat`, Tanpa Panggilan LLM

**Sumber Paksaan**
Preseden `retriever/kecocokan_makna.py` (M3.2) Keputusan 10 — jalur pintas kandidat kosong M3.1: span `chat` HANYA dibuka kalau LLM benar-benar dipanggil, bukan span kosong/percuma untuk kasus yang sudah pasti jawabannya dari kode.

**Keputusan yang Diikuti**
Kalau `_view_name_sesuai_retriever()` mengembalikan `False`, `verifikasi_bentuk_request_atomic_intent()` langsung mengembalikan `HasilVerifikasiBentukRequest(lolos=False, alasan=...)` TANPA membuka span `chat` dan TANPA memanggil LLM sama sekali.

**Catatan Ketergantungan**
Konsisten dengan kontrak observability — span `chat` di kontrak (`rancangan-observability-ai-chatbot.md` Bagian 2, "Query Engine Langkah 1 & 2: chat ×2") menghitung span PER PANGGILAN LLM sungguhan, bukan per pemanggilan fungsi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tetap buka span `chat` kosong untuk konsistensi struktur trace** — ditolak, akan mencatat metadata `gen_ai.*`/`prompt.id` yang tidak benar-benar terjadi (tidak ada pemanggilan model), menyesatkan pembacaan trace di Jaeger/dashboard publik.

---

## Keputusan 4: Satu Pemanggilan LLM untuk Kriteria 2, Tanpa Retry, Tanpa Verifier Independen Kedua

**Sumber Paksaan**
`rancangan-retrieval-query.md` eksplisit: "Mekanisme (pemanggilan model AI)" — bentuk tunggal. Preseden `susun_request_atomic_intent()` (M3.4 Keputusan 9), forced redaksi sumber serupa.

**Keputusan yang Diikuti**
`verifikasi_bentuk_request_atomic_intent()` melakukan SATU panggilan LLM untuk Kriteria 2, tanpa retry, tanpa verifier independen kedua di dalam milestone ini.

**Catatan Ketergantungan**
M3.5 SENDIRI sudah berperan sebagai sisi "verify" dari pasangan generate-verify M3.4+M3.5 — menambah verifier kedua di dalam M3.5 akan jadi lapisan verifikasi ketiga yang tidak diminta sumber manapun (beda dari M3.2 yang genuinely py dua langkah generate+verify KARENA M3.2 sendiri BUKAN separuh dari pasangan generate-verify lintas-milestone seperti M3.4/M3.5).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced eksplisit oleh redaksi dokumen sumber sendiri.

---

## Keputusan 5: Model — DeepSeek V4 Pro `reasoning="high"`, Konstanta Terisolasi Sendiri

**Sumber Paksaan**
Preseden kuat dan konsisten: setiap kali suatu langkah berperan sebagai "verifikasi independen terhadap hasil langkah generate sebelumnya", proyek ini selalu memakai DeepSeek V4 Pro `reasoning="high"` untuk keragaman peran verifier — M1.6 Langkah 6 (Verifikasi Decomposition), M2.1 Langkah 2 (Verifikasi Titik Buta), M2.3 Langkah 2 (Verifikasi Cakupan Individu), M3.2 Langkah 2 (Verifikasi Kecocokan Makna). M3.5 adalah kasus PALING literal dari pola ini — memverifikasi hasil M3.4 secara independen, bukan sekadar langkah kedua dalam satu milestone yang sama.

**Keputusan yang Diikuti**
`OPENROUTER_MODEL_VERIFIKASI_BENTUK_REQUEST = "deepseek/deepseek-v4-pro"` (`src/config/llm.py`, konstanta baru terisolasi mengikuti preseden "satu konstanta per konsumen", M1.4 Keputusan 9), dipanggil dengan `extra_body={"reasoning": {"effort": "high"}}`.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Reuse Qwen3-32B (model M3.4)** — ditolak, bertentangan dengan preseden keragaman peran verifier yang konsisten dipakai proyek ini setiap kali suatu langkah SECARA EKSPLISIT berperan sebagai verifikasi independen terhadap langkah generate sebelumnya (beda dari M3.3 yang reuse Qwen3-32B untuk fallback konservatif SATU-langkah, bukan peran verifier-dari-generate-terpisah).

---

## Keputusan 6: Tidak Ada Retry/Jalur Perbaikan Balik ke Milestone 3.4 di Dalam Milestone Ini

**Sumber Paksaan**
Catatan Serah Terima `rancangan-retrieval-query.md` eksplisit: "Jalur perbaikan untuk request yang gagal... kembali ke Milestone 3.4 untuk direvisi — mekanisme pengiriman balik ini perlu disepakati bentuknya dengan pemilik `rancangan-execution-interpretation.md` **sebelum diimplementasikan di kedua sisi**." Diperkuat `docs/keterbatasan-diterima.md` #5 (mekanisme retry-dengan-feedback M1.6 belum terbukti memperbaiki hasil).

**Keputusan yang Diikuti**
`verifikasi_bentuk_request_atomic_intent()` murni MENILAI (mengembalikan `lolos`/`alasan`), TIDAK memanggil balik `susun_request_atomic_intent()` (M3.4) sendiri, tidak ada mekanisme retry apa pun di dalam milestone ini.

**Catatan Ketergantungan**
Jalur perbaikan (baik ke M3.4 maupun ke Execution `400`) dicatat sebagai follow-up eksplisit di `report.md` — keputusan bentuknya BUKAN milik milestone ini untuk diambil sepihak.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Bangun retry loop bounded (mis. maksimal 2x) memanggil M3.4 ulang dengan `alasan` sebagai feedback** — ditolak, bertentangan langsung dengan redaksi sumber yang eksplisit menyatakan mekanisme ini "perlu disepakati... sebelum diimplementasikan" (belum disepakati bentuknya dengan pemilik `rancangan-execution-interpretation.md`); juga preseden M1.6 retry-dengan-feedback belum terbukti memperbaiki hasil, menambah alasan untuk tidak mengulang pola yang sama tanpa bukti baru.

---

## Keputusan 7: `request` pada Output Selalu Utuh, Tidak Pernah Di-Null-kan atau Dimodifikasi

**Sumber Paksaan**
Redaksi sumber: "menilai ulang" (bukan "merevisi"). Beda eksplisit dari M2.4 (`tegakkan_constraint_cakupan_individu()` menimpa paksa `params`) — M2.4 MENOLAK dengan me-null-kan `request_final` saat `lolos=False`; M3.5 hanya MENDIAGNOSIS, tidak pernah membuang atau mengubah apa yang dinilainya.

**Keputusan yang Diikuti**
`HasilVerifikasiBentukRequest.request: QueryEngineRequest` (non-optional, selalu diisi persis apa yang diterima), terlepas hasil `lolos`/`status` apa pun.

**Catatan Ketergantungan**
Downstream (M4.x, belum dibangun) butuh melihat persis `request` apa yang dinilai — baik untuk logging kasus revisi maupun sebagai referensi kalau jalur perbaikan (Keputusan 6) nanti dibangun.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Ikuti pola `HasilVerifikasiGate` (M2.4), `request=None` saat `lolos=False`** — ditolak, semantik M3.5 beda dari M2.4 (mendiagnosis vs menolak); menghilangkan `request` justru menghilangkan informasi yang paling dibutuhkan untuk kasus revisi.

---

## Keputusan 8: Signature Menerima `atomic_intent`, `view_name_tervalidasi_retriever: str`, `request: QueryEngineRequest` Langsung — Bukan Wrapper `HasilPenyusunanRequest` Penuh

**Sumber Paksaan**
Preseden `susun_request_atomic_intent()` (M3.4 Keputusan 4) — menghindari fungsi harus menangani kasus upstream gagal (`HasilPenyusunanRequest.status=GAGAL_TEKNIS`/`request=None`) yang sebenarnya bukan tanggung jawabnya.

**Keputusan yang Diikuti**
`verifikasi_bentuk_request_atomic_intent(atomic_intent: AtomicIntent, view_name_tervalidasi_retriever: str, request: QueryEngineRequest) -> HasilVerifikasiBentukRequest` — `request` sudah pasti non-`None` (dijamin pemanggil).

**Catatan Ketergantungan**
Pemanggil (M4.x, belum dibangun) yang memutuskan item mana yang benar-benar dikirim ke M3.5 (hanya yang `HasilPenyusunanRequest.status=BERHASIL`) — menjaga ruang status `HasilVerifikasiBentukRequest` tetap bersih, konsisten pola M3.4.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Terima `HasilPenyusunanRequest` penuh, tangani kasus `GAGAL_TEKNIS` internal** — ditolak, akan memaksa `HasilVerifikasiBentukRequest` py nilai status tambahan untuk kasus "upstream M3.4 gagal" yang bukan kegagalan M3.5 sendiri — mengulangi alasan penolakan yang sama persis dengan M3.4 Keputusan 4.

---

## Keputusan 9: Skema `HasilVerifikasiBentukRequest` — Menggabungkan Dua Pola Preseden (`status` Teknis + `lolos`/`alasan` Substantif)

**Sumber Paksaan**
M3.5 py DUA sumber kegagalan berbeda sifat yang perlu dibedakan: (a) kegagalan TEKNIS pemanggilan LLM (API error/empty/parse gagal) — preseden `status: StatusEksekusi` biner (M3.4 Keputusan 6, SATU pemanggilan LLM tanpa semantik batch/parsial); (b) keputusan SUBSTANTIF gate (lolos/tidak beserta alasan) — preseden `lolos: bool` + `alasan_penolakan: str | None` (`HasilVerifikasiGate`, M2.4).

**Keputusan yang Diikuti**
```
class HasilVerifikasiBentukRequest(BaseModel):
    atomic_intent: AtomicIntent
    request: QueryEngineRequest
    status: StatusEksekusi          # BERHASIL | GAGAL_TEKNIS
    lolos: bool | None              # None hanya saat status=GAGAL_TEKNIS
    alasan: str | None              # wajib saat lolos=False, terlarang saat lolos=True
```
Validator tiga-arah: `status=GAGAL_TEKNIS ⟺ lolos is None ∧ alasan is None`; `status=BERHASIL ⟺ lolos is not None`; `lolos=True ⟹ alasan is None`; `lolos=False ⟹ alasan is not None`.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hanya pakai `lolos: bool` seperti `HasilVerifikasiGate`, tanpa `status` teknis terpisah** — ditolak, M2.4 murni deterministik (tidak py mode kegagalan teknis LLM), M3.5 py pemanggilan LLM yang genuinely bisa gagal teknis (API error dst.) — menghilangkan `status` akan memaksa kegagalan teknis disamarkan sebagai `lolos=False` semantik, padahal keduanya perlu dibedakan (kegagalan teknis ≠ keputusan "perlu revisi").

---

## Keputusan 10: Skema Baru Ditambahkan ke `src/schemas/query_engine.py` yang Sudah Ada (Bukan File Baru)

**Sumber Paksaan**
Preseden `src/schemas/retriever.py` (M3.1+M3.2+M3.3 satu file) — "satu file sama, bukan modul terpisah, mirror pola `domain_gate.py`" (`decisions.md` M3.4 Keputusan 6, catatan). Query Engine Langkah 1 (M3.4) dan Langkah 2 (M3.5) adalah satu domain skema yang sama.

**Keputusan yang Diikuti**
`HasilVerifikasiBentukRequest` ditambahkan sebagai kelas baru di `src/schemas/query_engine.py` (file M3.4 yang sudah ada), bukan file terpisah.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **File terpisah `src/schemas/verifikasi_bentuk_request.py`** — ditolak, bertentangan dengan preseden `retriever.py` yang eksplisit sudah menetapkan pola "satu file per komponen arsitektur (Retriever atau Query Engine), bukan per milestone".

---

## Keputusan 11: File Implementasi Baru di Subpackage `src/layers/query_engine/` yang Sudah Ada (Bukan Subpackage Baru)

**Sumber Paksaan**
Framing sumber sendiri sejak M3.4 Keputusan 11: "Query Engine (penyusunan request, verifikasi bentuk request)" sebagai SATU komponen arsitektur dua langkah — subpackage `query_engine/` sudah eksplisit disiapkan untuk menaungi kedua langkah.

**Keputusan yang Diikuti**
`src/layers/query_engine/verifikasi_bentuk_request.py` (baru), di subpackage yang sudah ada (bukan subpackage baru). `DEFINISI_LENGKAP_VIEW`/`CATATAN_LINTAS_DOMAIN` (M3.2, `src/layers/retriever/definisi_view.py`) tetap di-reuse LINTAS subpackage untuk konteks grain view di prompt — konsisten preseden single-source-of-truth yang sudah dipegang M3.3/M3.4.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced langsung oleh keputusan M3.4 yang sudah menetapkan subpackage ini untuk kedua langkah sejak awal.

---

## Keputusan 12: Observability — Span `chat` Literal (Hanya Saat LLM Benar-Benar Dipanggil) + Reuse `REQUEST_DOMAIN`/`REQUEST_VIEW_NAME` + `PROMPT_ID`/`PROMPT_VERSION`

**Sumber Paksaan**
`rancangan-observability-ai-chatbot.md` Bagian 2, baris "Query Engine (Langkah 1 & 2): chat ×2 ... request.domain, request.view_name, prompt.id/prompt.version" — kontrak eksplisit MENCAKUP Langkah 2 (M3.5), atribut yang sama dipakai ulang persis (bukan pasangan atribut baru).

**Keputusan yang Diikuti**
Span dibuka literal `"chat"` (hanya saat pre-check Kriteria 1 lolos, Keputusan 3). Atribut: `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens`, `PROMPT_ID`/`PROMPT_VERSION` (M3.4, reuse), `REQUEST_DOMAIN`/`REQUEST_VIEW_NAME` (M3.4, reuse — TIDAK perlu konstanta baru).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced kontrak observability + preseden konstanta M3.4 yang sudah eksplisit dirancang untuk dipakai KEDUA langkah Query Engine sejak awal.

---

## Keputusan 13: Orkestrator Batch `verifikasi_bentuk_request_semua()` dengan Span Pembungkus Non-LLM

**Sumber Paksaan**
Preseden konsisten seluruh layer LLM proyek yang memproses banyak item per turn — `nilai_kecocokan_makna_semua()` (M3.2), `identifikasi_domain_semua()` (M2.1), `deteksi_constraint_semua()` (M2.3), dst. — satu span pembungkus per turn mencatat statistik agregat.

**Keputusan yang Diikuti**
`verifikasi_bentuk_request_semua(daftar) -> list[HasilVerifikasiBentukRequest]` membungkus span non-LLM `query_engine.verifikasi_bentuk_request_semua`, atribut agregat `lolos_count`/`perlu_revisi_count`/`gagal_teknis_count`.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tanpa orkestrator batch, biarkan pemanggil (M4.x) melakukan loop sendiri** — ditolak, bertentangan dengan preseden konsisten SELURUH milestone LLM lain proyek ini yang selalu menyediakan fungsi `_semua()` sebagai kontrak layer, bukan mendelegasikan loop+span agregat ke pemanggil.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Mekanisme HYBRID: pre-check deterministik + satu LLM | B | Checkpoint 4 |
| 2 | Pre-check Kriteria 1: perbandingan string sederhana | B | Checkpoint 4 |
| 3 | Pre-check gagal → short-circuit, tanpa span `chat` | B | Checkpoint 4 |
| 4 | Satu pemanggilan LLM Kriteria 2, tanpa retry/verifier kedua | B | Checkpoint 4 |
| 5 | Model: DeepSeek V4 Pro `reasoning="high"`, konstanta terisolasi | B | Checkpoint 3 |
| 6 | Tidak ada retry/jalur perbaikan balik ke M3.4 | B | Checkpoint 4 |
| 7 | `request` output selalu utuh, tidak pernah di-null-kan | B | Checkpoint 2 |
| 8 | Signature menerima `view_name`/`request` langsung, bukan wrapper penuh | B | Checkpoint 4 |
| 9 | Skema gabungan `status` teknis + `lolos`/`alasan` substantif | B | Checkpoint 2 |
| 10 | Skema baru di `src/schemas/query_engine.py` yang sudah ada | B | Checkpoint 2 |
| 11 | File implementasi baru di subpackage `query_engine/` yang sudah ada | B | Checkpoint 4 |
| 12 | Observability: span `chat` + reuse `REQUEST_DOMAIN`/`REQUEST_VIEW_NAME` | B | Checkpoint 3-4 |
| 13 | Orkestrator batch `verifikasi_bentuk_request_semua()` | B | Checkpoint 4 |
