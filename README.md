# Enterprise Support Agent

A Python-based internal support agent for enterprise policy and IT questions. Answers only from authorized knowledge-base evidence, cites sources, and routes risky/unsupported questions to simulated tickets.

## Quick Start

```bash
docker compose up
```

Open http://localhost:8501 for the demo UI, or http://localhost:8000/docs for the API docs.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | DeepSeek API key |
| `LLM_BASE_URL` | `https://api.deepseek.com` | LLM provider endpoint |
| `LLM_MODEL` | `deepseek-chat` | Model name |
| `DATABASE_URL` | `postgresql+psycopg://app:app@localhost:5432/support_agent` | PostgreSQL connection |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | Embedding model name |
| `ADMIN_TOKEN` | — | Token for `/traces` and `/tickets` admin endpoints |
| `USER_ID` | `demo` | Default user identity for access control |

## Local Setup (no Docker)

```bash
# Install dependencies
uv sync

# Start PostgreSQL with pgvector, then:
uv run alembic upgrade head
uv run python scripts/seed_demo.py
uv run uvicorn app.api.main:app --reload
```

## Demo Commands

```bash
# Supported question
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"question": "How do I submit a travel expense?"}'

# Sensitive request (routes to ticket)
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"question": "Please reset my VPN password"}'

# View trace (requires admin token)
curl http://localhost:8000/traces/{trace_id} -H "X-Admin-Token: $ADMIN_TOKEN"
```

## Tests

```bash
# Fast unit tests (no database / LLM needed)
pytest -m "not integration" -v

# Integration tests (requires PostgreSQL + pgvector)
pytest -m integration -v

# All tests
pytest -v
```

## Evaluation

```bash
# Run development evaluation
python scripts/run_evaluation.py --version v1 --split development

# Run holdout evaluation (final only)
python scripts/run_evaluation.py --version v3 --split holdout
```

Results are saved to `artifacts/<version>/<timestamp>/` with per-case and aggregate metrics.

## Architecture

```
Client → FastAPI → Support Agent → search_knowledge_base / create_ticket
                                       ↓
                              PostgreSQL + pgvector
```

## Quality Experiments

| Version | Retrieval | Grounding | Access Filter |
|---------|-----------|-----------|---------------|
| V1 | vector-only | off | off |
| V2 | BM25 + vector hybrid | off | off |
| V3 | hybrid | mandatory citations | on |
| production | hybrid | mandatory citations | on |

Run `python scripts/run_evaluation.py --version <version> --split development` to generate actual metrics.

## Limitations

- Tickets are stored in PostgreSQL (via ORM), with in-memory cache
- Access control uses simulated department-to-level mapping, no real SSO/OIDC
- No privileged actions (password resets, permission changes) — all such requests are routed to tickets
- Embedding model downloads on first run
- Admin endpoints (`/traces`, `/tickets`) are protected with a configurable shared token (`ADMIN_TOKEN`)
