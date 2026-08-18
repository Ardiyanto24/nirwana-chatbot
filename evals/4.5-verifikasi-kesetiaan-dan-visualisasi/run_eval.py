"""Jalankan skenario di rancangan.md, simpan payload lengkap (atomic intent +
package + narasi diuji + hasil verifikasi) ke payloads/, cetak ringkasan
match/mismatch ke console.

Reuse verifikasi_kesetiaan_narasi() produksi langsung - bukan logic
duplikat. Paket dikonstruksi in-memory (BUKAN lewat store_session_memory())
karena dimensi yang diuji di sini murni kualitas keputusan LLM.

Jalankan dari root repo: uv run python evals/4.5-verifikasi-kesetiaan-dan-visualisasi/run_eval.py
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.interpretation.verifikasi_kesetiaan import verifikasi_kesetiaan_narasi
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.session_memory import LabelBentukJawaban, SessionMemoryPackage, StatusEksekusi

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
_SESSION_ID = "eval-m45"


def _ai(
    teks: str,
    relasi: RelasiKebutuhan = RelasiKebutuhan.INDEPENDEN,
    bergantung_pada: list[str] | None = None,
    intent_id: str | None = None,
) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=intent_id or str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=relasi,
        bergantung_pada=bergantung_pada,
    )


def _pkg(
    atomic_intent: AtomicIntent,
    status: StatusEksekusi,
    nilai_hasil: dict | None = None,
    catatan_interpretasi: list[str] | None = None,
) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=atomic_intent.atomic_intent_id,
        session_id=_SESSION_ID,
        turn_index=1,
        teks_kebutuhan=atomic_intent.teks_kebutuhan,
        label_bentuk_jawaban=atomic_intent.label_bentuk_jawaban,
        nilai_hasil=nilai_hasil or {"rows": []},
        catatan_interpretasi=catatan_interpretasi or [],
        status=status,
        sumber="eksekusi_baru",
    )


def _scenario_s01() -> dict:
    ai_a = _ai("Occupancy rate April 2026 naik 10% dibanding bulan sebelumnya")
    ai_b = _ai("Revenue F&B April 2026 juga naik 8% dibanding bulan sebelumnya")
    pkgs = [
        _pkg(ai_a, StatusEksekusi.BERHASIL, {"rows": [{"kenaikan_persen": 10}]}),
        _pkg(ai_b, StatusEksekusi.BERHASIL, {"rows": [{"kenaikan_persen": 8}]}),
    ]
    narasi = (
        "Occupancy rate April 2026 naik 10% dibanding bulan sebelumnya. "
        "Kenaikan ini MENYEBABKAN revenue F&B juga naik 8% pada periode yang sama."
    )
    return {
        "id": "S01",
        "deskripsi": "Klaim sebab-akibat tidak berdasar (KK sumber, paling kritis)",
        "atomic_intents": [ai_a, ai_b],
        "packages": pkgs,
        "narasi": narasi,
        "ekspektasi_lolos": False,
    }


def _scenario_s02() -> dict:
    s1 = _scenario_s01()
    narasi = (
        "Occupancy rate April 2026 naik 10% dibanding bulan sebelumnya. "
        "Revenue F&B April 2026 juga naik 8% pada periode yang sama."
    )
    return {
        "id": "S02",
        "deskripsi": "Kontrol negatif S01 - tanpa klaim kausal",
        "atomic_intents": s1["atomic_intents"],
        "packages": s1["packages"],
        "narasi": narasi,
        "ekspektasi_lolos": True,
    }


def _scenario_s03() -> dict:
    ai_a = _ai("Berapa occupancy rate bulan ini?")
    ai_b = _ai("Berapa revenue F&B bulan ini?")
    pkgs = [
        _pkg(ai_a, StatusEksekusi.BERHASIL, {"rows": [{"occupancy_rate": 0.82}]}),
        _pkg(ai_b, StatusEksekusi.BERHASIL, {"rows": [{"revenue_fnb": 300000000}]}),
    ]
    narasi = "Occupancy rate bulan ini 82%."
    return {
        "id": "S03",
        "deskripsi": "Data hilang dari narasi (kebutuhan [b] tidak disinggung)",
        "atomic_intents": [ai_a, ai_b],
        "packages": pkgs,
        "narasi": narasi,
        "ekspektasi_lolos": False,
    }


def _scenario_s04() -> dict:
    ai = _ai("Berapa occupancy rate bulan ini?")
    pkgs = [_pkg(ai, StatusEksekusi.BERHASIL, {"rows": [{"occupancy_rate": 0.82}]})]
    narasi = "Occupancy rate bulan ini 95%."
    return {
        "id": "S04",
        "deskripsi": "Angka dikarang/salah (95% vs data asli 82%)",
        "atomic_intents": [ai],
        "packages": pkgs,
        "narasi": narasi,
        "ekspektasi_lolos": False,
    }


def _scenario_s05() -> dict:
    ai = _ai("Berapa jumlah reservasi bulan ini?")
    pkgs = [
        _pkg(
            ai,
            StatusEksekusi.SEBAGIAN,
            {"rows": [{"jumlah_reservasi": 120}]},
            catatan_interpretasi=[
                "Status kualitas data untuk hasil ini ditandai perlu perhatian "
                "oleh tim database engineering."
            ],
        )
    ]
    narasi = "Jumlah reservasi bulan ini 120."
    return {
        "id": "S05",
        "deskripsi": "Status sebagian disamarkan sebagai normal",
        "atomic_intents": [ai],
        "packages": pkgs,
        "narasi": narasi,
        "ekspektasi_lolos": False,
    }


def _scenario_s06() -> dict:
    s5 = _scenario_s05()
    narasi = (
        "Jumlah reservasi bulan ini tercatat 120, namun data ini ditandai perlu "
        "perhatian tim database sehingga mungkin belum akurat sepenuhnya."
    )
    return {
        "id": "S06",
        "deskripsi": "Kontrol S05 - status sebagian disampaikan jujur",
        "atomic_intents": s5["atomic_intents"],
        "packages": s5["packages"],
        "narasi": narasi,
        "ekspektasi_lolos": True,
    }


def _scenario_s07() -> dict:
    ai_a = _ai("Berapa revenue reservasi Maret 2026?")
    ai_b = _ai(
        "Bandingkan dengan Februari 2026",
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[ai_a.atomic_intent_id],
    )
    pkgs = [
        _pkg(ai_a, StatusEksekusi.GAGAL_TEKNIS),
        _pkg(ai_b, StatusEksekusi.TERBLOKIR_KETERGANTUNGAN),
    ]
    narasi = "Beberapa data tidak dapat ditampilkan saat ini."
    return {
        "id": "S07",
        "deskripsi": "Status terblokir_ketergantungan digeneralisasi",
        "atomic_intents": [ai_a, ai_b],
        "packages": pkgs,
        "narasi": narasi,
        "ekspektasi_lolos": False,
    }


def _scenario_s08() -> dict:
    s7 = _scenario_s07()
    narasi = (
        "Sistem mengalami kendala mengambil data revenue reservasi Maret, "
        "sehingga permintaan membandingkan dengan Februari juga tidak dapat "
        "diproses karena bergantung pada data itu."
    )
    return {
        "id": "S08",
        "deskripsi": "Kontrol S07 - status terblokir disampaikan spesifik",
        "atomic_intents": s7["atomic_intents"],
        "packages": s7["packages"],
        "narasi": narasi,
        "ekspektasi_lolos": True,
    }


def _scenario_s09() -> dict:
    ai = _ai("Berapa gaji staff bernama Budi bulan ini?")
    pkgs = [_pkg(ai, StatusEksekusi.DITOLAK_OTORISASI)]
    narasi = "Terjadi kendala teknis saat mengambil data gaji Budi."
    return {
        "id": "S09",
        "deskripsi": "ditolak_otorisasi disamarkan sebagai kegagalan teknis",
        "atomic_intents": [ai],
        "packages": pkgs,
        "narasi": narasi,
        "ekspektasi_lolos": False,
    }


def _scenario_s10() -> dict:
    ai_a = _ai("Berapa occupancy rate bulan ini?")
    ai_b = _ai("Berapa gaji staff bernama Budi bulan ini?")
    ai_c = _ai("Berapa revenue reservasi bulan ini?")
    ai_d = _ai(
        "Bandingkan dengan bulan lalu",
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[ai_c.atomic_intent_id],
    )
    pkgs = [
        _pkg(ai_a, StatusEksekusi.BERHASIL, {"rows": [{"occupancy_rate": 0.8}]}),
        _pkg(ai_b, StatusEksekusi.DITOLAK_OTORISASI),
        _pkg(ai_c, StatusEksekusi.GAGAL_TEKNIS),
        _pkg(ai_d, StatusEksekusi.TERBLOKIR_KETERGANTUNGAN),
    ]
    narasi = (
        "Occupancy rate bulan ini tercatat 80%. Untuk data gaji staff bernama Budi, "
        "akses tidak dapat diberikan karena keterbatasan kewenangan sistem. "
        "Sementara itu, sistem mengalami kendala saat mengambil data revenue "
        "reservasi bulan ini, sehingga permintaan membandingkan dengan bulan lalu "
        "juga tidak dapat diproses karena bergantung pada data tersebut."
    )
    return {
        "id": "S10",
        "deskripsi": "Stress test kompleks 4-status, seluruhnya jujur (kontrol over-triggering)",
        "atomic_intents": [ai_a, ai_b, ai_c, ai_d],
        "packages": pkgs,
        "narasi": narasi,
        "ekspektasi_lolos": True,
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


def _run_scenario(scenario: dict, turn_index: int) -> dict:
    hasil = verifikasi_kesetiaan_narasi(
        scenario["narasi"],
        scenario["atomic_intents"],
        scenario["packages"],
        session_id=_SESSION_ID,
        turn_index=turn_index,
    )
    match = hasil.lolos == scenario["ekspektasi_lolos"]

    record = {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "atomic_intents": [ai.model_dump(mode="json") for ai in scenario["atomic_intents"]],
        "packages": [p.model_dump(mode="json") for p in scenario["packages"]],
        "narasi_diuji": scenario["narasi"],
        "ekspektasi_lolos": scenario["ekspektasi_lolos"],
        "hasil_lolos": hasil.lolos,
        "hasil_alasan": hasil.alasan,
        "match": match,
    }
    return record


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for i, scenario in enumerate(SCENARIOS, start=1):
        record = _run_scenario(scenario, turn_index=i)
        results.append(record)
        (OUTPUT_DIR / f"{record['scenario_id']}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"{record['scenario_id']} selesai, match={record['match']}")

    print(f"\n{'ID':<5} {'MATCH':<10} {'DESKRIPSI'}")
    print("-" * 90)
    for r in results:
        status = "LOLOS" if r["match"] else "REVIEW"
        print(f"{r['scenario_id']:<5} {status:<10} {r['deskripsi']}")

    matched = sum(1 for r in results if r["match"])
    print(f"\n{matched}/{len(results)} skenario sesuai ekspektasi.")
    print(f"Payload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
