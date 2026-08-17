"""Test pencarian embedding (Milestone 3.1) - seluruhnya monkeypatch
client OpenRouter, TANPA network call/biaya nyata (ditunda ke Checkpoint
7 eval). Model name UNIK per test function untuk menghindari cache
lru_cache embed_korpus() lintas-test saling mengotori."""

from src.layers.retriever.korpus_view import KORPUS_FUNGSI_VIEW
from src.layers.retriever.pencarian_embedding import cari_embedding
from src.schemas.domain_gate import Domain
from src.schemas.retriever import SumberPencarian

_VIEW_NAMES = list(KORPUS_FUNGSI_VIEW.keys())
_N = len(_VIEW_NAMES)


class _FakeEmbeddingItem:
    def __init__(self, index: int, embedding: list[float]):
        self.index = index
        self.embedding = embedding


class _FakeEmbeddingResponse:
    def __init__(self, data: list[_FakeEmbeddingItem]):
        self.data = data


def _one_hot(index: int, dim: int) -> list[float]:
    vektor = [0.0] * dim
    vektor[index] = 1.0
    return vektor


class _FakeEmbeddingsResource:
    """Mimic `client.embeddings` - korpus (67 teks) -> one-hot per posisi,
    query (1 teks) -> one-hot pada target_index (dikontrol per test)."""

    def __init__(self, target_index: int):
        self.target_index = target_index
        self.calls: list[dict] = []

    def create(self, model: str, input: list[str]):
        self.calls.append({"model": model, "input": input})
        if len(input) == 1:
            return _FakeEmbeddingResponse(
                [_FakeEmbeddingItem(0, _one_hot(self.target_index, _N))]
            )
        return _FakeEmbeddingResponse(
            [_FakeEmbeddingItem(i, _one_hot(i, _N)) for i in range(len(input))]
        )


class _FakeClient:
    def __init__(self, target_index: int):
        self.embeddings = _FakeEmbeddingsResource(target_index)


class _FakeClientGagal:
    def __init__(self):
        self.embeddings = self
        self._batch_done = False

    def create(self, model: str, input: list[str]):
        if len(input) > 1:
            self._batch_done = True
            return _FakeEmbeddingResponse(
                [_FakeEmbeddingItem(i, _one_hot(i, _N)) for i in range(len(input))]
            )
        raise RuntimeError("simulasi kegagalan API embedding query")


def test_ranking_cosine_similarity_benar(monkeypatch):
    target = "v_reservation_room_type_daily"
    target_index = _VIEW_NAMES.index(target)
    fake_client = _FakeClient(target_index)
    monkeypatch.setattr(
        "src.layers.retriever.pencarian_embedding.get_openrouter_client",
        lambda: fake_client,
    )

    kandidat, gagal = cari_embedding(
        "okupansi Bali bulan ini", [Domain.RESERVATION], "test-model-ranking"
    )

    assert gagal is False
    assert kandidat[0].view_name == target
    assert kandidat[0].skor == 1.0
    skor_list = [k.skor for k in kandidat]
    assert skor_list == sorted(skor_list, reverse=True)


def test_domain_filtering_identik_pola_bm25(monkeypatch):
    target = "v_reservation_room_type_daily"
    target_index = _VIEW_NAMES.index(target)
    fake_client = _FakeClient(target_index)
    monkeypatch.setattr(
        "src.layers.retriever.pencarian_embedding.get_openrouter_client",
        lambda: fake_client,
    )

    kandidat, gagal = cari_embedding(
        "okupansi Bali bulan ini", [Domain.FNB], "test-model-domain-filter"
    )

    assert gagal is False
    assert target not in [k.view_name for k in kandidat]
    for k in kandidat:
        assert k.domain == Domain.FNB


def test_parameter_model_diteruskan(monkeypatch):
    fake_client = _FakeClient(target_index=0)
    monkeypatch.setattr(
        "src.layers.retriever.pencarian_embedding.get_openrouter_client",
        lambda: fake_client,
    )

    model_dipakai = "test-model-parameter-check"
    cari_embedding("query apapun", [Domain.RESERVATION], model_dipakai)

    assert all(
        call["model"] == model_dipakai for call in fake_client.embeddings.calls
    )
    assert len(fake_client.embeddings.calls) == 2  # 1 batch korpus + 1 query


def test_sumber_selalu_embedding_fallback(monkeypatch):
    fake_client = _FakeClient(target_index=0)
    monkeypatch.setattr(
        "src.layers.retriever.pencarian_embedding.get_openrouter_client",
        lambda: fake_client,
    )

    kandidat, _ = cari_embedding(
        "query apapun", [Domain.RESERVATION], "test-model-sumber"
    )
    assert all(k.sumber == SumberPencarian.EMBEDDING_FALLBACK for k in kandidat)


def test_kegagalan_api_gagal_true_bukan_exception(monkeypatch):
    fake_client = _FakeClientGagal()
    monkeypatch.setattr(
        "src.layers.retriever.pencarian_embedding.get_openrouter_client",
        lambda: fake_client,
    )

    kandidat, gagal = cari_embedding(
        "query apapun", [Domain.RESERVATION], "test-model-gagal"
    )

    assert gagal is True
    assert kandidat == []
