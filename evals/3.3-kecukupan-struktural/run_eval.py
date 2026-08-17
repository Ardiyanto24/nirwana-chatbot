"""Jalankan skenario di rancangan.md, simpan payload lengkap ke payloads/,
cetak ringkasan match/mismatch ke console.

Reuse proses_retrieval_atomic_intent() produksi langsung (M3.1+M3.2+M3.3
NYATA end-to-end, bukan logic duplikat/mock) - beda dari
evals/3.2-.../run_eval.py yang mengonstruksi HasilPencarianKandidat manual
(M3.1 disimulasikan): di sini M3.1 JUGA dijalankan nyata (BM25/embedding),
supaya kandidat yang dievaluasi M3.3 benar-benar berasal dari pipeline
penuh, konsisten dengan cara mekanisme ini benar-benar dipakai produksi.

Jalankan dari root repo: uv run python evals/3.3-kecukupan-struktural/run_eval.py
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.retriever.kecukupan_struktural import proses_retrieval_atomic_intent
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.session_memory import LabelBentukJawaban

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"


def _ai(teks: str, label_bentuk_jawaban: LabelBentukJawaban) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=label_bentuk_jawaban,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _kandidat_of(hasil, view_name: str):
    for k in hasil.kecukupan:
        if k.kandidat.view_name == view_name:
            return k
    return None


def _scenario_s01() -> dict:
    return {
        "id": "S01",
        "deskripsi": "KK1 sumber persis: tren + kandidat snapshot tanpa dimensi waktu berulang",
        "atomic_intent": _ai(
            "Bagaimana tren turnover departemen Housekeeping di Bali 3 bulan terakhir?",
            LabelBentukJawaban.TREN,
        ),
        "domain_diizinkan": [Domain.HR],
        "check": lambda h: (
            _kandidat_of(h, "v_hr_turnover_snapshot") is None
            or (
                _kandidat_of(h, "v_hr_turnover_snapshot").cukup is False
                and _kandidat_of(h, "v_hr_turnover_snapshot").sumber_keputusan.value == "deterministik"
            )
        ),
        "toleransi": "kalau v_hr_turnover_snapshot tidak muncul sama sekali di kandidat M3.1/M3.2, "
        "dicatat sebagai catatan (bukan fail) - fokus KK1 adalah PERLAKUAN kandidat itu KALAU muncul",
    }


def _scenario_s02() -> dict:
    return {
        "id": "S02",
        "deskripsi": "KK2 sumber persis: nilai_tunggal + grain sesuai",
        "atomic_intent": _ai(
            "Berapa okupansi Suite di Bali bulan ini?", LabelBentukJawaban.NILAI_TUNGGAL
        ),
        "domain_diizinkan": [Domain.RESERVATION],
        "check": lambda h: h.view_name_final == "v_reservation_room_type_daily",
    }


def _scenario_s03() -> dict:
    return {
        "id": "S03",
        "deskripsi": "Jalur fallback LLM genuinely terpicu (grain row-level ambigu)",
        "atomic_intent": _ai(
            "Bagaimana tren booking di Bali 3 bulan terakhir?", LabelBentukJawaban.TREN
        ),
        "domain_diizinkan": [Domain.RESERVATION],
        "check": lambda h: (
            _kandidat_of(h, "v_lookup_bookings") is None
            or _kandidat_of(h, "v_lookup_bookings").sumber_keputusan.value != "llm"
            or _kandidat_of(h, "v_lookup_bookings").cukup is False
        ),
        "toleransi": "kalau v_lookup_bookings dilempar ke fallback LLM dan model tetap menjawab "
        "cukup=True, dicatat sebagai temuan nyata (bukan fail keras) - prompt sudah direvisi "
        "sekali (v2) berdasar bukti Checkpoint 7",
    }


def _scenario_s04() -> dict:
    return {
        "id": "S04",
        "deskripsi": "Perbandingan antar tipe kamar (dimensi pembanding jelas)",
        "atomic_intent": _ai(
            "Bandingkan performa revenue antar tipe kamar di Bali bulan ini",
            LabelBentukJawaban.PERBANDINGAN,
        ),
        "domain_diizinkan": [Domain.RESERVATION],
        "check": lambda h: h.view_name_final == "v_reservation_room_type_daily",
    }


def _scenario_s05() -> dict:
    return {
        "id": "S05",
        "deskripsi": "Tie-break nyata (dua kandidat sama-sama cukup)",
        "atomic_intent": _ai(
            "Tren revenue dan okupansi kamar di Bali 3 bulan terakhir", LabelBentukJawaban.TREN
        ),
        "domain_diizinkan": [Domain.RESERVATION],
        "check": lambda h: _tie_break_konsisten(h),
        "toleransi": "hasil M3.2 (kandidat mana yang ditemukan/sebagian) tidak dikontrol penuh - "
        "yang diverifikasi ketat adalah konsistensi view_name_final TERHADAP aturan tie-break "
        "dari kecukupan yang benar-benar dihasilkan",
    }


def _tie_break_konsisten(h) -> bool:
    kandidat_cukup = [k for k in h.kecukupan if k.cukup]
    if not kandidat_cukup:
        return h.view_name_final is None
    urutan_label = {"ditemukan": 0, "sebagian": 1}
    terpilih = min(
        kandidat_cukup,
        key=lambda k: (urutan_label.get(k.kecocokan_label.value, 99), -k.kandidat.skor),
    )
    return h.view_name_final == terpilih.kandidat.view_name


def _scenario_s06() -> dict:
    return {
        "id": "S06",
        "deskripsi": "Tidak ada kandidat cukup sama sekali (kejujuran keterbatasan)",
        "atomic_intent": _ai(
            "Tren nama dan region seluruh properti dari waktu ke waktu", LabelBentukJawaban.TREN
        ),
        "domain_diizinkan": [Domain.PROPERTIES_REF],
        "check": lambda h: h.view_name_final is None,
    }


SCENARIOS = [
    _scenario_s01(),
    _scenario_s02(),
    _scenario_s03(),
    _scenario_s04(),
    _scenario_s05(),
    _scenario_s06(),
]


def _run_scenario(scenario: dict) -> dict:
    hasil = proses_retrieval_atomic_intent(scenario["atomic_intent"], scenario["domain_diizinkan"])
    match = scenario["check"](hasil)
    return {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "atomic_intent": scenario["atomic_intent"].model_dump(mode="json"),
        "domain_diizinkan": [d.value for d in scenario["domain_diizinkan"]],
        "result": hasil.model_dump(mode="json"),
        "match": match,
        "toleransi": scenario.get("toleransi"),
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
