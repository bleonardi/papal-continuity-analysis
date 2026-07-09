# Chat with the Corpus (RAG demo)

A retrieval-augmented chat interface over the same primary-source corpus used
in the [continuity/rupture analysis](../index.qmd) — Catholic, Anglican,
Orthodox, Southern Baptist, and USCCB statements from the 19th–21st
centuries. Ask a question, get an answer grounded in cited excerpts from the
actual documents, not the model's general knowledge.

This turns the existing text-as-data corpus into something you can query
directly, instead of only reading the paper's aggregate findings.

There are two versions of this demo:

- **Live Shiny doc** — [rag-chat.qmd](../rag-chat.qmd), built with
  [shinychat](https://posit-dev.github.io/shinychat/) and
  [ellmer](https://ellmer.tidyverse.org/), backed by Gemini
  (`ellmer::chat_google_gemini()`, model `gemini-2.5-flash`). Gemini
  retrieves for itself via a `search_corpus` tool call rather than the app
  pre-retrieving before every turn. This is a live R process — it can't be
  static HTML, so it's deployed separately from the rest of the site (see
  Deploy, below), not into `docs/`.
- **Local FastAPI app** (this directory) — Claude-backed, semantic
  (embedding-based) retrieval instead of lexical search, run locally or in
  Docker. Better retrieval quality, but needs a Python process running, and
  isn't wired into the Quarto site at all.

## Architecture (Shiny doc)

`rag-chat.qmd` is a single self-contained Quarto document:

- **`context: setup` chunk** — loads `rag/corpus.json` (1,474 documents, no
  embeddings) and defines `search_corpus(query, tradition)`, a plain
  keyword-frequency scorer with basic stopword filtering. No model download,
  no vector math.
- **UI chunk** — `shinychat::chat_ui()`.
- **`context: server` chunk** — an `ellmer::chat_google_gemini()` client
  with `search_corpus` registered as a tool, wired to the chat UI via
  `chat_append()` + `stream_async()`. Gemini decides when to call the tool;
  the system prompt requires it to before answering, and to cite every claim
  by tradition and year.

`rag/build_corpus.py` builds `rag/corpus.json` from the same manifests as
the FastAPI app's index (LDS excluded — see below).

## Deploy the Shiny doc

```r
install.packages(c("shiny", "bslib", "shinychat", "ellmer", "jsonlite", "rsconnect"))

# One-time: point rsconnect at your shinyapps.io account
# (Account → Tokens → Show, then paste the rsconnect::setAccountInfo(...) call it gives you)

rsconnect::deployApp(
  appDir = ".",
  appPrimaryDoc = "rag-chat.qmd",
  appFiles = c("rag-chat.qmd", "rag/corpus.json", "assets/custom.scss"),
  appName = "papal-rag-chat"
)
```

**Don't use plain `rsconnect::deployDoc("rag-chat.qmd", ...)`.** For a Shiny
document it always passes `appFiles = NULL` internally (see
`rsconnect:::standardizeSingleDocDeployment` — `isShinyRmd()` short-circuits
to `NULL`, and it can't be overridden without an argument collision), which
falls back to bundling *every file under the directory containing the
doc*. Since `rag-chat.qmd` lives at the repo root, that means the whole
repo — `data/raw/`'s ~5,500 scraped text files included. Calling
`deployApp()` directly with an explicit `appFiles` is the only way to
restrict the bundle to what the app actually reads: the qmd itself,
`rag/corpus.json`, and `assets/custom.scss` (its theme).

Get a Gemini key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
The deployed app needs `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) available in
its environment — set it as an environment variable on the shinyapps.io app
(dashboard → your app → Settings → Vars), not locally; neither `deployApp()`
nor `deployDoc()` uploads local environment variables, and shinyapps.io
(unlike Posit Connect) has no `envVars`/`updateAccountEnvVars()` API path
for this — the dashboard is the only way.

Live at: **https://benedictleonardi.shinyapps.io/papal-rag-chat/**. If you
redeploy under a different account/app name, update the navbar link in
[`_quarto.yml`](../_quarto.yml) and re-render the site.

## Run it locally

```r
quarto::quarto_serve("rag-chat.qmd")
```

## Local FastAPI app (alternate version)

```bash
pip install -r ../requirements.txt

# Only needed once, or after data/raw changes — requires data/raw/ to be
# populated (run the scripts/scrape_*.py scripts first if it isn't).
python build_index.py

export ANTHROPIC_API_KEY=sk-ant-...
uvicorn rag.app:app --reload --app-dir ..
```

Then open http://localhost:8000.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How did Catholic and Anglican statements on religious liberty diverge after 1960?"}'
```

Optional `"tradition"` field restricts retrieval to one of `catholic`,
`anglican`, `orthodox`, `sbc`, `usccb`.

---

LDS conference reports and their aggregated variant are excluded from both
corpora (they dwarf the other five traditions combined in raw volume) so
each stays small enough to commit to git.
