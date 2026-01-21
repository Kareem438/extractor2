"""
CHUNK-010: OCR Utility (Tesseract)

OCR text extraction using Tesseract with configurable quality settings.
Provides confidence scoring for extracted text.
"""

try:
    import pytesseract
    from pytesseract import Output
except ImportError:
    # For environments where pytesseract is not installed
    # Create mock objects to allow patching in tests
    class _MockPytesseract:
        class pytesseract:
            tesseract_cmd = None

        @staticmethod
        def image_to_data(*args, **kwargs):
            raise ImportError("pytesseract is not installed")

        @staticmethod
        def image_to_string(*args, **kwargs):
            raise ImportError("pytesseract is not installed")

    class _MockOutput:
        DICT = 'dict'

    pytesseract = _MockPytesseract()
    Output = _MockOutput()

from PIL import Image

# Import settings - will be mocked in tests
try:
    from src.config import settings
except Exception:
    # Allow import to succeed even if settings validation fails
    settings = None


def ocr_image(image: Image.Image, language: str = 'eng', quality: str = 'balanced') -> tuple[str, float]:
    """
    Perform OCR on image using Tesseract.

    Extracts text from an image and calculates average confidence score.
    Supports multiple quality levels and languages.

    Args:
        image: PIL Image object to perform OCR on
        language: Tesseract language code (default: 'eng')
            - 'eng' for English
            - 'ara' for Arabic
            - 'fra' for French, etc.
        quality: OCR quality setting (default: 'balanced')
            - 'fast': Quick processing with --psm 3
            - 'balanced': Standard quality with --psm 3 --oem 3
            - 'high': Best quality with --psm 3 --oem 3 --dpi 300

    Returns:
        tuple[str, float]: (extracted_text, confidence_score)
            - extracted_text: Stripped text content from image
            - confidence_score: Average confidence (0-100)

    Raises:
        Exception: If Tesseract is not installed or configured incorrectly

    Example:
        >>> from PIL import Image
        >>> img = Image.open('page.png')
        >>> text, confidence = ocr_image(img, language='eng', quality='high')
        >>> print(f"Text: {text}, Confidence: {confidence}%")
    """
    # Configure Tesseract path
    if pytesseract and settings:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

    # Quality configuration mapping
    config_map = {
        'fast': '--psm 3',
        'balanced': '--psm 3 --oem 3',
        'high': '--psm 3 --oem 3 --dpi 300'
    }

    config = config_map.get(quality, config_map['balanced'])

    # Get OCR data with confidence scores
    data = pytesseract.image_to_data(
        image,
        lang=language,
        config=config,
        output_type=Output.DICT
    )

    # Calculate average confidence (ignore -1 values)
    confidences = [int(conf) for conf in data['conf'] if conf != '-1']
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Extract text
    text = pytesseract.image_to_string(
        image,
        lang=language,
        config=config
    )

    return text.strip(), avg_confidence
