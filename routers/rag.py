# routers/rag.py

from fastapi import APIRouter
from typing import List
from util.vector_search import retrieve_similar_medicines

router = APIRouter(prefix="/rag", tags=["RAG"])

@router.post("/get_prices")
async def get_prices(salts: List[str]):
    results = {}
    for salt in salts:
        matches = retrieve_similar_medicines(salt)
        results[salt] = matches
    return {"msg": "✅ Prices retrieved successfully", "prices": results}