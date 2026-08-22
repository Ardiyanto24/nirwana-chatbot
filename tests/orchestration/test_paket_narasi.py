"""Test suite `susun_paket_narasi()` (Milestone 7.15) - penggabungan
paket "selesai" (re-key) + hasil Execution + paket sintetis untuk item
tersaring (gap RBAC/teknis), standalone (tanpa mock layer manapun,
seluruh fungsi yang dipanggil murni deterministik)."""

import uuid

from src.orchestration.paket_narasi import susun_paket_narasi
from src.schemas.authorization import AtomicIntentAuthorization, DomainAuthorization
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.matching import AtomicIntentMatch, MatchStatus
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)


def _buat_atomic_intent(teks: str = "kebutuhan uji") -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
        bergantung_pada=None,
    )


def _buat_paket_lama(
    teks: str = "kebutuhan lama", turn_index: int = 1, sumber: str = "eksekusi_baru"
) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=str(uuid.uuid4()),  # ID TURN ASAL, sengaja beda dari turn ini
        session_id="sess-lama",
        turn_index=turn_index,
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_hasil={"rows": [{"nilai": 42}]},
        catatan_interpretasi=["catatan lama"],
        status=StatusEksekusi.BERHASIL,
        sumber=sumber,
    )


def _buat_paket_eksekusi(
    atomic_intent: AtomicIntent, turn_index: int = 5
) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=atomic_intent.atomic_intent_id,
        session_id="sess-1",
        turn_index=turn_index,
        teks_kebutuhan=atomic_intent.teks_kebutuhan,
        label_bentuk_jawaban=atomic_intent.label_bentuk_jawaban,
        nilai_hasil={"rows": [{"nilai": 99}]},
        catatan_interpretasi=[],
        status=StatusEksekusi.BERHASIL,
        sumber="eksekusi_baru",
    )


def _buat_otorisasi(
    atomic_intent: AtomicIntent, domain_decisions: list[DomainAuthorization]
) -> AtomicIntentAuthorization:
    return AtomicIntentAuthorization(
        atomic_intent=atomic_intent, domain_decisions=domain_decisions
    )


def test_selesai_re_key_atomic_intent_id_dan_sumber_benar():
    ai = _buat_atomic_intent("butuh A")
    paket_lama = _buat_paket_lama(teks="butuh A", turn_index=3, sumber="eksekusi_baru")
    match = AtomicIntentMatch(
        atomic_intent=ai, status=MatchStatus.SELESAI, paket=paket_lama
    )

    atomic_intents, packages = susun_paket_narasi(
        [match],
        paket_dari_eksekusi=[],
        otorisasi_result=[],
        session_id="sess-1",
        turn_index=5,
    )

    assert atomic_intents == [ai]
    assert len(packages) == 1
    paket = packages[0]
    # atomic_intent_id di-re-key ke ID turn INI, bukan ID turn asal
    assert paket.atomic_intent_id == ai.atomic_intent_id
    assert paket.atomic_intent_id != paket_lama.atomic_intent_id
    # session_id/turn_index = turn INI
    assert paket.session_id == "sess-1"
    assert paket.turn_index == 5
    # sumber dihitung sumber_arsip(): paket lama "eksekusi_baru" turn 3 -> "session_memory (turn 3)"
    assert paket.sumber == "session_memory (turn 3)"
    # field lain disalin utuh dari paket lama
    assert paket.nilai_hasil == paket_lama.nilai_hasil
    assert paket.catatan_interpretasi == paket_lama.catatan_interpretasi
    assert paket.status == paket_lama.status


def test_selesai_sumber_arsip_berantai_dipertahankan_utuh():
    """Paket lama SUDAH berupa arsip ("session_memory (turn 2)") - sumber_arsip()
    mempertahankan utuh, bukan menimpa jadi turn saat ini."""
    ai = _buat_atomic_intent()
    paket_lama = _buat_paket_lama(sumber="session_memory (turn 2)")
    match = AtomicIntentMatch(
        atomic_intent=ai, status=MatchStatus.SELESAI, paket=paket_lama
    )

    _, packages = susun_paket_narasi(
        [match],
        paket_dari_eksekusi=[],
        otorisasi_result=[],
        session_id="sess-1",
        turn_index=9,
    )

    assert packages[0].sumber == "session_memory (turn 2)"


def test_eksekusi_dipakai_apa_adanya():
    ai = _buat_atomic_intent()
    match = AtomicIntentMatch(
        atomic_intent=ai, status=MatchStatus.PERLU_EKSEKUSI, paket=None
    )
    paket_eksekusi = _buat_paket_eksekusi(ai)

    atomic_intents, packages = susun_paket_narasi(
        [match],
        paket_dari_eksekusi=[paket_eksekusi],
        otorisasi_result=[],
        session_id="sess-1",
        turn_index=5,
    )

    assert atomic_intents == [ai]
    assert packages == [paket_eksekusi]


def test_gap_rbac_seluruh_domain_ditolak():
    ai = _buat_atomic_intent()
    match = AtomicIntentMatch(
        atomic_intent=ai, status=MatchStatus.PERLU_EKSEKUSI, paket=None
    )
    otorisasi = _buat_otorisasi(
        ai,
        [
            DomainAuthorization(
                domain=Domain.FINANCIAL, diizinkan=False, alasan="role tidak diizinkan"
            ),
            DomainAuthorization(
                domain=Domain.HR, diizinkan=False, alasan="role tidak diizinkan"
            ),
        ],
    )

    _, packages = susun_paket_narasi(
        [match],
        paket_dari_eksekusi=[],
        otorisasi_result=[otorisasi],
        session_id="sess-1",
        turn_index=1,
    )

    assert len(packages) == 1
    assert packages[0].status == StatusEksekusi.DITOLAK_OTORISASI
    assert "akses" in packages[0].catatan_interpretasi[0]
    assert packages[0].nilai_hasil == {"rows": []}


def test_gap_teknis_domain_decisions_kosong():
    """Domain Gate sendiri gagal teknis (domain_decisions=[]) - BUKAN RBAC,
    walau tidak ada satu pun domain diizinkan."""
    ai = _buat_atomic_intent()
    match = AtomicIntentMatch(
        atomic_intent=ai, status=MatchStatus.PERLU_EKSEKUSI, paket=None
    )
    otorisasi = _buat_otorisasi(ai, [])

    _, packages = susun_paket_narasi(
        [match],
        paket_dari_eksekusi=[],
        otorisasi_result=[otorisasi],
        session_id="sess-1",
        turn_index=1,
    )

    assert packages[0].status == StatusEksekusi.GAGAL_TEKNIS
    assert "kendala teknis" in packages[0].catatan_interpretasi[0]


def test_gap_teknis_domain_decisions_campuran_sebagian_diizinkan():
    """SEBAGIAN domain diizinkan tapi tetap gap (mis. Retriever/Query
    Engine gagal) - BUKAN RBAC (tidak seluruhnya ditolak)."""
    ai = _buat_atomic_intent()
    match = AtomicIntentMatch(
        atomic_intent=ai, status=MatchStatus.PERLU_EKSEKUSI, paket=None
    )
    otorisasi = _buat_otorisasi(
        ai,
        [
            DomainAuthorization(domain=Domain.RESERVATION, diizinkan=True),
            DomainAuthorization(
                domain=Domain.FINANCIAL, diizinkan=False, alasan="ditolak"
            ),
        ],
    )

    _, packages = susun_paket_narasi(
        [match],
        paket_dari_eksekusi=[],
        otorisasi_result=[otorisasi],
        session_id="sess-1",
        turn_index=1,
    )

    assert packages[0].status == StatusEksekusi.GAGAL_TEKNIS


def test_gap_teknis_tanpa_entry_otorisasi_sama_sekali():
    ai = _buat_atomic_intent()
    match = AtomicIntentMatch(
        atomic_intent=ai, status=MatchStatus.PERLU_EKSEKUSI, paket=None
    )

    _, packages = susun_paket_narasi(
        [match],
        paket_dari_eksekusi=[],
        otorisasi_result=[],
        session_id="sess-1",
        turn_index=1,
    )

    assert packages[0].status == StatusEksekusi.GAGAL_TEKNIS


def test_campuran_ketiga_kategori_dalam_satu_turn_urutan_dan_panjang_sinkron():
    ai_selesai = _buat_atomic_intent("selesai")
    paket_lama = _buat_paket_lama(teks="selesai")
    match_selesai = AtomicIntentMatch(
        atomic_intent=ai_selesai, status=MatchStatus.SELESAI, paket=paket_lama
    )

    ai_eksekusi = _buat_atomic_intent("eksekusi")
    match_eksekusi = AtomicIntentMatch(
        atomic_intent=ai_eksekusi, status=MatchStatus.PERLU_EKSEKUSI, paket=None
    )
    paket_eksekusi = _buat_paket_eksekusi(ai_eksekusi)

    ai_gap_rbac = _buat_atomic_intent("gap rbac")
    match_gap_rbac = AtomicIntentMatch(
        atomic_intent=ai_gap_rbac, status=MatchStatus.PERLU_EKSEKUSI, paket=None
    )
    otorisasi_rbac = _buat_otorisasi(
        ai_gap_rbac,
        [DomainAuthorization(domain=Domain.FINANCIAL, diizinkan=False, alasan="x")],
    )

    ai_gap_teknis = _buat_atomic_intent("gap teknis")
    match_gap_teknis = AtomicIntentMatch(
        atomic_intent=ai_gap_teknis, status=MatchStatus.PERLU_EKSEKUSI, paket=None
    )

    matches = [match_selesai, match_eksekusi, match_gap_rbac, match_gap_teknis]

    atomic_intents, packages = susun_paket_narasi(
        matches,
        paket_dari_eksekusi=[paket_eksekusi],
        otorisasi_result=[otorisasi_rbac],
        session_id="sess-1",
        turn_index=5,
    )

    assert len(atomic_intents) == 4
    assert len(packages) == 4
    assert atomic_intents == [ai_selesai, ai_eksekusi, ai_gap_rbac, ai_gap_teknis]
    assert [p.atomic_intent_id for p in packages] == [
        ai_selesai.atomic_intent_id,
        ai_eksekusi.atomic_intent_id,
        ai_gap_rbac.atomic_intent_id,
        ai_gap_teknis.atomic_intent_id,
    ]
    assert packages[1] is paket_eksekusi
    assert packages[2].status == StatusEksekusi.DITOLAK_OTORISASI
    assert packages[3].status == StatusEksekusi.GAGAL_TEKNIS


def test_list_kosong_hasil_kosong():
    atomic_intents, packages = susun_paket_narasi(
        [],
        paket_dari_eksekusi=[],
        otorisasi_result=[],
        session_id="sess-1",
        turn_index=1,
    )
    assert atomic_intents == []
    assert packages == []
