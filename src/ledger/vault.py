import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

chroma_client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_db"
))

collection = chroma_client.get_or_create_collection("ceti_decisions")

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str) -> list:
    return embedding_model.encode(text).tolist()

def ledger_check(query: str, risk_tier: str) -> dict | None:
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=1,
        where={"risk_tier": risk_tier}
    )
    if results['distances'][0][0] < 0.15:  # similarity threshold
        return results['metadatas'][0][0]
    return None

def ledger_write(response: dict, query: str, embedding: list):
    collection.add(
        embeddings=[embedding],
        metadatas=[response],
        ids=[hashlib.sha256(query.encode()).hexdigest()]
    )
