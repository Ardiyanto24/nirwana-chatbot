"""Jalankan skenario di rancangan.md, simpan payload lengkap ke payloads/,
cetak ringkasan ke console.

Bagian A: cari_bm25() langsung (deterministik, tanpa network) - dua kali
jalan (A1/A2), bukti tambahan KK1/KK2 sudah lolos tests/.

Bagian B: cari_embedding() TIGA KALI per skenario (satu run per model
embedding dibandingkan) - EKSEKUSI NYATA ke OpenRouter, bukan mock.

Jalankan dari root repo: uv run python evals/3.1-pengumpulan-kandidat-view/run_eval.py
Filter opsional: `run_eval.py B3` hanya jalankan skenario B3 (3 model).
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.layers.retriever.pencarian_bm25 import cari_bm25
from src.layers.retriever.pencarian_embedding import cari_embedding
from src.schemas.domain_gate import Domain

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"

# ID model literal (BUKAN import dari src/config/llm.py) - script ini
# membandingkan 3 KANDIDAT TETAP, sengaja tidak mengikuti perubahan
# konstanta produksi pasca-Checkpoint 8 (yang hanya menyisakan 1 model
# final). Arsip historis perbandingan, tetap bisa dijalankan ulang kapan
# pun tanpa bergantung konfigurasi produksi saat ini.
MODELS = {
    "qwen3-4b": "qwen/qwen3-embedding-4b",
    "qwen3-8b": "qwen/qwen3-embedding-8b",
    "openai-small-3": "openai/text-embedding-3-small",
}

BAGIAN_A = [
    {
        "id": "A1",
        "deskripsi": "KK1: okupansi Bali bulan ini",
        "teks_kebutuhan": "okupansi Bali bulan ini",
        "domain_diizinkan": [Domain.RESERVATION],
        "check": lambda kandidat, fb: (
            "v_reservation_room_type_daily" in [k.view_name for k in kandidat]
            and fb is False
        ),
    },
    {
        "id": "A2",
        "deskripsi": "KK2: zero-leakage domain ditolak",
        "teks_kebutuhan": "okupansi Bali bulan ini",
        "domain_diizinkan": [Domain.FNB],
        "check": lambda kandidat, fb: all(
            k.domain == Domain.FNB for k in kandidat
        ),
    },
]

BAGIAN_B = [
    {
        "id": "B1",
        "deskripsi": "Sinonim non-literal: kanal booking (reservation)",
        "teks_kebutuhan": (
            "tamu-tamu ini pesannya lewat mana aja ya, langsung ke kita apa "
            "lewat aplikasi pihak ketiga"
        ),
        "domain_diizinkan": [Domain.RESERVATION],
        "target": "v_reservation_channel_daily",
    },
    {
        "id": "B2",
        "deskripsi": "Bahasa sehari-hari vs istilah teknis: waste F&B (fnb)",
        "teks_kebutuhan": (
            "berapa duit yang kebuang percuma gara-gara bahan makanan gak "
            "kepake, dan kenapa bisa gitu"
        ),
        "domain_diizinkan": [Domain.FNB],
        "target": "v_fnb_waste_daily",
    },
    {
        "id": "B3",
        "deskripsi": "Typo/variasi ejaan: okupansi (reservation)",
        "teks_kebutuhan": "okupasi hotel minggu ini gimana",
        "domain_diizinkan": [Domain.RESERVATION],
        "target": "v_reservation_room_type_daily",
    },
    {
        "id": "B4",
        "deskripsi": "Framing bisnis abstrak: diskon vs margin (reservation)",
        "teks_kebutuhan": (
            "kenapa untung kita turun padahal harga kamar lagi didiskon "
            "gede-gedean"
        ),
        "domain_diizinkan": [Domain.RESERVATION],
        "target": "v_reservation_gop_impact_monthly",
    },
    {
        "id": "B5",
        "deskripsi": "Partial-stem/kosakata umum lintas-view: turnover HR (hr)",
        "teks_kebutuhan": (
            "berapa banyak karyawan yang keluar atau berhenti kerja di tiap "
            "departemen"
        ),
        "domain_diizinkan": [Domain.HR],
        "target": "v_hr_turnover_snapshot",
    },
]


def _run_bagian_a(scenario: dict) -> dict:
    kandidat, perlu_fallback = cari_bm25(
        scenario["teks_kebutuhan"], scenario["domain_diizinkan"]
    )
    match = scenario["check"](kandidat, perlu_fallback)
    return {
        "scenario_id": scenario["id"],
        "bagian": "A",
        "deskripsi": scenario["deskripsi"],
        "teks_kebutuhan": scenario["teks_kebutuhan"],
        "domain_diizinkan": [d.value for d in scenario["domain_diizinkan"]],
        "kandidat": [k.model_dump(mode="json") for k in kandidat],
        "perlu_fallback": perlu_fallback,
        "match": match,
    }


def _run_bagian_b(scenario: dict, model_key: str, model_id: str) -> dict:
    mulai = time.perf_counter()
    kandidat, gagal = cari_embedding(
        scenario["teks_kebutuhan"], scenario["domain_diizinkan"], model_id
    )
    latensi_detik = time.perf_counter() - mulai

    view_names = [k.view_name for k in kandidat]
    target = scenario["target"]
    recall = target in view_names
    posisi = view_names.index(target) + 1 if recall else None

    return {
        "scenario_id": scenario["id"],
        "bagian": "B",
        "model_key": model_key,
        "model_id": model_id,
        "deskripsi": scenario["deskripsi"],
        "teks_kebutuhan": scenario["teks_kebutuhan"],
        "domain_diizinkan": [d.value for d in scenario["domain_diizinkan"]],
        "target": target,
        "gagal": gagal,
        "recall": recall,
        "posisi_target": posisi,
        "total_kandidat": len(kandidat),
        "latensi_detik": round(latensi_detik, 3),
        "kandidat": [k.model_dump(mode="json") for k in kandidat],
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    only_id = sys.argv[1] if len(sys.argv) > 1 else None

    hasil_a = []
    for scenario in BAGIAN_A:
        if only_id and scenario["id"] != only_id:
            continue
        record = _run_bagian_a(scenario)
        hasil_a.append(record)
        (OUTPUT_DIR / f"{record['scenario_id']}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"{record['scenario_id']} selesai, match={record['match']}", flush=True)

    hasil_b = []
    for scenario in BAGIAN_B:
        if only_id and scenario["id"] != only_id:
            continue
        for model_key, model_id in MODELS.items():
            record = _run_bagian_b(scenario, model_key, model_id)
            hasil_b.append(record)
            (OUTPUT_DIR / f"{record['scenario_id']}_{model_key}.json").write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(
                f"{record['scenario_id']} [{model_key}] selesai, "
                f"recall={record['recall']}, posisi={record['posisi_target']}, "
                f"latensi={record['latensi_detik']}s",
                flush=True,
            )

    if only_id:
        return

    print(f"\n{'ID':<5} {'MATCH':<10} {'DESKRIPSI'}")
    print("-" * 80)
    for r in hasil_a:
        status = "LOLOS" if r["match"] else "REVIEW"
        print(f"{r['scenario_id']:<5} {status:<10} {r['deskripsi']}")

    print(f"\n{'ID':<5} {'MODEL':<16} {'RECALL':<8} {'POSISI':<8} {'LATENSI(s)'}")
    print("-" * 80)
    for r in hasil_b:
        print(
            f"{r['scenario_id']:<5} {r['model_key']:<16} {str(r['recall']):<8} "
            f"{str(r['posisi_target']):<8} {r['latensi_detik']}"
        )

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
