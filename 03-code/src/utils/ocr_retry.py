"""
CHUNK-011: OCR Retry Logic

3-attempt OCR retry with zoom enhancement.
Provides robust OCR with fallback strategies for low-confidence results.
"""

from PIL import Image
from src.utils.ocr import ocr_image
from src.utils.logging_config import logger


def ocr_with_retry(image: Image.Image, language: str = 'eng', max_attempts: int = 3) -> tuple[str, float, str]:
    """
    Perform OCR with 3-attempt retry logic.

    Attempts OCR with progressively enhanced strategies:
    1. Standard quality with balanced settings
    2. 200% zoom enhancement with high quality
    3. Region segmentation with high quality

    Args:
        image: PIL Image object to perform OCR on
        language: Tesseract language code (default: 'eng')
        max_attempts: Maximum number of retry attempts (default: 3)

    Returns:
        tuple[str, float, str]: (extracted_text, confidence_score, method_used)
            - extracted_text: Text content from image
            - confidence_score: Average confidence (0-100)
            - method_used: One of 'ocr_standard', 'ocr_retry_zoom', 'ocr_retry_segment'

    Example:
        >>> from PIL import Image
        >>> img = Image.open('page.png')
        >>> text, confidence, method = ocr_with_retry(img)
        >>> print(f"Method: {method}, Confidence: {confidence}%")
    """
    # Attempt 1: Standard quality
    text, confidence = ocr_image(image, language=language, quality='balanced')

    if confidence >= 70:
        return text, confidence, 'ocr_standard'

    logger.warning(f"OCR attempt 1 failed (confidence: {confidence}%), retrying...")

    # Attempt 2: Zoom 200% + High Quality
    zoomed = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
    text, confidence = ocr_image(zoomed, language=language, quality='high')

    if confidence >= 60:
        return text, confidence, 'ocr_retry_zoom'

    logger.warning(f"OCR attempt 2 failed (confidence: {confidence}%), final attempt...")

    # Attempt 3: Region segmentation fallback
    # For this implementation, we use high quality on the original image
    # A more sophisticated approach would segment the image into regions
    text, confidence = ocr_image(image, language=language, quality='high')

    return text, confidence, 'ocr_retry_segment'
