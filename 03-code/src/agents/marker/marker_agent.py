"""
CHUNK-021: Marker Agent - Rectangle Drawing

Draw green/orange rectangles on page images to visualize knowledge units
and images. Uses OpenCV for rectangle drawing and PIL for image handling.
"""

import cv2
import numpy as np
from PIL import Image


class MarkerAgent:
    """
    Agent responsible for drawing visual markers on page images.

    Draws green rectangles for text knowledge units and orange rectangles
    for image regions to create visual annotations of the page content.
    """

    def create_markers(self, page_image: Image.Image, knowledge_units: list[dict],
                      images: list[dict] = None) -> tuple[Image.Image, dict]:
        """
        Draw markers on page image.

        Draws colored rectangles to visualize knowledge units (green) and
        images (orange) on the page. Converts between PIL and OpenCV formats
        for drawing operations.

        Args:
            page_image: PIL Image of the page
            knowledge_units: List of knowledge unit dicts with position data:
                - position_x: X coordinate of top-left corner
                - position_y: Y coordinate of top-left corner
                - position_width: Width of rectangle
                - position_height: Height of rectangle
                - id: Unit identifier
            images: List of image dicts with position data (optional):
                - position_x, position_y, position_width, position_height
                - id: Image identifier

        Returns:
            tuple: (marked_image, rectangle_data) where:
                - marked_image: PIL Image with rectangles drawn
                - rectangle_data: dict with 'green_rectangles' and 'orange_rectangles'

        Example:
            >>> agent = MarkerAgent()
            >>> marked_img, rects = agent.create_markers(page_img, units, imgs)
            >>> print(f"Drew {len(rects['green_rectangles'])} text markers")
        """
        # Handle None for images
        if images is None:
            images = []

        # Convert PIL to OpenCV format (RGB -> BGR)
        img_array = np.array(page_image)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        green_rects = []
        orange_rects = []

        # Draw green rectangles for text knowledge units
        for ku in knowledge_units:
            # Check if position data exists
            if 'position_x' in ku and ku['position_x'] is not None:
                x1 = int(ku['position_x'])
                y1 = int(ku['position_y'])
                x2 = x1 + int(ku['position_width'])
                y2 = y1 + int(ku['position_height'])

                # Draw green rectangle (BGR color)
                cv2.rectangle(img_cv, (x1, y1), (x2, y2), (0, 255, 0), 2)

                green_rects.append({
                    'x': x1,
                    'y': y1,
                    'width': int(ku['position_width']),
                    'height': int(ku['position_height']),
                    'text_id': ku.get('id')
                })

        # Draw orange rectangles for images
        for img in images:
            # Check if position data exists
            if 'position_x' in img and img['position_x'] is not None:
                x1 = int(img['position_x'])
                y1 = int(img['position_y'])
                x2 = x1 + int(img['position_width'])
                y2 = y1 + int(img['position_height'])

                # Draw orange rectangle (BGR color)
                cv2.rectangle(img_cv, (x1, y1), (x2, y2), (0, 165, 255), 2)

                orange_rects.append({
                    'x': x1,
                    'y': y1,
                    'width': int(img['position_width']),
                    'height': int(img['position_height']),
                    'image_id': img.get('id')
                })

        # Convert back to PIL (BGR -> RGB)
        marked_image = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))

        return marked_image, {
            'green_rectangles': green_rects,
            'orange_rectangles': orange_rects
        }
