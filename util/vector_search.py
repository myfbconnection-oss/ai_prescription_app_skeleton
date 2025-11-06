from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load the Hugging Face model
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Sample in-memory medicine database with MRP
medicine_db = [
    {"salt": "Paracetamol", "brand": "Calpol", "dosage": "500mg", "price": 12.5, "mrp": 20.0, "pharmacy": "Jan Aushadhi"},
    {"salt": "Amoxicillin", "brand": "Mox", "dosage": "250mg", "price": 18.0, "mrp": 25.0, "pharmacy": "DavaIndia"},
    {"salt": "Cetirizine", "brand": "Zyrtec", "dosage": "10mg", "price": 9.0, "mrp": 15.0, "pharmacy": "Zeelab"},
    {"salt": "Ibuprofen", "brand": "Brufen", "dosage": "400mg", "price": 15.0, "mrp": 22.0, "pharmacy": "Jan Aushadhi"},
    {"salt": "Azithromycin", "brand": "Azithral", "dosage": "500mg", "price": 22.0, "mrp": 30.0, "pharmacy": "DavaIndia"}
]

def embed_salt_names(salt_names):
    return model.encode(salt_names)

def retrieve_similar_medicines(query_salt: str, top_k: int = 3, threshold: float = 0.7):
    query_embedding = embed_salt_names([query_salt])
    db_salts = [entry["salt"] for entry in medicine_db]
    db_embeddings = embed_salt_names(db_salts)
    similarities = cosine_similarity(query_embedding, db_embeddings)[0]

    scored_entries = [(entry, score) for entry, score in zip(medicine_db, similarities)]
    scored_entries.sort(key=lambda x: x[1], reverse=True)
    filtered = [entry for entry, score in scored_entries if score >= threshold]

    exact_matches = [entry for entry in medicine_db if entry["salt"].lower() == query_salt.lower()]
    others = [entry for entry in filtered if entry not in exact_matches]

    top_results = (exact_matches + others)[:top_k]
    top_results.sort(key=lambda x: x["price"])

    for entry in top_results:
        entry["savings"] = round(entry["mrp"] - entry["price"], 2)
        entry["savings_percent"] = round((entry["savings"] / entry["mrp"]) * 100, 2)

    return top_results

def suggest_cheapest_combination(salt_list):
    combination = []
    total_cost = 0.0
    total_mrp = 0.0

    for salt in salt_list:
        options = retrieve_similar_medicines(salt, top_k=3)
        if options:
            cheapest = options[0]
            combination.append(cheapest)
            total_cost += cheapest["price"]
            total_mrp += cheapest["mrp"]

    total_savings = round(total_mrp - total_cost, 2)
    savings_percent = round((total_savings / total_mrp) * 100, 2) if total_mrp > 0 else 0.0

    return {
        "total_cost": round(total_cost, 2),
        "total_mrp": round(total_mrp, 2),
        "total_savings": total_savings,
        "savings_percent": savings_percent,
        "medicines": combination
    }