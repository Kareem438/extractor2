"""
CHUNK-023: Agent Orchestrator - Sequential Execution

Coordinate all agents for page-by-page PDF processing.
Manages the workflow: Reader → Splitter → Image Reader → Marker.
"""

from src.agents.reader.reader_agent import ReaderAgent
from src.agents.splitter.splitter_agent import SplitterAgent
from src.agents.marker.marker_agent import MarkerAgent
from src.agents.image_reader.image_extractor import ImageReaderAgent
from src.agents.reader.pdf_to_image import pdf_page_to_image
from src.utils.logging_config import logger


class AgentOrchestrator:
    """
    Orchestrator that coordinates all agents for PDF processing.

    Manages the sequential execution of agents to extract, process,
    and annotate PDF content page by page.
    """

    def __init__(self, book_id: int, pdf_path: str, settings: dict):
        """
        Initialize orchestrator with agents.

        Args:
            book_id: Database book ID
            pdf_path: Path to PDF file
            settings: Processing settings dict with:
                - language_setting: Language for OCR ('auto', 'english', 'arabic', 'mixed')
                - ocr_quality: OCR quality setting ('fast', 'balanced', 'high')
        """
        self.book_id = book_id
        self.pdf_path = pdf_path
        self.settings = settings

        # Initialize agents
        self.reader = ReaderAgent()
        self.splitter = SplitterAgent()
        self.marker = MarkerAgent()
        self.image_reader = ImageReaderAgent()

        logger.info(f"AgentOrchestrator initialized for book_id={book_id}")

    def process_page(self, page_number: int) -> dict:
        """
        Process single page through all agents.

        Executes agents sequentially:
        1. ReaderAgent: Extract text from page
        2. SplitterAgent: Split text into knowledge units
        3. ImageReaderAgent: Extract and caption images
        4. MarkerAgent: Draw visualization rectangles

        Args:
            page_number: Page number to process (1-indexed)

        Returns:
            dict: Complete page processing results with:
                - page_number: Page number processed
                - text_data: Raw text extraction data from ReaderAgent
                - knowledge_units: List of knowledge unit dicts
                - images: List of image dicts with AI captions
                - page_image: Original page image (PIL)
                - marked_image: Annotated page image with rectangles (PIL)
                - rectangle_data: Rectangle metadata

        Example:
            >>> orchestrator = AgentOrchestrator(1, 'doc.pdf', {'language_setting': 'auto', 'ocr_quality': 'balanced'})
            >>> result = orchestrator.process_page(1)
            >>> print(f"Extracted {len(result['knowledge_units'])} knowledge units")
            >>> print(f"Found {len(result['images'])} images")
        """
        logger.info(f"Processing page {page_number}...")

        # 1. Reader Agent - Extract text
        logger.debug(f"Page {page_number}: Running ReaderAgent...")
        text_data = self.reader.read_page(
            self.pdf_path,
            page_number,
            language_setting=self.settings.get('language_setting', 'auto'),
            ocr_quality=self.settings.get('ocr_quality', 'balanced')
        )

        # 2. Splitter Agent - Create knowledge units
        logger.debug(f"Page {page_number}: Running SplitterAgent...")
        knowledge_units = self.splitter.split_text(
            text_data['text'],
            page_number
        )

        # 3. Image-Reader Agent - Extract images
        logger.debug(f"Page {page_number}: Running ImageReaderAgent...")
        images = self.image_reader.extract_images(
            self.pdf_path,
            page_number
        )

        # 4. Marker Agent - Create visualization
        logger.debug(f"Page {page_number}: Running MarkerAgent...")
        page_image = pdf_page_to_image(self.pdf_path, page_number)
        marked_image, rect_data = self.marker.create_markers(
            page_image,
            knowledge_units,
            images
        )

        logger.info(
            f"Page {page_number} complete: "
            f"{len(knowledge_units)} knowledge units, "
            f"{len(images)} images"
        )

        return {
            'page_number': page_number,
            'text_data': text_data,
            'knowledge_units': knowledge_units,
            'images': images,
            'page_image': page_image,
            'marked_image': marked_image,
            'rectangle_data': rect_data
        }
