"""
CHUNK-013: PDF to Image Conversion

Convert PDF pages to PNG images using PyMuPDF.
Supports configurable DPI for different quality levels.
"""

try:
    import fitz  # PyMuPDF
except ImportError:
    # For environments where PyMuPDF is not installed
    class _MockFitz:
        class Matrix:
            def __init__(self, *args, **kwargs):
                pass

        @staticmethod
        def open(pdf_path):
            raise ImportError("PyMuPDF (fitz) is not installed")

    fitz = _MockFitz()

from PIL import Image


def pdf_page_to_image(pdf_path: str, page_number: int, dpi: int = 150) -> Image.Image:
    """
    Convert PDF page to PIL Image.

    Renders a PDF page at specified DPI and returns as a PIL Image object.
    Higher DPI produces larger, higher-quality images.

    Args:
        pdf_path: Path to the PDF file
        page_number: Page number to convert (1-indexed)
        dpi: Dots per inch for rendering (default: 150)
            - 72: Standard PDF resolution
            - 150: Balanced quality/size
            - 300: High quality for OCR

    Returns:
        Image.Image: PIL Image object in RGB mode

    Raises:
        Exception: If PDF cannot be opened
        IndexError: If page number is out of range

    Example:
        >>> img = pdf_page_to_image('document.pdf', 1, dpi=300)
        >>> img.save('page1.png')
        >>> print(f"Image size: {img.width}x{img.height}")
    """
    # Open PDF document
    doc = fitz.open(pdf_path)

    # Get page (convert 1-indexed to 0-indexed)
    page = doc[page_number - 1]

    # Calculate zoom factor from DPI
    # PDF standard is 72 DPI, so zoom = desired_dpi / 72
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    # Render page to pixmap
    pix = page.get_pixmap(matrix=mat)

    # Convert pixmap to PIL Image
    # PyMuPDF pixmap is in RGB format
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    return img
