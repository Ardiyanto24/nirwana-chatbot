"""Retry E02/E03 dengan session_id baru - percobaan pertama gagal_teknis
murni di Domain Gate (M2.1, LLM hiccup, tidak terkait wiring M7.14),
nol item mencapai Execution sama sekali. Reuse fungsi run_eval.py."""

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_spec = importlib.util.spec_from_file_location("run_eval_m714", Path(__file__).parent / "run_eval.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def run_e02b():
    raw = {
        "session_id": "eval-7.14-e02b",
        "turn_index": 1,
        "role_title": "HR Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana hasil review kinerja Budi semester ini?",
    }
    return _mod._jalankan_kejadian(
        "E02", "Baseline 1 wave, koreksi paksa employee_id (retry - percobaan 1 gagal_teknis Domain Gate)", raw
    )


def run_e03b():
    raw = {
        "session_id": "eval-7.14-e03b",
        "turn_index": 1,
        "role_title": "Maintenance Staff",
        "employee_id": "emp-eval",
        "question": "Berapa banyak tiket yang ditangani teknisi Andi bulan ini?",
    }
    return _mod._jalankan_kejadian(
        "E03", "Bukti kedua independen, domain facility (retry - percobaan 1 gagal_teknis Domain Gate)", raw
    )


def main():
    _mod._cek_prasyarat()
    _mod._setup_tracing_dengan_capture()

    for label, runner in [("E02", run_e02b), ("E03", run_e03b)]:
        print(f"Menjalankan {label} (retry)...")
        record = runner()
        _mod._simpan(record)
        print(f"  trace_id={record['trace_id']}")
        for laporan in record["laporan_execution"]:
            print(
                f"  intent={laporan['atomic_intent_id'][:8]} "
                f"status={laporan['status']} "
                f"bug_prioritas_tinggi={laporan['bug_prioritas_tinggi']} "
                f"kegagalan_alasan={laporan['kegagalan_alasan']}"
            )
        print(f"  analisis_wave={json.dumps(record['analisis_wave'], ensure_ascii=False)}")
        print(f"  domain_gate_status={[d['status'] for d in record['hasil']['domain_gate']]}")


if __name__ == "__main__":
    main()
