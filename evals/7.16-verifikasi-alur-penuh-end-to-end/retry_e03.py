"""Retry E03 SAJA - percobaan 1 (`session_id=eval-7.16-e03`) hang tanpa
exception ~20 menit (0 request OpenRouter baru, CPU proses nyaris nol)
setelah genuinely maju sampai Retriever (span terakhir tercatat:
`retriever.cari_kandidat_view` selesai, lalu 2 span `chat` kecukupan
struktural) - proses dihentikan paksa (`Stop-Process`), TIDAK ada
payload tersimpan (proses mati sebelum sempat menulis file). Pola HANG
IDENTIK `docs/keterbatasan-diterima.md` #7 (I/O-bound blocking tanpa
exception, CPU nyaris nol) - percobaan ini genuinely informed retry
(session_id BARU), bukan retry membabi-buta. E01/E02 SUDAH tersimpan
sukses di percobaan pertama, TIDAK diulang di sini.

Percobaan 2 (`session_id=eval-7.16-e03b`) HANG LAGI - kali ini maju
LEBIH JAUH (38 span, sampai akhir Retriever/awal Query Engine, offset
~676s) sebelum macet total ~5 menit (CPU proses 11.45->11.59, nyaris
tidak bergerak) - dihentikan paksa lagi. Pola berulang 2x berturut-turut
KHUSUS di E03 (E01/E02 sukses percobaan pertama) - kemungkinan besar
E03 punya rantai panggilan LLM lebih panjang (Decomposition komparatif
2-3 atomic intent x Retriever kecukupan per-item), memberi lebih banyak
KESEMPATAN kena hang infra acak (`docs/keterbatasan-diterima.md` #7),
bukan bug spesifik E03. Percobaan 3 (`session_id=eval-7.16-e03c`)
adalah upaya TERAKHIR sebelum didokumentasikan sebagai temuan formal -
konsisten filosofi project (M7.15 E01: diagnosis dulu, bukan retry
tanpa batas).

Jalankan dari root repo: uv run python evals/7.16-verifikasi-alur-penuh-end-to-end/retry_e03.py
"""

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_SPEC = importlib.util.spec_from_file_location(
    "run_eval_7_16", Path(__file__).resolve().parent / "run_eval.py"
)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)


def run_e03_percobaan3() -> dict:
    raw = {
        "session_id": "eval-7.16-e03c",
        "turn_index": 2,
        "role_title": "Corporate Revenue Director",
        "employee_id": "emp-eval",
        "question": "Bandingkan dengan bulan sebelumnya.",
        "history": [
            {
                "turn_index": 1,
                "question": "Berapa revenue reservasi bulan Maret 2026?",
                "answer": "Revenue reservasi Maret 2026 sebesar Rp 800 juta.",
            }
        ],
    }
    return _MOD._jalankan_kejadian(
        "E03",
        "Rujukan lintas-turn, history fiktif (mirror M7.7 E01) - percobaan 3, "
        "session_id baru setelah percobaan 1+2 hang (docs/keterbatasan-diterima.md #7)",
        raw,
    )


def main() -> None:
    _MOD._cek_prasyarat()
    _MOD._setup_tracing_dengan_capture()

    print("Menjalankan E03 (percobaan 3)...")
    record = run_e03_percobaan3()
    _MOD._simpan(record)
    print(f"  trace_id={record['trace_id']}")
    print(f"  lengkap={record['cakupan_span']['lengkap']}")
    print(f"  cakupan_unik={record['cakupan_span']['cakupan_unik']}")
    print(
        f"  chat_sebelum_domain_gate={record['cakupan_span']['chat_count_sebelum_domain_gate']} "
        f"chat_setelah_paket_narasi={record['cakupan_span']['chat_count_setelah_paket_narasi']} "
        f"memory_retrieve_ada={record['cakupan_span']['memory_retrieve_ada']}"
    )
    print(f"\nPayload tersimpan di: {_MOD.OUTPUT_DIR}")


if __name__ == "__main__":
    main()
