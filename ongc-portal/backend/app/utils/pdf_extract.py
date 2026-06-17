import fitz
import logging

logger = logging.getLogger(__name__)

def extract_text_from_pdf(content: bytes) -> str:
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        text_parts = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                text_parts.append(text)
        doc.close()
        result = "\n".join(text_parts)
        logger.info("Extracted %d chars from PDF", len(result))
        return result
    except Exception as e:
        logger.warning("PDF text extraction failed: %s", e)
        return ""
