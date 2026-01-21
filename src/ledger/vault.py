from typing import Optional

import time
import chromadb
from sentence_transformers import SentenceTransformer

from src.config.settings import CHROMA_PATH, SIMILARITY_THRESHOLD
from src.api.schemas import CETIResponse, AuthorizationScope
from src.utils.embeddings import get_embedding


embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(
    name="ceti_ledger",
    embedding_function=lambda texts: embedding_model.encode(texts).tolist()
)

def ledger_check(query: str, risk_tier: str = "MEDIUM") -> Optional[CETIResponse]:
    query_embedding = embedding_model.encode([query]).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=1,
        include=["metadatas", "documents", "distances"]
    )

    if results['distances'][0] and results['distances'][0][0] < (1 - SIMILARITY_THRESHOLD):
        cached_document = results['documents'][0][0]
        cached_meta = results['metadatas'][0][0]

        ttl = cached_meta.get("ttl", 2592000)
        if time.time() - cached_meta["timestamp"] > ttl:
            return None

        cached_risk = cached_meta["risk_tier"]
        if ALLOWED_RISK_TIERS.index(risk_tier) > ALLOWED_RISK_TIERS.index(cached_risk):
            return None

        return CETIResponse(
            authorization="GRANTED",
            response_content=cached_document,
            scope=AuthorizationScope(**cached_meta["scope"]),
            refusal_diagnostics=None,
            certification_id=cached_meta["certification_id"],
            meta={
                "cached": True,
                "source": "ledger_hit",
                "timestamp": cached_meta["timestamp"],
            },
        )

    return None

def ledger_write(response: CETIResponse, query: str, query_embedding: List[float]) -> None:
    if response.authorization != "GRANTED":
        return

    # Conflict check: reject write if similar entry with conflicting content
    existing = ledger_check(query)
    if existing and existing.response_content != response.response_content:
        return  # Conflict — do not overwrite

    meta = {
        "timestamp": time.time(),
        "ttl": 2592000,
        "risk_tier": response.scope.risk_tier_applied,
        "scope": response.scope.dict(),
        "certification_id": response.certification_id,
    }

    collection.add(
        documents=[response.response_content],
        embeddings=[query_embedding],
        metadatas=[meta],
        ids=[response.certification_id],
    )
