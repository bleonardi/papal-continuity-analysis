"""Build a retrieval index over the papal-continuity corpus.

Chunks the raw denominational-statement texts, embeds each chunk with a
local sentence-transformers model, and writes the result to data/rag_index/
so the chat app (rag/app.py) can do similarity search without re-embedding
on every request.

Traditions with very large raw corpora relative to their analytical role in
this project (LDS conference reports and their aggregated variant) are
excluded to keep the index small enough to commit to git; the five
manifests below already cover the traditions the qualitative analysis in
this repo actually compares.
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INDEX_DIR = DATA_DIR / "rag_index"

MANIFESTS = [
    "catholic_manifest.json",
    "anglican_manifest.json",
    "orthodox_manifest.json",
    "sbc_manifest.json",
    "usccb_manifest.json",
]

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_CHARS = 1000
CHUNK_OVERLAP = 150


def chunk_text(text: str, chunk_chars: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = " ".join(text.split())
    if len(text) <= chunk_chars:
        return [text] if text else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_chars
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def load_chunks() -> list[dict]:
    records = []
    for manifest_name in MANIFESTS:
        manifest_path = DATA_DIR / "corpus" / manifest_name
        if not manifest_path.exists():
            print(f"skip (missing manifest): {manifest_name}")
            continue
        entries = json.loads(manifest_path.read_text())
        tradition = manifest_name.replace("_manifest.json", "")
        raw_dir = DATA_DIR / "raw" / tradition

        for entry in entries:
            text_path = raw_dir / entry["file"]
            if not text_path.exists():
                continue
            raw_text = text_path.read_text(errors="ignore")
            for i, chunk in enumerate(chunk_text(raw_text)):
                if len(chunk) < 100:  # skip near-empty trailing chunks
                    continue
                records.append(
                    {
                        "text": chunk,
                        "tradition": entry.get("tradition", tradition),
                        "year": entry.get("year"),
                        "title": entry.get("title", entry["file"]),
                        "url": entry.get("url"),
                        "chunk_index": i,
                    }
                )
        print(f"{manifest_name}: {len(entries)} documents")
    return records


def main() -> None:
    print("Loading and chunking corpus...")
    chunks = load_chunks()
    print(f"Total chunks: {len(chunks)}")

    print(f"Embedding with {EMBEDDING_MODEL}...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64, normalize_embeddings=True)

    INDEX_DIR.mkdir(exist_ok=True)
    np.save(INDEX_DIR / "embeddings.npy", embeddings.astype("float32"))
    (INDEX_DIR / "chunks.json").write_text(json.dumps(chunks))
    (INDEX_DIR / "model.txt").write_text(EMBEDDING_MODEL)
    print(f"Wrote index to {INDEX_DIR} ({len(chunks)} chunks, {embeddings.shape[1]}-dim)")


if __name__ == "__main__":
    main()
