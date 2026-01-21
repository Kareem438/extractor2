"""
CHUNK-036: API Routes - Images

Retrieve and serve extracted images.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import Optional
from src.database.services.image_service import ImageService
from src.utils.logging_config import logger

router = APIRouter()


@router.get("/books/{book_id}/images")
async def list_images(
    book_id: int,
    page_number: Optional[int] = None
):
    """List images for a book."""
    service = ImageService()
    images = service.get_images(book_id, page_number)

    return {
        "book_id": book_id,
        "images": images
    }


@router.get("/books/{book_id}/images/{image_id}")
async def get_image_metadata(book_id: int, image_id: int):
    """Get image metadata."""
    service = ImageService()
    image = service.get_image(book_id, image_id)

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    return image


@router.get("/books/{book_id}/images/{image_id}/data")
async def get_image_data(book_id: int, image_id: int):
    """Get actual image binary data."""
    service = ImageService()
    image = service.get_image(book_id, image_id)

    if not image or not image.get('image_data'):
        raise HTTPException(status_code=404, detail="Image not found")

    # Return image as binary response
    return Response(
        content=image['image_data'],
        media_type=f"image/{image.get('image_format', 'png')}"
    )
