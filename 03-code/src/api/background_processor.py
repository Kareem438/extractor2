"""
CHUNK-030: Background Processing Task

Async background task for processing books page-by-page.
Integrates orchestrator with all database services for complete book processing.
"""

import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.connection import SessionLocal
from src.database.models.books_metadata import BooksMetadata
from src.database.services.book_settings_service import BookSettingsService
from src.database.services.processing_state_service import ProcessingStateService
from src.database.services.knowledge_unit_service import KnowledgeUnitService
from src.database.services.image_service import ImageService
from src.database.services.page_service import PageService
from src.agents.orchestrator import AgentOrchestrator
from src.utils.logging_config import logger


async def process_book_background(book_id: int, pdf_path: str) -> bool:
    """
    Background task for processing book page-by-page.

    Orchestrates the complete book processing workflow:
    1. Reads book metadata and settings
    2. Processes each page through the agent orchestrator
    3. Saves results to database (knowledge units, images, pages)
    4. Updates processing state and progress
    5. Handles pause signals and checkpoints
    6. Handles errors and updates status accordingly

    Args:
        book_id: Book ID to process
        pdf_path: Path to PDF file

    Returns:
        bool: True if processing completed successfully, False if paused or failed

    Example:
        >>> await process_book_background(book_id=1, pdf_path='/path/to/book.pdf')
    """
    db = SessionLocal()

    try:
        # Get book metadata
        book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
        if not book:
            raise ValueError(f"Book {book_id} not found in metadata")

        # Get book settings
        settings_service = BookSettingsService()
        settings = settings_service.get_settings(book_id)

        # Initialize orchestrator
        orchestrator = AgentOrchestrator(book_id, pdf_path, settings)

        # Determine total pages to process
        total_pages = book.total_pages
        if settings['partial_processing_enabled'] and settings['partial_processing_pages']:
            total_pages = min(total_pages, settings['partial_processing_pages'])
            logger.info(f"Partial processing enabled: processing first {total_pages} pages")

        # Update book status to processing
        book.processing_status = 'processing'
        db.commit()

        # Update processing state
        state_service = ProcessingStateService()
        state_service.update_state(book_id, {
            'status': 'processing',
            'total_pages': total_pages,
            'processing_started_at': datetime.now()
        })

        logger.info(f"Starting background processing for book {book_id}: {total_pages} pages")

        # Initialize services
        ku_service = KnowledgeUnitService()
        image_service = ImageService()
        page_service = PageService()

        # Track timing for progress estimation
        start_time = datetime.now()

        # Process pages sequentially
        for page_num in range(1, total_pages + 1):
            # Check for pause signal
            state = state_service.get_state(book_id)
            if state['status'] == 'paused':
                logger.info(f"Processing paused at page {page_num} for book {book_id}")
                book.processing_status = 'paused'
                db.commit()
                return False

            # Process page through orchestrator
            logger.info(f"Processing page {page_num}/{total_pages} for book {book_id}")
            page_data = orchestrator.process_page(page_num)

            # Save knowledge units to database
            if page_data['knowledge_units']:
                ku_service.insert_knowledge_units(book_id, page_data['knowledge_units'])

            # Save images to database
            if page_data['images']:
                image_service.insert_images(book_id, page_data['images'])

            # Save page with images and rectangles
            page_service.insert_page(book_id, {
                'page_number': page_num,
                'page_image': page_data['page_image'],
                'marked_image': page_data['marked_image'],
                'rectangle_data': page_data['rectangle_data']
            })

            # Calculate average processing time
            elapsed_time = (datetime.now() - start_time).total_seconds()
            avg_time_per_page = elapsed_time / page_num

            # Update processing state with progress
            state_service.update_state(book_id, {
                'current_page': page_num,
                'pages_processed': page_num,
                'avg_page_processing_time': avg_time_per_page
            })

            # Increment counters atomically
            state_service.increment_counters(book_id, {
                'knowledge_units_extracted': len(page_data['knowledge_units']),
                'images_extracted': len(page_data['images'])
            })

            # Save checkpoint every N pages
            if page_num % settings['checkpoint_frequency'] == 0:
                state_service.save_checkpoint(book_id, page_num)
                logger.info(f"Checkpoint saved at page {page_num} for book {book_id}")

            # Allow other async tasks to run
            await asyncio.sleep(0)

        # Mark processing as completed
        book.processing_status = 'completed'
        db.commit()

        state_service.update_state(book_id, {
            'status': 'completed',
            'processing_completed_at': datetime.now()
        })

        logger.info(f"Book {book_id} processing completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Processing error for book {book_id}: {e}", exc_info=True)

        # Update book status to error
        try:
            book = db.query(BooksMetadata).filter(BooksMetadata.book_id == book_id).first()
            if book:
                book.processing_status = 'error'
                db.commit()
        except Exception as inner_e:
            logger.error(f"Failed to update book status to error: {inner_e}")

        # Update processing state with error
        try:
            state_service = ProcessingStateService()
            state_service.update_state(book_id, {
                'status': 'error',
                'last_error_message': str(e),
                'last_error_at': datetime.now()
            })
        except Exception as inner_e:
            logger.error(f"Failed to update processing state: {inner_e}")

        return False

    finally:
        db.close()


def run_background_processor_sync(book_id: int, pdf_path: str) -> bool:
    """
    Synchronous wrapper for background processor.

    Useful for running in thread pools or process pools where async
    is not available.

    Args:
        book_id: Book ID to process
        pdf_path: Path to PDF file

    Returns:
        bool: True if processing completed successfully

    Example:
        >>> from concurrent.futures import ThreadPoolExecutor
        >>> with ThreadPoolExecutor() as executor:
        ...     future = executor.submit(run_background_processor_sync, 1, '/path/to/book.pdf')
        ...     result = future.result()
    """
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(process_book_background(book_id, pdf_path))
        return result
    finally:
        loop.close()
