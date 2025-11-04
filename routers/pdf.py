from PyPDF2 import PdfReader
import io

def extract_text_from_pdf(content: bytes) -> str:
    """
    Extracts text from a PDF file given its content in bytes.
    """
    try:
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"PDF extraction failed: {str(e)}")