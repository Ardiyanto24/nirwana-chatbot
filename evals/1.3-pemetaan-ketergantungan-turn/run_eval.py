"""Jalankan 12 skenario di rancangan.md, simpan payload lengkap (request+
response mentah) ke payloads/, cetak ringkasan match/mismatch ke console.

Satu panggilan API nyata per skenario (lewat _call_llm() + _parse_and_validate()
yang sama persis dipakai detect_turn_dependency() produksi - bukan logic
duplikat).

Jalankan dari root repo: uv run python evals/1.3-pemetaan-ketergantungan-turn/run_eval.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Skrip ini dijalankan langsung (bukan lewat `-c`), jadi sys.path[0] adalah
# folder skrip ini sendiri, bukan root repo - root repo ditambahkan manual
# supaya "src" bisa diimpor, sama seperti pola infra/observability/smoke_test/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config.llm import OPENROUTER_MODEL
from src.layers.context_resolution.turn_dependency import (
    _SYSTEM_PROMPT,
    _build_user_prompt,
    _call_llm,
    _parse_and_validate,
)
from src.schemas.turn_payload import HistoryTurn, TurnPayload

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"


def _h(turn_index: int, question: str, answer: str) -> HistoryTurn:
    return HistoryTurn(turn_index=turn_index, question=question, answer=answer)


SCENARIOS = [
    {
        "id": "S01",
        "deskripsi": "Baseline: independen tanpa histori sama sekali",
        "payload": TurnPayload(
            session_id="eval-s01",
            turn_index=1,
            role_title="General Manager",
            employee_id="emp-eval",
            question="Berapa occupancy rate properti kita bulan Juni 2026?",
            history=[],
        ),
        "expected": {"is_dependent": False, "referenced_turn_index": None},
        "acceptable_referenced_turn_index": None,
    },
    {
        "id": "S02",
        "deskripsi": "Independen meski histori ada tapi tidak relevan",
        "payload": TurnPayload(
            session_id="eval-s02",
            turn_index=2,
            role_title="HR Manager",
            employee_id="emp-eval",
            question="Apa saja fasilitas yang tersedia di area spa?",
            history=[_h(1, "Berapa jumlah staff aktif di departemen HR?", "Departemen HR memiliki 8 staff aktif.")],
        ),
        "expected": {"is_dependent": False, "referenced_turn_index": None},
        "acceptable_referenced_turn_index": None,
    },
    {
        "id": "S03",
        "deskripsi": "Dependent eksplisit, turn N-1",
        "payload": TurnPayload(
            session_id="eval-s03",
            turn_index=2,
            role_title="Corporate Revenue Director",
            employee_id="emp-eval",
            question="Bandingkan dengan bulan sebelumnya.",
            history=[_h(1, "Berapa revenue reservasi bulan Maret 2026?", "Revenue reservasi Maret 2026 sebesar Rp 800 juta.")],
        ),
        "expected": {"is_dependent": True, "referenced_turn_index": 1},
        "acceptable_referenced_turn_index": {1},
    },
    {
        "id": "S04",
        "deskripsi": "Dependent implisit (tanpa penanda eksplisit), turn N-1",
        "payload": TurnPayload(
            session_id="eval-s04",
            turn_index=2,
            role_title="Front Office Staff",
            employee_id="emp-eval",
            question="Kalau untuk Housekeeping?",
            history=[_h(1, "Berapa rating kepuasan tamu untuk Front Office bulan ini?", "Rating kepuasan tamu Front Office bulan ini 4.6 dari 5.")],
        ),
        "expected": {"is_dependent": True, "referenced_turn_index": 1},
        "acceptable_referenced_turn_index": {1},
        "toleransi": "implisit dekat - False diterima sebagai keterbatasan model, bukan bug",
    },
    {
        "id": "S05",
        "deskripsi": "Dependent eksplisit, turn jauh + distractor",
        "payload": TurnPayload(
            session_id="eval-s05",
            turn_index=6,
            role_title="Front Office Staff",
            employee_id="emp-eval",
            question="Balik lagi ke soal komplain Front Office tadi, sudah ada tindak lanjutnya?",
            history=[
                _h(1, "Berapa jumlah komplain yang diterima Front Office bulan ini?", "Front Office menerima 7 komplain bulan ini, mayoritas soal waktu check-in."),
                _h(2, "Bagaimana kondisi kolam renang?", "Kolam renang beroperasi normal, terakhir dibersihkan kemarin."),
                _h(3, "Berapa revenue spa minggu ini?", "Revenue spa minggu ini Rp 32 juta."),
                _h(4, "Siapa yang bertugas shift malam hari ini?", "Shift malam dipegang oleh 3 staff Front Office dan 2 staff Housekeeping."),
                _h(5, "Berapa kamar yang sedang dalam maintenance?", "5 kamar sedang dalam maintenance, estimasi selesai 3 hari."),
            ],
        ),
        "expected": {"is_dependent": True, "referenced_turn_index": 1},
        "acceptable_referenced_turn_index": {1},
    },
    {
        "id": "S06",
        "deskripsi": "Dependent implisit, turn jauh + distractor",
        "payload": TurnPayload(
            session_id="eval-s06",
            turn_index=4,
            role_title="Spa & Event Staff",
            employee_id="emp-eval",
            question="Naik atau turun dibanding minggu sebelumnya?",
            history=[
                _h(1, "Berapa booking spa yang masuk minggu ini?", "Spa menerima 45 booking minggu ini."),
                _h(2, "Bagaimana revenue F&B bulan ini?", "Revenue F&B bulan ini Rp 450 juta."),
                _h(3, "Berapa unit AC yang rusak di lantai 3?", "3 unit AC di lantai 3 sedang dalam perbaikan."),
            ],
        ),
        "expected": {"is_dependent": True, "referenced_turn_index": 1},
        "acceptable_referenced_turn_index": {1},
        "toleransi": "implisit jauh - False atau referenced_turn_index lain diterima sebagai keterbatasan model, tapi tetap harus dalam himpunan histori valid {1,2,3} (bounds-check tidak boleh gagal)",
    },
    {
        "id": "S07",
        "deskripsi": "Ambigu: topik sama muncul di 2 turn berbeda",
        "payload": TurnPayload(
            session_id="eval-s07",
            turn_index=5,
            role_title="Revenue Manager",
            employee_id="emp-eval",
            question="Bandingkan dengan bulan sebelumnya.",
            history=[
                _h(1, "Berapa occupancy rate bulan April 2026?", "Occupancy April 2026 mencapai 78%."),
                _h(2, "Bagaimana dengan revenue F&B bulan yang sama?", "Revenue F&B April 2026 Rp 450 juta."),
                _h(3, "Berapa occupancy rate bulan Mei 2026?", "Occupancy Mei 2026 mencapai 82%."),
                _h(4, "Berapa banyak staff baru direkrut bulan ini?", "5 staff baru direkrut bulan ini."),
            ],
        ),
        "expected": {"is_dependent": True, "referenced_turn_index": 3},
        "acceptable_referenced_turn_index": {1, 3},
        "toleransi": "ambigu - 1 ATAU 3 diterima, is_dependent=True wajib",
    },
    {
        "id": "S08",
        "deskripsi": "Negasi eksplisit",
        "payload": TurnPayload(
            session_id="eval-s08",
            turn_index=2,
            role_title="Maintenance Manager",
            employee_id="emp-eval",
            question="Ini pertanyaan baru, tidak ada hubungannya dengan tadi: berapa staff maintenance yang aktif sekarang?",
            history=[_h(1, "Berapa revenue reservasi bulan Maret 2026?", "Revenue reservasi Maret 2026 sebesar Rp 800 juta.")],
        ),
        "expected": {"is_dependent": False, "referenced_turn_index": None},
        "acceptable_referenced_turn_index": None,
    },
    {
        "id": "S09",
        "deskripsi": "Sesi panjang (10 turn histori), tanpa dependency",
        "payload": TurnPayload(
            session_id="eval-s09",
            turn_index=11,
            role_title="General Manager",
            employee_id="emp-eval",
            question="Berapa jumlah kamar tipe suite yang tersedia?",
            history=[
                _h(1, "Berapa occupancy rate April 2026?", "78%."),
                _h(2, "Revenue F&B bulan ini?", "Rp 450 juta."),
                _h(3, "Komplain housekeeping bulan ini?", "12 komplain."),
                _h(4, "Kondisi maintenance AC lantai 3?", "3 unit diperbaiki."),
                _h(5, "Booking spa minggu ini?", "45 booking."),
                _h(6, "Staff terbaik bulan ini?", "Sari dari Front Office."),
                _h(7, "Staff HR aktif?", "8 staff."),
                _h(8, "Revenue financial Q1 2026?", "Rp 2.1 miliar."),
                _h(9, "Ada komplain tamu VIP?", "1 komplain, sudah ditangani GM."),
                _h(10, "Revenue reservasi bulan lalu?", "Rp 800 juta."),
            ],
        ),
        "expected": {"is_dependent": False, "referenced_turn_index": None},
        "acceptable_referenced_turn_index": None,
    },
    {
        "id": "S10",
        "deskripsi": "Rujukan pronoun/deiksis ('itu') tanpa penyebutan ulang topik",
        "payload": TurnPayload(
            session_id="eval-s10",
            turn_index=2,
            role_title="Housekeeping Manager",
            employee_id="emp-eval",
            question="Itu sudah ditindaklanjuti belum?",
            history=[_h(1, "Berapa banyak komplain yang diterima housekeeping bulan ini?", "Housekeeping menerima 12 komplain bulan ini, mayoritas soal kebersihan kamar.")],
        ),
        "expected": {"is_dependent": True, "referenced_turn_index": 1},
        "acceptable_referenced_turn_index": {1},
    },
    {
        "id": "S11",
        "deskripsi": "Rujukan ke turn paling awal dari sesi sangat panjang (jarak ekstrem)",
        "payload": TurnPayload(
            session_id="eval-s11",
            turn_index=8,
            role_title="General Manager",
            employee_id="emp-eval",
            question="Balik lagi ke soal occupancy di awal tadi, apakah ada proyeksi untuk bulan depan?",
            history=[
                _h(1, "Berapa occupancy rate bulan April 2026?", "Occupancy April 2026 mencapai 78%."),
                _h(2, "Bagaimana revenue F&B?", "Revenue F&B Rp 450 juta."),
                _h(3, "Berapa komplain housekeeping?", "12 komplain, mayoritas kebersihan kamar."),
                _h(4, "Kondisi maintenance AC lantai 3?", "3 unit sedang diperbaiki."),
                _h(5, "Booking spa minggu ini?", "45 booking."),
                _h(6, "Siapa staff terbaik bulan ini?", "Sari dari Front Office."),
                _h(7, "Berapa staff HR aktif?", "8 staff aktif."),
            ],
        ),
        "expected": {"is_dependent": True, "referenced_turn_index": 1},
        "acceptable_referenced_turn_index": {1},
    },
    {
        "id": "S12",
        "deskripsi": "Jebakan false-positive: overlap leksikal, domain berbeda (PALING KRITIS)",
        "payload": TurnPayload(
            session_id="eval-s12",
            turn_index=2,
            role_title="Corporate Revenue Director",
            employee_id="emp-eval",
            question="Berapa revenue reservasi bulan April 2026?",
            history=[_h(1, "Berapa revenue F&B bulan April 2026?", "Revenue F&B April 2026 sebesar Rp 450 juta.")],
        ),
        "expected": {"is_dependent": False, "referenced_turn_index": None},
        "acceptable_referenced_turn_index": None,
    },
]


def run_scenario(scenario: dict) -> dict:
    payload: TurnPayload = scenario["payload"]
    response = _call_llm(payload)
    raw_content = response.choices[0].message.content or ""
    valid_turn_indices = {h.turn_index for h in payload.history}
    result, forced_reason = _parse_and_validate(raw_content, valid_turn_indices)

    acceptable = scenario["acceptable_referenced_turn_index"]
    is_dependent_match = result.is_dependent == scenario["expected"]["is_dependent"]
    if not result.is_dependent:
        referenced_match = scenario["expected"]["referenced_turn_index"] is None
    else:
        referenced_match = acceptable is not None and result.referenced_turn_index in acceptable
    overall_match = is_dependent_match and referenced_match

    record = {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": OPENROUTER_MODEL,
        "request": {
            "system": _SYSTEM_PROMPT,
            "user": _build_user_prompt(payload),
        },
        "raw_response_content": raw_content,
        "usage": {
            "input_tokens": response.usage.prompt_tokens if response.usage else None,
            "output_tokens": response.usage.completion_tokens if response.usage else None,
        },
        "parsed_result": result.model_dump(),
        "forced_independent_reason": forced_reason,
        "expected": scenario["expected"],
        "acceptable_referenced_turn_index": sorted(acceptable) if acceptable else None,
        "toleransi": scenario.get("toleransi"),
        "match": overall_match,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{scenario['id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    return record


def main() -> None:
    results = [run_scenario(s) for s in SCENARIOS]
    print(f"\n{'ID':<5} {'MATCH':<8} {'is_dependent':<14} {'ref_turn':<10} {'expected'}")
    print("-" * 70)
    for r in results:
        status = "LOLOS" if r["match"] else "REVIEW"
        got = f"{r['parsed_result']['is_dependent']}"
        ref = str(r["parsed_result"]["referenced_turn_index"])
        exp = f"{r['expected']['is_dependent']}/{r['expected']['referenced_turn_index']}"
        print(f"{r['scenario_id']:<5} {status:<8} {got:<14} {ref:<10} {exp}")

    total = len(results)
    matched = sum(1 for r in results if r["match"])
    print(f"\n{matched}/{total} sesuai ekspektasi (termasuk toleransi eksplisit).")
    print(f"Payload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
