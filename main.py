from fastapi import FastAPI
from routers import auth, upload, ocr, nlp, rag, optimizer, delivery, payment, admin  # ✅ Added test_ocr

app = FastAPI(title="AI Prescription App MVP - Modular Skeleton")

# Attach each router with a prefix and tag
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/upload", tags=["File Upload"])
app.include_router(ocr.router, prefix="/ocr", tags=["OCR"])
app.include_router(nlp.router, prefix="/nlp", tags=["NLP"])
app.include_router(rag.router, prefix="/rag", tags=["RAG"])
app.include_router(optimizer.router, prefix="/optimizer", tags=["Optimizer"])
app.include_router(delivery.router, prefix="/delivery", tags=["Delivery"])
app.include_router(payment.router, prefix="/payment", tags=["Payment"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

@app.get("/")
def home():
    return {"msg": "AI Prescription App API running. All modules are ready for integration."}