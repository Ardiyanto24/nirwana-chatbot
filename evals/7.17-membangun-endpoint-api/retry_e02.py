"""Retry E02 SAJA - percobaan 1 (`session_id=eval-7.17-e02-http`) melebihi
timeout klien 600s (`httpx.ReadTimeout`), BUKAN hang tanpa progres
(span Jaeger terus bertambah sampai tick terakhir sebelum timeout) -
murni timeout klien yang terlalu ketat untuk skenario gop_margin yang
dikenal lambat (preseden M7.12 ~24.7 menit terburuk). Timeout dinaikkan
ke 1800s di run_eval.py.

Percobaan 2 (`session_id=eval-7.17-e02-http-b`) GAGAL START SAMA SEKALI
("App server gagal start dalam waktu wajar") - akar masalah ditemukan:
`app_proc.terminate()` pada proses "uv run uvicorn ..." percobaan 1
HANYA mematikan proses "uv" (induk), BUKAN "uvicorn" (proses cucu
terpisah di Windows) - server lama tetap hidup+menempati port 8001,
percobaan 2 gagal bind port yang sama. Diperbaiki PERMANEN di
run_eval.py: `_start_app_server()` sekarang memanggil `sys.executable
-m uvicorn ...` LANGSUNG (bukan lewat wrapper "uv run"), `_matikan_app_
server()` baru menambah `taskkill /F /T` sebagai pengaman pohon proses
di Windows. Proses orphan percobaan 1 (PID 24340) dimatikan manual
sebelum percobaan 3 ini.

Percobaan 3 (`session_id=eval-7.17-e02-http-c`) memakai fungsi yang
sudah diperbaiki, TAPI hang lagi tanpa exception (~beberapa menit CPU
nyaris nol, span Jaeger berhenti setelah 2 span awal) - dihentikan
paksa. SAAT investigasi ditemukan bug TERPISAH: `submit_turn()` di
`src/main.py` dideklarasikan `async def` tapi memanggil `proses_turn()`
(sepenuhnya sinkron/blocking) langsung - memblokir event loop TUNGGAL
uvicorn sepenuhnya selama satu turn diproses (server berhenti
merespons APA PUN, termasuk health check, selama request berjalan).
Diperbaiki PERMANEN: `submit_turn()` jadi `def` biasa (FastAPI otomatis
menjalankan di threadpool worker). Percobaan 3 SENDIRI kemungkinan
besar genuinely hang LLM (`docs/keterbatasan-diterima.md` #7 recurrence
lagi), bukan disebabkan bug event-loop ini - tapi bug event-loop tetap
wajib diperbaiki terlepas dari itu.

Percobaan 4 (`session_id=eval-7.17-e02-http-d`) memakai server yang
SUDAH diperbaiki (def biasa) TAPI HANG LAGI di titik yang SAMA (setelah
ketergantungan, sebelum Rewrite/Tarik Memory) - diagnostik terpisah
(panggilan proses_turn() LANGSUNG, TANPA HTTP sama sekali, payload
identik) DIJALANKAN untuk mengisolasi penyebab: hasilnya JUGA hang
(pada titik BERBEDA - setelah 6 span, bukan 2), CPU nyaris nol sama
persis. Ini MENYINGKIRKAN dugaan bug HTTP/nested-threading - pola
konsisten `docs/keterbatasan-diterima.md` #7 (infra acak), sedang lebih
sering terjadi sesi ini (4 hang total: E02 percobaan 3+4, diagnostik
langsung).

Percobaan 5 (`session_id=eval-7.17-e02-http-e`) - upaya terakhir wajar
sebelum didokumentasikan sebagai temuan formal (konsisten filosofi
project, M7.15 E01: diagnosis dulu, bukan retry tanpa batas). E01 SUDAH
tersimpan sukses di percobaan pertama, TIDAK diulang di sini.

Jalankan dari root repo: uv run python evals/7.17-membangun-endpoint-api/retry_e02.py
"""

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_SPEC = importlib.util.spec_from_file_location(
    "run_eval_7_17", Path(__file__).resolve().parent / "run_eval.py"
)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)


def run_e02_percobaan2() -> dict:
    from datetime import datetime, timezone

    raw_http = {
        "session_id": "eval-7.17-e02-http-e",
        "turn_index": 1,
        "role_title": "Front Office Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?",
    }
    print("E02 (percobaan 5): panggilan via HTTP (skenario RBAC gop_margin)...")
    via_http = _MOD._jalankan_via_http(raw_http)
    print(f"  http status={via_http['status_code']}")
    return {
        "kejadian_id": "E02",
        "deskripsi": (
            "Penolakan otorisasi Domain Gate, KK2 - reuse skenario gop_margin - "
            "percobaan 5, session_id baru setelah: percobaan 1 timeout klien 600s, "
            "percobaan 2 gagal start (port bentrok orphan), percobaan 3+4 hang LLM "
            "(keterbatasan-diterima.md #7, dikonfirmasi BUKAN bug HTTP/threading "
            "lewat diagnostik panggilan langsung yang JUGA hang)"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload_http": raw_http,
        "hasil_http": via_http,
        "error": None,
    }


def main() -> None:
    _MOD._cek_prasyarat()
    _MOD._setup_tracing_dengan_capture()

    app_proc = _MOD._start_app_server()
    try:
        record = run_e02_percobaan2()
        _MOD._simpan(record)
        print(f"  http status={record['hasil_http']['status_code']}")
        print(f"\nPayload tersimpan di: {_MOD.OUTPUT_DIR}")
    finally:
        print("Mematikan app server...")
        _MOD._matikan_app_server(app_proc)
        print("  app server dimatikan.")


if __name__ == "__main__":
    main()
