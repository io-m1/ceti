"""Embedding helpers — for ledger semantic search (Invariant 6 mechanical seed)."""

from sentence_transformers import SentenceTransformer

# Singleton embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str) -> List[float]:
    """Get embedding for text."""
    return embedding_model.encode([text]).tolist()[0]
