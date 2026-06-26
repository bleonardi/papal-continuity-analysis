"""
BERTopic topic modeling across the full corpus.
Produces per-document topic proportions added to features.csv.
Also runs LDA as a fallback / comparison.

Outputs:
  corpus/topic_model/        — saved BERTopic model
  corpus/topic_proportions.csv  — document x topic matrix
  corpus/topics_summary.csv  — top words per topic
"""

import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")

CORPUS_DIR = Path(__file__).parent.parent / "corpus"
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_DIR = CORPUS_DIR / "topic_model"
OUT_DIR.mkdir(exist_ok=True)

FEATURES_CSV = CORPUS_DIR / "features.csv"


def load_corpus() -> tuple[list[str], list[dict]]:
    manifests = list(CORPUS_DIR.glob("*_manifest.json"))
    texts, meta = [], []
    for mpath in manifests:
        docs = json.loads(mpath.read_text())
        for doc in docs:
            tradition = doc.get("tradition", "unknown")
            fpath = DATA_DIR / tradition / doc["file"]
            if not fpath.exists():
                continue
            text = fpath.read_text(encoding="utf-8", errors="replace")
            if len(text.split()) < 100:
                continue
            texts.append(text)
            meta.append({
                "tradition": tradition,
                "year": doc.get("year"),
                "title": doc.get("title", ""),
                "file": doc["file"],
            })
    return texts, meta


def run_bertopic(texts: list[str], meta: list[dict]):
    try:
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("BERTopic not installed. Run: pip install bertopic sentence-transformers")
        return

    print(f"Running BERTopic on {len(texts)} documents...")
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    # Truncate texts to 512 tokens for embedding efficiency
    truncated = [" ".join(t.split()[:512]) for t in texts]

    topic_model = BERTopic(
        embedding_model=embedding_model,
        nr_topics=30,
        min_topic_size=3,
        verbose=True,
    )
    topics, probs = topic_model.fit_transform(truncated)

    # Save model
    topic_model.save(str(OUT_DIR / "bertopic_model"))

    # Topic summary
    topic_info = topic_model.get_topic_info()
    topic_info.to_csv(CORPUS_DIR / "topics_summary.csv", index=False)
    print(f"Topics: {CORPUS_DIR / 'topics_summary.csv'}")

    # Per-document topic assignments
    df_meta = pd.DataFrame(meta)
    df_meta["topic_id"] = topics
    df_meta["topic_prob"] = [p.max() if hasattr(p, "max") else p for p in probs]

    # Approximate topic proportions via probability array
    if hasattr(probs, "shape") and len(probs.shape) == 2:
        for i in range(probs.shape[1]):
            df_meta[f"topic_{i}_prob"] = probs[:, i]

    df_meta.to_csv(CORPUS_DIR / "topic_proportions.csv", index=False)
    print(f"Proportions: {CORPUS_DIR / 'topic_proportions.csv'}")
    return df_meta


def run_lda(texts: list[str], meta: list[dict], n_topics: int = 20):
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation

    print(f"\nRunning LDA ({n_topics} topics) on {len(texts)} documents...")
    vec = CountVectorizer(max_features=3000, stop_words="english", min_df=2)
    dtm = vec.fit_transform(texts)

    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=42,
        max_iter=50,
        learning_method="online",
    )
    doc_topics = lda.fit_transform(dtm)

    # Top words per topic
    vocab = vec.get_feature_names_out()
    rows = []
    for i, comp in enumerate(lda.components_):
        top_words = [vocab[j] for j in comp.argsort()[-15:][::-1]]
        rows.append({"topic": i, "top_words": ", ".join(top_words)})
    pd.DataFrame(rows).to_csv(CORPUS_DIR / "lda_topics_summary.csv", index=False)

    # Per-document proportions
    df_meta = pd.DataFrame(meta)
    for i in range(n_topics):
        df_meta[f"lda_topic_{i}"] = doc_topics[:, i].round(4)
    df_meta["lda_dominant_topic"] = doc_topics.argmax(axis=1)

    df_meta.to_csv(CORPUS_DIR / "lda_proportions.csv", index=False)
    print(f"LDA results saved to {CORPUS_DIR}")
    return df_meta


if __name__ == "__main__":
    texts, meta = load_corpus()
    print(f"Loaded {len(texts)} documents")

    # LDA runs without GPU — always try first
    lda_df = run_lda(texts, meta)

    # BERTopic — requires sentence-transformers; best run with GPU
    try:
        bertopic_df = run_bertopic(texts, meta)
    except Exception as e:
        print(f"BERTopic skipped: {e}")
