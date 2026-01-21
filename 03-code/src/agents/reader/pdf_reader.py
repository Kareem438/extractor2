"""
CHUNK-012: PDF Text Extraction (PyMuPDF)

Extract text from PDF using PyMuPDF with detailed block-level information.
Provides text content, bounding boxes, and font information.
"""

try:
    import fitz  # PyMuPDF
except ImportError:
    # For environments where PyMuPDF is not installed
    # Create mock to allow patching in tests
    class _MockFitz:
        @staticmethod
        def open(pdf_path):
            raise ImportError("PyMuPDF (fitz) is not installed")

    fitz = _MockFitz()


def extract_text_from_pdf_page(pdf_path: str, page_number: int) -> dict:
    """
    Extract text from a specific PDF page.

    Extracts both plain text and structured text blocks with positioning,
    font, and size information. Useful for layout analysis and OCR detection.

    Args:
        pdf_path: Path to the PDF file
        page_number: Page number to extract (1-indexed)

    Returns:
        dict: {
            'text': str - Plain text content from the page
            'blocks': list - List of text blocks with metadata:
                - text: Text content of the span
                - bbox: Bounding box tuple (x0, y0, x1, y1)
                - font: Font name
                - size: Font size
            'has_text': bool - Whether page contains text
        }

    Raises:
        Exception: If PDF cannot be opened
        IndexError: If page number is out of range

    Example:
        >>> result = extract_text_from_pdf_page('document.pdf', 1)
        >>> print(f"Text: {result['text']}")
        >>> print(f"Has text: {result['has_text']}")
        >>> for block in result['blocks']:
        ...     print(f"Block at {block['bbox']}: {block['text']}")
    """
    # Open PDF document
    doc = fitz.open(pdf_path)

    # Get page (convert 1-indexed to 0-indexed)
    # PyMuPDF supports both doc[n] and doc.load_page(n)
    # We use load_page() for better compatibility with mocks
    page = doc.load_page(page_number - 1)

    # Extract structured text with coordinates
    dict_result = page.get_text("dict")
    blocks_data = dict_result["blocks"]

    # Process text blocks
    text_blocks = []
    for block in blocks_data:
        if block['type'] == 0:  # Text block (type 0)
            for line in block['lines']:
                for span in line['spans']:
                    text_blocks.append({
                        'text': span['text'],
                        'bbox': span['bbox'],
                        'font': span['font'],
                        'size': span['size']
                    })

    # Extract plain text
    full_text = page.get_text()

    return {
        'text': full_text,
        'blocks': text_blocks,
        'has_text': len(full_text.strip()) > 0
    }
