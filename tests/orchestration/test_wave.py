"""Test suite `kelompokkan_wave()` (Milestone 7.14) - pengelompokan
gelombang eksekusi murni deterministik berdasar `AtomicIntent.relasi`/
`bergantung_pada`, standalone (tanpa mock layer manapun)."""

import uuid

from src.orchestration.wave import kelompokkan_wave
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.query_engine import HasilPenyusunanRequest, HasilVerifikasiBentukRequest
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.verification_gate import QueryEngineRequest


def _buat_atomic_intent(
    teks: str = "kebutuhan uji",
    relasi: RelasiKebutuhan = RelasiKebutuhan.INDEPENDEN,
    bergantung_pada: list[str] | None = None,
) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=relasi,
        bergantung_pada=bergantung_pada,
    )


def _buat_entry(
    atomic_intent: AtomicIntent,
) -> tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]:
    request = QueryEngineRequest(domain="facility", view_name="v_housekeeping_staff_daily", params={})
    hasil_susun = HasilPenyusunanRequest(
        atomic_intent=atomic_intent, request=request, status=StatusEksekusi.BERHASIL
    )
    hasil_verifikasi = HasilVerifikasiBentukRequest(
        atomic_intent=atomic_intent, request=request, status=StatusEksekusi.BERHASIL,
        lolos=True, alasan=None,
    )
    return hasil_susun, hasil_verifikasi


def _ids(wave: list) -> set[str]:
    return {item[0].atomic_intent.atomic_intent_id for item in wave}


def test_list_kosong_hasil_kosong():
    assert kelompokkan_wave([]) == []


def test_semua_independen_satu_wave():
    a = _buat_atomic_intent("a")
    b = _buat_atomic_intent("b")
    c = _buat_atomic_intent("c")
    items = [_buat_entry(a), _buat_entry(b), _buat_entry(c)]

    waves = kelompokkan_wave(items)

    assert len(waves) == 1
    assert _ids(waves[0]) == {a.atomic_intent_id, b.atomic_intent_id, c.atomic_intent_id}


def test_satu_dependensi_sederhana_dua_wave():
    a = _buat_atomic_intent("a")
    b = _buat_atomic_intent(
        "b", relasi=RelasiKebutuhan.BERGANTUNG, bergantung_pada=[a.atomic_intent_id]
    )
    items = [_buat_entry(a), _buat_entry(b)]

    waves = kelompokkan_wave(items)

    assert len(waves) == 2
    assert _ids(waves[0]) == {a.atomic_intent_id}
    assert _ids(waves[1]) == {b.atomic_intent_id}


def test_multi_dependensi_level_dari_max_parent():
    """C bergantung pada A (wave 1) dan B (wave 1) -> C wave 2.
    D bergantung pada C (wave 2) -> D wave 3."""
    a = _buat_atomic_intent("a")
    b = _buat_atomic_intent("b")
    c = _buat_atomic_intent(
        "c",
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[a.atomic_intent_id, b.atomic_intent_id],
    )
    d = _buat_atomic_intent(
        "d", relasi=RelasiKebutuhan.BERGANTUNG, bergantung_pada=[c.atomic_intent_id]
    )
    items = [_buat_entry(a), _buat_entry(b), _buat_entry(c), _buat_entry(d)]

    waves = kelompokkan_wave(items)

    assert len(waves) == 3
    assert _ids(waves[0]) == {a.atomic_intent_id, b.atomic_intent_id}
    assert _ids(waves[1]) == {c.atomic_intent_id}
    assert _ids(waves[2]) == {d.atomic_intent_id}


def test_dependensi_hilang_seluruhnya_masuk_wave_1():
    """bergantung_pada merujuk id yang TIDAK ADA di query_engine_result
    sama sekali (tersaring layer sebelumnya) - dianggap terpenuhi,
    intent tetap masuk wave 1 (tidak ada dependensi nyata yang tersisa)."""
    id_hilang = str(uuid.uuid4())
    b = _buat_atomic_intent(
        "b", relasi=RelasiKebutuhan.BERGANTUNG, bergantung_pada=[id_hilang]
    )
    items = [_buat_entry(b)]

    waves = kelompokkan_wave(items)

    assert len(waves) == 1
    assert _ids(waves[0]) == {b.atomic_intent_id}


def test_dependensi_sebagian_hilang_pakai_yang_masih_ada():
    """B bergantung pada [A (ada, wave 1), id_hilang (tidak ada)] ->
    dependensi yang dipakai hanya A -> B wave 2."""
    a = _buat_atomic_intent("a")
    id_hilang = str(uuid.uuid4())
    b = _buat_atomic_intent(
        "b",
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[a.atomic_intent_id, id_hilang],
    )
    items = [_buat_entry(a), _buat_entry(b)]

    waves = kelompokkan_wave(items)

    assert len(waves) == 2
    assert _ids(waves[0]) == {a.atomic_intent_id}
    assert _ids(waves[1]) == {b.atomic_intent_id}


def test_siklus_fail_open_tidak_infinite_loop():
    """A bergantung pada B, B bergantung pada A - siklus murni buatan
    (tidak mungkin organik dari Decomposition asli). Wajib TERMINATE
    (bukan infinite loop) dan mengembalikan seluruh item apa adanya di
    SATU wave fallback, bukan crash/hang."""
    id_a = str(uuid.uuid4())
    id_b = str(uuid.uuid4())
    a = AtomicIntent(
        atomic_intent_id=id_a,
        teks_kebutuhan="a",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[id_b],
    )
    b = AtomicIntent(
        atomic_intent_id=id_b,
        teks_kebutuhan="b",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[id_a],
    )
    items = [_buat_entry(a), _buat_entry(b)]

    waves = kelompokkan_wave(items)

    total_items = sum(len(w) for w in waves)
    assert total_items == 2
    assert _ids(waves[-1]) == {id_a, id_b}


def test_seluruh_item_muncul_persis_sekali_kasus_campuran():
    a = _buat_atomic_intent("a")
    b = _buat_atomic_intent("b")
    c = _buat_atomic_intent(
        "c",
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[a.atomic_intent_id, b.atomic_intent_id],
    )
    items = [_buat_entry(a), _buat_entry(b), _buat_entry(c)]

    waves = kelompokkan_wave(items)

    seen = [aid for w in waves for aid in _ids(w)]
    assert sorted(seen) == sorted([a.atomic_intent_id, b.atomic_intent_id, c.atomic_intent_id])
    assert len(seen) == len(set(seen))
