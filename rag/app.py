from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rag.retrieval import RetrievalIndex

MODEL = "claude-sonnet-5"
STATIC_DIR = Path(__file__).resolve().parent / "static"

SYSTEM_PROMPT = """You are a research assistant answering questions about continuity and \
divergence across Christian traditions (Catholic, Anglican, Orthodox, Southern Baptist, \
and USCCB statements), based on a corpus of denominational encyclicals, resolutions, and \
conference statements spanning the 19th-21st centuries.

Answer ONLY using the excerpts provided in <context>. Each excerpt is tagged with its \
tradition and year. When you make a claim, cite it inline like (Catholic, 1965) using the \
tags from the excerpts you drew on. If the excerpts don't contain enough information to \
answer, say so explicitly rather than filling in from general knowledge — this corpus is \
a historical-document sample, not a complete record of any tradition's teaching."""

app = FastAPI(title="Papal Continuity RAG Chat")

_index: RetrievalIndex | None = None
_client: anthropic.Anthropic | None = None


def get_index() -> RetrievalIndex:
    global _index
    if _index is None:
        _index = RetrievalIndex()
    return _index


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


class ChatRequest(BaseModel):
    question: str
    tradition: str | None = None
    top_k: int = 6


class Source(BaseModel):
    tradition: str
    year: int | None
    title: str
    url: str | None
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


def _format_context(chunks: list[dict]) -> str:
    blocks = []
    for c in chunks:
        tag = f"{c['tradition']}, {c['year']}" if c.get("year") else c["tradition"]
        blocks.append(f'<excerpt tradition="{c["tradition"]}" year="{c.get("year")}" title="{c["title"]}">\n{c["text"]}\n</excerpt>')
    return "\n\n".join(blocks)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if not req.question.strip():
        raise HTTPException(400, "question must not be empty")

    chunks = get_index().search(req.question, top_k=req.top_k, tradition=req.tradition)
    if not chunks:
        raise HTTPException(404, f"No indexed passages for tradition='{req.tradition}'")

    context = _format_context(chunks)
    try:
        response = get_client().messages.create(
            model=MODEL,
            max_tokens=1500,
            thinking={"type": "disabled"},
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"<context>\n{context}\n</context>\n\nQuestion: {req.question}",
                }
            ],
        )
    except Exception as e:
        raise HTTPException(502, f"Claude API request failed: {e}")

    answer = "".join(b.text for b in response.content if b.type == "text")
    sources = [
        Source(
            tradition=c["tradition"],
            year=c.get("year"),
            title=c["title"],
            url=c.get("url"),
            snippet=c["text"][:280],
        )
        for c in chunks
    ]
    return ChatResponse(answer=answer, sources=sources)
