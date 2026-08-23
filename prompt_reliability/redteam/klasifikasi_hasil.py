"""Klasifikasi hasil red-team Milestone 8.5 dari output `promptfoo eval --repeat N`.

Menerima satu atau lebih path `--output <file>.json` (skema sama
`push_results.py`, `results.results[]` per repetisi), kelompokkan per
(file, skenario) - BUKAN skenario saja, supaya 2 config berbeda yang
kebetulan py nama skenario identik (mis. "S05_..." dipakai ulang di
`identifikasi.redteam.promptfooconfig.yaml` DAN
`verifikasi_titik_buta.redteam.promptfooconfig.yaml`, ditemukan saat
verifikasi Checkpoint 4) TIDAK diam-diam tercampur jadi satu baris
menyesatkan. Pisahkan error infra (mis. "Python worker timed out" -
`docs/keterbatasan-diterima.md` #7) dari kegagalan assertion genuine
(`success=False` tanpa indikasi infra) sebelum diklasifikasi
(Keputusan 3, `milestones/8.5-.../decisions.md`):
    - bertahan_konsisten: SELURUH run valid lolos
    - gagal_konsisten: SELURUH run valid gagal (temuan nyata, prioritas tinggi)
    - flaky: campuran lolos/gagal (kemungkinan non-determinisme LLM)
    - tidak_terverifikasi: SEMUA run kena error infra, tidak ada run valid sama sekali

Cetak tabel Markdown ke stdout, siap ditulis ke `$GITHUB_STEP_SUMMARY`.

Jalankan:
    uv run python prompt_reliability/redteam/klasifikasi_hasil.py <output1.json> [output2.json ...]
"""

import json
import sys
from pathlib import Path

_INDIKATOR_ERROR_INFRA = ("timed out", "timeout", "econnreset", "econnrefused")


def _adalah_error_infra(error: str | None) -> bool:
    if not error:
        return False
    error_lower = error.lower()
    return any(indikator in error_lower for indikator in _INDIKATOR_ERROR_INFRA)


def _muat_hasil_per_skenario(
    paths: list[Path],
) -> dict[tuple[str, str], list[tuple[bool, str | None]]]:
    per_skenario: dict[tuple[str, str], list[tuple[bool, str | None]]] = {}
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for hasil in data["results"]["results"]:
            deskripsi = hasil.get("testCase", {}).get("description", "?")
            kunci = (path.stem, deskripsi)
            per_skenario.setdefault(kunci, []).append(
                (bool(hasil.get("success")), hasil.get("error"))
            )
    return per_skenario


def _klasifikasi_skenario(runs: list[tuple[bool, str | None]]) -> tuple[str, int, int]:
    """Return (kategori, jumlah_lolos_valid, jumlah_run_valid)."""
    valid = [sukses for sukses, error in runs if not _adalah_error_infra(error)]
    if not valid:
        return "tidak_terverifikasi", 0, 0

    lolos = sum(1 for sukses in valid if sukses)
    total = len(valid)
    if lolos == total:
        return "bertahan_konsisten", lolos, total
    if lolos == 0:
        return "gagal_konsisten", lolos, total
    return "flaky", lolos, total


_LABEL_KATEGORI = {
    "bertahan_konsisten": "Bertahan konsisten",
    "flaky": "Flaky (kemungkinan non-determinisme)",
    "gagal_konsisten": "GAGAL KONSISTEN (temuan prioritas tinggi)",
    "tidak_terverifikasi": "Tidak terverifikasi (seluruh run kena error infra)",
}


def bangun_laporan_markdown(paths: list[Path]) -> str:
    per_skenario = _muat_hasil_per_skenario(paths)

    baris = [
        "| Config | Skenario | Lolos/Valid | Kategori |",
        "|---|---|---|---|",
    ]
    for config, deskripsi in sorted(per_skenario):
        runs = per_skenario[(config, deskripsi)]
        kategori, lolos, total = _klasifikasi_skenario(runs)
        rasio = f"{lolos}/{total}" if total else f"0/{len(runs)} (seluruh error infra)"
        baris.append(
            f"| `{config}` | `{deskripsi}` | {rasio} | {_LABEL_KATEGORI[kategori]} |"
        )

    return "\n".join(baris)


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: klasifikasi_hasil.py <output1.json> [output2.json ...]",
            file=sys.stderr,
        )
        sys.exit(2)

    paths = [Path(arg) for arg in sys.argv[1:]]
    print(bangun_laporan_markdown(paths))


if __name__ == "__main__":
    main()
