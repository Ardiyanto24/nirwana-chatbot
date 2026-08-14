# Aturan Proyek — AI Chatbot RBAC Nirwana Hospitality Group

File ini identik dengan file aturan pasangannya. Ia adalah konteks persisten untuk setiap agen yang bekerja di repository ini. File ini sendiri, beserta tiga template resmi (`template-plan-milestone-lengkap.md`, `template-decisions.md`, `template-logs.md`, `template-report.md`), berada di `docs/00-project-governance/` — dipisah dari dokumentasi isi project (`docs/01-architecture/` dst.) karena sifatnya perkakas proses, bukan artefak desain sistem.

## Tujuan Proyek

Membangun sistem AI Chatbot internal dengan Role-Based Access Control (RBAC) sebagai portofolio AI/ML Engineer — Lapis 1 dari RBAC dua lapis di atas serving layer data platform yang **sudah selesai dan terverifikasi**. `chatbot_api` (Lapis 2, kontrak `GET /chatbot/{domain}/{view_name}`), 67 view `chatbot_views`, dan seluruh reverse ETL di baliknya berada di luar cakupan — dikonsumsi sebagai HTTP client, tidak dimodifikasi.

Hasil sistem yang dituju:

- Sembilan layer pemrosesan (Input Layer hingga Interpretation) yang memahami maksud pertanyaan natural, menegakkan otorisasi berbasis peran, memilih data yang tepat dari 67 view, dan menyusun jawaban jujur — termasuk dukungan percakapan multi-turn dengan resolusi referensi lintas-turn.
- Observability penuh berbasis OpenTelemetry: trace/metrics privat (Jaeger, Prometheus, Grafana) dan dashboard publik (Next.js + Supabase) dengan isi yang identik.
- Custom exporter OTel Collector (Go) yang menjembatani span ke Supabase, dengan fallback tersedia ke pendekatan sidecar Python.

## Dokumen Sumber Kebenaran

Sebelum mengerjakan sebuah milestone, baca hanya dokumen yang relevan berikut:

1. `docs/01-architecture/arsitektur-ai-chatbot-rbac.md` — peta 9-layer, prinsip fondasi, RBAC dua lapis, bentuk data kunci. Status tiap bagian ditandai `[SOLID]`/`[KERANGKA AWAL]` — jangan perlakukan bagian `[KERANGKA AWAL]` sebagai sudah final.
2. `docs/01-architecture/rancangan-observability-ai-chatbot.md` — kontrak span per layer, arsitektur pipeline Collector, skema Supabase. **Wajib dibaca sebelum milestone manapun yang menyentuh instrumentasi** — kontrak span di Bagian 2 dokumen ini mengikat seluruh PIC 1-4.
3. `docs/02-implementation-plan/rancangan-context-decomposition.md` — Milestone 1.x (PIC 1: Input Layer, Context Resolution, Decomposition, fondasi Collector).
4. `docs/02-implementation-plan/rancangan-rbac-authorization.md` — Milestone 2.x (PIC 2: Domain Gate, Verification Gate).
5. `docs/02-implementation-plan/rancangan-retrieval-query.md` — Milestone 3.x (PIC 3: Retriever, Query Engine).
6. `docs/02-implementation-plan/rancangan-execution-interpretation.md` — Milestone 4.x (PIC 4: Execution, Interpretation).
7. `docs/02-implementation-plan/rancangan-observability-dashboard.md` — Milestone 5.x (PIC 5: Grafana + Next.js).
8. `docs/02-implementation-plan/rancangan-custom-exporter-supabase.md` — Milestone 6.x (PIC 6: custom exporter Go).
9. `docs/03-domain-source/katalog-data-chatbot.md` + `rancangan-rbac-ai-chatbot.md` + `api-chatbot.md` — sumber kebenaran domain: definisi 67 view (grain, sumber, kolom turunan), tabel `role_permissions` (19 role × 10 domain), kontrak parameter `chatbot_api`. Sudah final dan diverifikasi tim database engineering — bukan cakupan yang direvisi di sini.
10. Keputusan, log, dan report milestone terkait di bawah `milestones/`.

Jangan menganggap detail teknis yang sengaja terbuka di dokumen arsitektur (ditandai `[KERANGKA AWAL]` atau tersurat di "Bagian 8 — Yang Masih Terbuka") sebagai sudah diputuskan. Telusuri keputusan milestone terdahulu terlebih dahulu; bila tidak ada preseden yang mengikat, ajukan opsi kepada pengguna sebelum implementasi.

## Struktur Repository

Struktur ini **dinamis, bukan baku** — mengikuti apa yang benar-benar sudah dikerjakan, bukan rencana di depan. Belum ada satu pun folder yang benar-benar dibuat sampai penulisan ini (repo belum diinisialisasi) — bagian di bawah adalah folder yang **sudah pasti** akan terbentuk (dirujuk eksplisit di kedelapan dokumen sumber kebenaran atau ketiga template milestone) dan diberi keterangan fungsi berdasarkan itu, bukan hasil eksplorasi folder sungguhan.

**Aturan wajib**: setiap kali sebuah checkpoint menghasilkan folder baru yang belum tercatat di bawah — baik folder tingkat atas baru maupun subfolder baru di bawah `src/` yang jadi rumah kode PIC tertentu — perbarui bagian ini di `CLAUDE.md` dan `AGENT.md` sebagai bagian dari checkpoint itu sendiri (bukan pekerjaan terpisah yang ditunda), disertai keterangan singkat fungsi folder tersebut. Ini konsisten dengan Workflow Wajib "3. Implementasikan per checkpoint" — pembaruan struktur repo adalah bagian dari mendokumentasikan checkpoint, sama seperti mencatat commit hash di `logs.md`.

| Folder | Fungsi | Status |
|---|---|---|
| `docs/01-architecture/` | Dua dokumen arsitektur induk (`arsitektur-ai-chatbot-rbac.md`, `rancangan-observability-ai-chatbot.md`) — kontrak lintas-PIC yang tidak direvisi sepihak oleh satu pekerjaan saja. | Sudah py isi (dari fase desain) |
| `docs/02-implementation-plan/` | Enam dokumen implementasi per PIC (`rancangan-*.md`) — cakupan, milestone, kriteria keberhasilan per pemilik pekerjaan. | Sudah py isi (dari fase desain) |
| `docs/03-domain-source/` | Tiga dokumen sumber kebenaran domain dari tim database engineering (`katalog-data-chatbot.md`, `rancangan-rbac-ai-chatbot.md`, `api-chatbot.md`) — final, bukan cakupan yang direvisi di sini. | Sudah py isi (dari fase desain) |
| `docs/keputusan-tertunda.md` | Backlog project-wide untuk keputusan yang belum saatnya diambil, lintas milestone. | **Belum dibuat** — file tunggal, bukan folder; diinisialisasi saat keputusan tertunda pertama muncul |
| `docs/keterbatasan-diterima.md` | Backlog project-wide untuk keterbatasan yang ditemukan dan sengaja diterima (bukan diperbaiki). | **Belum dibuat** — file tunggal, bukan folder; diinisialisasi saat keterbatasan pertama diterima |
| `milestones/<id>-<slug>/` | Satu folder per milestone (mis. `milestones/1.1-fondasi-collector/`), masing-masing berisi `decisions.md`, `logs.md`, `report.md` mengikuti tiga template resmi. | **Belum dibuat** — folder pertama lahir begitu Milestone 1.1 dimulai |
| `src/` | Kode sumber Python untuk logic 9 layer (PIC 1-4). Struktur subfolder di bawahnya (per-layer atau per-PIC) belum ditentukan — keputusan ini sendiri layak diajukan ke user di awal implementasi Milestone 1.2, bukan diasumsikan sepihak. | **Belum dibuat** |
| `tests/` | Test otomatis, struktur mengikuti `src/` sekali itu terbentuk. | **Belum dibuat** |
| *(folder Go untuk PIC 6 — custom exporter)* | Rumah kode Go terpisah dari `src/` Python, karena py toolchain build sendiri (lihat `rancangan-custom-exporter-supabase.md`). Nama folder dan strukturnya belum ditentukan — kemungkinan besar bukan di bawah `src/` mengingat perbedaan bahasa dan siklus build, tapi ini keputusan yang perlu diajukan ke user saat Milestone 6.1 dimulai, bukan diasumsikan di sini. | **Belum dibuat, nama belum ditentukan** |
| *(folder Next.js untuk PIC 5 — dashboard publik)* | Aplikasi dashboard publik, kemungkinan besar repo/root terpisah dari kode Python mengingat ekosistem package manager yang berbeda total (npm vs pip) — sama seperti pola project pembanding yang memisahkan API publik ke repo tersendiri. Keputusan konkret diajukan ke user saat Milestone 5.2 dimulai. | **Belum dibuat, lokasi belum ditentukan** |

## Prinsip Arsitektur yang Tidak Boleh Dilanggar

- AI hanya penulis rencana, bukan pengeksekusi langsung — setiap request ke `chatbot_api` wajib lewat Verification Gate (deterministik) sebelum benar-benar dipanggil di Execution.
- Sistem ini adalah Lapis 1 RBAC, bukan pengganti Lapis 2. Jangan membangun ulang penegakan row-level `property_id` — itu sepenuhnya didelegasikan ke `chatbot_api`. Lapis 1 hanya menangani yang tidak dijamin Lapis 2: pemahaman maksud sebelum bertindak, dan constraint cakupan-individu dalam satu properti (mis. Staff hanya boleh lihat performanya sendiri).
- Generate lalu verify, independen, di setiap titik yang keputusannya melibatkan pemahaman makna/maksud bahasa. Verifikasi boleh murni deterministik (tanpa LLM) **hanya jika** seluruh ruang kesalahan yang mungkin terjadi bisa didaftar sebagai aturan eksplisit di depan (ruang kesalahan tertutup) — bukan sekadar karena permukaan tugasnya kelihatan sempit. Kalau verifikasi masih menyentuh kesesuaian makna yang tak terduga bentuknya (ruang kesalahan terbuka), LLM independen wajib dipertahankan.
- Kejujuran terhadap keterbatasan — status non-normal, hasil parsial, penolakan, kegagalan teknis harus selalu tersurat ke user, tidak pernah disamarkan demi jawaban yang terlihat lengkap.
- `403`/`404` dari `chatbot_api` adalah sinyal bug prioritas tinggi (kebocoran di Domain Gate atau Retriever), dieskalasi langsung tanpa retry dan tanpa dikirim balik untuk revisi — bukan alur kegagalan normal. `400` dikirim balik ke Query Engine untuk revisi. `5xx`/timeout di-retry sama persis.
- Skema paket Session Memory (`atomic_intent_id`, `session_id`, `turn_index`, `teks_kebutuhan`, `label_bentuk_jawaban`, `nilai_hasil`, `catatan_interpretasi`, `status`, `sumber`) adalah kontrak yang dipakai bersama PIC 1 (membaca) dan PIC 4 (menulis) — perubahan wajib disepakati kedua pemilik, tidak diubah sepihak.
- Instrumentasi span mengikuti kontrak Bagian 2 `rancangan-observability-ai-chatbot.md` sebagai bagian dari definisi "selesai" tiap milestone PIC 1-4, bukan pekerjaan tambahan di akhir. Default aman: instruksi/input/output LLM tidak direkam sebagai isi span, hanya metadata terstruktur.
- Dashboard publik (Next.js + Supabase) wajib identik isinya dengan dashboard privat (Grafana) — bukan versi ringkas. Pemisahan murni alasan operasional (keterbatasan publish gratis Grafana Cloud), bukan alasan privasi data.
- Rahasia tidak boleh di-hardcode atau di-commit. Gunakan kredensial least-privilege yang dipisah menurut pola akses (mis. kredensial exporter Supabase terpisah dari kredensial lain).

## Workflow Wajib per Milestone

### 1. Rencanakan sebelum mengimplementasikan

1. Baca deskripsi milestone (`docs/02-implementation-plan/*.md`) dan kontrak/dependensi relevan — termasuk bagian "Catatan Serah Terima ke Pekerjaan Lain" di dokumen milestone lain yang disebut sebagai dependensi.
2. Buat plan lewat Plan Mode — proposal diajukan eksplisit ke user (`ExitPlanMode`) sebelum eksekusi dimulai. Surfacekan pertanyaan genuinely-terbuka lewat `AskUserQuestion` SEBELUM plan ditulis, jangan berasumsi (lihat "Kelola keputusan teknis" di bawah).
3. Break down pekerjaan menjadi atomic task yang dapat diuji — ingat milestone di dokumen plan bukan atomic task itu sendiri, melainkan satu lingkup kerja koheren yang perlu dipecah saat perencanaan.
4. Kelompokkan atomic task ke checkpoint yang kecil, independen, dan dapat di-rollback secara spesifik.
5. Identifikasi semua gap keputusan teknis yang material — untuk milestone di PIC 1, cek dulu apakah bagian "Catatan Ketidakpastian" berlaku (mis. Milestone 1.7 mekanisme pencocokan belum final di dokumen arsitektur).

### 2. Kelola keputusan teknis

- Untuk keputusan yang benar-benar terbuka, berdampak material, atau mahal bila diubah (contoh dari dokumen arsitektur: mekanisme Milestone 1.7, daftar eksplisit view kategori "cakupan-individu" untuk Milestone 2.3, model per langkah/provider routing): ajukan beberapa alternatif, trade-off, dan rekomendasi kepada pengguna (`AskUserQuestion`). Jangan implementasikan sebelum pengguna memilih.
- Untuk keputusan yang sudah dipaksa oleh arsitektur, kontrak, temuan audit, atau keputusan sebelumnya: jangan tanya ulang. Catat sebagai keputusan turunan beserta dasar/buktinya.
- Untuk keputusan yang belum saatnya dibuat: catat sebagai keputusan tertunda di `docs/keputusan-tertunda.md` (backlog project-wide, terpisah dari `decisions.md` per-milestone) serta pemicu peninjauannya. **File ini belum dibuat** — inisialisasi saat keputusan tertunda pertama muncul.
- Untuk keterbatasan teknis yang DITEMUKAN dan SENGAJA DITERIMA (bukan diperbaiki) karena biaya perbaikan tidak sepadan atau di luar kendali kita (mis. keterbatasan tier gratis suatu layanan, batasan library pihak ketiga): catat di `docs/keterbatasan-diterima.md` — sertakan konteks penemuan, kenapa diterima, dampak+mitigasi, dan pemicu peninjauan ulang. **File ini belum dibuat** — inisialisasi saat keterbatasan pertama diterima.
- Setelah pilihan pengguna final, tulis keputusan di `milestones/<id>-<slug>/decisions.md`.
- **Setiap entri di `decisions.md` wajib memuat section "Opsi yang Dipertimbangkan tapi Ditolak"** — bukan cuma keputusan final dan alasannya, tapi juga alternatif yang sempat dipertimbangkan dan kenapa tidak dipilih (sertakan bukti: riset, kendala teknis, atau prinsip arsitektur yang dilanggar opsi itu). Untuk keputusan turunan/forced yang tidak punya alternatif nyata, cukup nyatakan singkat "tidak ada alternatif dipertimbangkan karena forced by X" — jangan dihilangkan begitu saja.
- Perbarui plan atomic task agar mengacu pada keputusan final sebelum implementasi dimulai dan propose ke user.

### 3. Implementasikan per checkpoint

1. Kerjakan atomic task checkpoint saat ini saja.
2. Jalankan verifikasi yang telah direncanakan; jangan menganggap perubahan benar tanpa bukti (panggilan nyata ke `chatbot_api`, span yang benar-benar terlihat di Jaeger, query langsung ke Supabase, run CI sungguhan — bukan cuma baca log script sendiri).
3. Catat event nyata di `milestones/<id>-<slug>/logs.md`: mulai pekerjaan, temuan, error, diagnosis, perbaikan, hasil verifikasi, dan hash commit.
4. Commit setiap checkpoint yang lolos dengan pesan Git yang menjelaskan alasan perubahan, mengikuti standar industri **Conventional Commits** (`feat`, `fix`, `docs`, `test`, `chore`, dst., mis. `feat(milestone-1.3): ...`). **Satu checkpoint bisa terdiri dari beberapa commit** — kalau perubahan checkpoint itu mencakup lebih dari satu kategori (mis. `feat` untuk kode + `docs` untuk `decisions.md`/`logs.md`), pisahkan per kategori, jangan digabung jadi satu commit campuran. Yang atomik adalah tiap commit individual, bukan checkpoint sebagai satu kesatuan tunggal — lihat "Git dan Kualitas Perubahan" untuk penegasan aturan ini.
5. Jika checkpoint ini menghasilkan folder baru yang belum tercatat di "Struktur Repository", perbarui bagian itu di `CLAUDE.md` dan `AGENT.md` sebagai bagian dari checkpoint ini — bukan ditunda ke penutupan milestone.
6. Jangan lanjut ke checkpoint berikutnya jika checkpoint sekarang belum diverifikasi dan di-commit (seluruh commit tipe checkpoint itu, bukan cuma sebagian).

### 4. Tutup milestone

1. Uji kembali semua kriteria keberhasilan sumber (dari dokumen `rancangan-*.md` terkait) secara end-to-end.
2. Tulis `milestones/<id>-<slug>/report.md` berisi hasil aktual, bukti verifikasi, keputusan final relevan, perubahan dari plan, keterbatasan/provisional item, dan follow-up bila ada. Untuk milestone yang punya "Catatan Serah Terima" di dokumen plan, konfirmasi eksplisit di report apakah kontrak yang diwariskan ke pekerjaan lain benar-benar terpenuhi sesuai bentuk yang dijanjikan.
3. Jangan menghapus atau menyembunyikan sejarah error/perubahan arah; log adalah catatan peristiwa, report adalah ringkasan hasil.

### Status Saat Ini

- **Fase desain SELESAI.** Delapan dokumen sumber kebenaran (2 arsitektur + 6 implementasi PIC) sudah ditulis dan diaudit silang — setiap kewajiban tersurat di kedua dokumen arsitektur terkonfirmasi memiliki rumah di salah satu dari 22 milestone (1.1–1.7, 2.1–2.4, 3.1–3.5, 4.1–4.5, 5.1–5.4, 6.1–6.2). Tidak ada milestone eksekusi yang sudah dimulai.
- **Urutan pengerjaan yang disarankan** (bukan kaku — lihat dokumen implementasi masing-masing untuk alasan urutan): Milestone 1.1 (fondasi Collector) wajib duluan — prasyarat sebelum PIC manapun bisa emit span. Setelah PIC 1 selesai, PIC 2 (RBAC), PIC 3 (Retrieval), dan PIC 6 (Custom Exporter) boleh berjalan paralel — PIC 6 khususnya hanya butuh kontrak span dari dokumen observability, tidak perlu menunggu implementasi PIC 2/3/4 nyata. PIC 4 (Execution & Interpretation) menunggu kontrak final dari PIC 2 dan PIC 3. PIC 5 (Observability Dashboard) di ekor, murni konsumsi — boleh mulai lebih awal dengan data dummy mengikuti skema Bagian 4 dokumen observability, tanpa menunggu PIC 6 selesai mengalirkan data asli.
- **Tiga area yang sudah teridentifikasi eksplisit sebagai keputusan terbuka**, tercatat di dokumen arsitektur/implementasi terkait, akan pindah ke `docs/keputusan-tertunda.md` begitu file itu diinisialisasi: mekanisme pencocokan Milestone 1.7 (LLM semantik vs deterministik — perlu bukti empiris dari implementasi nyata), daftar eksplisit view kategori "cakupan-individu" untuk Milestone 2.3 (perlu tinjauan langsung ke 67 view), dan keputusan lanjut/pindah fallback untuk PIC 6 (custom exporter Go vs sidecar Python, bergantung kecepatan progres).
- Model per langkah dan provider routing (Claude Console / OpenRouter) belum ditentukan — akan menjadi keputusan teknis pertama yang perlu diajukan ke user begitu implementasi Milestone 1.2 dimulai.
- Repo belum diinisialisasi/di-push ke remote manapun.

Perbarui bagian ini bila status proyek secara keseluruhan berubah. Untuk progres rinci, gunakan artefak milestone, bukan tabel ini sebagai pengganti log.

## Git dan Kualitas Perubahan

- Periksa `git status` sebelum dan sesudah bekerja.
- Jangan mengubah atau menghapus pekerjaan pengguna yang tidak relevan dengan task aktif.
- Satu checkpoint tervalidasi bisa terdiri dari beberapa commit, dipisah per kategori Conventional Commits (`feat`, `fix`, `docs`, `test`, `chore`, dst.) — bukan satu commit besar yang mencampur kode dan dokumentasi. Yang **atomik** adalah tiap commit individual (satu commit = satu kategori perubahan yang koheren), bukan checkpoint sebagai satu kesatuan tunggal. Lihat Workflow Wajib "3. Implementasikan per checkpoint" untuk aturan lengkapnya — jangan menggabungkan refactor, fitur, dan perubahan dokumentasi yang tidak berkaitan ke dalam satu commit yang sama.
- Sebelum commit, periksa staged diff, pastikan tidak ada secret (kredensial `chatbot_api`, Supabase, provider LLM), dan jalankan verifikasi yang relevan dengan perubahan.
- Jangan gunakan `git reset --hard`, force push, atau operasi destruktif lain tanpa instruksi eksplisit pengguna.
- Jangan push atau membuat remote tanpa instruksi eksplisit pengguna.

## Batas Implementasi Saat Ini

- Jangan memodifikasi `chatbot_api`, 67 view `chatbot_views`, atau `role_permissions` — seluruhnya sudah selesai dan terverifikasi di luar cakupan proyek ini. Konsumsi sebagai HTTP client saja.
- Jangan membangun ulang penegakan RBAC row-level (`property_id`/`own_property`/`all_properties`) — itu sepenuhnya tanggung jawab `chatbot_api`.
- Jangan memilih tool, model LLM, provider, skema penyimpanan Session Memory, atau kontrak yang dokumen arsitektur/implementasi sengaja biarkan terbuka (ditandai `[KERANGKA AWAL]`, "Catatan Ketidakpastian", atau di "Bagian 8 — Yang Masih Terbuka") tanpa mengikuti workflow keputusan di atas.
- Jangan membangun kapabilitas di luar cakupan delapan dokumen sumber kebenaran, termasuk mekanisme deployment produksi penuh di luar yang eksplisit disebut tiap PIC (deployment tersebar sebagai bagian "definisi selesai" masing-masing pekerjaan), kecuali pengguna memperluas cakupan.

## Cara Memulai Sesi Kerja

Sebelum perubahan non-trivial, nyatakan konteks yang dibaca, milestone aktif, dependensi, keputusan yang sudah final, dan gap yang masih terbuka. Jika ada konflik antara dokumen atau implementasi, berhenti, jelaskan konflik dengan bukti, tawarkan alternatif, dan tunggu arahan pengguna.
