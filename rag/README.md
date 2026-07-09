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

# Get a Gemini key at aistudio.google.com/apikey, then make it available
# locally however you like (Sys.setenv, .Renviron, keyring, ...):
Sys.setenv(GOOGLE_API_KEY = "AIza...")

# From the repo root:
```
```sh
Rscript rag/deploy.R
```

`rag/deploy.R` exists because every more-obvious approach fails a
different way — worth knowing if you're debugging a future deploy:

- **Plain `rsconnect::deployDoc("rag-chat.qmd", ...)`** — for a Shiny
  document it always passes `appFiles = NULL` internally
  (`rsconnect:::standardizeSingleDocDeployment` — `isShinyRmd()`
  short-circuits to `NULL`, and it can't be overridden without an argument
  collision), which falls back to bundling *every file under the directory
  containing the doc*. Since `rag-chat.qmd` lives at the repo root, that's
  the whole repo — `data/raw/`'s ~5,500 scraped text files included.
- **`deployApp(appFiles = c("rag-chat.qmd", "rag/corpus.json", "assets/custom.scss"))`**
  fixes the bundle size but silently disables rsconnect's automatic R
  dependency scan — the server ends up with no packages installed at all
  and the app fails to start (`Error in enforcePackage(...): The shiny
  package was not found in the library`).
- Deploying just those 3 *source* files (even with correct dependencies)
  also fails: shinyapps.io does **not** pre-render Shiny Quarto content
  server-side (`Content pre-render disabled for Shiny Quarto content`) —
  it expects the already-rendered `rag-chat.html` + `rag-chat_files/` in
  the bundle, and errors with `Prerendered HTML file not found` without
  them.
- **`deployApp(envVars = "GOOGLE_API_KEY")`** — the documented way to sync
  a local env var to the server — errors immediately: *"shinyapps.io does
  not support setting envVars."* That parameter, and the dashboard "Vars"
  page some guides mention, are both Posit Connect–only; shinyapps.io has
  neither. The only thing that actually works is bundling a `.Renviron`
  file with the deploy — R reads it from the working directory at startup
  as a base-R feature, independent of platform support.

`rag/deploy.R` copies the 3 source files plus a generated `.Renviron`
(containing whatever `GOOGLE_API_KEY`/`GEMINI_API_KEY` is set in your local
session — never written into the git repo) into an isolated temp
directory, renders there (`quarto render`, producing `rag-chat.html` +
`rag-chat_files/`), then deploys *that* directory with no `appFiles`
restriction — since it only contains what's needed, the natural
(unrestricted) scan gets both the right file list and the right
dependencies for free.

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
