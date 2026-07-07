import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

INDEX_DIR = Path(__file__).resolve().parent.parent / "data" / "rag_index"


class RetrievalIndex:
    def __init__(self, index_dir: Path = INDEX_DIR):
        self.chunks: list[dict] = json.loads((index_dir / "chunks.json").read_text())
        self.embeddings: np.ndarray = np.load(index_dir / "embeddings.npy")
        model_name = (index_dir / "model.txt").read_text().strip()
        self.model = SentenceTransformer(model_name)

    def search(self, query: str, top_k: int = 6, tradition: str | None = None) -> list[dict]:
        query_vec = self.model.encode([query], normalize_embeddings=True)[0]
        scores = self.embeddings @ query_vec

        if tradition:
            mask = np.array([c["tradition"] == tradition for c in self.chunks])
            scores = np.where(mask, scores, -1.0)

        top_indices = np.argsort(-scores)[:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] <= -1.0:
                continue
            chunk = self.chunks[idx]
            results.append({**chunk, "score": float(scores[idx])})
        return results
