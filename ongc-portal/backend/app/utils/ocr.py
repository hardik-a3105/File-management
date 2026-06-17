import io
import logging
from PIL import Image, ImageFilter, ImageOps
import pytesseract
from pdf2image import convert_from_bytes

logger = logging.getLogger(__name__)


def preprocess_image(img: Image.Image) -> Image.Image:
    img = img.convert("L")
    img = img.filter(ImageFilter.MedianFilter(size=3))
    img = ImageOps.invert(img)
    img = img.point(lambda x: 0 if x < 140 else 255, "1")
    return img


def ocr_pdf(content: bytes, lang: str = "eng+hin") -> str:
    try:
        pages = convert_from_bytes(content, dpi=300)
    except Exception as e:
        logger.warning("pdf2image conversion failed: %s", e)
        return ""

    all_text = []
    for i, page in enumerate(pages):
        try:
            processed = preprocess_image(page)
            text = pytesseract.image_to_string(processed, lang=lang, config="--psm 6 --oem 3")
            if text.strip():
                all_text.append(text)
            logger.info("OCR page %d: %d chars", i + 1, len(text))
        except Exception as e:
            logger.warning("OCR failed on page %d: %s", i + 1, e)
            continue

    result = "\n".join(all_text)
    logger.info("OCR total: %d chars", len(result))
    return result


def needs_ocr(text: str, min_chars: int = 50) -> bool:
    return not text or len(text.strip()) < min_chars
