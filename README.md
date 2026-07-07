# Continuity or Rupture?

A text-as-data analysis of whether Vatican II produced a doctrinal rupture
in Catholic teaching, tested against a comparative corpus of ~1,900
documents across five Christian traditions (Catholic, LDS, Southern
Baptist, Anglican, Orthodox) spanning 1845–2026.

- **Paper:** [index.qmd](index.qmd) (rendered site: `docs/index.html`)
- **Chat with the corpus:** [rag/](rag/) — a retrieval-augmented chat
  interface over the same primary sources, so you can query the documents
  directly instead of only reading the paper's aggregate findings

## Repo layout

| Path | Contents |
|---|---|
| `scripts/` | Scrapers, feature extraction, ITS/DiD models, topic modeling |
| `data/corpus/` | Document manifests and extracted features (committed) |
| `data/raw/` | Raw scraped text (gitignored — regenerate via `scripts/scrape_*.py`) |
| `data/rag_index/` | Precomputed embeddings for the RAG chat demo (committed) |
| `analysis/` | Model outputs and figures |
| `rag/` | FastAPI + local-embedding RAG chat app |

## Setup

```bash
pip install -r requirements.txt
```

See [rag/README.md](rag/README.md) for the chat demo specifically.
