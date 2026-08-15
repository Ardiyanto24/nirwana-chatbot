"""Jalankan 12 skenario di rancangan.md, simpan payload lengkap (request+
response mentah) ke payloads/, cetak ringkasan match/mismatch ke console.

Satu panggilan API nyata per skenario (lewat _call_llm() yang sama persis
dipakai rewrite_to_standalone() produksi - bukan logic duplikat). Match
dinilai lewat required_phrases (semua harus muncul) dan forbidden_phrases
(tidak boleh muncul sama sekali) di rewritten_question, case-insensitive.

Jalankan dari root repo: uv run python evals/1.4-rewrite-mandiri/run_eval.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Skrip ini dijalankan langsung (bukan lewat `-c`), jadi sys.path[0] adalah
# folder skrip ini sendiri, bukan root repo - root repo ditambahkan manual
# supaya "src" bisa diimpor, sama seperti pola evals/1.3-.../run_eval.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config.llm import OPENROUTER_MODEL_REWRITE
from src.layers.context_resolution.rewrite import (
    _SYSTEM_PROMPT,
    _build_user_prompt,
    _call_llm,
    _detect_residual_reference,
)
from src.schemas.turn_payload import HistoryTurn, TurnPayload

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"


def _h(turn_index: int, question: str, answer: str) -> HistoryTurn:
    return HistoryTurn(turn_index=turn_index, question=question, answer=answer)


SCENARIOS = [
    {
        "id": "S01",
        "deskripsi": "Baseline: sudah mandiri, tanpa histori sama sekali",
        "payload": TurnPayload(
            session_id="eval-s01",
            turn_index=1,
            role_title="General Manager",
            employee_id="emp-eval",
            question="Berapa occupancy rate properti kita bulan Juni 2026?",
            history=[],
        ),
        "required_phrases": ["juni", "2026", "occupancy"],
        "forbidden_phrases": [],
    },
    {
        "id": "S02",
        "deskripsi": "Sudah mandiri meski histori ada tapi tidak relevan",
        "payload": TurnPayload(
            session_id="eval-s02",
            turn_index=2,
            role_title="HR Manager",
            employee_id="emp-eval",
            question="Apa saja fasilitas yang tersedia di area spa?",
            history=[_h(1, "Berapa jumlah staff aktif di departemen HR?", "Departemen HR memiliki 8 staff aktif.")],
        ),
        "required_phrases": ["spa", "fasilitas"],
        "forbidden_phrases": ["hr", "8 staff"],
    },
    {
        "id": "S03",
        "deskripsi": "Elipsis eksplisit, turn N-1",
        "payload": TurnPayload(
            session_id="eval-s03",
            turn_index=2,
            role_title="Corporate Revenue Director",
            employee_id="emp-eval",
            question="Bandingkan dengan bulan sebelumnya.",
            history=[_h(1, "Berapa revenue reservasi bulan Maret 2026?", "Revenue reservasi Maret 2026 sebesar Rp 800 juta.")],
        ),
        "required_phrases": ["februari", "2026", "reservasi"],
        "forbidden_phrases": [],
    },
    {
        "id": "S04",
        "deskripsi": "Elipsis implisit (tanpa penanda eksplisit), turn N-1",
        "payload": TurnPayload(
            session_id="eval-s04",
            turn_index=2,
            role_title="Front Office Staff",
            employee_id="emp-eval",
            question="Kalau untuk Housekeeping?",
            history=[_h(1, "Berapa rating kepuasan tamu untuk Front Office bulan ini?", "Rating kepuasan tamu Front Office bulan ini 4.6 dari 5.")],
        ),
        "required_phrases": ["housekeeping", "rating", "kepuasan"],
        "forbidden_phrases": [],
        "toleransi": "implisit dekat - kegagalan menyebut rating/kepuasan diterima sebagai keterbatasan model, bukan bug",
    },
    {
        "id": "S05",
        "deskripsi": "Elipsis eksplisit, turn jauh + distractor",
        "payload": TurnPayload(
            session_id="eval-s05",
            turn_index=6,
            role_title="Front Office Staff",
            employee_id="emp-eval",
            question="Balik lagi ke komplain yang di awal tadi, apa sudah ada tindak lanjutnya?",
            history=[
                _h(1, "Berapa jumlah komplain yang diterima Front Office bulan ini?", "Front Office menerima 7 komplain bulan ini, mayoritas soal waktu check-in."),
                _h(2, "Bagaimana kondisi kolam renang?", "Kolam renang beroperasi normal, terakhir dibersihkan kemarin."),
                _h(3, "Berapa revenue spa minggu ini?", "Revenue spa minggu ini Rp 32 juta."),
                _h(4, "Siapa yang bertugas shift malam hari ini?", "Shift malam dipegang oleh 3 staff Front Office dan 2 staff Housekeeping."),
                _h(5, "Berapa kamar yang sedang dalam maintenance?", "5 kamar sedang dalam maintenance, estimasi selesai 3 hari."),
            ],
        ),
        "required_phrases": ["front office", "komplain"],
        "forbidden_phrases": ["kolam renang", "maintenance", "shift malam"],
    },
    {
        "id": "S06",
        "deskripsi": "Elipsis implisit, turn jauh + distractor",
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
        "required_phrases": ["spa"],
        "forbidden_phrases": ["f&b", "ac", "lantai 3"],
        "toleransi": "implisit jauh - tidak menyebut kata 'booking' eksplisit diterima, selama tetap 'spa' dan tidak salah tangkap (forbidden tetap wajib)",
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
        "required_phrases": ["occupancy"],
        "forbidden_phrases": ["staff baru", "f&b"],
        "toleransi": "ambigu - bulan spesifik yang dirujuk (April/Maret/lainnya) tidak dipaksa satu jawaban, dicatat di audit",
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
        "required_phrases": ["staff", "maintenance"],
        "forbidden_phrases": ["reservasi", "maret", "800 juta"],
    },
    {
        "id": "S09",
        "deskripsi": "Sesi panjang (10 turn histori), tanpa elipsis apa pun",
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
        "required_phrases": ["suite", "kamar"],
        "forbidden_phrases": ["occupancy", "f&b", "housekeeping", "spa", "hr", "vip", "reservasi"],
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
        "required_phrases": ["housekeeping", "komplain"],
        "forbidden_phrases": [],
    },
    {
        "id": "S11",
        "deskripsi": "Kalimat majemuk campuran elipsis + non-elipsis",
        "payload": TurnPayload(
            session_id="eval-s11",
            turn_index=2,
            role_title="Corporate Revenue Director",
            employee_id="emp-eval",
            question="Bandingkan dengan bulan sebelumnya, dan juga berapa jumlah staff Front Office yang aktif sekarang?",
            history=[_h(1, "Berapa revenue reservasi bulan Maret 2026?", "Revenue reservasi Maret 2026 sebesar Rp 800 juta.")],
        ),
        "required_phrases": ["februari", "2026", "front office", "staff"],
        "forbidden_phrases": [],
    },
    {
        "id": "S12",
        "deskripsi": "Jebakan overlap leksikal: entitas mirip kata, domain berbeda (PALING KRITIS)",
        "payload": TurnPayload(
            session_id="eval-s12",
            turn_index=2,
            role_title="Corporate Revenue Director",
            employee_id="emp-eval",
            question="Berapa revenue reservasi bulan April 2026 tahun ini?",
            history=[_h(1, "Berapa revenue F&B bulan April 2026?", "Revenue F&B April 2026 sebesar Rp 450 juta.")],
        ),
        "required_phrases": ["reservasi", "april", "2026"],
        "forbidden_phrases": ["f&b", "450"],
    },
]


def _call_with_retry(payload: TurnPayload, max_attempts: int = 3):
    """Ditemukan saat eksekusi pertama: OpenRouter kadang mengembalikan
    response tanpa `choices` (200 OK, bukan exception) - transient, tidak
    reproducible dengan payload yang sama (dikonfirmasi lewat retry manual).
    Retry sederhana di sini, terpisah dari fallback produksi rewrite.py yang
    sengaja tidak retry (fail-fast ke teks asli, lihat decisions.md
    Keputusan 8) - skrip eval boleh retry karena tujuannya mengumpulkan data
    kualitas model, bukan melayani request pengguna nyata."""
    last_response = None
    for attempt in range(max_attempts):
        response = _call_llm(payload)
        if response.choices:
            return response
        last_response = response
    raise RuntimeError(
        f"response.choices kosong setelah {max_attempts} percobaan: {last_response!r}"
    )


def run_scenario(scenario: dict) -> dict:
    payload: TurnPayload = scenario["payload"]
    response = _call_with_retry(payload)
    raw_content = (response.choices[0].message.content or "").strip()
    lowered = raw_content.lower()

    required = scenario["required_phrases"]
    forbidden = scenario["forbidden_phrases"]
    required_missing = [p for p in required if p not in lowered]
    forbidden_present = [p for p in forbidden if p in lowered]
    match = not required_missing and not forbidden_present

    residual_phrases = _detect_residual_reference(raw_content) if payload.history else []

    record = {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": OPENROUTER_MODEL_REWRITE,
        "request": {
            "system": _SYSTEM_PROMPT,
            "user": _build_user_prompt(payload),
        },
        "rewritten_question": raw_content,
        "usage": {
            "input_tokens": response.usage.prompt_tokens if response.usage else None,
            "output_tokens": response.usage.completion_tokens if response.usage else None,
        },
        "required_phrases": required,
        "forbidden_phrases": forbidden,
        "required_missing": required_missing,
        "forbidden_present": forbidden_present,
        "residual_reference_phrases": residual_phrases,
        "toleransi": scenario.get("toleransi"),
        "match": match,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{scenario['id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    return record


def main() -> None:
    results = [run_scenario(s) for s in SCENARIOS]
    print(f"\n{'ID':<5} {'MATCH':<8} {'REWRITTEN_QUESTION'}")
    print("-" * 100)
    for r in results:
        status = "LOLOS" if r["match"] else "REVIEW"
        print(f"{r['scenario_id']:<5} {status:<8} {r['rewritten_question']}")

    total = len(results)
    matched = sum(1 for r in results if r["match"])
    print(f"\n{matched}/{total} sesuai ekspektasi (termasuk toleransi eksplisit).")
    print(f"Payload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
