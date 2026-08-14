# Keterbatasan Diterima — Backlog Project-Wide

Dokumen ini mencatat keterbatasan teknis yang **ditemukan** selama pengerjaan proyek dan **sengaja diterima** (bukan diperbaiki), karena biaya perbaikan tidak sepadan atau di luar kendali tim ini. Lintas milestone — berbeda dari `decisions.md` per-milestone yang isinya keputusan desain, bukan keterbatasan yang ditemukan di tengah jalan.

Format tiap entri: konteks penemuan, kenapa diterima, dampak + mitigasi, dan pemicu peninjauan ulang.

---

## 1. Governance OTel GenAI Semantic Conventions pindah repo, belum ada paket Python resmi di repo baru

**Ditemukan di:** Milestone 1.1, Checkpoint 3, Task 8 (2026-08-14).

**Konteks penemuan:** Saat mengunci versi konvensi atribut `gen_ai.*` (kewajiban eksplisit Milestone 1.1), ditemukan bahwa seluruh konstanta `gen_ai.*` di paket `opentelemetry-semantic-conventions` (versi ter-install: `0.65b0`) sudah ditandai "Deprecated" di docstring, dengan catatan governance spesifikasi GenAI pindah dari repo utama `open-telemetry/semantic-conventions` ke repo terpisah `open-telemetry/semantic-conventions-genai` sejak rilis `semantic-conventions v1.42.0` (2026-06-12). Dikonfirmasi lewat web search + `WebFetch` ke repo baru: per 2026-08-14, repo tersebut **belum punya release/tag resmi maupun paket PyPI generated-code sendiri** untuk konstanta atribut Python. Nilai string atribut yang dipakai proyek ini (`gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.conversation.id`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) dikonfirmasi **identik** antara paket lama dan dokumentasi repo baru — belum ada rename, hanya perpindahan governance dokumentasi/stabilitas.

**Kenapa diterima (bukan diperbaiki):** Tidak ada alternatif yang lebih baik tersedia saat ini — repo baru belum menerbitkan paket Python apa pun untuk dependency langsung. Menunda Milestone 1.1 sampai repo baru merilis paket resmi bukan pilihan wajar (tidak ada linimasa yang diketahui, dan konvensi ini memang secara eksplisit didesain "pre-stable" oleh OTel sendiri — sesuai catatan di header `rancangan-observability-ai-chatbot.md`).

**Dampak + mitigasi:** Kode proyek (`src/observability/genai_semconv.py`, dipindah dari `infra/observability/` di Milestone 1.2) tetap mengimpor dari `opentelemetry.semconv._incubating.attributes.gen_ai_attributes`, dipin lewat `opentelemetry-semantic-conventions==0.65b0` di `uv.lock`. Dampak: perubahan nama atribut di masa depan (kalau terjadi saat repo baru mulai stabil) tidak akan otomatis tertangkap oleh dependency checker manapun — harus dicek manual. Mitigasi: seluruh konstanta yang dipakai proyek diisolasi lewat satu modul (`genai_semconv.py`), sehingga kalau terjadi perubahan nyata, cukup satu file yang perlu diperbarui, bukan tersebar di seluruh kode 9 layer.

**Pemicu peninjauan ulang:** (a) setiap kali `opentelemetry-semantic-conventions` di-upgrade versi lewat `uv lock --upgrade`, cek ulang apakah modul `gen_ai_attributes` masih ada dan nilainya belum berubah; (b) sebelum Milestone 2.1 (instrumentasi PIC 2 pertama di luar PIC 1) dimulai, cek apakah `open-telemetry/semantic-conventions-genai` sudah merilis paket Python resmi — kalau sudah, evaluasi migrasi; (c) kalau ada breaking rename pada atribut yang dipakai proyek ini di rilis semantic-conventions manapun, revisi `genai_semconv.py` segera dan catat sebagai entri `decisions.md` baru di milestone yang sedang berjalan saat itu.

---

## 2. Payload turn membawa histori sesi penuh — bisa membesar untuk sesi sangat panjang

**Ditemukan di:** Milestone 1.3, Checkpoint 1 (2026-08-14), sebagai konsekuensi langsung revisi kontrak payload (lihat `decisions.md` Milestone 1.3 Keputusan 1).

**Konteks penemuan:** Payload M1.2 direvisi membawa seluruh histori turn dalam sesi (bukan window terbatas) supaya Milestone 1.3 bisa mendeteksi rujukan ke turn manapun dalam sesi, termasuk yang jauh dari turn saat ini. Konsekuensinya: ukuran payload bertambah linear seiring sesi memanjang — tidak ada mekanisme ringkasan, pemangkasan, atau kompresi histori sama sekali di titik ini.

**Kenapa diterima (bukan diperbaiki):** Belum ada bukti nyata bahwa ini jadi masalah operasional (belum ada frontend/traffic sungguhan). Membangun mekanisme ringkas/pangkas sekarang berarti menyelesaikan masalah yang belum terbukti ada, berpotensi menambah kompleksitas yang tidak diperlukan (mis. threshold panjang sesi, strategi ringkasan mana yang dipilih) sebelum ada data nyata soal pola panjang sesi yang sesungguhnya terjadi.

**Dampak + mitigasi:** Sesi yang sangat panjang (puluhan turn) akan mengirim payload besar tiap request, berpotensi memperlambat request atau menyentuh limit ukuran body HTTP/context window LLM di langkah-langkah yang memprosesnya (M1.3 dan seterusnya). Mitigasi saat ini: tidak ada mekanisme aktif — diterima sebagai keterbatasan awal desain.

**Pemicu peninjauan ulang:** (a) begitu ada payload sungguhan dari frontend nyata dengan sesi yang cukup panjang untuk diukur, evaluasi apakah ukuran payload benar-benar jadi masalah; (b) kalau context window model LLM manapun yang dipakai di Context Resolution (M1.3/1.4/1.7) mulai terlampaui oleh histori panjang, revisi mendesak diperlukan (mis. ringkasan histori lama, atau batasi ke N-turn + fallback ke session memory untuk turn yang lebih tua — catatan: opsi terakhir ini butuh Session Memory, M1.5, sudah tersedia).
