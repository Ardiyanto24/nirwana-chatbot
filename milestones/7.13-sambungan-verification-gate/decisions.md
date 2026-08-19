# Decisions — Milestone 7.13: Sambungan 8 (Query Engine → Verification Gate)

Dokumen ini mencatat keputusan desain untuk Milestone 7.13, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: Fungsi batch baru mengembalikan `list[tuple[AtomicIntent, HasilVerifikasiGate]]`, tanpa skema baru

**Status:** Diputuskan sebelum implementasi (dari plan)

**Latar Belakang**
`HasilVerifikasiGate` (M2.4, `src/schemas/verification_gate.py`) TIDAK membawa field `atomic_intent` sama sekali — satu-satunya skema hasil layer di seluruh project yang tidak menyimpan identitas atomic_intent-nya sendiri (berbeda dari `HasilKecukupanStruktural`, `HasilPenyusunanRequest`, `HasilVerifikasiBentukRequest`, `AtomicIntentDomains`, `AtomicIntentAuthorization`, `AtomicIntentConstraint` — semua membawa field ini). M2.4 dibangun sebelum orkestrasi Level 2 (M7.x) dipikirkan, jadi tidak dirancang untuk konteks batch. Fungsi batch baru M7.13 genuinely butuh mengembalikan asosiasi atomic_intent-nya sendiri (M7.14 nanti perlu tahu request final milik atomic_intent mana untuk penulisan Session Memory) — genuinely terbuka: bungkus tuple apa adanya, atau tambah skema baru bernama.

**Keputusan yang Dipilih**
`verifikasi_gate_semua() -> list[tuple[AtomicIntent, HasilVerifikasiGate]]` — `AtomicIntent` PENUH (bukan cuma ID), TIDAK ada skema baru ditambahkan ke `src/schemas/verification_gate.py`.

**Alasan**
Konsisten preferensi user di M7.12 (Keputusan 1 milestone itu) untuk kasus serupa (fan-out data lewat tuple, bukan skema baru) — mekanisme itu sudah terbukti tidak menyulitkan di titik konsumsi pertamanya. `AtomicIntent` penuh (bukan sekadar `atomic_intent_id` string) dipilih supaya M7.14 langsung punya akses `teks_kebutuhan`/`label_bentuk_jawaban` tanpa perlu lookup balik ke list lain.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Skema baru bernama** (mis. `class AtomicIntentVerifikasiGate(BaseModel): atomic_intent: AtomicIntent; hasil: HasilVerifikasiGate`) — dipertimbangkan karena lebih self-documenting, tapi ditolak: kasus ini (field yang genuinely hilang dari skema aslinya) tetap tidak dinilai user cukup berbeda dari M7.12 untuk menyimpang dari preferensi nol-skema-baru yang sudah dikonfirmasi.

**Dampak**
M7.14 (Sambungan 9: Verification Gate → Execution) akan mengonsumsi `KeadaanTurn.verification_gate` dalam bentuk tuple ini.

---

### Keputusan 2: Item `HasilVerifikasiBentukRequest.lolos=False` di-SKIP dari pemanggilan Verification Gate

**Status:** Diputuskan sebelum implementasi (dari plan)

**Latar Belakang**
`verifikasi_gate()` menerima `request: QueryEngineRequest` (non-Optional) — untuk item dengan `hasil_verifikasi.lolos=False` (M3.5 bilang bentuk jawaban tidak cukup, mis. tren tapi rentang tanggal cuma 1 hari), `hasil_verifikasi.request` TETAP ADA (skema M3.5: "request SELALU utuh, bukan Optional, M3.5 mendiagnosis bukan merevisi/menolak") — jadi secara struktur `verifikasi_gate()` BISA dipanggil untuk item ini, TIDAK forced-skip seperti kasus `hasil_verifikasi is None` (M3.4 gagal total, benar-benar tidak ada request). Genuinely terbuka: teruskan ke Verification Gate juga (murni wiring, tidak membuat keputusan semantik baru) atau skip di titik ini (Verification Gate murni struktural/RBAC, KK-nya tidak menyentuh bentuk jawaban).

**Keputusan yang Dipilih**
`verifikasi_gate_semua()` memfilter `query_engine_result` ke item `hasil_verifikasi is not None AND hasil_verifikasi.lolos is True` SEBELUM memanggil `verifikasi_gate()`.

**Alasan**
Meneruskan request yang sudah ditandai Query Engine sendiri (M3.5) sebagai TIDAK CUKUP untuk bentuk jawaban yang diminta berisiko Execution "berhasil" (200 dari `chatbot_api`, yang tidak tahu apa-apa soal `label_bentuk_jawaban`) dengan data yang genuinely tidak menjawab kebutuhan asli — bertentangan dengan prinsip "Kejujuran terhadap keterbatasan" (`CLAUDE.md`: status non-normal/hasil parsial harus selalu tersurat, tidak disamarkan demi jawaban yang terlihat lengkap). Nasib item `lolos=False` (retry via feedback loop, atau dilaporkan sebagai kegagalan) diserahkan ke milestone lain (M7.14+) — M7.13 hanya memastikan item semacam ini tidak diam-diam lolos ke Execution seolah valid.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Teruskan semua item yang py `request` (termasuk `lolos=False`), hanya skip `hasil_verifikasi is None`** — dipertimbangkan karena menjaga M7.13 murni wiring tanpa keputusan semantik baru (Verification Gate toh tidak membaca `lolos`), tapi ditolak user demi mencegah risiko data tidak sesuai kebutuhan lolos diam-diam ke Execution.

**Dampak**
`KeadaanTurn.verification_gate` bisa lebih pendek dari `KeadaanTurn.query_engine` karena DUA alasan sekarang (bukan cuma satu seperti M7.12): item `hasil_verifikasi is None` DAN item `lolos=False`.

---

### Keputusan 3: Fungsi batch baru `verifikasi_gate_semua()` ditempatkan di `src/layers/verification_gate/verifikasi_gate.py`

**Sumber Paksaan**
Preseden M7.11 Keputusan 3 dan M7.12 Keputusan 2 (fungsi batch baru hidup di layer package sendiri, bukan inline `turn_pipeline.py`) — dikonfirmasi user eksplisit DUA KALI berturut-turut di dua milestone terakhir.

**Keputusan yang Diikuti**
Fungsi baru ditambahkan di `src/layers/verification_gate/verifikasi_gate.py` (file yang sama dengan `verifikasi_gate()`, M2.4).

**Catatan Ketergantungan**
Tidak ada alasan untuk menyimpang dari preseden yang baru saja dikonfirmasi 2x berturut-turut tanpa perubahan konteks yang relevan.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden ganda M7.11+M7.12 — tidak diajukan ulang ke user.

---

### Keputusan 4: Item dengan `hasil_verifikasi is None` di-SKIP

**Sumber Paksaan**
Signature `verifikasi_gate(request: QueryEngineRequest, ...)` (non-Optional) — untuk item `hasil_verifikasi is None` (M3.4 gagal total, `susun_dan_verifikasi_request_atomic_intent()` return `(hasil_susun, None)`), TIDAK ADA `request` sama sekali untuk dievaluasi.

**Keputusan yang Diikuti**
Filter internal `verifikasi_gate_semua()` mengecualikan item ini sebelum memanggil `verifikasi_gate()` — mirror kondisi forced yang sama persis dengan M7.12 Keputusan 4 (item `view_name_final=None`, Retriever tidak menemukan view cukup).

**Catatan Ketergantungan**
Tidak ada cara aman memanggil `verifikasi_gate()` tanpa `request` — forced murni oleh ketiadaan data, bukan pilihan gaya.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by ketiadaan data valid.

---

### Keputusan 5: `view_name_tervalidasi_retriever` diambil dari `retriever_result[i].view_name_final` (sumber independen), BUKAN dari `hasil_verifikasi.request.view_name`

**Sumber Paksaan**
Tujuan Cek 2 M2.4 (`verifikasi_kepatuhan_sumber()`) sendiri: memverifikasi `view_name` yang akan dikirim BENAR-BENAR sama dengan yang divalidasi Retriever — sebuah pengecekan yang HANYA bermakna kalau kedua nilai berasal dari sumber yang genuinely independen. Kalau `view_name_tervalidasi_retriever` diisi dari `hasil_verifikasi.request.view_name` (yaitu, nilai yang SAMA dengan `request.view_name` yang sedang diperiksa), Cek 2 jadi tautologi (`x == x`, selalu `True` tanpa mendeteksi apa pun) — mirror persis alasan M7.4 mempertahankan parameter `view_name_tervalidasi_retriever` terpisah dari `view_name` di `susun_dan_verifikasi_request_atomic_intent()` (`milestones/7.4-.../decisions.md` Keputusan 3).

**Keputusan yang Diikuti**
`verifikasi_gate_semua()` mengambil `view_name_final` dari `retriever_result` (dicocokkan via `atomic_intent_id`), BUKAN dari `request.view_name` milik hasil Query Engine yang sedang diperiksa.

**Catatan Ketergantungan**
Melanggar ini akan membuat Cek 2 M2.4 kehilangan maknanya sebagai pemeriksaan independen — konsisten prinsip "generate lalu verify, independen" (`CLAUDE.md` Prinsip Arsitektur).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Reuse `request.view_name` langsung (tanpa fetch ulang ke `retriever_result`)** — ditolak: membuat Cek 2 M2.4 tautologis, forced by tujuan pemeriksaan itu sendiri.

---

### Keputusan 6: `constraint` diekstrak sebagai `cakupan_individu_result[i].constraint` (tipe `ConstraintCakupanIndividu`), bukan `AtomicIntentConstraint` wrapper-nya

**Sumber Paksaan**
Signature `verifikasi_gate(constraint: ConstraintCakupanIndividu, ...)` — `AtomicIntentConstraint` (M2.3/M7.11) adalah WRAPPER yang membawa `atomic_intent` + `domain_decisions` + `constraint: ConstraintCakupanIndividu` — bukan tipe yang sama.

**Keputusan yang Diikuti**
`verifikasi_gate_semua()` mengambil `.constraint` dari elemen `AtomicIntentConstraint` yang cocok (via `atomic_intent_id`) sebelum meneruskannya ke `verifikasi_gate()`.

**Catatan Ketergantungan**
Meneruskan `AtomicIntentConstraint` utuh akan menyebabkan `TypeError`/kegagalan validasi type-hint — forced murni oleh mismatch tipe.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by signature.

---

### Keputusan 7: Pencocokan `query_engine_result`/`retriever_result`/`cakupan_individu_result` dilakukan via `atomic_intent_id`, bukan index list

**Sumber Paksaan**
Ketiga list berpotensi py PANJANG BERBEDA per konstruksi pipeline: `cakupan_individu_result` (M7.11, tidak difilter dari `otorisasi_result`) == `retriever_result` (M7.11, `proses_retrieval_semua()` memproses SEMUA `cakupan_individu_result` tanpa filter, 1:1) ⊇ `query_engine_result` (M7.12, difilter ke `view_name_final is not None`). Mengasumsikan ketiganya sejajar by index akan salah begitu ADA satu item saja yang difilter di titik manapun sepanjang rantai.

**Keputusan yang Diikuti**
Bangun lookup dict `retriever_by_id`/`constraint_by_id` (key: `atomic_intent_id`) di awal `verifikasi_gate_semua()`, iterasi `query_engine_result` sebagai basis (list terpendek/paling terfilter), lookup dua sumber lain per item.

**Catatan Ketergantungan**
Pencocokan by-index akan salah mengambil data milik atomic_intent LAIN begitu ada divergensi panjang — bug senyap yang sulit terdeteksi tanpa test eksplisit (lihat Risiko & Mitigasi Plan).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Asumsikan ketiga list sejajar by index** — ditolak: forced salah oleh konstruksi pipeline sendiri begitu ada filtering di titik manapun sebelumnya (M7.10 `domain_gate`, M7.11 `otorisasi`, M7.12 `query_engine` — seluruhnya sudah terbukti bisa lebih pendek dari input masing-masing).

---

### Keputusan 8: `employee_id` diambil dari `payload.employee_id`

**Sumber Paksaan**
`TurnPayload.employee_id: str` (sudah tervalidasi sejak M1.2) — satu-satunya sumber employee_id pemanggil di seluruh alur `proses_turn()`, sudah dipakai pola serupa untuk `role_title` di M7.11 Keputusan 5.

**Keputusan yang Diikuti**
`verifikasi_gate_semua(..., employee_id: str)` dipanggil dengan `payload.employee_id`, diteruskan sebagai skalar yang SAMA untuk seluruh item dalam satu turn (satu turn = satu pemanggil).

**Catatan Ketergantungan**
Tidak ada sumber employee_id lain yang valid di titik ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kontrak `TurnPayload` yang sudah final.

---

### Keputusan 9: `KeadaanTurn` bertambah field `verification_gate`, non-Optional, panjang bisa lebih pendek dari `query_engine`

**Sumber Paksaan**
Preseden konsisten M7.6-7.12 (tiap unit tersambung dapat field sendiri). `verifikasi_gate_semua()` tidak pernah raise (fungsi murni deterministik, tanpa LLM, tanpa I/O eksternal selain span).

**Keputusan yang Diikuti**
`verification_gate: list[tuple[AtomicIntent, HasilVerifikasiGate]]` — wajib tanpa default.

**Catatan Ketergantungan**
Panjang bisa lebih pendek dari `query_engine` karena DUA sumber filter (Keputusan 2+4 di atas) — bukan indikasi kegagalan.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden M7.6-7.12.

---

### Keputusan 10: Span pembungkus `verifikasi_gate_semua()` dengan atribut `intent.count`

**Sumber Paksaan**
Preseden SEKARANG 6-7x konsisten di seluruh project: `identifikasi_domain_semua`, `periksa_otorisasi_semua`, `deteksi_constraint_semua`, `proses_retrieval_semua` (M7.11), `susun_dan_verifikasi_request_semua` (M7.12), `verifikasi_bentuk_request_semua` (M3.5, existing).

**Keputusan yang Diikuti**
Span baru dibuka (nama mengikuti pola `verification_gate.verifikasi_gate_semua`), tracer sudah didefinisikan di `verifikasi_gate.py` (`_TRACER_NAME = "verification_gate.verifikasi_gate"`), atribut `intent.count` = panjang `query_engine_result` SEBELUM filter.

**Catatan Ketergantungan**
Tidak ada atribut lain yang perlu — kontrak observability Verification Gate (`verification.check_name`, `error.type`, `verification_gate.lolos`/`terkoreksi`) sudah lengkap di span existing per item.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by pola konsisten 6-7x preseden.

---

### Keputusan 11: Tidak ada instrumentasi span baru di luar wrapping span `_semua()`

**Sumber Paksaan**
`rancangan-orkestrasi-api.md` baris 10: "observability lintas-layer di luar span pembungkus sudah tercakup instrumentasi masing-masing PIC 1-4".

**Keputusan yang Diikuti**
M7.13 murni wiring — tidak menambah atribut/span baru di `verifikasi_gate.py` logic internal (Cek 1-4).

**Catatan Ketergantungan**
Menambah instrumentasi baru di logic internal M2.4 akan melanggar batasan "Tidak termasuk: Logic internal kesembilan layer... memanggil mekanisme yang sudah ada, bukan menulis ulang."

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by batasan dokumen sumber.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Bentuk return batch (tuple, tanpa skema baru) | A | Plan |
| 2 | Item `lolos=False` di-skip | A | Plan |
| 3 | Fungsi batch baru di `verifikasi_gate.py` | B | Plan |
| 4 | Item `hasil_verifikasi is None` di-skip | B | Plan |
| 5 | `view_name_tervalidasi_retriever` dari `retriever_result`, bukan tautologi | B | Plan |
| 6 | `constraint` diekstrak dari `AtomicIntentConstraint.constraint` | B | Plan |
| 7 | Pencocokan via `atomic_intent_id`, bukan index | B | Plan |
| 8 | `employee_id` dari `payload.employee_id` | B | Plan |
| 9 | Field `verification_gate` non-Optional, bisa lebih pendek | B | Plan |
| 10 | Span pembungkus `intent.count` | B | Plan |
| 11 | Tidak ada instrumentasi span baru | B | Plan |
