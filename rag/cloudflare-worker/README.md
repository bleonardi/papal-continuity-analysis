# Cloudflare Worker proxy

Holds `ANTHROPIC_API_KEY` server-side so the static chat page
(`rag-chat.qmd`, published to `bleonardi.github.io/papal-continuity-analysis/rag-chat.html`)
can call Claude without exposing the key in browser JS. Retrieval already
happens client-side (MiniSearch over `rag/web/corpus.json`) — this worker's
only job is the completion call.

## Deploy

```bash
npm install -g wrangler
cd rag/cloudflare-worker
wrangler login                                    # one-time, opens a browser
wrangler secret put ANTHROPIC_API_KEY              # paste your key when prompted
wrangler deploy
```

`wrangler deploy` prints the Worker's URL, e.g.
`https://papal-rag-proxy.<your-subdomain>.workers.dev`. Copy it into
`WORKER_URL` near the top of the `<script>` block in `../../rag-chat.qmd`,
then re-render the site (`quarto render`) and push `docs/`.

## Cost control

- `worker.js` caps `max_tokens` at 1024 and disables extended thinking, so
  each request is cheap and bounded regardless of who calls it.
- The worker only accepts requests from `Access-Control-Allow-Origin:
  https://bleonardi.github.io` — update `ALLOWED_ORIGIN` in `worker.js` if
  the site moves.
- CORS is a browser-enforced check, not a server-side one — it stops normal
  browser traffic from other origins but doesn't stop a scripted request
  that omits the `Origin` header. For real abuse protection, add a rate
  limiting rule in the Cloudflare dashboard (Workers & Pages → your worker →
  Settings → Rate limiting rules — free tier covers a handful of rules) and
  set a monthly spend cap on the Anthropic API key in the Anthropic Console.

## Local testing

```bash
wrangler dev
# then in another terminal:
curl -X POST http://localhost:8787/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "test", "context": "<excerpt tradition=\"catholic\" year=\"1965\">test excerpt</excerpt>"}'
```
