# Fix reranker test mock report

## Root cause

The API test autouse fixture mocked `SentenceTransformer` only. FastAPI startup now invokes `warm_reranker_model()`, which imports and constructs `sentence_transformers.CrossEncoder`. That unmocked constructor attempted to download the reranker model from Hugging Face during `TestClient` startup.

## TDD evidence

- RED: `tests/api/test_health.py::test_client_startup_completes_with_mocked_models` failed during `TestClient` startup. The traceback reached `warm_reranker_model()` and the real `CrossEncoder`, then attempted a HEAD request to `hf-mirror.com`.
- GREEN: Added a `CrossEncoder` patch to the API autouse fixture. Its fake model exposes `predict`, matching the reranker's runtime contract.

## Verification

- Focused test: passed (1 passed).
- API suite: passed (16 passed).
- Ruff on touched files: passed.
- Repository-wide Ruff: blocked by a pre-existing unrelated I001 import-order failure in `app/ui/streamlit_app.py`.

The production warmup behavior was not changed.
