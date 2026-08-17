"""Jalankan skenario di rancangan.md, simpan payload lengkap ke payloads/,
cetak ringkasan match/mismatch ke console.

Reuse nilai_kecocokan_makna_atomic_intent() produksi langsung (Langkah 1 +
Langkah 2 NYATA, bukan logic duplikat/mock).

Jalankan dari root repo: uv run python evals/3.2-kecocokan-makna/run_eval.py
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.retriever.kecocokan_makna import nilai_kecocokan_makna_atomic_intent
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.retriever import HasilPencarianKandidat, KandidatView, SumberPencarian
from src.schemas.session_memory import LabelBentukJawaban

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"


def _hp(
    teks: str,
    label_bentuk_jawaban: LabelBentukJawaban,
    kandidat: list[tuple[str, Domain]],
) -> HasilPencarianKandidat:
    ai = AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=label_bentuk_jawaban,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )
    kv = [
        KandidatView(view_name=v, domain=d, skor=1.0, sumber=SumberPencarian.BM25)
        for v, d in kandidat
    ]
    return HasilPencarianKandidat(
        atomic_intent=ai,
        domain_diizinkan=list({d for _, d in kandidat}),
        kandidat=kv,
        fallback_terpicu=False,
        status="berhasil",
    )


def _label_of(hasil, view_name: str) -> str | None:
    for k in hasil.kecocokan:
        if k.kandidat.view_name == view_name:
            return k.label.value
    return None


def _scenario_s01() -> dict:
    hp = _hp(
        "Tampilkan breakdown okupansi per tipe kamar untuk properti Bali bulan ini",
        LabelBentukJawaban.KOMPOSISI,
        [
            ("v_reservation_room_type_daily", Domain.RESERVATION),
            ("v_reservation_property_daily", Domain.RESERVATION),
        ],
    )
    return {
        "id": "S01",
        "deskripsi": "KK1 sumber persis: grain-mismatch ringkasan properti vs per tipe kamar",
        "hp": hp,
        "check": lambda h: _label_of(h, "v_reservation_room_type_daily") == "ditemukan"
        and _label_of(h, "v_reservation_property_daily") != "ditemukan",
    }


def _scenario_s02() -> dict:
    hp = _hp(
        "Berapa okupansi Suite di Bali bulan ini?",
        LabelBentukJawaban.NILAI_TUNGGAL,
        [("v_reservation_room_type_daily", Domain.RESERVATION)],
    )
    return {
        "id": "S02",
        "deskripsi": "KK2 sumber persis: cocok penuh tanpa ragu",
        "hp": hp,
        "check": lambda h: _label_of(h, "v_reservation_room_type_daily") == "ditemukan",
    }


def _scenario_s03() -> dict:
    hp = _hp(
        "Berapa batas SLA (dalam jam) untuk tiket prioritas critical?",
        LabelBentukJawaban.NILAI_TUNGGAL,
        [("v_maintenance_ticket_daily", Domain.FACILITY)],
    )
    return {
        "id": "S03",
        "deskripsi": "Kolom turunan tetap valid (anti false-negative)",
        "hp": hp,
        "check": lambda h: _label_of(h, "v_maintenance_ticket_daily") == "ditemukan",
        "toleransi": "kalau sebagian dengan alasan merujuk sifat turunan, dicatat sebagai "
        "temuan nyata (nuansa interpretatif), bukan fail keras",
    }


def _scenario_s04() -> dict:
    hp = _hp(
        "Bagaimana TREN turnover karyawan departemen HR selama setahun terakhir?",
        LabelBentukJawaban.TREN,
        [("v_hr_turnover_snapshot", Domain.HR)],
    )
    return {
        "id": "S04",
        "deskripsi": "Snapshot vs kebutuhan tren historis",
        "hp": hp,
        "check": lambda h: _label_of(h, "v_hr_turnover_snapshot") != "ditemukan",
    }


def _scenario_s05() -> dict:
    hp = _hp(
        "Berapa tingkat turnover departemen HR bulan ini?",
        LabelBentukJawaban.NILAI_TUNGGAL,
        [("v_hr_turnover_snapshot", Domain.HR)],
    )
    return {
        "id": "S05",
        "deskripsi": "Snapshot cocok untuk kebutuhan point-in-time (counter-case S04)",
        "hp": hp,
        "check": lambda h: _label_of(h, "v_hr_turnover_snapshot") == "ditemukan",
    }


_HR_VIEWS = [
    "v_hr_attendance_daily",
    "v_hr_employee_monthly",
    "v_hr_employee_performance_semester",
    "v_hr_headcount_status_daily",
    "v_hr_performance_by_status_semester",
    "v_hr_performance_department_semester",
    "v_hr_turnover_snapshot",
    "v_hr_watchlist_monthly",
    "v_lookup_employee_performance",
    "v_lookup_staff_shifts",
]


def _scenario_s06() -> dict:
    hp = _hp(
        "Karyawan mana saja yang pola absensinya menyimpang jauh dari kebiasaan pribadinya "
        "bulan ini?",
        LabelBentukJawaban.PERINGKAT,
        [(v, Domain.HR) for v in _HR_VIEWS],
    )

    def _check(h):
        if _label_of(h, "v_hr_watchlist_monthly") != "ditemukan":
            return False
        lain = [v for v in _HR_VIEWS if v != "v_hr_watchlist_monthly"]
        salah_ditemukan = sum(1 for v in lain if _label_of(h, v) == "ditemukan")
        return salah_ditemukan <= 2

    return {
        "id": "S06",
        "deskripsi": "Domain padat kandidat (10 kandidat sekaligus)",
        "hp": hp,
        "check": _check,
        "toleransi": "kandidat fokus (v_hr_watchlist_monthly) wajib ditemukan tanpa toleransi; "
        "hingga 2 dari 9 kandidat lain boleh salah dilabel ditemukan tanpa dianggap fail keras",
    }


def _scenario_s07() -> dict:
    hp = _hp(
        "Bandingkan durasi pembersihan tiap staf housekeeping per properti bulan ini",
        LabelBentukJawaban.PERBANDINGAN,
        [("v_housekeeping_staff_daily", Domain.FACILITY)],
    )
    return {
        "id": "S07",
        "deskripsi": "Kolom hasil join lintas-tabel (berpotensi nullable)",
        "hp": hp,
        "check": lambda h: _label_of(h, "v_housekeeping_staff_daily") in ("ditemukan", "sebagian"),
        "toleransi": "observasional - dicatat di audit.md apakah alasan menyinggung nuansa "
        "join/nullable property_id, bukan uji pass/fail biner",
    }


def _scenario_s08() -> dict:
    hp = _hp(
        "Berapa margin per departemen (Room, F&B, Spa&Event) bulan ini, tanpa data ringkasan "
        "level properti?",
        LabelBentukJawaban.PERBANDINGAN,
        [
            ("v_financial_departmental_margin", Domain.FINANCIAL),
            ("v_lookup_financial_summary", Domain.FINANCIAL),
        ],
    )
    return {
        "id": "S08",
        "deskripsi": "Dua view mirip, beda filter bawaan (baked-in vs manual)",
        "hp": hp,
        "check": lambda h: _label_of(h, "v_financial_departmental_margin") == "ditemukan"
        and _label_of(h, "v_lookup_financial_summary") == "sebagian",
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
]


def _run_scenario(scenario: dict) -> dict:
    hasil = nilai_kecocokan_makna_atomic_intent(scenario["hp"])
    match = scenario["check"](hasil)
    return {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hasil_pencarian": scenario["hp"].model_dump(mode="json"),
        "result": hasil.model_dump(mode="json"),
        "match": match,
        "toleransi": scenario.get("toleransi"),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Filter opsional lewat argv: `run_eval.py S03` hanya jalankan S03 - dipakai
    # untuk eksekusi per-skenario dengan kontrol timeout di level proses, mirror
    # pola evals/2.1-identifikasi-domain/run_eval.py.
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
