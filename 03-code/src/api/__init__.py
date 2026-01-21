"""
API Module

Contains API endpoints and background processing tasks.
"""

from src.api.background_processor import process_book_background

__all__ = ['process_book_background']
