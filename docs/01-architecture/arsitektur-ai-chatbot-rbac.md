# Arsitektur AI Chatbot — Nirwana Hospitality Group

> Dokumen ini mengunci hasil diskusi arsitektur end-to-end untuk sistem AI
> Chatbot RBAC — portofolio AI/ML Engineer. Merevisi total dokumen
> `Workflow-Per-Layer.md` (versi 822 kolom/SQL generation) berdasarkan
> perubahan fundamental: serving layer sekarang berupa 67 view melalui
> REST API (`chatbot_api`, sudah selesai & terverifikasi), bukan akses SQL
> langsung ke database mentah.
>
> Status tiap bagian ditandai eksplisit: **[SOLID]** = sudah dibahas
> mendalam dan disepakati, **[KERANGKA AWAL]** = arah sudah disepakati
> tapi detail teknis belum digodok, layak didiskusikan lebih lanjut
> sebelum diimplementasi.

---

## 1. Prinsip Fondasi (tidak berubah dari desain awal)

1. **AI hanya penulis rencana, bukan pengeksekusi langsung** — di dunia baru
   ini, "menulis SQL" berubah jadi "menyusun HTTP request", tapi prinsipnya
   sama: setiap rencana wajib lewat gerbang verifikasi non-AI sebelum
   benar-benar memanggil `chatbot_api`.
2. **Defense-in-depth** — sistem ini adalah **Lapis 1** dari RBAC dua lapis.
   **Lapis 2** adalah `chatbot_api` (eksternal, sudah selesai) yang
   menegakkan otorisasi domain (`role_permissions`) dan resolusi
   `property_id` dari `employee_id` secara independen dari kode AI kita.
   Lapis 1 tidak boleh dianggap "opsional karena Lapis 2 sudah menjaga" —
   perannya beda: Lapis 2 menjaga *data* tidak bocor secara teknis, Lapis 1
   menjaga *pemahaman* tidak pernah salah sejak niatnya.
3. **Generate lalu verify, independen** — dipertahankan di setiap titik
   yang keputusannya masih melibatkan pemahaman *makna/maksud* bahasa.
   **Prinsip baru hasil diskusi**: verifikasi boleh berubah jadi murni
   deterministik (tanpa LLM) **hanya jika** seluruh ruang kesalahan yang
   mungkin terjadi bisa didaftar sebagai aturan eksplisit di depan (ruang
   kesalahan *tertutup*). Kalau verifikasi itu masih menyentuh "apakah ini
   sungguh merepresentasikan maksud" (ruang kesalahan *terbuka*, tak
   terduga sebelumnya), LLM independen tetap wajib dipertahankan.
4. **Kejujuran terhadap keterbatasan** — status non-normal, hasil parsial,
   penolakan, kegagalan teknis harus selalu tersurat ke user, tidak pernah
   disamarkan demi jawaban yang terlihat lengkap.

---

## 2. Fondasi Eksternal (di luar scope kode ini, tapi menentukan desainnya)

```
Production DB → BigQuery (raw → mart_cleaned → mart_aggregated)
                        │  reverse ETL
                        ▼
              PostgreSQL Serving Layer (chatbot_views, 67 view)
                        │
                        ▼
              chatbot_api — GET /chatbot/{domain}/{view_name}
              [SELESAI, terverifikasi KK1-3]
                        │
                        ▼
              ═══ AI Chatbot (sistem yang dirancang di dokumen ini) ═══
```

**Yang sudah ditegakkan `chatbot_api` secara independen (Lapis 2):**
- `role_title` divalidasi terhadap `role_permissions` sebelum query apa pun jalan (403 kalau gagal)
- `view_name` harus ada di whitelist per domain (404 kalau tidak)
- `access_scope == own_property` → `property_id` yang diklaim caller **diabaikan**, di-resolve ulang dari `employee_id` (klaim tidak pernah dipercaya)
- `access_scope == all_properties` → `property_id` dipakai sebagai filter opsional
- `role_permissions` sendiri **tidak pernah** punya endpoint (404 struktural, bukan ditolak runtime)

**Konsekuensi ke desain AI Chatbot:**
- Tidak ada SQL yang ditulis sistem ini — output akhir adalah `{domain, view_name, params}`
- Row-level security untuk `property_id` **sepenuhnya didelegasikan** ke Lapis 2 — sistem ini tidak perlu menyuntik filter property
- Satu gap yang **tidak** dijamin Lapis 2: cakupan *individu dalam satu properti* (mis. Staff hanya boleh lihat data performanya sendiri, bukan staff lain) — ini jadi tanggung jawab Lapis 1 (lihat §4, Domain Gate & Verification Gate)

---

## 3. Peta Layer (9 layer, penomoran final)

| # | Nama | Peran singkat |
|---|---|---|
| 1 | Input Layer | Validasi kontrak payload, murni mekanis |
| 2 | Context Resolution | Deteksi ketergantungan turn + rewrite mandiri |
| 3 | Decomposition | Klasifikasi + pemecahan atomik + verifikasi |
| 4 | Domain Gate | Otorisasi domain berbasis pemahaman maksud |
| 5 | Retriever | Pilih `view_name` yang tepat dari katalog |
| 6 | Query Engine | Susun `{domain, view_name, params}` |
| 7 | Verification Gate | Tegakkan konsistensi otorisasi vs request final |
| 8 | Execution | Panggil `chatbot_api`, klasifikasi respons |
| 9 | Interpretation | Susun narasi jawaban akhir |

---

## 4. Fase 1 — Pra-Eksekusi **[SOLID, dengan satu titik KERANGKA AWAL]**

```
Frontend → payload: session_id, turn_index, role_title, employee_id,
           teks pertanyaan turn ini, (+ seluruh histori turn-turn
           sebelumnya dalam sesi — turn 1 s.d. turn_index-1, masing-
           masing dengan turn_index, teks pertanyaan & jawabannya —
           kalau turn_index > 1)
           [Direvisi di Milestone 1.3: desain awal hanya membawa SATU
           turn sebelumnya (N-1), tapi Kriteria Keberhasilan Milestone
           1.3 menuntut deteksi rujukan ke turn yang jauh lebih lama
           (bukan cuma N-1) — sementara Langkah 2 di titik ini belum
           boleh membaca session memory, sehingga histori penuh di
           payload adalah satu-satunya sumber data yang memungkinkan
           deteksi itu. Lihat milestones/1.3-pemetaan-ketergantungan-
           turn/decisions.md untuk kronologi lengkap.]
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ 1. Input Layer                                              │
│    Validasi field wajib. Murni mekanis, TANPA LLM.             │
│    Turn yang perlu diproses = turn terakhir dalam payload —       │
│    otomatis jelas dari bentuk payload, tidak perlu deteksi.          │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ 2. Pemetaan Ketergantungan Turn  ← LLM                        │
│    Deteksi: apakah turn terakhir bergantung ke turn LAIN           │
│    dalam sesi ini (tidak harus turn tepat sebelumnya)?                │
│    Output kalau bergantung: {session_id, turn_index} yang dirujuk.       │
│    TIDAK menghasilkan atomic_intent_id — LLM di titik ini BELUM              │
│    pernah membaca isi session memory, memaksa ID spesifik di sini              │
│    membuka risiko halusinasi.                                                    │
└───────────────────────────────────────────────────────┘
        │
        ├─────────────────────────────┬─────────────────────────┐
        ▼                             ▼                         
┌──────────────────────┐   ┌──────────────────────────┐
│ 3a. Rewrite Jadi Mandiri  │   │ 3b. Tarik Data dari Session   │
│     ← LLM                    │   │     Memory                       │
│                                  │   │     (deterministik / tool call,      │
│ Input: teks turn terakhir          │   │     berdasar {session_id,               │
│ TIDAK peduli apakah nanti              │   │     turn_index} dari Langkah 2)            │
│ datanya sudah tersedia di                  │   │                                                │
│ memory atau belum — murni                      │   │ Output: daftar atomic intent + nilai +            │
│ linguistik, hasilkan kalimat                       │   │ status + catatan_interpretasi dari turn               │
│ yang berdiri sendiri                                   │   │ yang dirujuk. DITAHAN, belum dipakai apa-apa.             │
└──────────────────────┘   └──────────────────────────┘
        │                                                             │
        ▼                                                             │  (menunggu,
┌───────────────────────────────────────────────────┐             │   TIDAK digabung
│ 4. Klasifikasi Kebutuhan  ← LLM                          │             │   prematur —
│    Tunggal / majemuk-independen / majemuk-bergantung        │             │   mencegah
└───────────────────────────────────────────────────┘             │   "context bleed")
        │                                                             │
        ▼                                                             │
┌───────────────────────────────────────────────────┐             │
│ 5. Pemecahan Atomik  ← LLM                                │             │
│    Pecah jadi atomic intent + relasi + label bentuk jawaban    │             │
└───────────────────────────────────────────────────┘             │
        │                                                             │
        ▼                                                             │
┌───────────────────────────────────────────────────┐             │
│ 6. Verifikasi Pemecahan  ← LLM, independen dari Langkah 5      │             │
└───────────────────────────────────────────────────┘             │
        │                                                             │
        └─────────────────────────┬───────────────────────────────────┘
                                   ▼
        ┌───────────────────────────────────────────────┐
        │ 7. Pencocokan Atomic Intent × Data Memory   [KERANGKA AWAL] │
        │    Cocokkan atomic intent hasil Langkah 5-6 terhadap          │
        │    daftar dari 3b. Mekanisme pencocokan (semantik? by          │
        │    label? ambang kecocokan?) BELUM digodok detail.               │
        └───────────────────────────────────────────────┘
                    │
                    ├─ COCOK → status "selesai", bawa nilai+status
                    │   +catatan_interpretasi+sumber ke Fase 3
                    │
                    └─ TIDAK COCOK → status "perlu eksekusi" → Fase 2
```

---

## 5. Fase 2 — Eksekusi Domain **[SOLID]**
*(hanya untuk atomic intent berstatus "perlu eksekusi"; berjalan per wave
untuk kebutuhan yang saling bergantung dalam satu turn, sama seperti
desain wave original)*

```
┌───────────────────────────────────────────────────┐
│ 8. Domain Gate                                          │
│    • Identifikasi domain (LLM) + verifikasi titik buta (LLM,   │
│      independen) — termasuk domain yang "bocor" lewat kolom       │
│      turunan (mis. gop_margin di view domain reservation)            │
│    • Pemeriksaan otorisasi (deterministik, lookup role_permissions)     │
│    • Deteksi constraint cakupan-individu (mis. Staff → wajib filter        │
│      staff_id=self untuk view performa individu) — DICATAT sebagai            │
│      metadata, bukan ditegakkan di sini                                          │
│    → domain ditolak → REJECT, status "ditolak_otorisasi"                            │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│ 9. Retriever                                             │
│    Kandidat luas (pencarian semantik atas 67 view) →           │
│    kecocokan makna → kecukupan struktural (grain view vs             │
│    label bentuk jawaban)                                                │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│ 10. Query Engine                                          │
│     Langkah 1 (LLM) — susun {domain, view_name, params}          │
│     Langkah 2 (LLM, TETAP — bukan deterministik: masih soal           │
│     kesesuaian MAKNA, ruang kesalahan terbuka)                            │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│ 11. Verification Gate  (deterministik, TANPA LLM —              │
│     ruang kesalahan tertutup: kepatuhan struktural murni)              │
│     • Validasi bentuk request statis                                     │
│     • Kepatuhan sumber (view_name cocok hasil Retriever)                    │
│     • Penegakan constraint cakupan-individu (dari Domain Gate)                 │
│     • Verifikasi kelengkapan penegakan                                            │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│ 12. Execution                                             │
│     Panggil chatbot_api. Klasifikasi respons:                    │
│     • 200 → kumpulkan hasil, status "berhasil"/"sebagian"            │
│     • 400 → kirim balik ke Query Engine (mode perbaikan)                │
│     • 5xx/timeout → retry sama persis (infrastruktural)                    │
│     • 403/404 → ESKALASI LANGSUNG, status "gagal_teknis", TANPA               │
│       retry — deterministik terhadap isi request, retry sia-sia dan              │
│       berisiko terlihat seperti percobaan brute-force; sinyal bug                    │
│       audit prioritas tinggi (L4/Domain Gate atau L5/Retriever gagal)                   │
└───────────────────────────────────────────────────┘
        │
        ▼
   Simpan paket ke Session Memory:
   { atomic_intent_id, session_id, turn_index, teks_kebutuhan,
     label_bentuk_jawaban, nilai_hasil, catatan_interpretasi,
     status, sumber: "eksekusi_baru" }
```

---

## 6. Fase 3 — Interpretation **[SOLID]**

```
Menerima CAMPURAN paket berskema SAMA, diperlakukan IDENTIK
terlepas dari asal:
  • dari Fase 1 Langkah 7 → sumber: "session_memory (turn N)"
  • dari Fase 2                → sumber: "eksekusi_baru"
        │
        ▼
┌───────────────────────────────────────────────────┐
│ 13. Penyusunan Narasi  ← LLM                             │
│     5 instruksi wajib (jujur soal status non-normal, hasil          │
│     parsial, ditolak/gagal secara eksplisit, tidak ada klaim              │
│     sebab-akibat dari korelasi, kebutuhan terblokir ketergantungan            │
│     disampaikan spesifik) + narasi lintas-turn yang jujur (pakai              │
│     field "sumber" untuk bedakan nada kalimat, mis. "dibanding X                  │
│     yang sudah dihitung sebelumnya...")                                              │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│ 14. Verifikasi Kesetiaan Data  ← LLM, independen dari Langkah 13 │
└───────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│ 15. Penyusunan Data Visualisasi  (deterministik)         │
└───────────────────────────────────────────────────┘
        │
        ▼
Jawaban akhir → frontend
   + paket hasil SEMUA atomic intent turn ini disimpan permanen
     ke Session Memory (untuk dirujuk turn-turn berikutnya)
```

---

## 7. Bentuk Data Kunci

### Paket Session Memory (per atomic intent)
```
{
  atomic_intent_id: string,
  session_id: string,
  turn_index: int,
  teks_kebutuhan: string,
  label_bentuk_jawaban: "nilai_tunggal" | "tren" | "perbandingan"
                         | "peringkat" | "komposisi",
  nilai_hasil: object,              // data terstruktur, bukan teks
  catatan_interpretasi: string[],   // pola nullable-bermakna, dsb —
                                     // BUKAN dari API otomatis, tapi dari
                                     // pengetahuan yang ditempel ke katalog
  status: "berhasil" | "sebagian" | "ditolak_otorisasi" | "gagal_teknis"
          | "terblokir_ketergantungan",
  sumber: "eksekusi_baru" | "session_memory (turn N)"
}
```

---

## 8. Bagian yang Masih Terbuka untuk Didalami

Ditulis eksplisit supaya tidak diam-diam dianggap selesai:

1. **Langkah 7 (Pencocokan Atomic Intent × Data Memory)** — mekanisme
   pencocokan belum ditentukan: apakah perlu LLM (pencocokan semantik,
   karena teks atomic intent hasil rewrite belum tentu identik string-nya
   dengan teks_kebutuhan yang tersimpan), atau bisa deterministik dengan
   bantuan struktur tambahan dari Langkah 2.
2. **Bentuk konkret "tools" penarik data session memory (3b)** — teknologi
   penyimpanan, skema lookup key, TTL/masa berlaku entri.
3. **Daftar eksplisit view kategori "cakupan-individu"** — sengaja belum
   dibahas (keputusan teknis, disepakati untuk didiskusikan belakangan).
4. **Model per langkah, provider routing (Claude Console / OpenRouter)** —
   belum ditentukan.
5. **Skema parameter per `view_name`** (whitelist_<domain>.py) — perlu
   dibaca detail sebelum Retriever & Query Engine bisa diimplementasi.

---

## 9. Prinsip Baru yang Lahir dari Diskusi Ini

Layak dicatat sebagai kontribusi tersendiri di luar "Prinsip yang
Berulang" dokumen asli:

> **Kesempitan permukaan tugas tidak otomatis mengizinkan verifikasi
> deterministik.** Yang menentukan adalah apakah seluruh ruang kesalahan
> yang mungkin terjadi bisa didaftar sebagai aturan eksplisit di depan
> (tertutup → boleh deterministik) atau masih menyentuh soal kesesuaian
> makna/maksud yang tak terduga bentuknya (terbuka → wajib LLM independen).
> Ini yang membedakan kenapa Verification Gate (langkah 11) boleh
> sepenuhnya deterministik sementara Query Engine langkah 2 (langkah 10)
> tetap mempertahankan LLM, meski dua-duanya kelihatan "sederhana" di
> permukaan setelah pergeseran dari SQL ke HTTP request.
