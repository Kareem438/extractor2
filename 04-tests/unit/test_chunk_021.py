"""
Unit tests for CHUNK-021: Marker Agent - Rectangle Drawing

Tests marker agent - rectangle drawing functionality.

Test Coverage:
- Rectangle drawing
- Color coding
- Coordinate handling
- Image conversion
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from PIL import Image


class TestChunk021MarkerAgentRectangleDrawing:
    """Test suite for CHUNK-021: Marker Agent - Rectangle Drawing"""

    def test_happy_path_rectangle_drawing(self):
        """Test rectangle drawing for text units"""
        from src.agents.marker.marker_agent import MarkerAgent

        # Create test image (100x100 white image)
        test_image = Image.new('RGB', (100, 100), color='white')

        # Create knowledge units with position data
        knowledge_units = [
            {
                'id': 1,
                'position_x': 10,
                'position_y': 20,
                'position_width': 30,
                'position_height': 40
            },
            {
                'id': 2,
                'position_x': 50,
                'position_y': 60,
                'position_width': 20,
                'position_height': 30
            }
        ]

        agent = MarkerAgent()
        marked_image, rect_data = agent.create_markers(test_image, knowledge_units)

        # Verify marked image is returned
        assert isinstance(marked_image, Image.Image)
        assert marked_image.size == test_image.size

        # Verify rectangle data
        assert 'green_rectangles' in rect_data
        assert 'orange_rectangles' in rect_data
        assert len(rect_data['green_rectangles']) == 2
        assert len(rect_data['orange_rectangles']) == 0

        # Verify first rectangle
        rect1 = rect_data['green_rectangles'][0]
        assert rect1['x'] == 10
        assert rect1['y'] == 20
        assert rect1['width'] == 30
        assert rect1['height'] == 40
        assert rect1['text_id'] == 1

    def test_orange_rectangles_for_images(self):
        """Test orange rectangle drawing for images"""
        from src.agents.marker.marker_agent import MarkerAgent

        test_image = Image.new('RGB', (100, 100), color='white')

        # Create image units with position data
        images = [
            {
                'id': 101,
                'position_x': 5,
                'position_y': 10,
                'position_width': 25,
                'position_height': 35
            }
        ]

        agent = MarkerAgent()
        marked_image, rect_data = agent.create_markers(test_image, [], images)

        # Verify orange rectangles
        assert len(rect_data['orange_rectangles']) == 1
        assert len(rect_data['green_rectangles']) == 0

        rect1 = rect_data['orange_rectangles'][0]
        assert rect1['x'] == 5
        assert rect1['y'] == 10
        assert rect1['width'] == 25
        assert rect1['height'] == 35
        assert rect1['image_id'] == 101

    def test_mixed_text_and_images(self):
        """Test drawing both text and image rectangles"""
        from src.agents.marker.marker_agent import MarkerAgent

        test_image = Image.new('RGB', (200, 200), color='white')

        knowledge_units = [
            {'id': 1, 'position_x': 10, 'position_y': 10, 'position_width': 50, 'position_height': 20}
        ]

        images = [
            {'id': 201, 'position_x': 100, 'position_y': 100, 'position_width': 40, 'position_height': 30}
        ]

        agent = MarkerAgent()
        marked_image, rect_data = agent.create_markers(test_image, knowledge_units, images)

        # Verify both types of rectangles
        assert len(rect_data['green_rectangles']) == 1
        assert len(rect_data['orange_rectangles']) == 1

    def test_missing_position_data(self):
        """Test handling of units without position data"""
        from src.agents.marker.marker_agent import MarkerAgent

        test_image = Image.new('RGB', (100, 100), color='white')

        # Mix of units with and without position data
        knowledge_units = [
            {
                'id': 1,
                'position_x': 10,
                'position_y': 20,
                'position_width': 30,
                'position_height': 40
            },
            {
                'id': 2,
                'text_content': 'No position data'
            },
            {
                'id': 3,
                'position_x': None,  # Explicit None
                'position_y': 50,
                'position_width': 20,
                'position_height': 10
            }
        ]

        agent = MarkerAgent()
        marked_image, rect_data = agent.create_markers(test_image, knowledge_units)

        # Should only draw rectangle for unit with valid position data
        assert len(rect_data['green_rectangles']) == 1
        assert rect_data['green_rectangles'][0]['text_id'] == 1

    def test_edge_cases(self):
        """Test boundary conditions"""
        from src.agents.marker.marker_agent import MarkerAgent

        test_image = Image.new('RGB', (100, 100), color='white')
        agent = MarkerAgent()

        # Test empty lists
        marked_image1, rect_data1 = agent.create_markers(test_image, [])
        assert len(rect_data1['green_rectangles']) == 0
        assert len(rect_data1['orange_rectangles']) == 0

        # Test None for images parameter
        marked_image2, rect_data2 = agent.create_markers(test_image, [], None)
        assert len(rect_data2['orange_rectangles']) == 0

        # Test with empty knowledge units
        marked_image3, rect_data3 = agent.create_markers(test_image, [], [])
        assert isinstance(marked_image3, Image.Image)

    def test_coordinate_handling(self):
        """Test coordinate calculations"""
        from src.agents.marker.marker_agent import MarkerAgent

        test_image = Image.new('RGB', (500, 500), color='white')

        knowledge_units = [
            {
                'id': 1,
                'position_x': 100,
                'position_y': 150,
                'position_width': 200,
                'position_height': 100
            }
        ]

        agent = MarkerAgent()
        marked_image, rect_data = agent.create_markers(test_image, knowledge_units)

        rect = rect_data['green_rectangles'][0]
        # Verify coordinates are preserved correctly
        assert rect['x'] == 100
        assert rect['y'] == 150
        assert rect['width'] == 200
        assert rect['height'] == 100

    def test_float_coordinates_conversion(self):
        """Test that float coordinates are converted to int"""
        from src.agents.marker.marker_agent import MarkerAgent

        test_image = Image.new('RGB', (100, 100), color='white')

        knowledge_units = [
            {
                'id': 1,
                'position_x': 10.7,
                'position_y': 20.3,
                'position_width': 30.9,
                'position_height': 40.2
            }
        ]

        agent = MarkerAgent()
        marked_image, rect_data = agent.create_markers(test_image, knowledge_units)

        rect = rect_data['green_rectangles'][0]
        # Should convert to int
        assert rect['x'] == 10
        assert rect['y'] == 20
        assert rect['width'] == 30
        assert rect['height'] == 40

    def test_image_conversion(self):
        """Test PIL to OpenCV to PIL conversion"""
        from src.agents.marker.marker_agent import MarkerAgent

        # Create test image with specific color
        test_image = Image.new('RGB', (100, 100), color=(255, 0, 0))  # Red

        agent = MarkerAgent()
        marked_image, rect_data = agent.create_markers(test_image, [])

        # Verify output is PIL Image
        assert isinstance(marked_image, Image.Image)
        assert marked_image.size == (100, 100)
        assert marked_image.mode == 'RGB'

        # Image should still be mostly red (no rectangles drawn)
        pixel = marked_image.getpixel((50, 50))
        assert pixel == (255, 0, 0)
