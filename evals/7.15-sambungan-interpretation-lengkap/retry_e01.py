"""Retry E01 (turn 1+2) dengan session_id baru - percobaan pertama turn 1
gagal teknis (revisi_gagal_verifikasi_bentuk, view berbeda dari yang
terbukti Checkpoint 1) sehingga tidak pernah jadi kandidat "selesai" untuk
turn 2 (match_atomic_intents() M1.7 hanya menawarkan kandidat status=
berhasil). Sesuai rancangan.md "Catatan Non-Determinisme" - dipertimbangkan
retry SEKALI dengan session_id baru sebelum audit ditulis."""

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_spec = importlib.util.spec_from_file_location("run_eval_m715", Path(__file__).parent / "run_eval.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def run_e01b():
    session_id = "eval-7.15-e01d"
    raw_turn1 = {
        "session_id": session_id,
        "turn_index": 1,
        "role_title": "Maintenance Staff",
        "employee_id": "E0071",
        "question": "Berapa banyak tiket maintenance yang ditangani bulan ini?",
    }
    record_turn1 = _mod._jalankan_kejadian(
        "E01-turn1",
        "Turn 1 (retry ke-4, view facility) - dijalankan nyata, akan tersimpan Session Memory",
        raw_turn1,
    )

    raw_turn2 = {
        "session_id": session_id,
        "turn_index": 2,
        "role_title": "Maintenance Staff",
        "employee_id": "E0071",
        "question": "Bandingkan dengan jumlah tiket bulan lalu.",
        "history": [
            {
                "turn_index": 1,
                "question": raw_turn1["question"],
                "answer": record_turn1["narasi_final"],
            }
        ],
    }
    record_turn2 = _mod._jalankan_kejadian(
        "E01-turn2",
        "Turn 2 (retry) - KK literal utama, campuran selesai (turn 1)+eksekusi baru",
        raw_turn2,
    )
    return record_turn1, record_turn2


def main():
    _mod._cek_prasyarat()
    _mod._setup_tracing_dengan_capture()

    print("Menjalankan E01 (retry, turn 1+2)...")
    record_turn1, record_turn2 = run_e01b()
    _mod._simpan(record_turn1)
    _mod._simpan(record_turn2)
    _mod._cetak_laporan(record_turn1)
    _mod._cetak_laporan(record_turn2)


if __name__ == "__main__":
    main()
