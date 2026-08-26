# Kebijakan Versi

*[English](VERSIONING.md)*

Proyek ini mengikuti [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`), disesuaikan untuk layanan API backend, bukan library:

| Kenaikan | Dipicu oleh |
|---|---|
| **MAJOR** | Perubahan breaking pada kontrak request/response `POST /v1/turns` (lihat [`docs/panduan-integrasi-frontend.md`](panduan-integrasi-frontend.md)), atau perubahan perilaku RBAC yang mengubah siapa berwenang melihat apa. |
| **MINOR** | Kapabilitas baru ditambahkan tanpa merusak kontrak yang sudah ada — layer pemrosesan baru, field opsional baru, kapabilitas deployment/operasional baru (mis. pipeline deployment produksi yang akan datang). |
| **PATCH** | Bug fix, refactor internal, atau kenaikan versi dependency tanpa perubahan yang teramati pada kontrak atau perilaku RBAC. |

## Di mana versi disimpan

- **[`pyproject.toml`](../pyproject.toml)** (`[project].version`) adalah satu-satunya sumber kebenaran versi saat ini.
- Tiap rilis mendapat **git tag annotated** (`vX.Y.Z`) yang cocok dengan versi itu.
- **[`CHANGELOG.md`](../CHANGELOG.md)** mendokumentasikan tiap rilis yang di-tag di bawah heading `## [X.Y.Z] - YYYY-MM-DD`, mengikuti format [Keep a Changelog](https://keepachangelog.com/).

## Kenapa `v1.0.0` sekarang, meski deployment masih tertunda

Seluruh 7 lini kerja pemrosesan inti (24 milestone) dan fondasi CI/CD (lint, secret scan, dependency scan, test gate, regression suite RBAC, gate evaluasi prompt LLM, dan scan keamanan adversarial terjadwal) sudah selesai dan diverifikasi independen. Yang tersisa — provisioning VPS produksi, reverse proxy dengan TLS, dan pipeline deploy otomatis — adalah *infrastruktur* deployment, bukan perubahan kontrak API atau perilaku sistem. `v1.0.0` menandai "software-nya lengkap dan berperilaku sesuai dokumentasi"; milestone deployment akan mendarat sebagai kenaikan `MINOR` begitu selesai, karena menambah kapabilitas operasional (dapat diakses publik, rilis otomatis) tanpa mengubah kontrak.

Sebelum proyek ini mencapai titik ini, `pyproject.toml` berada di `0.1.0` pra-1.0 tanpa tag sama sekali — sesuai konvensi SemVer, itu berarti "apa pun masih bisa berubah". Itu bukan lagi sinyal yang akurat sekarang setelah sistem inti stabil dan diverifikasi independen dari ujung ke ujung.
