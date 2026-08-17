"""Jalankan skenario di rancangan.md, simpan payload lengkap ke payloads/,
cetak ringkasan match/mismatch ke console.

Reuse verifikasi_bentuk_request_atomic_intent() produksi langsung
(panggilan LLM NYATA, bukan logic duplikat/mock). `AtomicIntent` dan
`QueryEngineRequest` dikonstruksi manual per skenario (mensimulasikan
hasil M3.4/M3.1-3.3, tidak menunggu pipeline penuh - mirror pola
evals/3.4-penyusunan-request/run_eval.py).

Jalankan dari root repo: uv run python evals/3.5-verifikasi-bentuk-request/run_eval.py
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.query_engine.verifikasi_bentuk_request import (
    verifikasi_bentuk_request_atomic_intent,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.session_memory import LabelBentukJawaban
from src.schemas.verification_gate import QueryEngineRequest

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"


def _ai(teks: str, label: LabelBentukJawaban) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=label,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _request(domain: Domain, view_name: str, params: dict) -> QueryEngineRequest:
    return QueryEngineRequest(domain=domain, view_name=view_name, params=params)


def _scenario_s01() -> dict:
    return {
        "id": "S01",
        "deskripsi": "KK1: view_name sengaja tidak sesuai Retriever",
        "atomic_intent": _ai("Berapa okupansi Bali bulan lalu?", LabelBentukJawaban.NILAI_TUNGGAL),
        "view_name_tervalidasi_retriever": "v_reservation_room_type_daily",
        "request": _request(
            Domain.RESERVATION, "v_reservation_channel_daily", {"property_id": "P01"}
        ),
        "check": lambda lolos, alasan: lolos is False and alasan is not None,
    }


def _scenario_s02() -> dict:
    return {
        "id": "S02",
        "deskripsi": "KK2: label tren, rentang tanggal dipersempit satu hari",
        "atomic_intent": _ai(
            "Bagaimana tren revenue outlet F&B tiga bulan terakhir?", LabelBentukJawaban.TREN
        ),
        "view_name_tervalidasi_retriever": "v_fnb_outlet_daily",
        "request": _request(
            Domain.FNB,
            "v_fnb_outlet_daily",
            {"period_date_from": "2026-08-17", "period_date_to": "2026-08-17"},
        ),
        "check": lambda lolos, alasan: lolos is False,
    }


def _scenario_s03() -> dict:
    return {
        "id": "S03",
        "deskripsi": "Kontrol positif: request tren valid, rentang cukup panjang",
        "atomic_intent": _ai(
            "Bagaimana tren revenue outlet F&B tiga bulan terakhir?", LabelBentukJawaban.TREN
        ),
        "view_name_tervalidasi_retriever": "v_fnb_outlet_daily",
        "request": _request(
            Domain.FNB,
            "v_fnb_outlet_daily",
            {"period_date_from": "2026-05-17", "period_date_to": "2026-08-17"},
        ),
        "check": lambda lolos, alasan: lolos is True,
    }


def _scenario_s04() -> dict:
    return {
        "id": "S04",
        "deskripsi": "Kontrol positif: request nilai_tunggal valid",
        "atomic_intent": _ai("Berapa okupansi Bali bulan lalu?", LabelBentukJawaban.NILAI_TUNGGAL),
        "view_name_tervalidasi_retriever": "v_reservation_room_type_daily",
        "request": _request(
            Domain.RESERVATION,
            "v_reservation_room_type_daily",
            {"property_id": "P01", "period_date_from": "2026-07-01", "period_date_to": "2026-07-31"},
        ),
        "check": lambda lolos, alasan: lolos is True,
    }


def _scenario_s05() -> dict:
    """Replikasi PERSIS payload evals/3.4-penyusunan-request/payloads/S04.json
    - nilai occupancy_rate nonsensikal yang SENGAJA tidak diperbaiki M3.4."""
    return {
        "id": "S05",
        "deskripsi": "Replikasi temuan nyata S04 M3.4: nilai parameter nonsensikal",
        "atomic_intent": _ai(
            "Okupansi Nirwana Lombok Escape bulan ini", LabelBentukJawaban.NILAI_TUNGGAL
        ),
        "view_name_tervalidasi_retriever": "v_reservation_room_type_daily",
        "request": _request(
            Domain.RESERVATION,
            "v_reservation_room_type_daily",
            {
                "property_name": "Nirwana Lombok Escape",
                "period_date_from": "2026-08-01",
                "period_date_to": "2026-08-31",
                "occupancy_rate": "nilai_tunggal",
            },
        ),
        "check": lambda lolos, alasan: lolos is False,
    }


SCENARIOS = [
    _scenario_s01(),
    _scenario_s02(),
    _scenario_s03(),
    _scenario_s04(),
    _scenario_s05(),
]


def _run_scenario(scenario: dict) -> dict:
    hasil = verifikasi_bentuk_request_atomic_intent(
        scenario["atomic_intent"],
        scenario["view_name_tervalidasi_retriever"],
        scenario["request"],
    )
    match = hasil.status.value == "berhasil" and scenario["check"](hasil.lolos, hasil.alasan)
    return {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "atomic_intent": scenario["atomic_intent"].model_dump(mode="json"),
        "view_name_tervalidasi_retriever": scenario["view_name_tervalidasi_retriever"],
        "request_input": scenario["request"].model_dump(mode="json"),
        "result": hasil.model_dump(mode="json"),
        "match": match,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    only_id = sys.argv[1] if len(sys.argv) > 1 else None

    results = []
    for scenario in SCENARIOS:
        if only_id and scenario["id"] != only_id:
            continue
        record = _run_scenario(scenario)
        results.append(record)
        (OUTPUT_DIR / f"{record['scenario_id']}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"{record['scenario_id']} selesai, match={record['match']}", flush=True)

    if only_id:
        return

    print(f"\n{'ID':<5} {'MATCH':<10} {'DESKRIPSI'}")
    print("-" * 80)
    for r in sorted(results, key=lambda x: x["scenario_id"]):
        status = "LOLOS" if r["match"] else "REVIEW"
        print(f"{r['scenario_id']:<5} {status:<10} {r['deskripsi']}")

    matched = sum(1 for r in results if r["match"])
    print(f"\n{matched}/{len(results)} skenario lolos.")
    print(f"Payload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
