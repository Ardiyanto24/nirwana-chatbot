# Template Plan Milestone — Panduan, Template, dan Contoh

**AI Chatbot RBAC — Nirwana Hospitality Group**

Dokumen ini py tiga komponen terpisah, dalam urutan berikut:

1. **Panduan Penggunaan** — penjelasan tujuan tiap section template dan jebakan umum saat mengisinya.
2. **Template** — salinan kosong yang siap disalin apa adanya setiap kali menulis plan milestone baru.
3. **Contoh Terisi Penuh** — satu plan hipotetis lengkap (Milestone 1.3 — Pemetaan Ketergantungan Turn) yang menunjukkan bagaimana template ini terlihat setelah benar-benar diisi dari awal sampai akhir, bukan potongan-potongan lepas per section.

Contoh di Bagian 3 adalah ilustrasi untuk keperluan panduan ini — belum tentu identik dengan plan sungguhan yang nanti ditulis saat Milestone 1.3 benar-benar dikerjakan, karena beberapa keputusan di dalamnya memang menunggu jawaban user yang genuinely belum ada.

---

# Bagian 1 — Panduan Penggunaan

## Kapan Template Ini Dipakai

Satu file plan per milestone, ditulis di Plan Mode sebelum implementasi dimulai, mengikuti Workflow Wajib "1. Rencanakan sebelum mengimplementasikan" di `CLAUDE.md`/`AGENT.md`. Plan ini **bukan** dokumen yang di-commit sebagai file permanen terpisah — ia hidup selama sesi perencanaan, lalu begitu disetujui user, isinya (terutama section keputusan) jadi dasar penulisan `milestones/<id>-<slug>/decisions.md` yang sesungguhnya di-commit.

## Penjelasan per Section

### Context

**Tujuan:** memberi pembaca (termasuk diri Anda sendiri di sesi kerja berikutnya) gambaran cukup untuk paham posisi milestone ini tanpa harus membuka ulang seluruh dokumen `rancangan-*.md`. Bukan tempat untuk menyalin ulang seluruh isi Lingkup dari dokumen sumber — cukup inti dan posisinya dalam urutan kerja.

**Jebakan umum:** menyalin definisi milestone kata per kata dari dokumen implementasi. Kalau itu yang terjadi, pembaca akan lebih baik langsung membuka dokumen sumbernya — Context di sini harus menambah nilai (terutama bagian "Temuan penting"), bukan mengulang.

### Keputusan Desain Turunan (Forced/Preseden, Tidak Perlu Ditanya Ulang)

**Tujuan:** memisahkan tegas apa yang **sudah** diputuskan (lewat dokumen arsitektur, kontrak milestone lain, atau prinsip yang sudah dipegang konsisten) dari apa yang **belum**. Ini mencegah dua kesalahan berlawanan: menanyakan ulang sesuatu yang sudah jelas jawabannya (membuang waktu user), atau diam-diam mengambil keputusan yang sebenarnya belum py dasar kuat (berisiko salah tanpa disadari).

**Jebakan umum:** menulis keputusan tanpa menyebut sumber paksaannya. "Output berupa `{session_id, turn_index}`" tanpa rujukan terdengar seperti pilihan bebas — padahal itu kontrak wajib. Selalu sebutkan dari mana paksaannya berasal.

### Keputusan yang Ditanyakan ke User

**Tujuan:** section yang paling sering diabaikan atau diisi asal — padahal justru paling penting untuk dijaga jujur. Section ini WAJIB memuat setiap keputusan yang genuinely tidak py jawaban di dokumen manapun, dan TIDAK boleh diam-diam pindah ke section "Keputusan Desain Turunan" hanya supaya plan terlihat lebih siap.

**Cara membedakan forced vs genuinely-terbuka:** tanyakan "kalau saya buka kembali kedelapan dokumen sumber, apakah saya bisa temukan jawabannya secara eksplisit atau tersirat kuat?" Kalau ya → forced, taruh di section atas beserta rujukannya. Kalau tidak (dan project ini belum py preseden implementasi nyata untuk menariknya) → genuinely-terbuka, taruh di sini.

**Jebakan umum paling berbahaya:** mengasumsikan sepihak lalu menuliskannya seolah itu forced. Misalnya memilih model tertentu untuk suatu milestone dengan alasan "kelihatannya masuk akal" — itu bukan keputusan yang bisa ditarik dari dokumen manapun, jadi wajib diajukan, bukan diasumsikan atas nama efisiensi.

**Kalau seluruh keputusan di suatu milestone ternyata forced semua** (tidak ada yang genuinely terbuka) — itu sah terjadi, nyatakan eksplisit alih-alih menghapus section-nya.

### Checkpoint & Task Breakdown

**Tujuan:** memecah milestone jadi unit kerja yang masing-masing bisa diverifikasi dan di-commit sendiri — bukan satu lompatan besar dari "belum ada apa-apa" ke "milestone selesai".

**Jebakan umum:** menulis task yang sebenarnya masih menyembunyikan keputusan yang belum dibahas di dua section sebelumnya. Kalau saat menulis Task Anda menyadari ada pilihan yang belum py jawaban, itu tandanya section "Keputusan yang Ditanyakan ke User" di atas belum lengkap — kembali ke sana dulu, jangan menebak di level Task.

### Kriteria Keberhasilan (dari Dokumen Sumber)

**Tujuan:** jembatan eksplisit antara apa yang dijanjikan di dokumen implementasi dan apa yang dibuktikan di plan ini — supaya di akhir milestone, tidak ada Kriteria Keberhasilan sumber yang diam-diam terlewat tanpa task pembuktinya.

## Urutan Pengisian yang Disarankan

Meski template ditulis top-down, pengisian yang paling aman **tidak** selalu berurutan top-down murni:

1. Context (termasuk Temuan Penting) — dulu, untuk membangun pemahaman.
2. **Keputusan Desain Turunan** dan **Keputusan yang Ditanyakan ke User** — diisi **bersamaan**, saling silang cek: setiap kali menulis satu butir di salah satu section, tanyakan "apakah ini benar-benar forced, atau saya cuma berasumsi?" Pindahkan butir ke section yang tepat begitu jawabannya jelas.
3. Ajukan section "Keputusan yang Ditanyakan ke User" ke user lewat `AskUserQuestion`, **tunggu jawaban**.
4. Baru setelah itu tulis Checkpoint & Task Breakdown — di titik ini, seharusnya tidak ada lagi keputusan tersembunyi yang belum terjawab.
5. Kriteria Keberhasilan, Commit, Risiko & Mitigasi — pengecekan akhir sebelum plan diajukan lewat `ExitPlanMode`.

---

# Bagian 2 — Template

*(Salin bagian di bawah ini apa adanya untuk memulai plan milestone baru.)*

```markdown
# Plan — Milestone <id>: <Nama Milestone>

## Context

<Ringkas dari dokumen `rancangan-*.md` terkait: apa Lingkup milestone ini, kenapa ia jadi milestone terpisah (bagian "Kenapa Ini Jadi Milestone Terpisah" di dokumen sumber), dan bagaimana posisinya dalam urutan pengerjaan — milestone apa yang jadi prasyaratnya, milestone apa yang menunggu hasilnya. Jangan menyalin ulang seluruh isi dokumen sumber di sini — cukup konteks yang perlu diingat sepanjang plan ini dibaca.>

**Temuan penting sebelum plan ditulis:** <Apa yang ditemukan saat membaca dokumen sumber + kode/state repo yang sudah ada, yang mengubah bentuk pekerjaan dari yang terbayang sekilas. Contoh pola: sebagian mekanisme sudah ada dari milestone lain dan tinggal dipakai ulang (reuse), bukan dibangun dari nol; atau kontrak dari milestone lain ternyata membatasi opsi yang tersedia di sini. Jika tidak ada temuan yang mengubah bentuk pekerjaan, nyatakan eksplisit "Tidak ada temuan yang mengubah bentuk pekerjaan dari deskripsi milestone sumber" — jangan dihilangkan begitu saja seolah tidak pernah dicek.>

**Batasan mengikat:** <Batasan dari `CLAUDE.md`/`AGENT.md` (bagian "Batas Implementasi Saat Ini") atau dari prinsip arsitektur yang secara langsung membatasi opsi yang tersedia untuk milestone ini secara spesifik — bukan mengulang seluruh isi `CLAUDE.md`, hanya yang relevan dan berdampak langsung ke plan ini.>

**Klarifikasi yang dikonfirmasi user (jika ada, sebelum plan ini ditulis):** <Jika sudah ada percakapan pendahuluan dengan user yang mengklarifikasi sesuatu sebelum plan resmi ditulis — beda dari section "Keputusan yang Ditanyakan ke User" di bawah, yang isinya pertanyaan yang BELUM dijawab. Section ini untuk yang SUDAH dijawab lebih dulu, dicatat di sini supaya konteksnya tidak hilang. Kosongkan/hapus section ini kalau tidak ada.>

## Keputusan Desain Turunan (Forced/Preseden, Tidak Perlu Ditanya Ulang)

<Daftar keputusan yang TIDAK memerlukan konfirmasi user karena sudah dipaksa oleh: kontrak milestone lain yang sudah final, prinsip arsitektur di `arsitektur-ai-chatbot-rbac.md`/`rancangan-observability-ai-chatbot.md`, atau preseden pola yang sudah dipakai konsisten di milestone sebelumnya. Setiap butir WAJIB menyebutkan sumber paksaannya secara eksplisit (nama dokumen/milestone/prinsip) — bukan pernyataan tanpa rujukan. Contoh bentuk butir:

- **<Keputusan>** — <alasan/sumber paksaan, mis. "sudah dikunci di Bagian 2 rancangan-observability-ai-chatbot.md, tinggal dipakai" atau "forced by prinsip ruang-kesalahan-tertutup-vs-terbuka di Bagian 1 arsitektur induk">.

Jika sebuah keputusan forced tidak punya alternatif nyata yang sempat dipertimbangkan, itu wajar — bagian "Opsi yang Dipertimbangkan tapi Ditolak" di `decisions.md` nanti cukup menyatakan singkat "tidak ada alternatif dipertimbangkan karena forced by X", bukan dihilangkan.>

## Keputusan yang Ditanyakan ke User

<Daftar keputusan yang GENUINELY terbuka — tidak bisa ditarik dari preseden milestone manapun, berdampak material terhadap hasil, atau mahal diubah kalau salah pilih di awal. Ini yang wajib diajukan lewat `AskUserQuestion` SEBELUM checkpoint ditulis final, bukan diasumsikan sepihak lalu diberitahukan belakangan. Untuk tiap keputusan, sertakan alternatif yang dipertimbangkan dan rekomendasi (jika ada), supaya user bisa memilih dengan konteks yang cukup — bukan pertanyaan kosong tanpa arah. Contoh bentuk butir:

- **<Keputusan>** — <kenapa ini genuinely terbuka, bukan forced>. Alternatif: <opsi A vs opsi B, dengan trade-off singkat>. <Rekomendasi jika ada, dengan alasan.>

**Jika seluruh keputusan di milestone ini bisa ditarik dari preseden/kontrak yang sudah ada** (tidak ada yang genuinely terbuka), nyatakan itu eksplisit di sini alih-alih menghapus section ini seluruhnya — supaya jelas bahwa ketiadaan pertanyaan adalah hasil pengecekan sadar, bukan langkah yang terlewat. Formatnya: "Tidak ada keputusan genuinely terbuka untuk milestone ini — seluruh keputusan desain tercakup di atas sebagai turunan dari <sebutkan sumber preseden/kontraknya>."

Section ini WAJIB dituntaskan (diisi hasil `AskUserQuestion` yang sudah dijawab, atau dinyatakan kosong secara eksplisit seperti di atas) sebelum Checkpoint & Task Breakdown di bawah ditulis final — checkpoint yang disusun di atas keputusan yang belum terjawab berisiko harus dirombak ulang.>

## Checkpoint & Task Breakdown

<Pecah pekerjaan milestone jadi beberapa checkpoint kecil, independen secara verifikasi, dan bisa di-rollback secara spesifik — bukan satu checkpoint besar mencakup seluruh milestone. Urutan checkpoint mengikuti dependensi logis (checkpoint berikutnya butuh checkpoint sebelumnya sudah terverifikasi dan ter-commit, sesuai Workflow Wajib "Implementasikan per checkpoint" di CLAUDE.md/AGENT.md).>

### Checkpoint <n> — <Nama Checkpoint>

- **Task <n>.** <Task atomik, cukup spesifik untuk langsung dikerjakan tanpa keputusan tersembunyi lagi di dalamnya — nama fungsi/file boleh disebut kalau sudah jelas dari keputusan desain di atas, tapi jangan menyembunyikan keputusan baru yang belum dibahas di dua section sebelumnya.>
- **Task <n+1>.** <dst — pecah cukup halus agar tiap task bisa diverifikasi sendiri, tapi jangan berlebihan sampai kehilangan makna sebagai satu unit kerja checkpoint>

**Verifikasi:** <Bagaimana checkpoint ini dibuktikan benar-benar bekerja — mengikuti prinsip "jangan menganggap perubahan benar tanpa bukti" dari CLAUDE.md/AGENT.md: panggilan nyata (ke chatbot_api, ke Collector/Jaeger, ke Supabase), bukan cuma membaca log sendiri atau asumsi. Sebutkan bukti konkret apa yang akan dicatat.>

**Files:** <Daftar file yang disentuh/dibuat checkpoint ini — termasuk file test, bukan hanya file implementasi.>

---

<Ulangi struktur Checkpoint di atas untuk tiap checkpoint berikutnya>

---

### Checkpoint <terakhir> — Dokumentasi dan Penutupan

- **Task.** Tulis `milestones/<id>-<slug>/decisions.md` — seluruh keputusan dari section "Keputusan Desain Turunan" dan "Keputusan yang Ditanyakan ke User" di atas, masing-masing dengan "Opsi yang Dipertimbangkan tapi Ditolak".
- **Task.** Tulis `milestones/<id>-<slug>/logs.md`.
- **Task.** Tulis `milestones/<id>-<slug>/report.md` — Kriteria Keberhasilan sumber vs bukti run nyata; catat eksplisit bagian yang di luar cakupan milestone ini (jika ada) beserta kapan dijadwalkan; catat status pemenuhan "Catatan Serah Terima ke Pekerjaan Lain" dari dokumen sumber, jika milestone ini adalah milestone terakhir di dokumen `rancangan-*.md`-nya.
- **Task.** Perbarui "Status Saat Ini" di `CLAUDE.md` dan `AGENT.md`.

**Files:** `milestones/<id>-<slug>/{decisions.md,logs.md,report.md}`, `CLAUDE.md`, `AGENT.md`.

---

## Kriteria Keberhasilan (dari Dokumen Sumber)

<Salin persis Kriteria Keberhasilan dari bagian milestone terkait di dokumen `rancangan-*.md` sumber — jangan ditulis ulang dengan kata-kata sendiri, supaya tidak ada penyimpangan makna dari yang sudah disepakati di dokumen implementasi. Untuk tiap kriteria, sebutkan Task/Checkpoint mana yang membuktikannya, sehingga di akhir plan ini jelas tidak ada kriteria sumber yang terlewat tanpa task pembuktinya.>

- <Kriteria 1 dari dokumen sumber> — **Task <n>**.
- <Kriteria 2 dari dokumen sumber> — **Task <n>**.

## Commit

<Bagaimana checkpoint di atas dipecah jadi commit, mengikuti aturan Conventional Commits dan pemisahan tipe dari CLAUDE.md/AGENT.md — mis. `feat` untuk kode/infra, `docs` untuk decisions/logs/report, dipisah kalau satu checkpoint mencakup keduanya.>

## Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| <Risiko konkret yang spesifik untuk milestone ini — bukan risiko generik seperti "bug bisa terjadi"> | <Mitigasi konkret, idealnya merujuk checkpoint/task tertentu yang jadi pengamannya> |
```

---

# Bagian 3 — Contoh Terisi Penuh

*(Ilustrasi hipotetis untuk Milestone 1.3 — Pemetaan Ketergantungan Turn. Lihat catatan di pembuka dokumen ini soal statusnya.)*

```markdown
# Plan — Milestone 1.3: Pemetaan Ketergantungan Turn

## Context

Milestone 1.3 mendeteksi apakah pertanyaan di turn terakhir bergantung pada turn lain dalam sesi yang sama, dan kalau ya, turn mana persisnya — cukup `{session_id, turn_index}`, bukan `atomic_intent_id` (kontrak wajib dari `arsitektur-ai-chatbot-rbac.md` §4, karena LLM di titik ini belum pernah membaca session memory). Hasilnya memicu dua jalur paralel di Milestone 1.4 (Rewrite) dan 1.5 (Tarik Session Memory) yang keduanya bergantung pada output milestone ini sebagai prasyarat — 1.3 wajib selesai dan teruji lebih dulu sebelum 1.4/1.5 py sesuatu untuk dikerjakan.

**Temuan penting sebelum plan ditulis:** Tidak ada mekanisme session memory yang sudah berjalan pada titik ini — Milestone 1.1 (Collector) dan 1.2 (Input Layer) sudah selesai, tapi keduanya tidak menyentuh penyimpanan sesi. Ini berarti Milestone 1.3 perlu diuji dengan data percakapan tiruan yang disusun manual (skenario multi-turn buatan), bukan session sungguhan — karena Milestone 1.5 (yang benar-benar membangun penyimpanan) belum ada.

**Batasan mengikat:** Model per langkah dan provider routing belum ditentukan (dicatat eksplisit di "Status Saat Ini" `CLAUDE.md`) — ini bukan sekadar detail Milestone 1.3, tapi keputusan pertama yang perlu diajukan begitu implementasi menyentuh pemanggilan LLM pertama di seluruh project.

## Keputusan Desain Turunan (Forced/Preseden, Tidak Perlu Ditanya Ulang)

- **Output berupa `{session_id, turn_index}`, bukan `atomic_intent_id`** — forced by `arsitektur-ai-chatbot-rbac.md` §4 (baris 111-113): LLM di Milestone 1.3 belum pernah membaca isi session memory, memaksa ID spesifik di sini membuka risiko halusinasi. Sudah dikunci eksplisit sebagai kontrak, bukan pilihan implementasi.
- **Tidak menghasilkan hasil untuk turn yang tidak bergantung (bukan memaksa mengarang rujukan)** — forced by Kriteria Keberhasilan Milestone 1.3 di `rancangan-context-decomposition.md`: "Kalimat yang sepenuhnya berdiri sendiri... menghasilkan penanda 'tidak bergantung', tanpa memaksakan rujukan yang sebenarnya tidak ada."
- **Berjalan sebagai pemanggilan LLM tunggal (satu langkah), bukan dipecah jadi sub-langkah tambahan** — preseden dari pola seluruh milestone LLM lain di dokumen ini (Milestone 1.4, 1.6, 2.1, dst.) yang masing-masing satu tugas = satu pemanggilan, kecuali dokumen sumber eksplisit menyebut lebih dari satu (seperti Decomposition 3 langkah). Tidak ada alternatif dipertimbangkan karena forced by konsistensi pola dokumen implementasi.

## Keputusan yang Ditanyakan ke User

- **Model LLM untuk pemanggilan di Milestone 1.3** — genuinely terbuka; `CLAUDE.md` eksplisit mencatat ini sebagai keputusan pertama yang belum ditentukan di seluruh project, dan Milestone 1.3 kemungkinan jadi titik pertama yang menyentuhnya. Alternatif: model dari Claude Console vs model dari OpenRouter (keduanya sudah disebut sebagai opsi provider campuran di awal diskusi arsitektur, tapi model spesifik belum dipilih untuk langkah manapun). Tidak ada rekomendasi tegas di titik ini — pilihan provider/model untuk tugas klasifikasi ringan seperti ini sebaiknya mempertimbangkan biaya per-panggilan mengingat frekuensi tinggi (dipanggil tiap turn bukan turn pertama), bukan cuma akurasi semata; keputusan ini sebaiknya user yang timbang karena menyangkut anggaran pribadi.
- **Bentuk konkret data percakapan tiruan untuk pengujian (lihat Temuan Penting di Context)** — genuinely terbuka; tidak ada dokumen yang menentukan skenario uji spesifik apa yang representatif. Alternatif: menyusun beberapa skenario manual mencakup kasus dari Kriteria Keberhasilan sumber (rujukan eksplisit, tidak ada rujukan, rujukan ke turn bukan tepat sebelumnya) vs menunggu Milestone 1.2 py contoh payload nyata dari frontend. Rekomendasi: skenario manual dulu — menunggu payload nyata akan menahan Milestone 1.3 tanpa alasan kuat, karena bentuk payload sendiri sudah dikunci di `arsitektur-ai-chatbot-rbac.md` §4.

*(Kedua keputusan di atas diajukan lewat `AskUserQuestion`. Jawaban hipotetis untuk keperluan contoh ini: model dipilih dari OpenRouter dengan pertimbangan biaya; skenario uji manual disepakati dimulai sekarang, tidak menunggu payload nyata.)*

## Checkpoint & Task Breakdown

### Checkpoint 1 — Mekanisme Deteksi Ketergantungan

- **Task 1.** Susun prompt untuk pemanggilan LLM tunggal: menerima teks turn terakhir + konteks turn-turn sebelumnya yang tersedia di payload, menghasilkan struktur `{bergantung: bool, session_id: str|None, turn_index: int|None}`.
- **Task 2.** Implementasikan pemanggilan sesuai model/provider hasil keputusan user (OpenRouter), dengan span `chat` ter-emit sesuai kontrak observability Bagian 2.
- **Task 3.** Susun skenario uji manual sesuai kesepakatan — minimal tiga kelompok: rujukan eksplisit ke turn terdekat, tanpa rujukan sama sekali, rujukan ke turn yang bukan tepat sebelumnya.

**Verifikasi:** ketiga kelompok skenario uji dijalankan nyata lewat pemanggilan LLM sungguhan (bukan mock), hasilnya dicocokkan manual terhadap ekspektasi tiap skenario, dicatat di `logs.md` dengan skenario mana yang lolos/gagal.

**Files:** `src/context_resolution/turn_dependency.py` (baru), `tests/context_resolution/test_turn_dependency.py` (baru).

---

### Checkpoint 2 — Dokumentasi dan Penutupan

- **Task 4.** Tulis `milestones/1.3-pemetaan-ketergantungan-turn/decisions.md` — kedua keputusan di atas dengan "Opsi yang Dipertimbangkan tapi Ditolak".
- **Task 5.** Tulis `milestones/1.3-pemetaan-ketergantungan-turn/logs.md`.
- **Task 6.** Tulis `milestones/1.3-pemetaan-ketergantungan-turn/report.md`.
- **Task 7.** Perbarui "Status Saat Ini" di `CLAUDE.md` dan `AGENT.md`.

**Files:** `milestones/1.3-pemetaan-ketergantungan-turn/{decisions.md,logs.md,report.md}`, `CLAUDE.md`, `AGENT.md`.

---

## Kriteria Keberhasilan (dari Dokumen Sumber)

- "Kalimat dengan rujukan eksplisit ke turn sebelumnya... menghasilkan referensi turn yang benar." (`rancangan-context-decomposition.md`, Milestone 1.3) — **Task 3, kelompok skenario "rujukan eksplisit"**.
- "Kalimat yang sepenuhnya berdiri sendiri tanpa rujukan apa pun... menghasilkan penanda 'tidak bergantung', tanpa memaksakan rujukan yang sebenarnya tidak ada." — **Task 3, kelompok skenario "tanpa rujukan"**.
- "Kalimat yang merujuk balik ke turn yang bukan tepat sebelumnya... tetap terdeteksi dan diarahkan ke turn yang benar." — **Task 3, kelompok skenario "rujukan ke turn bukan tepat sebelumnya"**.

## Commit

Checkpoint 1: `feat(milestone-1.3): implementasi deteksi ketergantungan turn` (Task 1-2) + `test(milestone-1.3): skenario uji deteksi ketergantungan turn` (Task 3, boleh digabung `feat` mengikuti pola M2.4 project pembanding). Checkpoint 2: `docs(milestone-1.3): decisions, logs, report` (Task 4-6) + `docs: perbarui status project` (Task 7, terpisah karena menyentuh file lintas-milestone).

## Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| Skenario uji manual (Task 3) tidak representatif terhadap variasi bahasa natural sungguhan, karena disusun tanpa payload nyata | Dicatat eksplisit sebagai keterbatasan di `report.md`, dengan pemicu peninjauan ulang: begitu Milestone 1.2 menerima payload nyata pertama dari frontend, bandingkan pola rujukan yang muncul di sana terhadap skenario uji Task 3 |
| Model dari OpenRouter yang dipilih user bisa berbeda perilaku/kualitas dari yang diasumsikan saat estimasi biaya | Task 3 dijalankan dengan model yang benar-benar dipilih (bukan model lain sebagai proxy), sehingga hasil verifikasi mencerminkan pilihan sesungguhnya |
```
