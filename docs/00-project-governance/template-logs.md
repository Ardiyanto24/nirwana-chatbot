# Logs — Milestone <id>: <Nama Milestone>

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan. Bedanya mendasar dari plan: **plan adalah rencana, logs adalah kenyataan**. Kalau eksekusi menyimpang dari yang direncanakan (task berubah bentuk, urutan berubah, task baru muncul, task yang direncanakan ternyata tidak diperlukan), itu **wajib dicatat sebagai penyimpangan eksplisit**, bukan diam-diam disamakan seolah plan dan eksekusi identik.

Logs adalah catatan peristiwa — tidak menghapus atau menghaluskan jejak error/perubahan arah yang sempat terjadi. Kesimpulan/ringkasan hasil akhir adalah tugas `report.md`, bukan file ini.

---

## Checkpoint <n> — <Nama Checkpoint, sesuai plan>

**Mulai:** <tanggal/waktu> · **Selesai:** <tanggal/waktu, isi setelah checkpoint tuntas>

### Task <n> — <Nama Task, sesuai plan>

**Kesesuaian dengan plan:** <Sesuai plan / Menyimpang dari plan — kalau menyimpang, jelaskan singkat apa yang berbeda dan kenapa (rujuk entri decisions.md kalau penyimpangan ini juga tercatat sebagai keputusan formal di sana).>

**Apa yang dilakukan**
<Narasi konkret: langkah yang benar-benar diambil, bukan menyalin ulang deskripsi task dari plan.>

**Temuan**
<Apa yang ditemukan selama mengerjakan ini — termasuk hal yang tidak terduga dari plan, bukan hanya hasil yang diharapkan.>

**Error/Kegagalan (jika ada)**
<Pesan error konkret, kondisi yang memicunya. Kosongkan/tulis "Tidak ada" kalau memang tidak terjadi — jangan dihilangkan section-nya, supaya jelas ini memang dicek bukan terlewat.>

**Diagnosis dan Perbaikan (jika ada error)**
<Bagaimana akar masalah ditelusuri, apa perbaikan yang diterapkan.>

**Hasil Verifikasi**
<Bukti konkret sesuai kriteria "Verifikasi" checkpoint di plan — hasil panggilan nyata, output test, span yang terlihat di Jaeger, dsb. Bukan "sudah dicek", tapi apa hasilnya.>

**Commit:** `<hash pendek>` — `<pesan commit>`

---

*(Ulangi struktur Task di atas untuk task berikutnya dalam checkpoint yang sama, lalu struktur Checkpoint untuk checkpoint berikutnya.)*

---

## Task/Checkpoint di Luar Plan (jika ada)

<Bagian ini WAJIB ada kalau sepanjang milestone muncul task atau bahkan checkpoint yang sama sekali tidak tercantum di plan — bukan penyesuaian kecil pada task yang sudah ada (itu dicatat di "Kesesuaian dengan plan" masing-masing task di atas), melainkan pekerjaan baru yang lahir dari temuan di tengah jalan. Gunakan struktur Task yang sama seperti di atas untuk tiap entrinya, dan jelaskan eksplisit kenapa ini tidak masuk plan sejak awal — apakah karena temuan genuinely baru, atau karena estimasi awal di plan kurang tepat. Kosongkan/tulis "Tidak ada" kalau memang tidak terjadi.>
