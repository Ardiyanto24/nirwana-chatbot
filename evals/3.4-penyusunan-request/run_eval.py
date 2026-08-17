"""Jalankan skenario di rancangan.md, simpan payload lengkap ke payloads/,
cetak ringkasan match/mismatch ke console.

Reuse susun_request_atomic_intent() produksi langsung (panggilan LLM
NYATA, bukan logic duplikat/mock). `tanggal_referensi` TETAP
(2026-08-17) untuk seluruh skenario supaya hasil resolusi tanggal bisa
dinilai literal, bukan bergeser tiap hari dijalankan ulang.

Jalankan dari root repo: uv run python evals/3.4-penyusunan-request/run_eval.py
"""

import json
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.query_engine.penyusunan_request import susun_request_atomic_intent
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.session_memory import LabelBentukJawaban

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
TANGGAL_REFERENSI = date(2026, 8, 17)


def _ai(teks: str, label: LabelBentukJawaban) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=label,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _scenario_s01() -> dict:
    return {
        "id": "S01",
        "deskripsi": "KK1: bulan lalu",
        "atomic_intent": _ai("Berapa okupansi Bali bulan lalu?", LabelBentukJawaban.NILAI_TUNGGAL),
        "view_name": "v_reservation_room_type_daily",
        "check": lambda p: p.get("period_date_from") == "2026-07-01" and p.get("period_date_to") == "2026-07-31",
    }


def _scenario_s02() -> dict:
    return {
        "id": "S02",
        "deskripsi": "KK1: tiga bulan terakhir",
        "atomic_intent": _ai(
            "Bagaimana tren revenue outlet F&B tiga bulan terakhir?", LabelBentukJawaban.TREN
        ),
        "view_name": "v_fnb_outlet_daily",
        "check": lambda p: _cek_jendela_tiga_bulan(p),
    }


def _cek_jendela_tiga_bulan(params: dict) -> bool:
    frm = params.get("period_date_from")
    to = params.get("period_date_to")
    if not frm or not to:
        return False
    try:
        d_from = date.fromisoformat(frm)
        d_to = date.fromisoformat(to)
    except ValueError:
        return False
    lebar_hari = (d_to - d_from).days
    dekat_referensi = abs((TANGGAL_REFERENSI - d_to).days) <= 31
    return 60 <= lebar_hari <= 100 and dekat_referensi


def _scenario_s03() -> dict:
    return {
        "id": "S03",
        "deskripsi": "Filter kategorikal persis",
        "atomic_intent": _ai(
            "Bagaimana performa kanal Direct di Bali bulan Juni 2026?", LabelBentukJawaban.NILAI_TUNGGAL
        ),
        "view_name": "v_reservation_channel_daily",
        "check": lambda p: (
            p.get("channel_name") == "Direct"
            and p.get("period_date_from") == "2026-06-01"
            and p.get("period_date_to") == "2026-06-30"
        ),
    }


def _scenario_s04() -> dict:
    return {
        "id": "S04",
        "deskripsi": "Resolusi nama properti ke kode",
        "atomic_intent": _ai(
            "Okupansi Nirwana Lombok Escape bulan ini", LabelBentukJawaban.NILAI_TUNGGAL
        ),
        "view_name": "v_reservation_room_type_daily",
        "check": lambda p: p.get("property_id") == "P05",
    }


def _scenario_s05() -> dict:
    return {
        "id": "S05",
        "deskripsi": "Kebutuhan minimal, tidak over-filling",
        "atomic_intent": _ai("Ada berapa venue yang dimiliki Nirwana?", LabelBentukJawaban.NILAI_TUNGGAL),
        "view_name": "v_lookup_venues",
        "check": lambda p: p == {},
    }


def _scenario_s06() -> dict:
    return {
        "id": "S06",
        "deskripsi": "View tanpa kolom tanggal sama sekali",
        "atomic_intent": _ai(
            "Bahan apa saja untuk membuat menu Nasi Goreng?", LabelBentukJawaban.NILAI_TUNGGAL
        ),
        "view_name": "v_lookup_recipe_bom",
        "check": lambda p: p.get("item_name") == "Nasi Goreng"
        and not any("date" in k for k in p),
    }


def _scenario_s07() -> dict:
    return {
        "id": "S07",
        "deskripsi": "KK2: parameter masuk akal tapi tidak ada di whitelist",
        "atomic_intent": _ai(
            "Tampilkan properti Nirwana dengan rating bintang 5", LabelBentukJawaban.NILAI_TUNGGAL
        ),
        "view_name": "v_properties_ref",
        "check": lambda p: "star_rating" not in p,
    }


SCENARIOS = [
    _scenario_s01(),
    _scenario_s02(),
    _scenario_s03(),
    _scenario_s04(),
    _scenario_s05(),
    _scenario_s06(),
    _scenario_s07(),
]


def _run_scenario(scenario: dict) -> dict:
    hasil = susun_request_atomic_intent(
        scenario["atomic_intent"], scenario["view_name"], tanggal_referensi=TANGGAL_REFERENSI
    )
    params = hasil.request.params if hasil.request is not None else {}
    match = hasil.status.value == "berhasil" and scenario["check"](params)
    return {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "atomic_intent": scenario["atomic_intent"].model_dump(mode="json"),
        "view_name": scenario["view_name"],
        "tanggal_referensi": TANGGAL_REFERENSI.isoformat(),
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
