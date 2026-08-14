# Keputusan Tertunda — Backlog Project-Wide

Dokumen ini mencatat keputusan teknis yang genuinely terbuka tapi **belum saatnya diambil** — beda dari `docs/keterbatasan-diterima.md` (keterbatasan yang sudah ditemukan dan sengaja diterima) dan `decisions.md` per-milestone (keputusan yang sudah final). Tiap entri menyebut konteks kemunculannya dan pemicu peninjauan ulang yang membuatnya layak diputuskan.

---

## 1. Database untuk Proyek Ini (Session Memory + Kemungkinan Migrasi Daftar Role)

**Muncul di:** Milestone 1.2 (Input Layer), saat mendiskusikan penyimpanan daftar 20 `role_title` untuk validasi struktural (2026-08-14).

**Konteks kemunculan:** Awalnya dipertimbangkan hardcode daftar role sebagai konstanta Python di Input Layer. User mempertanyakan apakah proyek ini sebaiknya punya database sendiri, mengingat Milestone 1.5 (Session Memory) akan butuh storage juga. Dikonfirmasi secara arsitektur: proyek ini **boleh** punya database sendiri (terpisah dari database data platform — larangan "REST API bukan akses SQL" di `arsitektur-ai-chatbot-rbac.md` baris 7 hanya soal database data platform, bukan database milik proyek Lapis 1 ini sendiri). Milestone 1.5 sendiri eksplisit menyatakan "keputusan implementasi bebas" soal teknologi storage Session Memory.

Untuk Milestone 1.2 spesifik, diputuskan **file config YAML** (`src/config/roles.yaml`) sebagai jalan tengah — tidak menambah kompleksitas database sebelum kebutuhan Session Memory yang sesungguhnya diketahui, tapi juga tidak serigid hardcode Python. Keputusan database *utuh* untuk proyek (dipakai Session Memory, dan berpotensi juga jadi tempat daftar role dipindahkan) sengaja ditunda ke sini.

**Kenapa belum saatnya diputuskan:** Milestone 1.5 belum dimulai — teknologi storage yang tepat sebaiknya dipilih dengan konteks kebutuhan Session Memory yang sesungguhnya (skema paket per atomic intent, pola akses/query, TTL, dst — lihat `arsitektur-ai-chatbot-rbac.md` §7), bukan diputuskan sekarang hanya berdasar kebutuhan kecil (20 baris statis daftar role).

**Pemicu peninjauan ulang:** Awal implementasi Milestone 1.5 (Penarikan/Penyimpanan Data Session Memory) — saat itu, putuskan teknologi storage (mis. SQLite/PostgreSQL/lainnya) untuk Session Memory, dan sekalian evaluasi apakah `src/config/roles.yaml` sebaiknya dipindahkan ke database yang sama (kemudahan admin terpusat) atau tetap sebagai file config terpisah (kesederhanaan, tidak ada dependency tambahan untuk data yang jarang berubah).
