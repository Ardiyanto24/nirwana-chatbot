# Rancangan RBAC untuk AI Chatbot — Revisi Granularitas `corporate_master`

**Nirwana Hospitality Group — Data Platform ELT**

| | |
|---|---|
| **Dokumen induk** | `rancangan-arsitektur-data-platform-elt.md` |
| **Referensi silang** | Bagian 8.2 (RBAC dua lapis AI Chatbot) dokumen induk |
| **Tujuan dokumen** | Merancang ulang skema `role_permissions` — bukan sekadar memetakan yang sudah ada — supaya benar-benar mencerminkan prinsip *segregation of responsibility*: satu posisi hanya mengakses data yang menjadi tanggung jawabnya |
| **Status sumber data** | `role_permissions` (42 baris) di data production **bukan acuan final** — tabel ini dibuat sendiri oleh pemilik sistem dalam tahap eksplorasi, dan secara eksplisit terbuka untuk dirancang ulang |
| **Status dokumen** | Rancangan disetujui — pengganti skema `corporate_master` lama |

---

## Konteks: Kenapa Dokumen Ini Ada

Selama proses pemetaan kebutuhan AI Chatbot, ditemukan bahwa domain `corporate_master` di `role_permissions` yang ada saat ini terlalu kasar granularitasnya: satu izin akses mencakup 4 tabel dengan sensitivitas yang sangat berbeda (`properties` — rendah, `employees` — sedang/tinggi, `guests` — tinggi/PII, `role_permissions` — kunci keamanan sistem itu sendiri). Ditemukan juga inkonsistensi tanpa alasan bisnis yang jelas di skema lama (mis. `Housekeeping Manager` tidak dapat `corporate_master` sementara `Maintenance Manager` — sesama manager level `facility` — dapat).

Karena pemilik sistem mengonfirmasi tabel `role_permissions` ini dibuat sendiri dalam tahap eksplorasi (bukan hasil keputusan final tim), dokumen ini merancang ulang pembagian akses `corporate_master` menjadi lebih granular, dengan prinsip: **setiap posisi hanya mengakses data yang menjadi tanggung jawabnya** — termasuk pemisahan properti (`own_property` vs `all_properties`) dan pemisahan jenis data dalam satu tabel sumber yang sama.

---

## 1. Pemecahan `corporate_master` Menjadi 4 Kelompok Granular

Domain `corporate_master` lama (4 tabel: `properties`, `employees`, `guests`, `role_permissions`) dipecah menjadi:

| Kelompok baru | Isi | Sensitivitas | Alasan pemisahan |
|---|---|---|---|
| **`properties_ref`** | `properties` (seluruh kolom) | Rendah | Metadata ringan (nama, lokasi, tahun dibangun) — aman untuk siapa saja yang sudah punya akses ke propertinya |
| **`employees_directory`** | `employees` (seluruh kolom) | Sedang–Tinggi | Data pribadi karyawan, tapi bukan yang paling sensitif di sistem (beda dari `payroll`) |
| **`guests_pii`** | `guests`, kolom kontak saja: `full_name`, `email`, `phone` | Tinggi (PII personal) | Dibutuhkan hanya untuk interaksi langsung dengan tamu, bukan untuk analisis |
| **`guests_profile`** | `guests`, kolom atribut analitis: `loyalty_tier`, `nationality`, riwayat booking (tidak termasuk kontak) | Sedang | Dibutuhkan untuk strategi pricing/segmentasi, tanpa perlu tahu kontak personal tamu |
| *(tidak dipetakan ke kelompok mana pun)* | `role_permissions` | Tertinggi — kunci keamanan sistem | **Sengaja tidak diberikan sebagai izin ke peran mana pun, termasuk CEO.** Tabel ini adalah alat kontrol akses itu sendiri — memberi akses "baca" atasnya lewat chatbot bertentangan dengan fungsinya sebagai kunci keamanan, mengikuti prinsip yang sama seperti audit trail: sistem yang diatur oleh sebuah matriks kontrol tidak boleh bisa membaca ulang matriks itu sendiri lewat jalur yang sama yang ia atur |

**Catatan tentang `guests`**: pemisahan `guests_pii` vs `guests_profile` bukan pemisahan tabel, melainkan pemisahan kolom dalam satu tabel yang sama — mengikuti pola yang sudah ada di data dictionary produksi (`payroll` sengaja dipisah dari `employees` karena beda kontrol akses). Saat implementasi, ini berarti dua *view* atau dua *kelompok kolom* dengan izin berbeda atas tabel fisik `guests` yang sama, bukan dua tabel fisik terpisah.

---

## 2. Rancangan `role_permissions` Baru — Lengkap per Peran

Domain operasional (7 domain: `reservation`, `fnb`, `facility`, `spa_event`, `hr`, `financial`, dan sekarang tanpa `corporate_master`) **tidak diubah** dari skema lama — hanya domain `corporate_master` yang direvisi jadi 4 kelompok granular di atas. Seluruh `permission_type` diperlakukan sebagai **`read` saja** untuk konteks AI Chatbot, konsisten dengan Bagian 8.2 dokumen arsitektur induk (chatbot hanya `SELECT` ke `mart_aggregated`, tidak pernah punya jalur tulis).

| Peran | Domain operasional | `properties_ref` | `employees_directory` | `guests_pii` | `guests_profile` |
|---|---|---|---|---|---|
| **CEO** | Semua 7, all_properties | ✅ all_properties | ✅ all_properties | ✅ all_properties | ✅ all_properties |
| **Corporate Finance Director** | financial, reservation, all_properties | ✅ all_properties | ✅ all_properties | ❌ | ❌ |
| **Corporate HR Director** | hr, all_properties | ✅ all_properties | ✅ all_properties | ❌ | ❌ |
| **Corporate Operations Director** | facility, fnb, spa_event, reservation, all_properties | ✅ all_properties | ✅ all_properties | ❌ | ❌ |
| **Corporate Revenue Director** | reservation, financial, all_properties | ✅ all_properties | ❌ | ✅ all_properties | ✅ all_properties |
| **General Manager** | Semua 7, own_property | ✅ own_property | ✅ own_property | ❌ | ❌ |
| **Revenue Manager** | reservation, own_property | ✅ own_property | ❌ | ✅ own_property | ✅ own_property |
| **F&B Manager** | fnb, own_property + reservation, own_property | ✅ own_property | ✅ own_property | ❌ | ❌ |
| **Housekeeping Manager** | facility, own_property + reservation, own_property | ✅ own_property | ✅ own_property | ❌ | ❌ |
| **Maintenance Manager** | facility, own_property | ✅ own_property | ✅ own_property | ❌ | ❌ |
| **Spa & Event Manager** | spa_event, own_property | ✅ own_property | ✅ own_property | ✅ own_property | ❌ |
| **HR Manager** | hr, own_property | ✅ own_property | ✅ own_property | ❌ | ❌ |
| **Finance Manager** | financial, own_property + reservation, own_property | ✅ own_property | ✅ own_property | ❌ | ❌ |
| **Front Office Staff** | reservation, own_property | ✅ own_property | ❌ | ✅ own_property | ❌ |
| **F&B Staff** | fnb, own_property | ❌ | ❌ | ❌ | ❌ |
| **Housekeeping Staff** | facility, own_property | ❌ | ❌ | ❌ | ❌ |
| **Maintenance Staff** | facility, own_property | ❌ | ❌ | ❌ | ❌ |
| **Spa & Event Staff** | spa_event, own_property | ❌ | ❌ | ✅ own_property | ❌ |
| **HR Staff** | hr, own_property | ❌ | ✅ own_property | ❌ | ❌ |
| **Finance Staff** | financial, own_property | ❌ | ✅ own_property | ❌ | ❌ |

---

## 3. Alasan Bisnis di Balik Keputusan Kunci

| Keputusan | Alasan |
|---|---|
| **Semua Manager & Corporate dapat `properties_ref`** | Metadata ringan, tidak ada alasan membatasinya secara berbeda antar peran setara. Ini memperbaiki inkonsistensi asli (`Housekeeping Manager` dulu tidak dapat `corporate_master`, sekarang diseragamkan dengan `Maintenance Manager`) |
| **Semua Manager & Corporate dapat `employees_directory` (termasuk Finance)** | Manager operasional (F&B/Maintenance/Housekeeping/Spa&Event) butuh untuk mengelola tim langsung. Finance Manager & Corporate Finance Director butuh untuk **tujuan berbeda**: rekonsiliasi payroll — memverifikasi status karyawan (aktif/resigned) sebelum memproses pembayaran, bukan untuk mengelola tim. Tanpa akses ini, proses payroll berjalan "buta" terhadap status karyawan aktual, yang merupakan risiko kontrol keuangan |
| **5 dari 7 Staff (F&B, Housekeeping, Maintenance, Spa&Event) tidak dapat satupun dari 4 kelompok baru** | Konsisten dengan pola asli — staff operasional murni bekerja dalam cakupan domain kerjanya sendiri, tidak perlu directory karyawan lain maupun data tamu |
| **HR Staff & Finance Staff (pengecualian) dapat `employees_directory`** | Ditemukan saat role-play kebutuhan chatbot: keduanya bekerja dengan data yang berisi `employee_id` (`staff_shifts`, `employee_performance`, `payroll`) dan perlu menerjemahkan ID tersebut menjadi nama karyawan. Beda dari 5 staff operasional lain yang murni bersifat "subjek data" — HR Staff & Finance Staff adalah "pengurus data" administratif, sehingga wajar mendapat directory dasar (nama, department), sama seperti alasan Finance Manager mendapatkannya untuk rekonsiliasi |
| **`guests_pii` (kontak) untuk Front Office Staff & Spa & Event Staff** | Ditemukan saat role-play kebutuhan chatbot: keduanya berinteraksi personal langsung dengan tamu (check-in/komplain untuk Front Office; booking spa/event untuk Spa & Event Staff) — bukan sekadar mencatat transaksi seperti F&B/Housekeeping/Maintenance Staff. Prinsip yang dipakai: akses `guests_pii` diberikan berdasarkan **sifat interaksi** (langsung dengan tamu atau tidak), bukan berdasarkan departemen semata |
| **`guests_profile` (atribut analitis) hanya Revenue Manager & Corporate Revenue Director** | Revenue management butuh atribut tamu (loyalty tier, nationality, riwayat booking) untuk strategi pricing/segmentasi/retensi — tapi tidak pernah berinteraksi langsung dengan tamu, sehingga tidak butuh kontak personal (`email`/`phone`) |
| **Rantai superset diperpanjang: `guests_pii` juga ditambahkan ke Corporate Revenue Director** | Setelah Revenue Manager direvisi mendapat `guests_pii`, Corporate Revenue Director (atasannya di domain `reservation` yang sama) akan menjadi lebih sempit dari bawahannya sendiri jika tidak ikut direvisi — audit superset perlu diperiksa berantai ke atas setiap kali ada revisi di tingkat manapun, bukan berhenti di satu pasangan tingkat saja |
| **F&B Manager, Housekeeping Manager, Finance Manager mendapat tambahan domain `reservation` (own_property)** | Ditemukan saat role-play kebutuhan chatbot: ketiganya butuh metrik yang sebagian datanya berasal dari domain `reservation` — capture rate F&B (tamu inhouse), delayed rate housekeeping terkait okupansi, dan korelasi service charge dengan okupansi. Diputuskan memberi akses domain `reservation` (own_property) langsung, bukan membatasi mereka hanya ke domainnya sendiri maupun membungkus hasil join sebagai kolom siap pakai di mart masing-masing |
| **`payroll` termasuk cakupan domain `financial`, tidak dipecah granular tersendiri** | Diputuskan payroll tidak perlu domain terpisah seperti `guests_pii`/`guests_profile` — siapa pun yang mendapat akses `financial` (own_property atau all_properties) otomatis dapat akses ke `payroll` juga |
| **Corporate Finance Director & Corporate Operations Director mendapat domain tambahan agar menjadi superset Manager di bawahnya** | Prinsip inti AI Chatbot adalah mempersingkat rantai eskalasi manual (Director tidak perlu lagi bertanya ke Manager, Manager ke Staff) — sehingga siapa pun di posisi lebih tinggi untuk domain yang sama harus minimal punya seluruh akses yang dimiliki bawahannya di domain itu, ditambah kapabilitas lintas-properti. Audit sistematis menemukan dua pelanggaran: Corporate Finance Director tidak memiliki `reservation` padahal Finance Manager sudah mendapatkannya (untuk metrik service charge vs okupansi), dan Corporate Operations Director tidak memiliki `employees_directory` maupun `reservation` padahal seluruh 4 Manager yang domainnya dia awasi (F&B, Housekeeping, Maintenance, Spa & Event Manager) memiliki setidaknya satu dari keduanya. Keduanya direvisi agar Director menjadi superset, bukan subset, dari Manager yang berada dalam cakupan tanggung jawabnya |
| **Revenue Manager & Spa & Event Manager mendapat tambahan `guests_pii`, agar menjadi superset Staff di bawahnya** | Audit yang sama diterapkan satu tingkat lebih rendah: Front Office Staff dan Spa & Event Staff sama-sama memiliki `guests_pii` (kontak tamu), tapi Revenue Manager dan Spa & Event Manager di domain yang sama tidak memilikinya — awalnya `guests_pii` dibatasi hanya untuk peran yang dinilai "berinteraksi langsung dengan tamu", tanpa mempertimbangkan bahwa ini membuat Manager menjadi lebih sempit dari Staff-nya sendiri. Prinsip superset ditegakkan konsisten di seluruh tingkat hierarki, tanpa pengecualian berdasarkan jenis interaksi |

---

## 4. Implikasi untuk Implementasi

- Pemecahan `guests_pii` vs `guests_profile` dilakukan di level **kolom**, bukan tabel — perlu dua definisi akses (mis. dua *view* `guests_contact_view` dan `guests_profile_view`) di atas tabel fisik `guests` yang sama, dieksekusi saat AI Agent menyusun query sesuai lapis RBAC pertama (Bagian 8.2 dokumen induk).
- `role_permissions` sebagai tabel tidak pernah menjadi target query chatbot dalam skenario apa pun — ini perlu ditegaskan secara eksplisit di logika validasi intent AI Agent (lapis pertama), bukan diasumsikan otomatis aman hanya karena tidak ada baris izinnya.
- Skema `role_permissions` di production perlu diperbarui mengikuti tabel Bagian 2 di atas — domain `corporate_master` lama pada 9 baris yang sebelumnya memilikinya (CEO, Corporate Finance Director, Corporate HR Director, F&B Manager, General Manager, HR Manager, Maintenance Manager, Revenue Manager, Spa & Event Manager) digantikan dengan kombinasi granular yang sesuai per peran, dan sejumlah peran baru ditambahkan aksesnya (Housekeeping Manager, Finance Manager, Corporate Finance Director untuk `employees_directory`; Front Office Staff untuk `guests_pii`; Revenue Manager & Corporate Revenue Director untuk `guests_profile`) sesuai tabel di atas.

---

*Dokumen ini menjadi dasar RBAC yang dipakai pada pemetaan kebutuhan tanya-jawab AI Chatbot per persona (dokumen terpisah).*
