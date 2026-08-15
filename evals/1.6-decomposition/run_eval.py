"""Jalankan skenario di rancangan.md, simpan payload lengkap (hasil
DecompositionResult/VerifikasiResult) ke payloads/, cetak ringkasan
match/mismatch ke console.

Reuse decompose_question()/verifikasi_pemecahan() produksi langsung - bukan
logic duplikat. Sebagian skenario punya "check" otomatis (structural), yang
lain genuinely butuh audit manual (ditandai toleransi) - keduanya tetap
disimpan lengkap untuk ditinjau di audit.md.

Jalankan dari root repo: uv run python evals/1.6-decomposition/run_eval.py
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.decomposition.decompose import decompose_question
from src.layers.decomposition.verifikasi import verifikasi_pemecahan
from src.schemas.decomposition import (
    AtomicIntent,
    KlasifikasiKebutuhan,
    PemecahanResult,
    RelasiKebutuhan,
)
from src.schemas.session_memory import LabelBentukJawaban

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"


def _count_relasi(result, relasi: RelasiKebutuhan) -> int:
    return sum(1 for ai in result.atomic_intents if ai.relasi == relasi)


def _has_label(result, label: LabelBentukJawaban) -> bool:
    return any(ai.label_bentuk_jawaban == label for ai in result.atomic_intents)


def _bergantung_pada_valid(result) -> bool:
    ids = {ai.atomic_intent_id for ai in result.atomic_intents}
    for ai in result.atomic_intents:
        if ai.relasi == RelasiKebutuhan.BERGANTUNG:
            if not ai.bergantung_pada or not set(ai.bergantung_pada).issubset(ids):
                return False
    return True


SCENARIOS = [
    {
        "id": "S01",
        "deskripsi": "Tunggal murni",
        "question": "Berapa occupancy rate bulan Juni 2026?",
        "check": lambda r: (
            r.klasifikasi == KlasifikasiKebutuhan.TUNGGAL
            and len(r.atomic_intents) == 1
            and r.atomic_intents[0].relasi == RelasiKebutuhan.INDEPENDEN
            and r.atomic_intents[0].label_bentuk_jawaban == LabelBentukJawaban.NILAI_TUNGGAL
            and r.verifikasi_valid is True
        ),
    },
    {
        "id": "S02",
        "deskripsi": "Majemuk independen murni (anti false-positive relasi)",
        "question": "Berapa revenue F&B bulan ini dan berapa jumlah staff Housekeeping yang aktif?",
        "check": lambda r: (
            r.klasifikasi == KlasifikasiKebutuhan.MAJEMUK_INDEPENDEN
            and len(r.atomic_intents) == 2
            and _count_relasi(r, RelasiKebutuhan.INDEPENDEN) == 2
            and r.verifikasi_valid is True
        ),
    },
    {
        "id": "S03",
        "deskripsi": "Majemuk bergantung, 2 kebutuhan",
        "question": "Bandingkan occupancy rate April 2026 dengan Maret 2026.",
        "check": lambda r: (
            r.klasifikasi == KlasifikasiKebutuhan.MAJEMUK_BERGANTUNG
            and len(r.atomic_intents) >= 2
            and _count_relasi(r, RelasiKebutuhan.BERGANTUNG) >= 1
            and _bergantung_pada_valid(r)
            and _has_label(r, LabelBentukJawaban.PERBANDINGAN)
            and r.verifikasi_valid is True
        ),
    },
    {
        "id": "S04",
        "deskripsi": "Majemuk bergantung berlapis (3 kebutuhan dasar + 1 gabungan)",
        "question": "Bandingkan revenue reservasi Januari, Februari, dan Maret 2026.",
        "check": lambda r: (
            r.klasifikasi == KlasifikasiKebutuhan.MAJEMUK_BERGANTUNG
            and len(r.atomic_intents) >= 4
            and any(
                ai.relasi == RelasiKebutuhan.BERGANTUNG and ai.bergantung_pada and len(ai.bergantung_pada) >= 2
                for ai in r.atomic_intents
            )
            and _bergantung_pada_valid(r)
            and _has_label(r, LabelBentukJawaban.PERBANDINGAN)
            and r.verifikasi_valid is True
        ),
    },
    {
        "id": "S05",
        "deskripsi": "Kalimat ambigu (tunggal vs majemuk implisit)",
        "question": "Bagaimana performa Front Office bulan ini?",
        "check": lambda r: r.verifikasi_valid is True,
        "toleransi": "klasifikasi bebas (tunggal/majemuk apa pun), yang wajib cuma internal-consistent (verifikasi_valid=True)",
    },
    {
        "id": "S06",
        "deskripsi": "Retry benar-benar terpicu",
        "question": (
            "Bandingkan rata-rata rating kepuasan tamu Front Office dengan rata-rata "
            "rating kepuasan tamu Housekeeping untuk periode yang sama, dengan tren 3 "
            "bulan terakhir masing-masing."
        ),
        "check": lambda r: r.verifikasi_valid is True and _has_label(r, LabelBentukJawaban.TREN),
        "toleransi": "retry_count boleh 0 - dicatat sebagai temuan (retry terpicu atau tidak), bukan pass/fail",
    },
    {
        "id": "S07",
        "deskripsi": "Label tren",
        "question": "Bagaimana tren occupancy rate 6 bulan terakhir?",
        "check": lambda r: (
            len(r.atomic_intents) == 1
            and r.atomic_intents[0].label_bentuk_jawaban == LabelBentukJawaban.TREN
            and r.atomic_intents[0].relasi == RelasiKebutuhan.INDEPENDEN
        ),
    },
    {
        "id": "S08",
        "deskripsi": "Label peringkat",
        "question": "Siapa 5 staff dengan rating kepuasan tamu tertinggi bulan ini?",
        "check": lambda r: (
            len(r.atomic_intents) == 1
            and r.atomic_intents[0].label_bentuk_jawaban == LabelBentukJawaban.PERINGKAT
        ),
    },
    {
        "id": "S09",
        "deskripsi": "Label komposisi",
        "question": "Bagaimana breakdown revenue bulan ini per departemen?",
        "check": lambda r: (
            len(r.atomic_intents) == 1
            and r.atomic_intents[0].label_bentuk_jawaban == LabelBentukJawaban.KOMPOSISI
        ),
    },
    {
        "id": "S10",
        "deskripsi": "Jebakan overlap leksikal (PALING KRITIS)",
        "question": "Berapa revenue F&B bulan ini, dan berapa revenue reservasi bulan ini?",
        "check": lambda r: (
            r.klasifikasi == KlasifikasiKebutuhan.MAJEMUK_INDEPENDEN
            and len(r.atomic_intents) == 2
            and _count_relasi(r, RelasiKebutuhan.INDEPENDEN) == 2
        ),
    },
    {
        "id": "S12",
        "deskripsi": "Stress test volume (4+ kebutuhan independen)",
        "question": "Berapa occupancy rate, revenue F&B, jumlah komplain housekeeping, dan jumlah staff aktif bulan ini?",
        "check": lambda r: (
            r.klasifikasi == KlasifikasiKebutuhan.MAJEMUK_INDEPENDEN
            and len(r.atomic_intents) == 4
            and _count_relasi(r, RelasiKebutuhan.INDEPENDEN) == 4
            and r.verifikasi_valid is True
        ),
    },
    {
        "id": "S13",
        "deskripsi": "Retry exhausted (usaha replikasi terkontrol, eksploratif)",
        "question": (
            "Bandingkan performa keseluruhan Front Office, Housekeeping, dan F&B "
            "bulan ini berdasarkan rating kepuasan tamu, jumlah komplain, dan "
            "kontribusi revenue masing-masing, lalu urutkan dari yang terbaik."
        ),
        "check": None,
        "toleransi": "eksploratif - dicatat apa adanya (retry_count, exhausted atau tidak), boleh gagal direplikasi",
    },
    {
        "id": "S14",
        "deskripsi": "Klasifikasi anti false-positive (kalimat panjang tapi sebenarnya tunggal)",
        "question": (
            "Berapa total revenue seluruh departemen (F&B, Housekeeping, Spa, dan "
            "Reservasi) yang digabung jadi satu angka bulan ini?"
        ),
        "check": lambda r: r.klasifikasi == KlasifikasiKebutuhan.TUNGGAL and len(r.atomic_intents) == 1,
        "toleransi": "label_bentuk_jawaban spesifik (nilai_tunggal vs komposisi) tidak dipatok, tapi klasifikasi WAJIB tunggal",
    },
]


def _run_decompose_scenario(scenario: dict) -> dict:
    result = decompose_question(scenario["question"])
    match = scenario["check"](result) if scenario["check"] else None
    record = {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": scenario["question"],
        "result": result.model_dump(mode="json"),
        "match": match,
        "toleransi": scenario.get("toleransi"),
    }
    return record


def _run_s11_verifikasi_subtil() -> dict:
    question = "Bandingkan revenue reservasi Maret 2026 dengan Februari 2026."
    id_maret, id_februari, id_bandingkan = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    hasil_keliru = PemecahanResult(
        atomic_intents=[
            AtomicIntent(
                atomic_intent_id=id_maret,
                teks_kebutuhan="Berapa revenue reservasi Maret 2026?",
                label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
            ),
            AtomicIntent(
                atomic_intent_id=id_februari,
                teks_kebutuhan="Berapa revenue reservasi Februari 2026?",
                label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
            ),
            # SENGAJA KELIRU: seharusnya label_bentuk_jawaban=perbandingan,
            # relasi=bergantung ke [id_maret, id_februari].
            AtomicIntent(
                atomic_intent_id=id_bandingkan,
                teks_kebutuhan="Bandingkan revenue reservasi Maret 2026 dengan Februari 2026",
                label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
            ),
        ]
    )
    verifikasi = verifikasi_pemecahan(question, hasil_keliru)
    match = verifikasi.valid is False and bool(verifikasi.alasan)
    return {
        "scenario_id": "S11",
        "deskripsi": "Verifikasi menangkap kesalahan subtil (label+relasi keliru, bukan hilang)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "hasil_keliru_injected": hasil_keliru.model_dump(mode="json"),
        "result": verifikasi.model_dump(mode="json"),
        "match": match,
        "toleransi": None,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for scenario in SCENARIOS:
        record = _run_decompose_scenario(scenario)
        results.append(record)
        (OUTPUT_DIR / f"{record['scenario_id']}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"{record['scenario_id']} selesai, match={record['match']}")

    s11 = _run_s11_verifikasi_subtil()
    results.append(s11)
    (OUTPUT_DIR / "S11.json").write_text(
        json.dumps(s11, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"S11 selesai, match={s11['match']}")

    print(f"\n{'ID':<5} {'MATCH':<10} {'DESKRIPSI'}")
    print("-" * 80)
    for r in sorted(results, key=lambda x: x["scenario_id"]):
        status = "N/A (manual)" if r["match"] is None else ("LOLOS" if r["match"] else "REVIEW")
        print(f"{r['scenario_id']:<5} {status:<10} {r['deskripsi']}")

    auto_checked = [r for r in results if r["match"] is not None]
    matched = sum(1 for r in auto_checked if r["match"])
    print(f"\n{matched}/{len(auto_checked)} skenario dengan check otomatis lolos.")
    print(f"{len(results) - len(auto_checked)} skenario butuh audit manual (toleransi/eksploratif).")
    print(f"Payload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
