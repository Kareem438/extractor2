"""
CHUNK-022: Image-Reader Agent - Image Extraction

Extract images from PDF pages and generate AI descriptions using BLIP captioning.
Integrates with PyMuPDF for image extraction and ImageCaptioner for descriptions.
"""

try:
    import fitz  # PyMuPDF
except ImportError:
    # Mock for testing when PyMuPDF is not available
    class MockDocument:
        def __getitem__(self, index):
            return MockPage()
        def close(self):
            pass

    class MockPage:
        def get_images(self):
            return []

    class fitz:
        @staticmethod
        def open(path):
            return MockDocument()

from PIL import Image
from io import BytesIO
from src.agents.image_reader.image_captioner import ImageCaptioner
from src.utils.logging_config import logger


class ImageReaderAgent:
    """
    Agent responsible for extracting images from PDF pages.

    Uses PyMuPDF to extract raw image data from PDFs and BLIP model
    to generate AI descriptions of image content.
    """

    def extract_images(self, pdf_path: str, page_number: int) -> list[dict]:
        """
        Extract all images from page with AI descriptions.

        Opens PDF, extracts all images from specified page, generates
        AI captions using BLIP, and classifies image types.

        Args:
            pdf_path: Path to PDF file
            page_number: Page number to extract from (1-indexed)

        Returns:
            list[dict]: List of image dictionaries with:
                - image_id: Unique identifier (IMG-PPP-II format)
                - page_number: Source page number
                - image_data: PIL Image object
                - ai_description: AI-generated caption
                - confidence_score: Caption confidence (0-100)
                - image_type: Classified type (diagram/photo/chart/other)
                - original_width: Image width in pixels
                - original_height: Image height in pixels

        Example:
            >>> agent = ImageReaderAgent()
            >>> images = agent.extract_images('document.pdf', 1)
            >>> for img in images:
            ...     print(f"{img['image_id']}: {img['ai_description']}")
        """
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]  # Convert to 0-indexed

        images = []
        image_list = page.get_images()

        logger.info(f"Found {len(image_list)} images on page {page_number}")

        for img_index, img_info in enumerate(image_list):
            try:
                # Extract image from PDF
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # Load as PIL Image
                image = Image.open(BytesIO(image_bytes))

                # Generate AI description using BLIP
                description, confidence = ImageCaptioner.generate_caption(image)

                # Classify image type
                image_type = self._classify_image_type(image, description)

                images.append({
                    'image_id': f"IMG-{page_number:03d}-{img_index:02d}",
                    'page_number': page_number,
                    'image_data': image,
                    'ai_description': description,
                    'confidence_score': confidence,
                    'image_type': image_type,
                    'original_width': image.width,
                    'original_height': image.height
                })

                logger.debug(f"Extracted {images[-1]['image_id']}: {description}")

            except Exception as e:
                logger.warning(f"Failed to extract image {img_index} from page {page_number}: {e}")
                continue

        doc.close()
        return images

    def _classify_image_type(self, image: Image.Image, description: str = "") -> str:
        """
        Classify image type based on heuristics.

        Uses simple heuristics based on image properties and AI description
        to classify images into categories.

        Args:
            image: PIL Image object
            description: AI-generated description (optional)

        Returns:
            str: Image type - 'diagram', 'photo', 'chart', or 'other'
        """
        # Simple heuristic classification
        width, height = image.size
        aspect_ratio = width / height if height > 0 else 1.0

        # Check description for keywords
        desc_lower = description.lower() if description else ""

        # Diagram keywords (check first - more specific)
        if any(keyword in desc_lower for keyword in ['diagram', 'schematic', 'flowchart', 'illustration']):
            return 'diagram'

        # Chart/graph keywords
        if any(keyword in desc_lower for keyword in ['chart', 'graph', 'plot', 'bar', 'pie']):
            return 'chart'

        # Photo keywords or typical photo aspect ratios
        if any(keyword in desc_lower for keyword in ['photo', 'picture', 'person', 'people', 'landscape', 'building']):
            return 'photo'

        # Very wide or tall images are likely diagrams
        if aspect_ratio > 2.5 or aspect_ratio < 0.4:
            return 'diagram'

        # Default to other
        return 'other'
