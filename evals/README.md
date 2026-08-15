# Evals — Pengujian Perilaku LLM

Folder ini menampung pengujian **perilaku model AI** (LLM) di proyek nirwana-chatbot — beda dari `tests/` yang isinya unit test kode biasa (validasi struktural, logic deterministik, dicek dengan `assert` otomatis).

Perbedaan mendasar dengan `tests/`:

| | `tests/` (pytest) | `evals/` |
|---|---|---|
| Yang diuji | Logic kode (validasi, parsing, endpoint) | Perilaku model AI atas skenario bahasa natural |
| Cara menilai | `assert` otomatis, hasil pasti benar/salah | Kombinasi otomatis (match/mismatch) + **audit manual** — sebagian skenario butuh penilaian (mis. jawaban ambigu yang tetap defensible) |
| Bukti disimpan | Hasil pass/fail di output pytest | Payload lengkap (request + response mentah) per skenario, untuk inspeksi/audit kapan pun |
| Dijalankan | Tiap kali kode berubah (regression) | Saat menguji/meninjau ulang perilaku model untuk satu kemampuan tertentu |

## Konvensi Struktur

Satu subfolder per kemampuan/milestone yang memanggil LLM, mirror penamaan `milestones/<id>-<slug>/`:

```
evals/<id>-<slug-milestone>/
├── rancangan.md      # Skenario + kriteria keberhasilan, ditulis SEBELUM eksekusi
├── run_eval.py        # Skrip yang mendefinisikan skenario (sesuai rancangan.md) dan menjalankannya
├── payloads/           # Request+response mentah per skenario (JSON), hasil eksekusi run_eval.py
│   └── <ID_SKENARIO>.json
└── audit.md            # Ditulis SETELAH eksekusi - ekspektasi vs aktual, verdict per skenario, penilaian kasus ambigu
```

## Kapan Dipakai

Proyek ini punya banyak milestone yang memanggil LLM (Context Resolution M1.3/1.4/1.7, Decomposition M1.6, Domain Gate M2.x, Retriever M3.x, Interpretation M4.x, dst). Tiap kali salah satunya butuh pengujian yang lebih menyeluruh dari sekadar skenario minimal Kriteria Keberhasilan sumber (mis. menguji ketahanan terhadap kasus ambigu, negasi, jebakan false-positive/negative), ikuti pola yang sama: tulis `rancangan.md` dulu (skenario + ekspektasi + kriteria), baru eksekusi, baru `audit.md`.

## Referensi Contoh

`evals/1.3-pemetaan-ketergantungan-turn/` — eval pertama yang mengikuti konvensi ini, untuk `detect_turn_dependency()` (`src/layers/context_resolution/turn_dependency.py`).
