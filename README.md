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

## Demo Commands

```bash
# Supported question
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"question": "How do I submit a travel expense?"}'

# Sensitive request (routes to ticket)
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"question": "Please reset my VPN password"}'
```

## Evaluation

```bash
# Run development evaluation
python scripts/run_evaluation.py --version v1 --split development

# Run holdout evaluation (final only)
python scripts/run_evaluation.py --version v4 --split holdout
```

Results are saved to `artifacts/<version>/<timestamp>/` with per-case and aggregate metrics.

## Architecture

```
Client → FastAPI → Support Agent → search_knowledge_base / create_ticket
                                       ↓
                              PostgreSQL + pgvector
```

## Quality Experiments

| Version | Change | Accuracy | Precision | Recall |
|---------|--------|----------|-----------|--------|
| V1 | Vector-only retrieval | _fill_ | _fill_ | _fill_ |
| V2 | BM25 + vector hybrid | _fill_ | _fill_ | _fill_ |
| V3 | Grounding guard | _fill_ | _fill_ | _fill_ |
| V4 | Final tuned | _fill_ | _fill_ | _fill_ |

> **Note:** Fill the metrics table by running evaluations locally. No metrics have been fabricated.

## Limitations

- Tickets are simulated (in-memory storage)
- No connection to real corporate identity or ticketing systems
- No privileged actions (password resets, permission changes)
- Embedding model downloads on first run
