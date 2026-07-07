# Chat with the Corpus (RAG demo)

A retrieval-augmented chat interface over the same primary-source corpus used
in the [continuity/rupture analysis](../index.qmd) — Catholic, Anglican,
Orthodox, Southern Baptist, and USCCB statements from the 19th–21st
centuries. Ask a question, get an answer grounded in cited excerpts from the
actual documents, not the model's general knowledge.

This turns the existing text-as-data corpus into something you can query
directly, instead of only reading the paper's aggregate findings.

There are two versions of this demo:

- **Live, on GitHub Pages** — [rag-chat.qmd](../rag-chat.qmd) (rendered to
  `bleonardi.github.io/papal-continuity-analysis/rag-chat.html`). Fully
  static: retrieval runs in the browser with MiniSearch, and the completion
  call goes through a small Cloudflare Worker
  ([cloudflare-worker/](cloudflare-worker/)) that holds the API key. No
  server to run, no setup for a visitor.
- **Local FastAPI app** (this directory) — semantic (embedding-based)
  retrieval instead of lexical search, run locally or in Docker. Better
  retrieval quality, but needs a Python process running.

## Architecture

1. **`build_index.py`** — chunks each document (~1000 chars, 150 overlap),
   embeds every chunk locally with `sentence-transformers`
   (`all-MiniLM-L6-v2`, no API calls), and writes a flat numpy index to
   `data/rag_index/`.
2. **`retrieval.py`** — loads that index and does cosine-similarity search
   at query time, optionally filtered to a single tradition.
3. **`app.py`** — a FastAPI app: embeds the question, retrieves the top-k
   chunks, sends them to Claude as `<excerpt>`-tagged context with a system
   prompt that requires citing every claim by tradition and year, and
   returns the answer plus the source excerpts.
4. **`static/index.html`** — a single-page chat UI for the local FastAPI app, no build step.
5. **`build_web_corpus.py`** — builds the leaner, unchunked, no-embeddings
   corpus (`rag/web/corpus.json`) that the GitHub Pages version indexes
   client-side.

LDS conference reports and their aggregated variant are excluded from the
index (they dwarf the other five traditions combined in raw volume) so the
index stays small enough to commit to git and load in the container
`pdf-ocr-api`-style, with no separate data-download step.

## Run it

```bash
pip install -r ../requirements.txt

# Only needed once, or after data/raw changes — requires data/raw/ to be
# populated (run the scripts/scrape_*.py scripts first if it isn't).
python build_index.py

export ANTHROPIC_API_KEY=sk-ant-...
uvicorn rag.app:app --reload --app-dir ..
```

Then open http://localhost:8000.

## API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How did Catholic and Anglican statements on religious liberty diverge after 1960?"}'
```

Optional `"tradition"` field restricts retrieval to one of `catholic`,
`anglican`, `orthodox`, `sbc`, `usccb`.
