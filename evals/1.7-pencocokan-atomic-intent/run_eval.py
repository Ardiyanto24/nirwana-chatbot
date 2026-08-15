"""Jalankan skenario di rancangan.md, simpan payload lengkap (atomic intent +
kandidat + hasil AtomicIntentMatch) ke payloads/, cetak ringkasan
match/mismatch ke console.

Reuse match_atomic_intents() produksi langsung - bukan logic duplikat.
Kandidat dikonstruksi in-memory (BUKAN lewat store_session_memory()) karena
dimensi yang diuji di sini murni kualitas keputusan LLM, bukan persistence
(sudah dibuktikan formal di tests/) - tidak ada DB yang perlu di-cleanup.

Jalankan dari root repo: uv run python evals/1.7-pencocokan-atomic-intent/run_eval.py
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.context_resolution.matching import match_atomic_intents
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.matching import AtomicIntentMatch, MatchStatus
from src.schemas.session_memory import LabelBentukJawaban, SessionMemoryPackage, StatusEksekusi

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"


def _ai(teks: str, label: LabelBentukJawaban) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=label,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _pkg(
    teks: str, label: LabelBentukJawaban, status: StatusEksekusi = StatusEksekusi.BERHASIL
) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=str(uuid.uuid4()),
        session_id="eval-m17",
        turn_index=1,
        teks_kebutuhan=teks,
        label_bentuk_jawaban=label,
        nilai_hasil={"value": 1},
        catatan_interpretasi=[],
        status=status,
        sumber="eksekusi_baru",
    )


def _selesai_ke(results: list[AtomicIntentMatch], i: int, candidates: list[SessionMemoryPackage], idx: int) -> bool:
    r = results[i]
    return (
        r.status == MatchStatus.SELESAI
        and r.paket is not None
        and r.paket.atomic_intent_id == candidates[idx].atomic_intent_id
    )


def _perlu_eksekusi(results: list[AtomicIntentMatch], i: int) -> bool:
    return results[i].status == MatchStatus.PERLU_EKSEKUSI and results[i].paket is None


def _scenario_s01() -> dict:
    ai = [_ai("pendapatan reservasi bulan Maret 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    candidates = [_pkg("revenue reservasi Maret 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    return {
        "id": "S01",
        "deskripsi": "Paraphrase kata berbeda makna sama",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _selesai_ke(r, 0, candidates, 0),
    }


def _scenario_s02() -> dict:
    ai = [_ai("occupancy rate Mei 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    candidates = [_pkg("occupancy rate bulan April 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    return {
        "id": "S02",
        "deskripsi": "Entitas kunci beda: bulan berbeda (topik sama)",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _perlu_eksekusi(r, 0),
    }


def _scenario_s03() -> dict:
    ai = [_ai("revenue F&B bulan Maret 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    candidates = [_pkg("jumlah komplain tamu F&B bulan Maret 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    return {
        "id": "S03",
        "deskripsi": "Entitas kunci beda: metrik berbeda, domain sama",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _perlu_eksekusi(r, 0),
    }


def _scenario_s04() -> dict:
    ai = [_ai("occupancy rate bulan April 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    candidates = [
        _pkg("occupancy rate bulan April 2026", LabelBentukJawaban.NILAI_TUNGGAL, StatusEksekusi.GAGAL_TEKNIS)
    ]
    return {
        "id": "S04",
        "deskripsi": "Filter kandidat: status=gagal_teknis, topik identik",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _perlu_eksekusi(r, 0),
    }


def _scenario_s05() -> dict:
    ai = [_ai("occupancy rate bulan April 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    candidates = [
        _pkg("occupancy rate bulan April 2026", LabelBentukJawaban.NILAI_TUNGGAL, StatusEksekusi.SEBAGIAN)
    ]
    return {
        "id": "S05",
        "deskripsi": "Filter kandidat: status=sebagian, topik identik",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _perlu_eksekusi(r, 0),
    }


def _scenario_s06() -> dict:
    ai = [
        _ai("berapa occupancy April 2026", LabelBentukJawaban.NILAI_TUNGGAL),
        _ai("berapa jumlah staff yang resign bulan Juni 2026", LabelBentukJawaban.NILAI_TUNGGAL),
    ]
    candidates = [_pkg("occupancy rate bulan April 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    return {
        "id": "S06",
        "deskripsi": "Mixed match dalam satu turn",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _selesai_ke(r, 0, candidates, 0) and _perlu_eksekusi(r, 1),
    }


def _scenario_s07() -> dict:
    ai = [
        _ai("berapa occupancy April 2026", LabelBentukJawaban.NILAI_TUNGGAL),
        _ai("occupancy rate bulan April kemarin", LabelBentukJawaban.NILAI_TUNGGAL),
    ]
    candidates = [_pkg("occupancy rate bulan April 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    return {
        "id": "S07",
        "deskripsi": "Non-eksklusivitas (dua atomic intent baru cocok ke kandidat sama)",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _selesai_ke(r, 0, candidates, 0) and _selesai_ke(r, 1, candidates, 0),
    }


def _scenario_s08() -> dict:
    ai = [_ai("berapa occupancy Maret 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    candidates = [
        _pkg("occupancy rate Januari 2026", LabelBentukJawaban.NILAI_TUNGGAL),
        _pkg("occupancy rate Februari 2026", LabelBentukJawaban.NILAI_TUNGGAL),
        _pkg("occupancy rate Maret 2026", LabelBentukJawaban.NILAI_TUNGGAL),
        _pkg("occupancy rate April 2026", LabelBentukJawaban.NILAI_TUNGGAL),
    ]
    return {
        "id": "S08",
        "deskripsi": "Pool kandidat besar, presisi pemilihan index yang benar",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _selesai_ke(r, 0, candidates, 2),
    }


def _scenario_s09() -> dict:
    ai = [_ai("berapa occupancy Februari 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    candidates = [
        _pkg("occupancy rate Februari 2026", LabelBentukJawaban.NILAI_TUNGGAL),  # [0] BENAR
        _pkg("revenue F&B Maret 2026", LabelBentukJawaban.NILAI_TUNGGAL),  # [1] pengisi
        _pkg("occupancy rate April 2026", LabelBentukJawaban.NILAI_TUNGGAL),  # [2] SALAH bulan, posisi akhir
    ]
    return {
        "id": "S09",
        "deskripsi": "Recency bias (posisi kandidat vs kebenaran makna)",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _selesai_ke(r, 0, candidates, 0),
        "toleransi": "kalau salah pilih index 2 (posisi akhir), dicatat sebagai temuan pola "
        "recency bias (docs/keterbatasan-diterima.md #3), bukan otomatis fail keras",
    }


def _scenario_s10() -> dict:
    ai = [_ai("bagaimana tren occupancy rate 6 bulan terakhir", LabelBentukJawaban.TREN)]
    candidates = [_pkg("occupancy rate bulan Januari 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    return {
        "id": "S10",
        "deskripsi": "label_bentuk_jawaban beda meski topik sama",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _perlu_eksekusi(r, 0),
    }


def _scenario_s11() -> dict:
    ai = [
        _ai("berapa occupancy April 2026", LabelBentukJawaban.NILAI_TUNGGAL),
        _ai("nilai occupancy rate untuk periode April 2026", LabelBentukJawaban.NILAI_TUNGGAL),
    ]
    candidates = [_pkg("occupancy rate bulan April 2026", LabelBentukJawaban.NILAI_TUNGGAL)]
    return {
        "id": "S11",
        "deskripsi": "Non-eksklusivitas (retest, paraphrase tidak ambigu)",
        "atomic_intents": ai,
        "candidates": candidates,
        "check": lambda r: _selesai_ke(r, 0, candidates, 0) and _selesai_ke(r, 1, candidates, 0),
    }


SCENARIOS = [
    _scenario_s01(),
    _scenario_s02(),
    _scenario_s03(),
    _scenario_s04(),
    _scenario_s05(),
    _scenario_s06(),
    _scenario_s07(),
    _scenario_s08(),
    _scenario_s09(),
    _scenario_s10(),
    _scenario_s11(),
]


def _run_scenario(scenario: dict) -> dict:
    results = match_atomic_intents(scenario["atomic_intents"], scenario["candidates"])
    match = scenario["check"](results)
    record = {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "atomic_intents": [ai.model_dump(mode="json") for ai in scenario["atomic_intents"]],
        "candidates": [c.model_dump(mode="json") for c in scenario["candidates"]],
        "results": [r.model_dump(mode="json") for r in results],
        "match": match,
        "toleransi": scenario.get("toleransi"),
    }
    return record


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for scenario in SCENARIOS:
        record = _run_scenario(scenario)
        results.append(record)
        (OUTPUT_DIR / f"{record['scenario_id']}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"{record['scenario_id']} selesai, match={record['match']}")

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
