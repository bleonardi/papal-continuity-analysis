# Continuity or Rupture?

A text-as-data analysis of whether Vatican II produced a doctrinal rupture
in Catholic teaching, tested against a comparative corpus of ~1,900
documents across five Christian traditions (Catholic, LDS, Southern
Baptist, Anglican, Orthodox) spanning 1845–2026.

- **Paper:** [index.qmd](index.qmd) — live at
  [bleonardi.github.io/papal-continuity-analysis](https://bleonardi.github.io/papal-continuity-analysis/)
- **Chat with the corpus:** [rag-chat.qmd](rag-chat.qmd) — a
  [shinychat](https://posit-dev.github.io/shinychat/)/[ellmer](https://ellmer.tidyverse.org/)
  app where Claude retrieves from the same primary sources itself via a tool
  call, instead of you only reading the paper's aggregate findings. Runs as
  a live R process, deployed separately from the static site — see
  [rag/README.md](rag/README.md) for the URL and deployment. `rag/` also
  has a Python/FastAPI version with semantic retrieval.

## Repo layout

| Path | Contents |
|---|---|
| `scripts/` | Scrapers, feature extraction, ITS/DiD models, topic modeling |
| `data/corpus/` | Document manifests and extracted features (committed) |
| `data/raw/` | Raw scraped text (gitignored — regenerate via `scripts/scrape_*.py`) |
| `data/rag_index/` | Precomputed embeddings for the local FastAPI RAG app (committed) |
| `analysis/` | Model outputs and figures |
| `rag/` | FastAPI + local-embedding RAG chat app, plus `corpus.json` behind the Shiny doc |
| `rag-chat.qmd` | The live shinychat/ellmer demo (deployed to shinyapps.io, not part of `docs/`) |

## Setup

```bash
pip install -r requirements.txt
```

See [rag/README.md](rag/README.md) for the chat demo specifically.
