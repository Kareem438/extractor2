"""
CHUNK-037: API Routes - Pages

Retrieve page images and rectangle data.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from src.database.services.page_service import PageService
from src.utils.logging_config import logger
from io import BytesIO

router = APIRouter()


@router.get("/books/{book_id}/pages")
async def list_pages(book_id: int):
    """List all pages for a book."""
    service = PageService()
    pages = service.get_pages(book_id)

    return {
        "book_id": book_id,
        "pages": pages
    }


@router.get("/books/{book_id}/pages/{page_number}")
async def get_page(book_id: int, page_number: int):
    """Get page metadata and rectangle data."""
    service = PageService()
    page = service.get_page(book_id, page_number, include_images=False)

    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    return page


@router.get("/books/{book_id}/pages/{page_number}/image")
async def get_page_image(book_id: int, page_number: int, marked: bool = False):
    """Get page image (original or marked)."""
    service = PageService()
    page = service.get_page(book_id, page_number, include_images=True)

    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Get the correct image (marked or original)
    pil_image = page.get('marked_image') if marked else page.get('original_image')

    if not pil_image:
        raise HTTPException(status_code=404, detail="Page image not found")

    # Convert PIL Image to bytes
    img_byte_arr = BytesIO()
    pil_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    return Response(content=img_byte_arr.getvalue(), media_type="image/png")
