import re
import numpy as np
from app.utils.embeddings import get_model

MAX_CHUNK = 250  # sentences per chunk


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


def summarize(text: str, max_sentences: int = 5) -> str:
    if not text or not text.strip():
        return ""
    sentences = split_sentences(text)
    if not sentences:
        return ""
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    # For large docs, do chunked summarization then combine
    if len(sentences) > MAX_CHUNK:
        chunks = [sentences[i:i + MAX_CHUNK] for i in range(0, len(sentences), MAX_CHUNK)]
        chunk_summaries = []
        for chunk in chunks:
            summary = _rank_sentences(chunk, max(2, max_sentences))
            chunk_summaries.extend(summary)
        return " ".join(_rank_sentences(chunk_summaries, max_sentences))

    return " ".join(_rank_sentences(sentences, max_sentences))


def _rank_sentences(sentences: list[str], top_k: int) -> list[str]:
    model = get_model()
    vecs = model.encode(sentences, normalize_embeddings=True)
    sim = vecs @ vecs.T
    np.fill_diagonal(sim, 0)

    scores = _pagerank(sim, 0.85, 100)
    ranked = sorted(range(len(sentences)), key=lambda i: scores[i], reverse=True)

    selected = set()
    result = []
    for idx in ranked:
        if idx not in selected:
            selected.add(idx)
            result.append(sentences[idx])
        if len(result) >= top_k:
            break
    return result


def _pagerank(M: np.ndarray, damp: float = 0.85, max_iter: int = 100) -> np.ndarray:
    n = M.shape[0]
    if n == 0:
        return np.array([])
    row_sums = M.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    M_norm = M / row_sums
    scores = np.ones(n) / n
    for _ in range(max_iter):
        prev = scores.copy()
        scores = (1 - damp) / n + damp * (M_norm.T @ scores)
        if np.linalg.norm(scores - prev, 1) < 1e-6:
            break
    return scores
