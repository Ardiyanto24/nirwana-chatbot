# Logs — Milestone 2.4: Membangun Verification Gate

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | *(menyusul)* | `docs(milestone-2.4): decisions` |

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan. Dua keputusan genuinely terbuka (konvensi filter employee_id, tabel employees) dikonfirmasi lewat DUA putaran `AskUserQuestion` SEBELUM plan ditulis (putaran pertama mengajukan gap kontrak, putaran kedua setelah user meminta klarifikasi dan memberikan `employees_deduped.csv` nyata) — `decisions.md` di sini mendokumentasikan hasil konfirmasi itu.

**Apa yang dilakukan**
9 entri keputusan: 2 Jenis A genuinely terbuka (konvensi employee_id sebagai filter cakupan-individu — eksplisit ditandai PROVISIONAL/belum dikonfirmasi tim database engineering; tabel employees Supabase khusus fixture test), 7 Jenis B forced/preseden (subpackage verification_gate/ terpisah dari domain_gate/, params tetap dict opaque, error.type=gagal_teknis, verification.check_name 4 nilai, tidak ada folder evals/, hire_date str polos karena inkonsistensi data nyata, decisions.md sebagai task pertama).

**Temuan**
Riset kontrak sebelum plan (agent Explore) mengonfirmasi gap arsitektur nyata: `api-chatbot.md` tidak mendokumentasikan parameter apa pun untuk filter level-individu — `staff_id=self` di dokumen arsitektur (baris 187) murni ilustrasi, bukan parameter terkontrak. Ini BUKAN kegagalan riset, melainkan keterbatasan nyata dokumen sumber yang harus ditangani sebagai keputusan provisional, bukan diasumsikan pasti benar.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** *(menyusul)*
