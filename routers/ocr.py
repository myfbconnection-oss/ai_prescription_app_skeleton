from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np
import cv2
from PIL import Image
import io
from paddleocr import PaddleOCR
from routers.pdf import extract_text_from_pdf
from routers.nlp import extract_salts_internal  # ✅ Use internal helper
from routers.rag import get_prices

router = APIRouter()

# ✅ Initialize OCR globally (avoid reloading on every request)
ocr = PaddleOCR(use_angle_cls=True, lang='en')

def should_run_ocr(filename: str) -> bool:
    """
    Check if OCR should run based on file extension.
    """
    return filename.lower().endswith((".jpg", ".jpeg", ".png"))

@router.post("/process_prescription")
async def process_prescription(file: UploadFile = File(...)):
    """
    Process prescription file (image or PDF):
    - Extract text using OCR or PDF parser
    - Run NLP to extract salts
    - Fetch prices using RAG
    """
    filename = file.filename.lower()
    content = await file.read()

    # ✅ Step 1: Extract text
    if should_run_ocr(filename):
        try:
            pil_image = Image.open(io.BytesIO(content)).convert("RGB")
        except Exception:
            raise HTTPException(status_code=400, detail="Image decoding failed.")

        img = np.array(pil_image)
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        try:
            result = ocr.ocr(img)
            lines = [line[1][0] for res in result for line in res]
            extracted_text = " ".join(lines)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

    else:
        try:
            extracted_text = extract_text_from_pdf(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF text extraction failed: {str(e)}")

    # ✅ Step 2: NLP processing using internal helper
    try:
        nlp_result = await extract_salts_internal(filename, extracted_text)
        salts = nlp_result.get("salts", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NLP processing failed: {str(e)}")

    # ✅ Step 3: Pricing retrieval
    try:
        rag_result = await get_prices(salts)
        prices = rag_result.get("prices", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pricing retrieval failed: {str(e)}")

    # ✅ Ensure JSON serializable response
    return {
        "msg": "✅ File processed successfully",
        "filename": filename,
        "extracted_text": extracted_text.strip(),
        "salts": list(salts),
        "prices": prices
    }