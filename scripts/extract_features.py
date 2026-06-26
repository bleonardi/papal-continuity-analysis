"""
Extract textual features from all corpus documents.
Outputs: corpus/features.csv — one row per document.

Features:
  - Readability: Flesch-Kincaid grade, Flesch reading ease
  - Lexical: type-token ratio, avg sentence length, avg word length
  - Formality: hedging word rate, passive construction rate, first-person plural rate
  - Theological vocabulary: rates of key term clusters
  - Cosine similarity to predecessor document (within tradition)
"""

import re
import json
import math
import string
from pathlib import Path
from collections import Counter

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CORPUS_DIR = Path(__file__).parent.parent / "data" / "corpus"
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT = CORPUS_DIR / "features.csv"

# Word lists for categorical features
HEDGE_WORDS = {
    "perhaps", "possibly", "might", "may", "could", "seem", "appears",
    "suggests", "indicates", "arguably", "somewhat", "rather", "generally",
    "often", "sometimes", "usually", "certain extent", "in some ways",
}

FIRST_PERSON_PLURAL = {"we", "our", "us", "ourselves"}
FIRST_PERSON_SINGULAR = {"i", "my", "me", "myself"}

# Theological vocabulary clusters
THEOL_CLUSTERS = {
    "juridical": ["canon", "law", "decree", "anathema", "obedience", "authority",
                  "precept", "obligation", "penalty", "censure", "jurisdiction"],
    "pastoral": ["pastoral", "shepherd", "flock", "mercy", "compassion", "accompaniment",
                 "dialogue", "encounter", "journey", "pilgrim", "tenderness"],
    "ecumenical": ["ecumenical", "unity", "separated", "brethren", "dialogue",
                   "communion", "reconciliation", "common ground"],
    "modern_world": ["modern", "contemporary", "today", "present age", "world",
                     "society", "culture", "human dignity", "rights", "progress"],
    "scripture": ["scripture", "gospel", "word of god", "bible", "testament",
                  "apostle", "prophet", "revelation"],
    "tradition": ["tradition", "fathers", "magisterium", "deposit", "councils",
                  "pontiff", "successor", "apostolic"],
}


def word_tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z\s'-]", " ", text)
    return [w.strip("'-") for w in text.split() if w.strip("'-")]


def sent_tokenize(text: str) -> list[str]:
    sents = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sents if len(s.strip()) > 10]


def syllable_count(word: str) -> int:
    word = word.lower().strip(".,;:!?\"'")
    if not word:
        return 0
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def flesch_kincaid(text: str) -> dict:
    words = word_tokenize(text)
    sents = sent_tokenize(text)
    if not words or not sents:
        return {"fk_grade": None, "flesch_ease": None}
    total_syllables = sum(syllable_count(w) for w in words)
    asl = len(words) / len(sents)   # avg sentence length
    asw = total_syllables / len(words)  # avg syllables per word
    ease = 206.835 - 1.015 * asl - 84.6 * asw
    grade = 0.39 * asl + 11.8 * asw - 15.59
    return {"fk_grade": round(grade, 2), "flesch_ease": round(ease, 2)}


def lexical_features(text: str) -> dict:
    words = word_tokenize(text)
    sents = sent_tokenize(text)
    if not words:
        return {}
    types = set(words)
    ttr = len(types) / len(words)
    avg_word_len = sum(len(w) for w in words) / len(words)
    avg_sent_len = len(words) / max(len(sents), 1)
    hedge_rate = sum(1 for w in words if w in HEDGE_WORDS) / len(words)
    fp_plural_rate = sum(1 for w in words if w in FIRST_PERSON_PLURAL) / len(words)
    fp_singular_rate = sum(1 for w in words if w in FIRST_PERSON_SINGULAR) / len(words)
    return {
        "word_count": len(words),
        "type_token_ratio": round(ttr, 4),
        "avg_word_length": round(avg_word_len, 3),
        "avg_sentence_length": round(avg_sent_len, 2),
        "hedge_rate": round(hedge_rate, 5),
        "fp_plural_rate": round(fp_plural_rate, 5),
        "fp_singular_rate": round(fp_singular_rate, 5),
    }


def theological_features(text: str) -> dict:
    text_lower = text.lower()
    words = word_tokenize(text)
    n = max(len(words), 1)
    out = {}
    for cluster, terms in THEOL_CLUSTERS.items():
        count = sum(text_lower.count(t) for t in terms)
        out[f"theol_{cluster}_rate"] = round(count / n, 5)
    return out


def extract_all_features() -> pd.DataFrame:
    manifests = list(CORPUS_DIR.glob("*_manifest.json"))
    if not manifests:
        print("No manifests found. Run scrapers first.")
        return pd.DataFrame()

    all_docs = []
    for mpath in manifests:
        docs = json.loads(mpath.read_text())
        all_docs.extend(docs)

    records = []
    texts_by_tradition: dict[str, list[tuple]] = {}  # tradition -> [(year, text)]

    for doc in all_docs:
        tradition = doc.get("tradition", "unknown")
        raw_dir = DATA_DIR / tradition
        fpath = raw_dir / doc["file"]

        if not fpath.exists():
            print(f"  Missing: {fpath}")
            continue

        text = fpath.read_text(encoding="utf-8", errors="replace")
        if len(text.split()) < 50:
            continue

        row = {
            "tradition": tradition,
            "year": doc.get("year"),
            "title": doc.get("title", ""),
            "file": doc["file"],
        }
        # Add tradition-specific metadata
        for k in ["pope", "speaker", "document_type", "pre_vii", "council_period",
                  "conservative_resurgence"]:
            if k in doc:
                row[k] = doc[k]

        row.update(flesch_kincaid(text))
        row.update(lexical_features(text))
        row.update(theological_features(text))
        row["paraphrased"] = doc.get("paraphrased", False)
        row["_text"] = text  # keep temporarily for cosine similarity

        records.append(row)
        # Exclude paraphrased reconstructions from cosine similarity chain
        if not doc.get("paraphrased", False):
            texts_by_tradition.setdefault(tradition, []).append((doc.get("year", 0), text, len(records) - 1))

    df = pd.DataFrame(records)

    # Compute cosine similarity to predecessor within each tradition
    df["cosine_sim_to_prev"] = np.nan
    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")

    for tradition, items in texts_by_tradition.items():
        items_sorted = sorted(items, key=lambda x: x[0])
        if len(items_sorted) < 2:
            continue
        texts = [t for _, t, _ in items_sorted]
        idxs = [i for _, _, i in items_sorted]
        try:
            tfidf = vectorizer.fit_transform(texts)
            for j in range(1, len(texts)):
                sim = cosine_similarity(tfidf[j - 1], tfidf[j])[0][0]
                df.at[idxs[j], "cosine_sim_to_prev"] = round(float(sim), 4)
        except Exception as e:
            print(f"  TF-IDF error for {tradition}: {e}")

    df = df.drop(columns=["_text"])
    df.to_csv(OUT, index=False)
    print(f"\nFeatures saved: {OUT} ({len(df)} documents)")
    return df


if __name__ == "__main__":
    df = extract_all_features()
    if df.empty:
        print("No documents processed — check manifests and raw data paths.")
    else:
        print(df.groupby("tradition")[["fk_grade", "type_token_ratio", "cosine_sim_to_prev"]].describe())
