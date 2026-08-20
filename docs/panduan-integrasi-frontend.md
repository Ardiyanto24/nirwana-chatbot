# Panduan Integrasi Frontend — Endpoint API AI Chatbot RBAC

**AI Chatbot RBAC — Nirwana Hospitality Group**

Dokumen ini untuk tim/pihak yang membangun antarmuka (frontend) yang mengonsumsi endpoint HTTP sistem ini. Bukan dokumen arsitektur internal — cukup dibaca untuk tahu **cara memanggil endpoint dan cara menampilkan responsnya**, tanpa perlu paham sembilan layer pemrosesan di baliknya.

**Beda dari `docs/03-domain-source/api-chatbot.md`**: dokumen itu tentang API Lapis 2 (`chatbot_api`) yang DIKONSUMSI sistem ini secara internal (bukan untuk frontend). Dokumen ini tentang API yang sistem ini SEDIAKAN untuk Anda.

---

## 1. Ringkasan Endpoint

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/v1/turns` |
| **Base URL (pengembangan lokal)** | `http://127.0.0.1:8001` |
| **Content-Type** | `application/json` |
| **Autentikasi** | **Belum ada** di lapisan HTTP ini — di luar cakupan saat ini (lihat `milestones/7.17-membangun-endpoint-api/decisions.md` Keputusan 10). RBAC ditegakkan INTERNAL berdasarkan `role_title`/`employee_id` yang Anda kirim di body — jangan mengekspos endpoint ini langsung ke publik tanpa lapisan otentikasi/gateway tambahan di depannya. |

Menjalankan server secara lokal (untuk development/testing):

```bash
uv run uvicorn src.main:app --port 8001
```

(Port 8000 dipakai layanan lain — jangan dipakai untuk app ini.)

---

## 2. Bentuk Request

Body JSON dengan field berikut (skema `TurnPayload`, `src/schemas/turn_payload.py`):

| Field | Tipe | Wajib? | Keterangan |
|---|---|---|---|
| `session_id` | string | Ya | Identitas sesi percakapan — sama untuk seluruh turn dalam satu percakapan. |
| `turn_index` | integer (≥1) | Ya | Nomor urut turn dalam sesi ini, mulai dari 1. |
| `role_title` | string | Ya | Peran pengguna (mis. `"General Manager"`, `"Front Office Staff"`) — menentukan data apa yang boleh diakses. Harus salah satu nilai yang dikenal sistem (nilai tidak dikenal ditolak, lihat Bagian 4). |
| `employee_id` | string | Ya | Identitas karyawan pemanggil — dipakai untuk membatasi cakupan data individu (mis. staf hanya melihat datanya sendiri). |
| `question` | string | Ya | Pertanyaan pengguna dalam bahasa natural. |
| `history` | array | Hanya kalau `turn_index > 1` | Daftar turn SEBELUMNYA dalam sesi ini — WAJIB berisi turn 1 sampai `turn_index - 1`, masing-masing lengkap, tanpa celah/duplikat. Tiap entri: `{"turn_index": int, "question": string, "answer": string}` (`answer` = narasi jawaban akhir yang Anda terima+tampilkan di turn tersebut sebelumnya — Anda yang menyimpannya, sistem tidak menyimpan riwayat aplikasi). |

### Contoh — turn pertama (tanpa histori)

```json
{
  "session_id": "sess-abc123",
  "turn_index": 1,
  "role_title": "General Manager",
  "employee_id": "emp-001",
  "question": "Berapa occupancy rate properti kita bulan Juni 2026?"
}
```

### Contoh — turn kedua (dengan histori)

```json
{
  "session_id": "sess-abc123",
  "turn_index": 2,
  "role_title": "General Manager",
  "employee_id": "emp-001",
  "question": "Bandingkan dengan bulan sebelumnya.",
  "history": [
    {
      "turn_index": 1,
      "question": "Berapa occupancy rate properti kita bulan Juni 2026?",
      "answer": "Occupancy rate Juni 2026 tercatat 78%."
    }
  ]
}
```

---

## 3. Bentuk Response — Kasus Berhasil (200)

Body JSON (skema `TurnResponse`, `src/schemas/api_response.py`):

| Field | Tipe | Keterangan |
|---|---|---|
| `session_id` | string | Sama seperti yang Anda kirim. |
| `turn_index` | integer | Sama seperti yang Anda kirim. |
| `narasi` | string | Jawaban dalam bahasa natural — **SELALU tampilkan field ini apa adanya sebagai jawaban utama**, tidak pernah kosong. |
| `terverifikasi` | boolean | `true` kalau narasi lolos pengecekan kesetiaan data internal, `false` kalau tidak (lihat Bagian 3.2). |
| `catatan_verifikasi` | string atau `null` | Hanya terisi kalau `terverifikasi=false` — alasan singkat kenapa. `null` kalau `terverifikasi=true`. |
| `visualisasi` | array atau `null` | Data terstruktur untuk grafik/chart (lihat Bagian 3.3). `null` kalau `terverifikasi=false`, atau kalau tidak ada data yang perlu divisualisasikan. |

### 3.1 Contoh nyata (dari eksekusi sungguhan)

Request:
```json
{
  "session_id": "eval-7.17-e01-http",
  "turn_index": 1,
  "role_title": "General Manager",
  "employee_id": "emp-eval",
  "question": "Berapa occupancy rate properti kita bulan Juni 2026?"
}
```

Response (`200`):
```json
{
  "session_id": "eval-7.17-e01-http",
  "turn_index": 1,
  "narasi": "Sistem mengalami kendala teknis saat mengambil data tingkat keterisian properti untuk bulan Juni 2026. Hasil yang diperoleh dari hitungan baru pada turn ini menunjukkan data tidak tersedia (nilai kosong). Perlu dicatat bahwa bulan tersebut masih berada di masa depan, sehingga data aktual belum dapat diakses. Kami akan terus memantau ketersediaan informasi ini.",
  "terverifikasi": true,
  "catatan_verifikasi": null,
  "visualisasi": [
    {
      "atomic_intent_id": "6839cb57-8c31-4642-893a-2d11f7e3ae0b",
      "label_bentuk_jawaban": "nilai_tunggal",
      "nilai_tunggal": null,
      "deret": []
    }
  ]
}
```

Catatan: contoh ini kebetulan berstatus kegagalan teknis internal (data belum tersedia) — narasi tetap `200` dan JUJUR menyampaikan kegagalan itu apa adanya, bukan berpura-pura berhasil (lihat Bagian 5). Kalau data berhasil diambil, `nilai_tunggal`/`deret` akan berisi nilai sesungguhnya, bukan `null`/`[]`.

### 3.2 `terverifikasi=false` — narasi diganti pesan aman

**[Contoh dikonstruksi — skema sudah diverifikasi lewat test deterministik `tests/test_main.py`, bukan hasil eksekusi nyata. Lihat Bagian 6 kenapa kasus ini belum organik muncul di eksekusi nyata M7.17.]**

Sistem punya pengecekan kesetiaan internal (LLM independen kedua yang membandingkan narasi ke data sumber) — kalau pengecekan itu menemukan narasi mengandung klaim yang TIDAK didukung data (mis. penjelasan sebab-akibat yang dikarang), atau pengecekan itu sendiri gagal dijalankan, sistem **mengganti SELURUH `narasi` dengan pesan generik aman** — bukan mengirim narasi asli yang berpotensi menyesatkan:

```json
{
  "session_id": "sess-abc123",
  "turn_index": 1,
  "narasi": "Sistem belum dapat memastikan keakuratan jawaban ini sepenuhnya. Mohon ajukan pertanyaan ini kembali, atau hubungi tim terkait untuk verifikasi lebih lanjut.",
  "terverifikasi": false,
  "catatan_verifikasi": "klaim sebab-akibat tidak didukung data yang diambil",
  "visualisasi": null
}
```

**Penting untuk frontend**: kapan pun `terverifikasi=false`, field `narasi` SUDAH berisi pesan aman ini (bukan teks asli LLM) — Anda TIDAK perlu menyaring/memvalidasi ulang isinya. Boleh menampilkan `catatan_verifikasi` sebagai info tambahan (mis. tooltip), tapi tidak wajib.

### 3.3 Field `visualisasi` — cara render per `label_bentuk_jawaban`

Tiap elemen array `visualisasi` (skema `DataVisualisasi`) merepresentasikan SATU kebutuhan data dalam jawaban:

| `label_bentuk_jawaban` | Field yang terisi | Cara render |
|---|---|---|
| `nilai_tunggal` | `nilai_tunggal` (angka/string tunggal) ATAU `deret` (kalau ekstraksi tunggal ambigu) | Tampilkan sebagai satu angka/statistik (mis. kartu ringkasan) kalau `nilai_tunggal` terisi; kalau ternyata `deret` yang terisi, tampilkan sebagai daftar/tabel kecil (fallback jujur, bukan tebakan). |
| `tren` | `deret` (list objek, biasanya berurutan waktu) | Grafik garis/batang time-series. |
| `perbandingan`, `peringkat`, `komposisi` | `deret` (list objek) | **Provisional** — bentuk `deret` untuk ketiga label ini BELUM final/dikonfirmasi tim dashboard (`docs/keputusan-tertunda.md` #4). Perlakukan sebagai daftar/tabel generik untuk saat ini; struktur kolom di dalam tiap objek `deret` bisa berbeda-beda tergantung data yang diambil (nama kolom apa adanya dari sumber data, belum diseragamkan). |

`nilai_tunggal` dan `deret` tidak pernah SAMA-SAMA `null`/kosong pada saat bersamaan KECUALI turn tersebut genuinely tidak menghasilkan data untuk kebutuhan itu (lihat contoh 3.1 — `nilai_tunggal: null, deret: []` berarti "tidak ada data", bukan error format).

---

## 4. Kode Status HTTP untuk Kasus Gagal

| Status | Kapan terjadi | Bentuk body |
|---|---|---|
| `422 Unprocessable Entity` | Request tidak valid (field wajib hilang, `role_title` tidak dikenal, `history` tidak lengkap/ada celah, dst). | `{"detail": [{"loc": [...], "msg": "...", "type": "..."}, ...]}` — daftar error per-field, format standar Pydantic/FastAPI. |
| `503 Service Unavailable` | Layanan AI (LLM) sedang tidak bisa dihubungi. **Boleh dicoba lagi** setelah jeda singkat. | `{"detail": "Layanan AI sedang tidak tersedia, silakan coba lagi beberapa saat lagi."}` |
| `500 Internal Server Error` | Kegagalan internal lain (database, atau kegagalan tak terduga). | `{"detail": "Terjadi kesalahan internal, silakan coba lagi atau hubungi tim terkait."}` |

**Penting**: `403`/penolakan otorisasi TIDAK memakai kode HTTP khusus — kalau pengguna tidak berhak atas data yang diminta, response tetap `200` dengan `narasi` yang secara eksplisit menjelaskan penolakan itu (mis. *"Anda tidak memiliki akses untuk data ini sesuai peran Anda."*). Ini SENGAJA (lihat Bagian 5) — perlakukan seperti response sukses biasa, narasi-nya sendiri yang membawa pesan penolakan.

Body error TIDAK PERNAH memuat detail teknis internal (nama exception, pesan error provider, query database, dst.) — aman ditampilkan `detail` apa adanya ke pengguna kalau perlu, atau cukup tampilkan pesan generik custom Anda sendiri.

---

## 5. Prinsip Kejujuran — Kenapa Bentuk Response Begini

Sistem ini dirancang untuk TIDAK PERNAH menyamarkan kegagalan/keterbatasan sebagai jawaban yang terlihat lengkap. Konsekuensi untuk frontend:

- `narasi` bisa berisi laporan kegagalan teknis, penolakan akses, atau data yang sebagian/parsial — bukan selalu "jawaban sukses". **Tampilkan `narasi` apa adanya**, jangan asumsikan selalu berisi jawaban positif.
- `terverifikasi=false` bukan error — itu tanda sistem SENGAJA berhati-hati (lihat Bagian 3.2), bukan tanda ada yang rusak.
- Status HTTP `200` tidak berarti "data ditemukan" — berarti "sistem berhasil MEMPROSES permintaan Anda sampai selesai", terlepas dari apa isi jawabannya.

---

## 6. Keterbatasan Saat Ini

- Contoh `terverifikasi=false` (Bagian 3.2) belum pernah muncul organik dari eksekusi nyata sampai dokumen ini ditulis — mekanismenya SUDAH diverifikasi lewat test otomatis (`tests/test_main.py`), tapi belum ada bukti langsung dari server sungguhan. Kalau Anda menemukan bentuk nyata yang berbeda dari contoh di atas, laporkan.
- Bentuk `deret` untuk label `perbandingan`/`peringkat`/`komposisi` (Bagian 3.3) masih provisional — kemungkinan berubah setelah kebutuhan dashboard/chart library nyata diketahui (`docs/keputusan-tertunda.md` #4).
- Server tunggal (`uvicorn` tanpa banyak worker) memproses SATU permintaan pada satu waktu secara efektif untuk beban kerja berat (satu turn bisa makan waktu beberapa menit tergantung kompleksitas pertanyaan) — pertimbangkan menampilkan indikator "sedang memproses" yang tahan lama di sisi frontend, bukan asumsi respons cepat.
