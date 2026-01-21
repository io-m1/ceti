import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import hashlib

# Persistent Chroma client (new API, no deprecated Settings)
client = chromadb.PersistentClient(path="./chroma_db")

# Use the same embedding model as before
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str) -> list:
    return embedding_model.encode(text).tolist()

# Get or create collection
collection = client.get_or_create_collection(
    name="ceti_decisions",
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
)

def ledger_check(query: str, risk_tier: str) -> dict | None:
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=1,
        where={"risk_tier": risk_tier},
        include=["metadatas", "distances"]
    )
    if results['distances'][0] and results['distances'][0][0] < 0.15:  # similarity threshold
        return results['metadatas'][0][0]
    return None

def ledger_write(response: dict, query: str, embedding: list):
    doc_id = hashlib.sha256(query.encode()).hexdigest()
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        metadatas=[response],
        documents=[response.get("response_content", "")]
    )
