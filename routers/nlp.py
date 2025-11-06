from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import torch
import re
from util.vector_search import retrieve_similar_medicines, suggest_cheapest_combination

router = APIRouter(prefix="/nlp", tags=["NLP"])

# Load public medical NER model from Hugging Face
model_name = "blaze999/Medical-NER"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)
ner_pipeline = pipeline(
    "ner",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple",
    device=0 if torch.cuda.is_available() else -1
)

class OCRInput(BaseModel):
    filename: str
    extracted_text: str

class PrescriptionText(BaseModel):
    text: str

def fallback_extract_drugs(text: str) -> List[str]:
    drug_pattern = r"\b([A-Z][a-zA-Z]{2,})\s*(?:\d+\s*(?:mg|g|mcg|ml))?"
    matches = re.findall(drug_pattern, text)
    return list(set(matches))

# ✅ Helper function for internal use (used by ocr.py)
def run_salt_extraction(filename: str, extracted_text: str) -> dict:
    entities = ner_pipeline(extracted_text)
    detected_entities = [{"word": ent["word"], "entity_group": ent["entity_group"]} for ent in entities]

    medicines: List[Dict] = []
    salts: List[str] = []
    current_med = {}

    for ent in entities:
        label = ent["entity_group"].upper()
        word = ent["word"]

        if label in ["DRUG", "MEDICINE", "CHEMICAL", "SUBSTANCE", "MEDICATION"]:
            if current_med:
                medicines.append(current_med)
                current_med = {}
            current_med["name"] = word
            salts.append(word)
        elif label in ["STRENGTH", "DOSAGE"]:
            current_med["dosage"] = word
        elif label == "FREQUENCY":
            current_med["frequency"] = word
        elif label == "DURATION":
            current_med["duration"] = word

    if current_med:
        medicines.append(current_med)

    if not salts:
        salts = fallback_extract_drugs(extracted_text)

    return {
        "msg": "✅ Medicines extracted using Blaze999 Medical-NER",
        "filename": filename,
        "medicines": medicines,
        "salts": list(set(salts)),
        "detected_entities": detected_entities
    }

# ✅ FastAPI route (unchanged)
@router.post("/extract_salts")
async def extract_salts(data: OCRInput):
    return run_salt_extraction(data.filename, data.extracted_text)

@router.post("/extract_and_recommend")
async def extract_and_recommend(payload: PrescriptionText):
    text = payload.text
    entities = ner_pipeline(text)

    extracted_salts: List[Dict[str, str]] = []
    detected_entities = [{"word": ent["word"], "entity_group": ent["entity_group"]} for ent in entities]
    current_med = {}

    for ent in entities:
        label = ent["entity_group"].upper()
        word = ent["word"]

        if label in ["DRUG", "MEDICINE", "CHEMICAL", "SUBSTANCE", "MEDICATION"]:
            if current_med:
                extracted_salts.append(current_med)
                current_med = {}
            current_med["name"] = word
        elif label in ["STRENGTH", "DOSAGE"]:
            current_med["dosage"] = word

    if current_med:
        extracted_salts.append(current_med)

    if not extracted_salts:
        pattern = r"\d+\.\s*([A-Za-z\s]+)\s+(\d+\s*mg)"
        matches = re.findall(pattern, text)
        extracted_salts = [{"name": name.strip(), "dosage": dosage.strip()} for name, dosage in matches]

    prices: Dict[str, List[Dict[str, Any]]] = {}
    for salt in extracted_salts:
        prices[salt["name"]] = retrieve_similar_medicines(salt["name"])

    salt_names = [s["name"] for s in extracted_salts]
    cheapest_combo = suggest_cheapest_combination(salt_names)

    return {
        "msg": "✅ Salts extracted, prices ranked, and cheapest combination suggested",
        "salts": extracted_salts,
        "prices": prices,
        "cheapest_combination": cheapest_combo,
        "detected_entities": detected_entities
    }

# ✅ Internal helper for ocr.py to call extract_salts correctly
async def extract_salts_internal(filename: str, extracted_text: str):
    return await extract_salts(OCRInput(filename=filename, extracted_text=extracted_text))