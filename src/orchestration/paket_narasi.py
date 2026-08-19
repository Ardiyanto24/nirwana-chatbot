"""Penggabungan Paket untuk Narasi (Milestone 7.15): menyatukan TIGA
kategori atomic intent satu turn jadi `list[SessionMemoryPackage]`
tunggal yang siap diteruskan ke Interpretation (`susun_dan_verifikasi_
narasi()`, M7.5) - "titik pertemuan kedua" project.

Kategori 1 - "selesai" (M1.7/M7.9, `matches` status=SELESAI): `match.paket`
masih membawa `atomic_intent_id` dari TURN ASAL (bukan turn ini) - di-key
ulang via `sumber_arsip()` (M1.7, kini publik - lihat
milestones/7.15-sambungan-interpretation-lengkap/decisions.md Keputusan 1)
supaya cocok dengan `match.atomic_intent` turn ini, field lain (nilai_
hasil/label/catatan/status) disalin utuh dari paket lama.

Kategori 2 - hasil Execution (`paket_dari_eksekusi`, M7.14 -> M4.3 lewat
`susun_dan_simpan_paket_semua()`) - dipakai apa adanya, sudah ber-`atomic_
intent_id` turn ini.

Kategori 3 - "gap": atomic intent `status=PERLU_EKSEKUSI` yang TIDAK
mencapai Execution (tersaring di Domain Gate/Otorisasi/Cakupan Individu/
Retriever/Query Engine/Verification Gate) - disurfacekan sebagai paket
sintetis, klasifikasi 2 tingkat (Keputusan 2): RBAC (SELURUH domain_
decisions `diizinkan=False`) -> status=DITOLAK_OTORISASI, pesan spesifik;
selainnya -> status=GAGAL_TEKNIS, pesan generik. TIDAK disimpan ke Session
Memory (Keputusan 3, murni in-memory untuk narasi turn ini).
"""

from src.layers.context_resolution.matching import sumber_arsip
from src.observability.tracing import get_tracer
from src.schemas.authorization import AtomicIntentAuthorization
from src.schemas.decomposition import AtomicIntent
from src.schemas.matching import AtomicIntentMatch, MatchStatus
from src.schemas.session_memory import SessionMemoryPackage, StatusEksekusi

_TRACER_NAME = "orchestration"

_PESAN_DITOLAK_OTORISASI = "Anda tidak memiliki akses untuk data ini sesuai peran Anda."
_PESAN_GAGAL_TEKNIS = "Sistem tidak berhasil memproses kebutuhan ini karena kendala teknis."


def _paket_selesai(match: AtomicIntentMatch, session_id: str, turn_index: int) -> SessionMemoryPackage:
    paket_lama = match.paket
    assert paket_lama is not None  # dijamin validator AtomicIntentMatch
    return SessionMemoryPackage(
        atomic_intent_id=match.atomic_intent.atomic_intent_id,
        session_id=session_id,
        turn_index=turn_index,
        teks_kebutuhan=paket_lama.teks_kebutuhan,
        label_bentuk_jawaban=paket_lama.label_bentuk_jawaban,
        nilai_hasil=paket_lama.nilai_hasil,
        catatan_interpretasi=paket_lama.catatan_interpretasi,
        status=paket_lama.status,
        sumber=sumber_arsip(paket_lama),
    )


def _adalah_gap_rbac(otorisasi_entry: AtomicIntentAuthorization | None) -> bool:
    if otorisasi_entry is None or not otorisasi_entry.domain_decisions:
        return False
    return all(not d.diizinkan for d in otorisasi_entry.domain_decisions)


def _paket_gap(
    match: AtomicIntentMatch,
    otorisasi_entry: AtomicIntentAuthorization | None,
    session_id: str,
    turn_index: int,
) -> SessionMemoryPackage:
    if _adalah_gap_rbac(otorisasi_entry):
        status = StatusEksekusi.DITOLAK_OTORISASI
        catatan = [_PESAN_DITOLAK_OTORISASI]
    else:
        status = StatusEksekusi.GAGAL_TEKNIS
        catatan = [_PESAN_GAGAL_TEKNIS]

    return SessionMemoryPackage(
        atomic_intent_id=match.atomic_intent.atomic_intent_id,
        session_id=session_id,
        turn_index=turn_index,
        teks_kebutuhan=match.atomic_intent.teks_kebutuhan,
        label_bentuk_jawaban=match.atomic_intent.label_bentuk_jawaban,
        nilai_hasil={"rows": []},
        catatan_interpretasi=catatan,
        status=status,
        sumber="eksekusi_baru",
    )


def susun_paket_narasi(
    matches: list[AtomicIntentMatch],
    paket_dari_eksekusi: list[SessionMemoryPackage],
    otorisasi_result: list[AtomicIntentAuthorization],
    session_id: str,
    turn_index: int,
) -> tuple[list[AtomicIntent], list[SessionMemoryPackage]]:
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("orchestration.susun_paket_narasi") as span:
        paket_eksekusi_by_id = {p.atomic_intent_id: p for p in paket_dari_eksekusi}
        otorisasi_by_id = {
            o.atomic_intent.atomic_intent_id: o for o in otorisasi_result
        }

        atomic_intents: list[AtomicIntent] = []
        packages: list[SessionMemoryPackage] = []
        selesai_count = 0
        eksekusi_count = 0
        gap_rbac_count = 0
        gap_teknis_count = 0

        for match in matches:
            atomic_intent_id = match.atomic_intent.atomic_intent_id

            if match.status == MatchStatus.SELESAI:
                atomic_intents.append(match.atomic_intent)
                packages.append(_paket_selesai(match, session_id, turn_index))
                selesai_count += 1
                continue

            if atomic_intent_id in paket_eksekusi_by_id:
                atomic_intents.append(match.atomic_intent)
                packages.append(paket_eksekusi_by_id[atomic_intent_id])
                eksekusi_count += 1
                continue

            otorisasi_entry = otorisasi_by_id.get(atomic_intent_id)
            atomic_intents.append(match.atomic_intent)
            packages.append(_paket_gap(match, otorisasi_entry, session_id, turn_index))
            if _adalah_gap_rbac(otorisasi_entry):
                gap_rbac_count += 1
            else:
                gap_teknis_count += 1

        span.set_attribute("paket_narasi.selesai_count", selesai_count)
        span.set_attribute("paket_narasi.eksekusi_count", eksekusi_count)
        span.set_attribute("paket_narasi.gap_rbac_count", gap_rbac_count)
        span.set_attribute("paket_narasi.gap_teknis_count", gap_teknis_count)

        return atomic_intents, packages
