_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    return _model


def generate_embedding(text: str) -> list[float]:
    if not text or not text.strip():
        return None
    model = get_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()
