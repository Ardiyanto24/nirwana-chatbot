"""Pengelompokan Wave (Milestone 7.14): partisi `query_engine_result` jadi
gelombang eksekusi berurutan berdasar `AtomicIntent.relasi`/`bergantung_pada`
(Milestone 1.6) - murni deterministik, TANPA LLM, TANPA span (fungsi ini
hidup di dalam span `invoke_agent` yang sudah terbuka `proses_turn()`).

Wave HANYA soal URUTAN EKSEKUSI - tidak ada data hasil wave sebelumnya
yang di-inject ke wave berikutnya (dikonfirmasi user, milestones/
7.14-sambungan-execution/decisions.md Keputusan 2). `susun_request_
atomic_intent()` (M3.4) TIDAK disentuh - wave 2 menyusun request-nya
PERSIS seperti wave 1, hanya PEMANGGILANNYA (Verification Gate +
Execution) yang ditunda sampai wave sebelumnya selesai.

Dua kasus tepi ditangani (Keputusan 8): (a) dependensi yang tidak ada di
`query_engine_result` (tersaring layer manapun sebelumnya) dianggap
"sudah terpenuhi", tidak menghalangi penempatan wave; (b) siklus
(seharusnya tidak mungkin terjadi organik - Decomposition M1.6 tidak
menjamin anti-siklus eksplisit) ditangani fail-open, sisa item yang tidak
terselesaikan setelah algoritma berhenti progress di-force ke wave
terakhir.
"""

from src.schemas.query_engine import (
    HasilPenyusunanRequest,
    HasilVerifikasiBentukRequest,
)

_QueryEngineItem = tuple[HasilPenyusunanRequest, "HasilVerifikasiBentukRequest | None"]


def kelompokkan_wave(
    query_engine_result: list[_QueryEngineItem],
) -> list[list[_QueryEngineItem]]:
    items = list(query_engine_result)
    if not items:
        return []

    by_id = {item[0].atomic_intent.atomic_intent_id: item for item in items}
    remaining = dict(by_id)
    wave_of: dict[str, int] = {}

    while remaining:
        progressed = False
        for atomic_intent_id, item in list(remaining.items()):
            atomic_intent = item[0].atomic_intent
            deps = [d for d in (atomic_intent.bergantung_pada or []) if d in by_id]
            unresolved = [d for d in deps if d not in wave_of]
            if unresolved:
                continue

            wave_of[atomic_intent_id] = max((wave_of[d] for d in deps), default=0) + 1
            del remaining[atomic_intent_id]
            progressed = True

        if not progressed:
            fallback_wave = (max(wave_of.values()) + 1) if wave_of else 1
            for atomic_intent_id in remaining:
                wave_of[atomic_intent_id] = fallback_wave
            break

    max_wave = max(wave_of.values())
    waves: list[list[_QueryEngineItem]] = [[] for _ in range(max_wave)]
    for atomic_intent_id, item in by_id.items():
        waves[wave_of[atomic_intent_id] - 1].append(item)

    return waves
