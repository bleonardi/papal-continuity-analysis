"""Build a lean, document-level corpus JSON for the shinychat RAG demo.

Unlike build_index.py (which produces overlapping chunks + embeddings for
the local FastAPI app's semantic search), this ships one entry per source
document with no embeddings — the Shiny app's search_corpus tool does plain
keyword scoring over it in R, so there's no model to download and no vector
math to run.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_PATH = Path(__file__).resolve().parent / "corpus.json"

MANIFESTS = [
    "catholic_manifest.json",
    "anglican_manifest.json",
    "orthodox_manifest.json",
    "sbc_manifest.json",
    "usccb_manifest.json",
]


def main() -> None:
    docs = []
    for manifest_name in MANIFESTS:
        manifest_path = DATA_DIR / "corpus" / manifest_name
        if not manifest_path.exists():
            print(f"skip (missing manifest): {manifest_name}")
            continue
        entries = json.loads(manifest_path.read_text())
        tradition = manifest_name.replace("_manifest.json", "")
        raw_dir = DATA_DIR / "raw" / tradition

        kept = 0
        for entry in entries:
            text_path = raw_dir / entry["file"]
            if not text_path.exists():
                continue
            text = " ".join(text_path.read_text(errors="ignore").split())
            if len(text) < 100:
                continue
            docs.append(
                {
                    "id": len(docs),
                    "tradition": entry.get("tradition", tradition),
                    "year": entry.get("year"),
                    "title": entry.get("title", entry["file"]),
                    "url": entry.get("url"),
                    "text": text,
                }
            )
            kept += 1
        print(f"{manifest_name}: {kept}/{len(entries)} documents")

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(docs))
    total_kb = OUT_PATH.stat().st_size / 1024
    print(f"Wrote {len(docs)} documents to {OUT_PATH} ({total_kb:.0f} KB)")


if __name__ == "__main__":
    main()
