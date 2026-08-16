"""Jalankan skenario di rancangan.md, simpan payload lengkap ke payloads/,
cetak ringkasan match/mismatch ke console.

Reuse deteksi_constraint_atomic_intent()/verifikasi_cakupan_individu()
produksi langsung - bukan logic duplikat.

Jalankan dari root repo: uv run python evals/2.3-deteksi-cakupan-individu/run_eval.py
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.domain_gate.cakupan_individu import deteksi_constraint_atomic_intent
from src.layers.domain_gate.verifikasi_cakupan_individu import verifikasi_cakupan_individu
from src.schemas.authorization import AtomicIntentAuthorization, DomainAuthorization
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.session_memory import LabelBentukJawaban

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"


def _ai(teks: str) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _aia(teks: str, domain: Domain) -> AtomicIntentAuthorization:
    return AtomicIntentAuthorization(
        atomic_intent=_ai(teks),
        domain_decisions=[DomainAuthorization(domain=domain, diizinkan=True)],
    )


def _scenario_s01() -> dict:
    aia = _aia("Bagaimana hasil review kinerja Budi semester ini?", Domain.HR)
    return {
        "id": "S01",
        "deskripsi": "Review kinerja individu by name (hr)",
        "aia": aia,
        "role_title": "HR Staff",
        "check": lambda r: r.constraint.terdeteksi is True,
    }


def _scenario_s02() -> dict:
    aia = _aia("Berapa banyak tiket yang ditangani teknisi Andi bulan ini?", Domain.FACILITY)
    return {
        "id": "S02",
        "deskripsi": "Beban kerja teknisi by name (facility)",
        "aia": aia,
        "role_title": "Maintenance Staff",
        "check": lambda r: r.constraint.terdeteksi is True,
    }


def _scenario_s03() -> dict:
    aia = _aia("Berapa banyak staf yang mengambil cuti bulan ini?", Domain.HR)
    return {
        "id": "S03",
        "deskripsi": "Distractor: jumlah cuti agregat (hr)",
        "aia": aia,
        "role_title": "HR Staff",
        "check": lambda r: r.constraint.terdeteksi is False,
    }


def _scenario_s04() -> dict:
    aia = _aia(
        "Berapa rata-rata durasi pembersihan kamar tipe Villa dibanding baseline?",
        Domain.FACILITY,
    )
    return {
        "id": "S04",
        "deskripsi": "Agregat facility tanpa kata staf",
        "aia": aia,
        "role_title": "Housekeeping Staff",
        "check": lambda r: r.constraint.terdeteksi is False,
    }


def _scenario_s05() -> dict:
    aia = _aia("Siapa yang paling banyak menangani tiket maintenance bulan ini?", Domain.FACILITY)
    return {
        "id": "S05",
        "deskripsi": "Ranking individu tanpa kata staf/karyawan (jebakan arah sebaliknya)",
        "aia": aia,
        "role_title": "Maintenance Staff",
        "check": lambda r: r.constraint.terdeteksi is True,
    }


def _scenario_s06() -> dict:
    aia = _aia(
        "Karyawan mana saja yang pola absensinya menyimpang jauh dari kebiasaan pribadinya "
        "bulan ini?",
        Domain.HR,
    )
    return {
        "id": "S06",
        "deskripsi": "Watchlist individu (hr)",
        "aia": aia,
        "role_title": "HR Staff",
        "check": lambda r: r.constraint.terdeteksi is True,
    }


def _scenario_s07() -> dict:
    aia = _aia("Apakah Budi sudah absen hari ini?", Domain.HR)
    return {
        "id": "S07",
        "deskripsi": "Kehadiran individu by name (hr)",
        "aia": aia,
        "role_title": "HR Staff",
        "check": lambda r: r.constraint.terdeteksi is True,
    }


def _run_scenario(scenario: dict) -> dict:
    result = deteksi_constraint_atomic_intent(scenario["aia"], scenario["role_title"])
    match = scenario["check"](result)
    return {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role_title": scenario["role_title"],
        "atomic_intent_authorization": scenario["aia"].model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "match": match,
        "toleransi": scenario.get("toleransi"),
    }


def _run_scenario_s08() -> dict:
    """Generalisasi role-differentiation ke teks baru - dijalankan dua kali,
    role berbeda, atomic_intent_id SAMA supaya jelas ini satu skenario."""
    teks = "Teknisi mana yang paling sering menangani perbaikan AC bulan ini?"
    aia_a = _aia(teks, Domain.FACILITY)
    aia_b = AtomicIntentAuthorization(
        atomic_intent=aia_a.atomic_intent, domain_decisions=aia_a.domain_decisions
    )

    hasil_a = deteksi_constraint_atomic_intent(aia_a, "Maintenance Staff")
    hasil_b = deteksi_constraint_atomic_intent(aia_b, "Maintenance Manager")

    match = hasil_a.constraint.terdeteksi is True and hasil_b.constraint.terdeteksi is False
    return {
        "scenario_id": "S08",
        "deskripsi": "Generalisasi role-differentiation ke teks baru",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role_a": "Maintenance Staff",
        "role_b": "Maintenance Manager",
        "hasil_a": hasil_a.model_dump(mode="json"),
        "hasil_b": hasil_b.model_dump(mode="json"),
        "match": match,
        "toleransi": None,
    }


def _run_scenario_s09() -> dict:
    """Titik-buta phrasing berbeda dari tests/ - verifikasi_cakupan_individu()
    dipanggil langsung dengan terdeteksi_awal=False dipaksa."""
    ai = _ai("Bandingkan kecepatan kerja tiap staf housekeeping minggu ini.")
    hasil = verifikasi_cakupan_individu(ai, terdeteksi_awal=False)

    match = hasil.terdeteksi_tambahan is True
    return {
        "scenario_id": "S09",
        "deskripsi": "Titik-buta phrasing berbeda (retest, bukan teks tests/)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "atomic_intent": ai.model_dump(mode="json"),
        "terdeteksi_awal_dipaksa": False,
        "result": hasil.model_dump(mode="json"),
        "match": match,
        "toleransi": None,
    }


def _scenario_s10() -> dict:
    aia = _aia(
        "Berapa rata-rata waktu penyelesaian tiket maintenance bulan ini, dan apakah "
        "melebihi SLA?",
        Domain.FACILITY,
    )
    return {
        "id": "S10",
        "deskripsi": "Distractor over-triggering: durasi/waktu agregat (facility)",
        "aia": aia,
        "role_title": "Maintenance Staff",
        "check": lambda r: r.constraint.terdeteksi is False,
        "toleransi": "kalau terdeteksi=True (verifier over-trigger), dicatat sebagai temuan "
        "pola over-triggering, BUKAN fail keras",
    }


SIMPLE_SCENARIOS = [
    _scenario_s01(),
    _scenario_s02(),
    _scenario_s03(),
    _scenario_s04(),
    _scenario_s05(),
    _scenario_s06(),
    _scenario_s07(),
    _scenario_s10(),
]

CUSTOM_SCENARIOS = {
    "S08": _run_scenario_s08,
    "S09": _run_scenario_s09,
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Filter opsional lewat argv: `run_eval.py S03` hanya jalankan S03 - dipakai
    # untuk eksekusi per-skenario dengan kontrol timeout di level proses, mirror
    # pola evals/2.1-identifikasi-domain/run_eval.py Checkpoint 10.
    only_id = sys.argv[1] if len(sys.argv) > 1 else None

    results = []

    for scenario in SIMPLE_SCENARIOS:
        if only_id and scenario["id"] != only_id:
            continue
        record = _run_scenario(scenario)
        results.append(record)
        (OUTPUT_DIR / f"{record['scenario_id']}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"{record['scenario_id']} selesai, match={record['match']}", flush=True)

    for scenario_id, runner in CUSTOM_SCENARIOS.items():
        if only_id and scenario_id != only_id:
            continue
        record = runner()
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
