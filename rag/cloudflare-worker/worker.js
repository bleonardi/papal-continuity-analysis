// Cloudflare Worker: proxies chat requests from the static rag-chat.qmd page
// to Claude, keeping ANTHROPIC_API_KEY server-side. The browser sends
// pre-retrieved context (search runs client-side via MiniSearch); this
// worker only makes the completion call.
//
// Deploy: see README.md in this directory.

const ALLOWED_ORIGIN = "https://bleonardi.github.io";
const MODEL = "claude-sonnet-5";
const MAX_TOKENS = 1024;

const SYSTEM_PROMPT = `You are a research assistant answering questions about continuity and \
divergence across Christian traditions (Catholic, Anglican, Orthodox, Southern Baptist, \
and USCCB statements), based on a corpus of denominational encyclicals, resolutions, and \
conference statements spanning the 19th-21st centuries.

Answer ONLY using the excerpts provided in <context>. Each excerpt is tagged with its \
tradition and year. When you make a claim, cite it inline like (Catholic, 1965) using the \
tags from the excerpts you drew on. If the excerpts don't contain enough information to \
answer, say so explicitly rather than filling in from general knowledge — this corpus is \
a historical-document sample, not a complete record of any tradition's teaching.`;

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405, headers: corsHeaders() });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return jsonError("invalid JSON body", 400);
    }

    const { question, context } = body;
    if (!question || !context) {
      return jsonError("question and context are required", 400);
    }

    const anthropicResponse = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: MAX_TOKENS,
        thinking: { type: "disabled" },
        system: SYSTEM_PROMPT,
        messages: [
          { role: "user", content: `<context>\n${context}\n</context>\n\nQuestion: ${question}` },
        ],
      }),
    });

    if (!anthropicResponse.ok) {
      const errText = await anthropicResponse.text();
      return jsonError(`Claude API error: ${errText}`, 502);
    }

    const data = await anthropicResponse.json();
    const answer = (data.content || [])
      .filter((b) => b.type === "text")
      .map((b) => b.text)
      .join("");

    return new Response(JSON.stringify({ answer }), {
      headers: { "Content-Type": "application/json", ...corsHeaders() },
    });
  },
};

function jsonError(message, status) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders() },
  });
}
