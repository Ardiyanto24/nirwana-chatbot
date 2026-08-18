"""Jalankan skenario di rancangan.md, simpan payload lengkap (atomic intent +
package + narasi hasil + heuristik) ke payloads/, cetak ringkasan
heuristik ke console.

Reuse susun_narasi()/_turn_reference() produksi langsung - bukan logic
duplikat. Paket dikonstruksi in-memory (BUKAN lewat store_session_memory())
karena dimensi yang diuji di sini murni kualitas narasi LLM, bukan
persistence (sudah dibuktikan formal M1.5/M4.3) - tidak ada DB yang perlu
di-cleanup.

PENTING: heuristik di sini murni LAPIS TAMBAHAN (kata kunci ringan) -
karena output adalah teks bebas (Keputusan 3 decisions.md), verdict akhir
TIDAK bisa hanya dari heuristik otomatis, wajib dilengkapi audit manual
(audit.md, Checkpoint 7 Task 10) - beda dari eval milestone sebelumnya
yang outputnya struktur bisa di-assert penuh otomatis.

Jalankan dari root repo: uv run python evals/4.4-penyusunan-narasi/run_eval.py
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.interpretation.narasi import _turn_reference, susun_narasi
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.session_memory import LabelBentukJawaban, SessionMemoryPackage, StatusEksekusi

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
_SESSION_ID = "eval-m44"


def _ai(
    teks: str,
    label: LabelBentukJawaban = LabelBentukJawaban.NILAI_TUNGGAL,
    relasi: RelasiKebutuhan = RelasiKebutuhan.INDEPENDEN,
    bergantung_pada: list[str] | None = None,
    intent_id: str | None = None,
) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=intent_id or str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=label,
        relasi=relasi,
        bergantung_pada=bergantung_pada,
    )


def _pkg(
    atomic_intent: AtomicIntent,
    status: StatusEksekusi,
    sumber: str = "eksekusi_baru",
    nilai_hasil: dict | None = None,
    catatan_interpretasi: list[str] | None = None,
    turn_index: int = 6,
) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=atomic_intent.atomic_intent_id,
        session_id=_SESSION_ID,
        turn_index=turn_index,
        teks_kebutuhan=atomic_intent.teks_kebutuhan,
        label_bentuk_jawaban=atomic_intent.label_bentuk_jawaban,
        nilai_hasil=nilai_hasil or {"rows": []},
        catatan_interpretasi=catatan_interpretasi or [],
        status=status,
        sumber=sumber,
    )


def _tidak_mengandung(*kata_kunci: str):
    def _cek(narasi: str) -> bool:
        lower = narasi.lower()
        return not any(k.lower() in lower for k in kata_kunci)

    return _cek


def _mengandung_salah_satu(*kata_kunci: str):
    def _cek(narasi: str) -> bool:
        lower = narasi.lower()
        return any(k.lower() in lower for k in kata_kunci)

    return _cek


# --- S01 -------------------------------------------------------------------


def _scenario_s01() -> dict:
    ai_baru = _ai("Berapa occupancy rate April 2026 di Nirwana Resort Bali?")
    ai_lama = _ai("Berapa revenue F&B bulan ini?")
    pkgs = [
        _pkg(ai_baru, StatusEksekusi.BERHASIL, nilai_hasil={"rows": [{"occupancy_rate": 0.82}]}),
        _pkg(
            ai_lama,
            StatusEksekusi.BERHASIL,
            sumber="session_memory (turn 3)",
            nilai_hasil={"rows": [{"revenue_fnb": 452000000}]},
        ),
    ]
    return {
        "id": "S01",
        "deskripsi": "Campuran sumber sederhana (KK1 dasar)",
        "atomic_intents": [ai_baru, ai_lama],
        "packages": pkgs,
        "heuristik": {"angka_82_dan_452_hadir": lambda n: "82" in n and "452" in n},
    }


# --- S02 -------------------------------------------------------------------


def _scenario_s02() -> dict:
    ai = _ai("Berapa gaji staff bernama Budi bulan ini?")
    pkgs = [_pkg(ai, StatusEksekusi.DITOLAK_OTORISASI)]
    return {
        "id": "S02",
        "deskripsi": "ditolak_otorisasi disampaikan spesifik (KK2a)",
        "atomic_intents": [ai],
        "packages": pkgs,
        "heuristik": {
            "menyebut_kata_akses_kewenangan": _mengandung_salah_satu(
                "akses", "kewenangan", "izin", "otorisasi"
            )
        },
    }


# --- S03 -------------------------------------------------------------------


def _scenario_s03() -> dict:
    ai = _ai("Berapa revenue reservasi bulan ini?")
    pkgs = [_pkg(ai, StatusEksekusi.GAGAL_TEKNIS)]
    return {
        "id": "S03",
        "deskripsi": "gagal_teknis disampaikan jujur tanpa detail teknis (KK2b)",
        "atomic_intents": [ai],
        "packages": pkgs,
        "heuristik": {
            "tidak_menyebut_istilah_teknis": _tidak_mengandung(
                "api", "endpoint", "database", "server", "400", "403", "404", "500"
            )
        },
    }


# --- S04 -------------------------------------------------------------------


def _scenario_s04() -> dict:
    ai_ditolak = _ai("Berapa gaji staff bernama Budi bulan ini?")
    ai_gagal = _ai("Berapa revenue reservasi bulan ini?")
    ai_berhasil = _ai("Berapa occupancy rate bulan ini?")
    pkgs = [
        _pkg(ai_ditolak, StatusEksekusi.DITOLAK_OTORISASI),
        _pkg(ai_gagal, StatusEksekusi.GAGAL_TEKNIS),
        _pkg(ai_berhasil, StatusEksekusi.BERHASIL, nilai_hasil={"rows": [{"occupancy_rate": 0.75}]}),
    ]
    return {
        "id": "S04",
        "deskripsi": "Kontras nada ditolak_otorisasi vs gagal_teknis berdampingan (KK2, paling kritis)",
        "atomic_intents": [ai_ditolak, ai_gagal, ai_berhasil],
        "packages": pkgs,
        "heuristik": {},  # murni audit manual
    }


# --- S05 -------------------------------------------------------------------


def _scenario_s05() -> dict:
    ai = _ai("Berapa jumlah reservasi bulan ini?")
    pkgs = [
        _pkg(
            ai,
            StatusEksekusi.SEBAGIAN,
            nilai_hasil={"rows": [{"jumlah_reservasi": 120}]},
            catatan_interpretasi=[
                "Status kualitas data untuk hasil ini ditandai perlu perhatian "
                "oleh tim database engineering (data_quality_status=flagged)."
            ],
        )
    ]
    return {
        "id": "S05",
        "deskripsi": "Hasil sebagian - catatan kualitas data flagged",
        "atomic_intents": [ai],
        "packages": pkgs,
        "heuristik": {
            "menyebut_kata_parsial": _mengandung_salah_satu(
                "parsial", "sebagian", "perlu diverifikasi", "perlu dicek ulang", "kurang pasti"
            )
        },
    }


# --- S06 -------------------------------------------------------------------


def _scenario_s06() -> dict:
    ai = _ai("Berapa jumlah tamu check-in bulan ini?")
    pkgs = [
        _pkg(
            ai,
            StatusEksekusi.SEBAGIAN,
            nilai_hasil={"rows": [{"jumlah_checkin": 340}]},
            catatan_interpretasi=[
                "Data terakhir diperbarui 2026-08-10T00:00:00Z, melewati ambang "
                "kesegaran yang ditetapkan (48 jam)."
            ],
        )
    ]
    return {
        "id": "S06",
        "deskripsi": "Hasil sebagian - catatan staleness (last_refreshed_at)",
        "atomic_intents": [ai],
        "packages": pkgs,
        "heuristik": {
            "menyebut_kata_kesegaran_waktu": _mengandung_salah_satu(
                "diperbarui", "terbaru", "usia data", "2026-08-10"
            )
        },
    }


# --- S07 -------------------------------------------------------------------


def _scenario_s07() -> dict:
    ai1 = _ai("Berapa occupancy rate bulan ini?")
    ai2 = _ai("Berapa revenue F&B bulan ini?")
    ai3 = _ai("Berapa jumlah staff aktif bulan ini?")
    pkgs = [
        _pkg(ai1, StatusEksekusi.BERHASIL, nilai_hasil={"rows": [{"occupancy_rate": 0.8}]}),
        _pkg(ai2, StatusEksekusi.BERHASIL, nilai_hasil={"rows": [{"revenue_fnb": 300000000}]}),
        _pkg(ai3, StatusEksekusi.BERHASIL, nilai_hasil={"rows": [{"jumlah_staff": 45}]}),
    ]
    return {
        "id": "S07",
        "deskripsi": "Berhasil murni, multi-atomic-intent (baseline jangan over-flag)",
        "atomic_intents": [ai1, ai2, ai3],
        "packages": pkgs,
        "heuristik": {
            "tidak_over_flag": _tidak_mengandung(
                "sebagian", "parsial", "perlu diverifikasi", "maaf", "kendala"
            )
        },
    }


# --- S08 -------------------------------------------------------------------


def _scenario_s08() -> dict:
    ai_a = _ai("Berapa revenue reservasi Maret 2026?")
    ai_b = _ai(
        "Bandingkan dengan Februari 2026",
        label=LabelBentukJawaban.PERBANDINGAN,
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[ai_a.atomic_intent_id],
    )
    pkgs = [
        _pkg(ai_a, StatusEksekusi.GAGAL_TEKNIS),
        _pkg(ai_b, StatusEksekusi.TERBLOKIR_KETERGANTUNGAN),
    ]
    return {
        "id": "S08",
        "deskripsi": "terblokir_ketergantungan 1 level",
        "atomic_intents": [ai_a, ai_b],
        "packages": pkgs,
        "heuristik": {
            "menyebut_kata_sebab": _mengandung_salah_satu("karena", "disebabkan", "bergantung", "akibat")
        },
    }


# --- S09 -------------------------------------------------------------------


def _scenario_s09() -> dict:
    ai_a = _ai("Berapa occupancy rate April 2026?")
    ai_b = _ai(
        "Bandingkan dengan Maret 2026",
        label=LabelBentukJawaban.PERBANDINGAN,
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[ai_a.atomic_intent_id],
    )
    ai_c = _ai(
        "Berapa persen kenaikannya",
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[ai_b.atomic_intent_id],
    )
    pkgs = [
        _pkg(ai_a, StatusEksekusi.GAGAL_TEKNIS),
        _pkg(ai_b, StatusEksekusi.TERBLOKIR_KETERGANTUNGAN),
        _pkg(ai_c, StatusEksekusi.TERBLOKIR_KETERGANTUNGAN),
    ]
    return {
        "id": "S09",
        "deskripsi": "terblokir_ketergantungan rantai 2 level (C<-B<-A)",
        "atomic_intents": [ai_a, ai_b, ai_c],
        "packages": pkgs,
        "heuristik": {},  # nuansa kedalaman penjelasan, murni audit manual
    }


# --- S10 -------------------------------------------------------------------


def _scenario_s10() -> dict:
    ai = _ai("Berapa jumlah tiket kerusakan fasilitas umum bulan ini?")
    pkgs = [
        _pkg(
            ai,
            StatusEksekusi.BERHASIL,
            nilai_hasil={"rows": []},
            catatan_interpretasi=[
                "Kosong jika tidak ada tiket kerusakan tercatat pada periode ini - "
                "bukan indikasi data hilang."
            ],
        )
    ]
    return {
        "id": "S10",
        "deskripsi": "Catatan nullable-bermakna disampaikan jujur",
        "atomic_intents": [ai],
        "packages": pkgs,
        "heuristik": {
            "tidak_bilang_data_hilang": _tidak_mengandung(
                "data tidak tersedia", "data hilang", "tidak ditemukan datanya"
            )
        },
    }


# --- S11 -------------------------------------------------------------------


def _scenario_s11() -> dict:
    ai_a = _ai("Occupancy rate April 2026 naik 10% dibanding bulan sebelumnya")
    ai_b = _ai("Revenue F&B April 2026 juga naik 8% dibanding bulan sebelumnya")
    pkgs = [
        _pkg(ai_a, StatusEksekusi.BERHASIL, nilai_hasil={"rows": [{"occupancy_rate_naik_persen": 10}]}),
        _pkg(ai_b, StatusEksekusi.BERHASIL, nilai_hasil={"rows": [{"revenue_fnb_naik_persen": 8}]}),
    ]
    return {
        "id": "S11",
        "deskripsi": "Jebakan klaim sebab-akibat dari data deskriptif",
        "atomic_intents": [ai_a, ai_b],
        "packages": pkgs,
        "heuristik": {
            "tidak_klaim_kausal": _tidak_mengandung(
                "menyebabkan", "sehingga revenue", "akibatnya revenue", "karena naiknya occupancy"
            )
        },
    }


# --- S12 -------------------------------------------------------------------


def _scenario_s12() -> dict:
    ai_a = _ai("Berapa gaji staff bernama Budi bulan ini?")
    ai_b = _ai("Berapa revenue reservasi bulan ini?")
    pkgs = [
        _pkg(ai_a, StatusEksekusi.DITOLAK_OTORISASI),
        _pkg(ai_b, StatusEksekusi.GAGAL_TEKNIS),
    ]
    return {
        "id": "S12",
        "deskripsi": "Seluruh atomic intent turn ini gagal/ditolak (kejujuran total)",
        "atomic_intents": [ai_a, ai_b],
        "packages": pkgs,
        "heuristik": {
            "tidak_ada_angka_hasil": _tidak_mengandung("75%", "452.000.000", "120 reservasi")
        },
    }


# --- S13 -------------------------------------------------------------------


def _scenario_s13() -> dict:
    ai_baru = _ai("Berapa occupancy rate bulan ini?")
    ai_turn2 = _ai("Berapa revenue F&B bulan lalu?")
    ai_turn4 = _ai("Berapa jumlah staff aktif dua bulan lalu?")
    pkgs = [
        _pkg(ai_baru, StatusEksekusi.BERHASIL, nilai_hasil={"rows": [{"occupancy_rate": 0.78}]}),
        _pkg(
            ai_turn2,
            StatusEksekusi.BERHASIL,
            sumber="session_memory (turn 2)",
            nilai_hasil={"rows": [{"revenue_fnb": 280000000}]},
        ),
        _pkg(
            ai_turn4,
            StatusEksekusi.BERHASIL,
            sumber="session_memory (turn 4)",
            nilai_hasil={"rows": [{"jumlah_staff": 42}]},
        ),
    ]
    return {
        "id": "S13",
        "deskripsi": "Lintas-turn ganda (2 turn berbeda dirujuk sekaligus)",
        "atomic_intents": [ai_baru, ai_turn2, ai_turn4],
        "packages": pkgs,
        "heuristik": {},
        "cek_turn_reference": [2, 4],
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
    _scenario_s12(),
    _scenario_s13(),
]


def _run_scenario(scenario: dict, turn_index: int) -> dict:
    hasil = susun_narasi(
        scenario["atomic_intents"], scenario["packages"], session_id=_SESSION_ID, turn_index=turn_index
    )
    narasi = hasil.narasi

    heuristik_hasil = {nama: fn(narasi) for nama, fn in scenario["heuristik"].items()}
    heuristik_lolos = all(heuristik_hasil.values()) if heuristik_hasil else None

    turn_ref_aktual = _turn_reference(scenario["packages"])
    cek_turn_ref = scenario.get("cek_turn_reference")
    turn_ref_lolos = (turn_ref_aktual == cek_turn_ref) if cek_turn_ref is not None else None

    record = {
        "scenario_id": scenario["id"],
        "deskripsi": scenario["deskripsi"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "atomic_intents": [ai.model_dump(mode="json") for ai in scenario["atomic_intents"]],
        "packages": [p.model_dump(mode="json") for p in scenario["packages"]],
        "narasi": narasi,
        "heuristik_hasil": heuristik_hasil,
        "heuristik_lolos": heuristik_lolos,
        "turn_reference_aktual": turn_ref_aktual,
        "turn_reference_ekspektasi": cek_turn_ref,
        "turn_reference_lolos": turn_ref_lolos,
    }
    return record


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for i, scenario in enumerate(SCENARIOS, start=6):
        record = _run_scenario(scenario, turn_index=i)
        results.append(record)
        (OUTPUT_DIR / f"{record['scenario_id']}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        status = "LOLOS" if record["heuristik_lolos"] is not False else "REVIEW"
        print(f"{record['scenario_id']} selesai, heuristik={status}")

    print(f"\n{'ID':<5} {'HEURISTIK':<12} {'DESKRIPSI'}")
    print("-" * 90)
    for r in results:
        if r["heuristik_lolos"] is None:
            status = "N/A"
        elif r["heuristik_lolos"]:
            status = "LOLOS"
        else:
            status = "REVIEW"
        print(f"{r['scenario_id']:<5} {status:<12} {r['deskripsi']}")

    print(f"\nPayload+narasi lengkap tersimpan di: {OUTPUT_DIR}")
    print("Verdict akhir tetap butuh audit manual (audit.md) - heuristik di atas hanya lapis tambahan.")


if __name__ == "__main__":
    main()
