"""Jalankan skenario di rancangan.md, simpan payload lengkap (atomic intent +
hasil AtomicIntentDomains) ke payloads/, cetak ringkasan match/mismatch ke
console.

Reuse identifikasi_domain_atomic_intent() produksi langsung - bukan logic
duplikat.

Jalankan dari root repo: uv run python evals/2.1-identifikasi-domain/run_eval.py
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.domain_gate.domain_gate import identifikasi_domain_atomic_intent
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import AtomicIntentDomains, Domain
from src.schemas.session_memory import LabelBentukJawaban

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"


def _ai(teks: str) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _cek_domain(
    result: AtomicIntentDomains,
    wajib_ada: list[Domain],
    wajib_tidak_ada: list[Domain] | None = None,
) -> bool:
    wajib_tidak_ada = wajib_tidak_ada or []
    ada_semua = all(d in result.domains for d in wajib_ada)
    tidak_ada_yang_dilarang = all(d not in result.domains for d in wajib_tidak_ada)
    return ada_semua and tidak_ada_yang_dilarang


def _scenario_s01() -> dict:
    ai = _ai("Bagaimana margin keuntungan F&B dibandingkan dengan revenue F&B bulan ini?")
    return {
        "id": "S01",
        "deskripsi": "Generalisasi pola cross-domain (kasus baru, bukan gop_margin)",
        "atomic_intent": ai,
        "check": lambda r: _cek_domain(r, [Domain.FNB, Domain.FINANCIAL]),
    }


def _scenario_s02() -> dict:
    ai = _ai("Siapa staff yang menangani housekeeping hari ini, dan berapa okupansi hotel saat itu?")
    return {
        "id": "S02",
        "deskripsi": "Fokus terlalu sempit (pola umum, bukan leakage kolom)",
        "atomic_intent": ai,
        "check": lambda r: _cek_domain(r, [Domain.FACILITY, Domain.RESERVATION]),
    }


def _scenario_s03() -> dict:
    ai = _ai("Siapkan laporan tamu VIP: nama, email, dan tingkat loyalitas mereka.")
    return {
        "id": "S03",
        "deskripsi": "guests_pii DAN guests_profile genuinely dibutuhkan sekaligus",
        "atomic_intent": ai,
        "check": lambda r: _cek_domain(r, [Domain.GUESTS_PII, Domain.GUESTS_PROFILE]),
    }


def _scenario_s04() -> dict:
    ai = _ai("Berapa nationality mix tamu bulan ini?")
    return {
        "id": "S04",
        "deskripsi": "Retest temuan Checkpoint 8 (potensi over-triggering reservation)",
        "atomic_intent": ai,
        "check": lambda r: _cek_domain(r, [Domain.GUESTS_PROFILE]),
        "toleransi": "kalau domain 'reservation' ikut muncul, itu mereplikasi temuan "
        "over-triggering Checkpoint 8 - dicatat sebagai temuan pola, BUKAN fail keras",
    }


def _scenario_s05() -> dict:
    ai = _ai("Berapa total revenue seluruh properti bulan ini?")
    return {
        "id": "S05",
        "deskripsi": "Baseline domain tunggal: financial murni",
        "atomic_intent": ai,
        "check": lambda r: _cek_domain(
            r, [Domain.FINANCIAL], [Domain.RESERVATION, Domain.FNB]
        ),
    }


def _scenario_s06() -> dict:
    ai = _ai("Berapa tingkat turnover karyawan bulan ini?")
    return {
        "id": "S06",
        "deskripsi": "Guard anti-false-positive: hr murni",
        "atomic_intent": ai,
        "check": lambda r: _cek_domain(
            r, [Domain.HR], [Domain.EMPLOYEES_DIRECTORY, Domain.FINANCIAL]
        ),
    }


def _scenario_s07() -> dict:
    ai = _ai("Sebutkan nama-nama hotel yang sudah beroperasi lebih dari 5 tahun.")
    return {
        "id": "S07",
        "deskripsi": "Domain minor: properties_ref",
        "atomic_intent": ai,
        "check": lambda r: _cek_domain(r, [Domain.PROPERTIES_REF]),
    }


def _scenario_s08() -> dict:
    ai = _ai("Bandingkan revenue F&B dengan tingkat okupansi kamar bulan ini.")
    return {
        "id": "S08",
        "deskripsi": "Multi-domain eksplisit (bukan leakage - keduanya disebut jelas)",
        "atomic_intent": ai,
        "check": lambda r: _cek_domain(r, [Domain.FNB, Domain.RESERVATION]),
    }


def _scenario_s09() -> dict:
    ai = _ai("Siapa saja karyawan departemen HR yang performanya menurun bulan ini?")
    return {
        "id": "S09",
        "deskripsi": "employees_directory + hr gabungan",
        "atomic_intent": ai,
        "check": lambda r: _cek_domain(r, [Domain.HR]),
        "toleransi": "employees_directory diharapkan tapi tidak wajib - dicatat sebagai "
        "observasi, bukan fail otomatis kalau tidak muncul",
    }


def _scenario_s10() -> dict:
    ai = _ai("Berapa total payroll yang dibayarkan bulan ini?")
    return {
        "id": "S10",
        "deskripsi": "Jebakan payroll: financial MURNI, bukan hr",
        "atomic_intent": ai,
        "check": lambda r: _cek_domain(r, [Domain.FINANCIAL], [Domain.HR]),
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
]


def _run_scenario(scenario: dict) -> dict:
    result = identifikasi_domain_atomic_intent(scenario["atomic_intent"])
    match = scenario["check"](result)
    record = {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "atomic_intent": scenario["atomic_intent"].model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "match": match,
        "toleransi": scenario.get("toleransi"),
    }
    return record


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Filter opsional lewat argv: `run_eval.py S03` hanya jalankan S03 - dipakai
    # untuk eksekusi per-skenario dengan kontrol timeout di level proses (bukan
    # klien HTTP saja) saat provider mengalami latensi tinggi, lihat logs.md
    # Checkpoint 10.
    only_id = sys.argv[1] if len(sys.argv) > 1 else None
    scenarios_to_run = (
        [s for s in SCENARIOS if s["id"] == only_id] if only_id else SCENARIOS
    )

    results = []
    for scenario in scenarios_to_run:
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
