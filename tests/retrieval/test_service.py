import asyncio
from types import SimpleNamespace

import app.retrieval.service as service_module
from app.retrieval.service import RetrievalService, rank_by_token_overlap


class _FakeEncoding:
    def tolist(self) -> list[list[float]]:
        return [[0.0] * 1024]


class _FakeEmbeddingModel:
    def encode(self, _questions, normalize_embeddings=True) -> _FakeEncoding:
        assert normalize_embeddings is True
        return _FakeEncoding()


class _FakeQuery:
    def __init__(self, rows, vector_rows, *, is_vector=False, limits=None) -> None:
        self.rows = rows
        self.vector_rows = vector_rows
        self.is_vector = is_vector
        self.limits = limits if limits is not None else []
        self.requested_limit = None

    def filter(self, _condition):
        return self

    def order_by(self, _ordering):
        return _FakeQuery(
            self.rows,
            self.vector_rows,
            is_vector=True,
            limits=self.limits,
        )

    def options(self, *_options):
        return self

    def limit(self, value):
        self.requested_limit = value
        self.limits.append(value)
        return self

    def all(self):
        rows = self.vector_rows if self.is_vector else self.rows
        return rows[: self.requested_limit]


class _FakeSession:
    def __init__(self, rows, vector_rows) -> None:
        self.query_object = _FakeQuery(rows, vector_rows)

    def query(self, _model):
        return self.query_object

    def close(self) -> None:
        pass


def _row(identifier: str, content: str):
    return SimpleNamespace(
        id=identifier,
        content=content,
        title=identifier,
        section="",
        access_level="public",
        department="General",
        source_type="markdown",
        source_path="",
        page_number=None,
        content_type="text",
        table_name=None,
        table_json=None,
    )


def _pdf_row(identifier: str, content: str):
    return SimpleNamespace(
        id=identifier,
        content=content,
        title=identifier,
        section="第 3 页",
        access_level="public",
        department="General",
        source_type="pdf",
        source_path="data/documents/travel-policy.pdf",
        page_number=3,
        content_type="table",
        table_name="表格 1",
        table_json='[["职级", "上限"], ["P4", "800 元"]]',
    )


def _install_hybrid_dependencies(monkeypatch):
    rows = [
        _row("vpn", "Reset a VPN password through IT."),
        _row("expense", "Submit an expense claim within 30 days."),
        _row("travel", "Book business travel through the company portal."),
    ]
    session = _FakeSession(rows, rows[:2])
    monkeypatch.setattr(service_module.settings, "app_env", "development")
    monkeypatch.setattr(service_module, "_get_embedding_model", _FakeEmbeddingModel)
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: session)
    return session


def test_expense_question_ranks_expense_chunk_first() -> None:
    ranked = rank_by_token_overlap(
        "When should I submit a receipt?",
        [
            "Reset VPN password via IT.",
            "Submit receipts within 30 days.",
        ],
    )
    assert ranked[0] == "Submit receipts within 30 days."


def test_retrieval_exposes_three_stage_timings() -> None:
    assert set(RetrievalService().last_timings) == {
        "embedding_ms",
        "vector_search_ms",
        "bm25_ms",
        "fusion_ms",
        "rerank_ms",
        "total_ms",
    }


def test_hybrid_search_reranks_only_when_requested(monkeypatch) -> None:
    session = _install_hybrid_dependencies(monkeypatch)
    reranker_calls = []

    def reverse_candidates(question, candidates):
        reranker_calls.append((question, candidates))
        return list(reversed(candidates))

    monkeypatch.setattr(service_module, "rerank_candidates", reverse_candidates)

    RetrievalService().hybrid_search(
        "expense deadline", limit=2, rerank=False
    )
    with_rerank = RetrievalService().hybrid_search(
        "expense deadline", limit=2, rerank=True
    )

    assert len(reranker_calls) == 1
    assert reranker_calls[0][0] == "expense deadline"
    assert len(reranker_calls[0][1]) <= 8
    assert [chunk.id for chunk in with_rerank] == [
        chunk.id for chunk in reversed(reranker_calls[0][1])
    ][:2]
    assert 8 in session.query_object.limits


def test_hybrid_search_limits_bm25_candidates_to_twice_top_k(monkeypatch) -> None:
    session = _install_hybrid_dependencies(monkeypatch)
    session.query_object.rows = [
        _row(str(index), f"expense policy section {index}")
        for index in range(10)
    ]
    session.query_object.vector_rows = []
    seen = []

    monkeypatch.setattr(service_module, "bm25_rank", lambda *_args: list(range(10)))
    monkeypatch.setattr(
        service_module,
        "rerank_candidates",
        lambda _question, candidates: seen.extend(candidates) or candidates,
    )

    RetrievalService().hybrid_search("expense", limit=2, rerank=True)

    assert len(seen) == 4


def test_hybrid_search_falls_back_to_rrf_when_reranker_is_unavailable(
    monkeypatch,
) -> None:
    _install_hybrid_dependencies(monkeypatch)

    baseline = RetrievalService().hybrid_search(
        "expense deadline", limit=2, rerank=False
    )

    monkeypatch.setattr(
        service_module,
        "rerank_candidates",
        lambda question, candidates: (_ for _ in ()).throw(OSError("offline")),
    )
    degraded = RetrievalService().hybrid_search(
        "expense deadline", limit=2, rerank=True
    )

    assert [chunk.id for chunk in degraded] == [chunk.id for chunk in baseline]


def test_lifespan_skips_reranker_warmup_in_demo(monkeypatch) -> None:
    from app.api import main

    calls = []
    monkeypatch.setattr(main.settings, "app_env", "demo")
    monkeypatch.setattr(main, "validate_production_config", lambda: calls.append("validate"))
    monkeypatch.setattr(main, "warm_embedding_model", lambda: calls.append("embedding"))
    monkeypatch.setattr(main, "warm_reranker_model", lambda: calls.append("reranker"))

    async def run_lifespan() -> None:
        async with main.lifespan(main.app):
            pass

    asyncio.run(run_lifespan())

    assert calls == ["validate", "embedding"]


def test_hybrid_search_preserves_pdf_source_metadata(monkeypatch) -> None:
    session = _install_hybrid_dependencies(monkeypatch)
    pdf_row = _pdf_row("pdf-1", "| 职级 | 上限 |\n| --- | --- |\n| P4 | 800 元 |")
    session.query_object.rows = [_row("md-1", "markdown content"), pdf_row]
    session.query_object.vector_rows = [pdf_row]

    results = RetrievalService().hybrid_search("住宿上限", limit=3)

    pdf_result = next(c for c in results if c.id == "pdf-1")
    assert pdf_result.source_type == "pdf"
    assert pdf_result.source_path == "data/documents/travel-policy.pdf"
    assert pdf_result.page_number == 3
    assert pdf_result.content_type == "table"
    assert pdf_result.table_name == "表格 1"


def test_search_preserves_pdf_source_metadata(monkeypatch) -> None:
    session = _install_hybrid_dependencies(monkeypatch)
    pdf_row = _pdf_row("pdf-1", "P4 住宿上限为 800 元。")
    session.query_object.rows = [pdf_row]
    session.query_object.vector_rows = [pdf_row]

    results = RetrievalService().search("住宿上限", limit=3)

    assert results[0].page_number == 3
    assert results[0].table_name == "表格 1"
