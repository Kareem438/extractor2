"""
Unit tests for CHUNK-022: Image-Reader Agent - Image Extraction

Tests image-reader agent - image extraction functionality.

Test Coverage:
- Image extraction
- Caption generation
- Multiple images
- Image classification
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from io import BytesIO


class TestChunk022ImageReaderAgentImageExtraction:
    """Test suite for CHUNK-022: Image-Reader Agent - Image Extraction"""

    @patch('src.agents.image_reader.image_extractor.fitz')
    @patch('src.agents.image_reader.image_extractor.ImageCaptioner')
    def test_happy_path_image_extraction(self, mock_captioner, mock_fitz):
        """Test image extraction from PDF page"""
        # Mock PDF document and page
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_fitz.open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page

        # Mock one image on the page
        mock_page.get_images.return_value = [
            (1234, 0, 100, 100, 0, '', '', '', '')  # xref and other metadata
        ]

        # Mock extracted image bytes
        test_image = Image.new('RGB', (100, 100), color='white')
        img_bytes = BytesIO()
        test_image.save(img_bytes, format='PNG')
        mock_doc.extract_image.return_value = {'image': img_bytes.getvalue()}

        # Mock AI caption
        mock_captioner.generate_caption.return_value = ('A white square', 85.0)

        from src.agents.image_reader.image_extractor import ImageReaderAgent

        agent = ImageReaderAgent()
        images = agent.extract_images('/path/to/file.pdf', 1)

        # Verify extraction
        assert len(images) == 1
        img = images[0]
        assert img['image_id'] == 'IMG-001-00'
        assert img['page_number'] == 1
        assert isinstance(img['image_data'], Image.Image)
        assert img['ai_description'] == 'A white square'
        assert img['confidence_score'] == 85.0
        assert img['image_type'] in ['diagram', 'photo', 'chart', 'other']
        assert img['original_width'] == 100
        assert img['original_height'] == 100

        # Verify mocks were called
        mock_fitz.open.assert_called_once_with('/path/to/file.pdf')
        mock_doc.__getitem__.assert_called_once_with(0)  # Page 1 -> index 0
        mock_page.get_images.assert_called_once()
        mock_doc.close.assert_called_once()

    @patch('src.agents.image_reader.image_extractor.fitz')
    @patch('src.agents.image_reader.image_extractor.ImageCaptioner')
    def test_multiple_images(self, mock_captioner, mock_fitz):
        """Test extracting multiple images from a page"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_fitz.open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page

        # Mock three images
        mock_page.get_images.return_value = [
            (1234, 0, 100, 100, 0, '', '', '', ''),
            (1235, 0, 200, 150, 0, '', '', '', ''),
            (1236, 0, 50, 50, 0, '', '', '', '')
        ]

        # Mock extracted images
        def mock_extract(xref):
            if xref == 1234:
                img = Image.new('RGB', (100, 100), color='red')
            elif xref == 1235:
                img = Image.new('RGB', (200, 150), color='green')
            else:
                img = Image.new('RGB', (50, 50), color='blue')

            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            return {'image': img_bytes.getvalue()}

        mock_doc.extract_image.side_effect = mock_extract

        # Mock captions
        mock_captioner.generate_caption.side_effect = [
            ('Image 1', 80.0),
            ('Image 2', 85.0),
            ('Image 3', 90.0)
        ]

        from src.agents.image_reader.image_extractor import ImageReaderAgent

        agent = ImageReaderAgent()
        images = agent.extract_images('/path/to/file.pdf', 2)

        # Verify all images extracted
        assert len(images) == 3
        assert images[0]['image_id'] == 'IMG-002-00'
        assert images[1]['image_id'] == 'IMG-002-01'
        assert images[2]['image_id'] == 'IMG-002-02'
        assert images[0]['ai_description'] == 'Image 1'
        assert images[1]['ai_description'] == 'Image 2'
        assert images[2]['ai_description'] == 'Image 3'

    @patch('src.agents.image_reader.image_extractor.fitz')
    def test_no_images_on_page(self, mock_fitz):
        """Test page with no images"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_fitz.open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page

        # No images
        mock_page.get_images.return_value = []

        from src.agents.image_reader.image_extractor import ImageReaderAgent

        agent = ImageReaderAgent()
        images = agent.extract_images('/path/to/file.pdf', 1)

        assert images == []
        mock_doc.close.assert_called_once()

    @patch('src.agents.image_reader.image_extractor.fitz')
    @patch('src.agents.image_reader.image_extractor.ImageCaptioner')
    @patch('src.agents.image_reader.image_extractor.logger')
    def test_error_handling_single_image(self, mock_logger, mock_captioner, mock_fitz):
        """Test that extraction continues when one image fails"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_fitz.open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page

        # Mock two images
        mock_page.get_images.return_value = [
            (1234, 0, 100, 100, 0, '', '', '', ''),
            (1235, 0, 200, 150, 0, '', '', '', '')
        ]

        # First image fails, second succeeds
        def mock_extract(xref):
            if xref == 1234:
                raise Exception("Corrupt image data")
            else:
                img = Image.new('RGB', (200, 150), color='green')
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                return {'image': img_bytes.getvalue()}

        mock_doc.extract_image.side_effect = mock_extract
        mock_captioner.generate_caption.return_value = ('Valid image', 85.0)

        from src.agents.image_reader.image_extractor import ImageReaderAgent

        agent = ImageReaderAgent()
        images = agent.extract_images('/path/to/file.pdf', 1)

        # Should extract only the second image
        assert len(images) == 1
        assert images[0]['image_id'] == 'IMG-001-01'
        assert images[0]['ai_description'] == 'Valid image'

        # Should log warning
        mock_logger.warning.assert_called_once()

    @patch('src.agents.image_reader.image_extractor.fitz')
    @patch('src.agents.image_reader.image_extractor.ImageCaptioner')
    def test_caption_generation_integration(self, mock_captioner, mock_fitz):
        """Test that AI caption generation is called correctly"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_fitz.open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page

        mock_page.get_images.return_value = [
            (1234, 0, 100, 100, 0, '', '', '', '')
        ]

        test_image = Image.new('RGB', (100, 100), color='white')
        img_bytes = BytesIO()
        test_image.save(img_bytes, format='PNG')
        mock_doc.extract_image.return_value = {'image': img_bytes.getvalue()}

        mock_captioner.generate_caption.return_value = ('Test caption', 90.0)

        from src.agents.image_reader.image_extractor import ImageReaderAgent

        agent = ImageReaderAgent()
        images = agent.extract_images('/path/to/file.pdf', 1)

        # Verify caption was generated
        assert mock_captioner.generate_caption.call_count == 1
        call_args = mock_captioner.generate_caption.call_args[0]
        assert isinstance(call_args[0], Image.Image)

        assert images[0]['ai_description'] == 'Test caption'
        assert images[0]['confidence_score'] == 90.0

    def test_image_classification_chart(self):
        """Test classification of chart images"""
        from src.agents.image_reader.image_extractor import ImageReaderAgent

        agent = ImageReaderAgent()
        test_image = Image.new('RGB', (100, 100), color='white')

        # Test chart keywords
        img_type1 = agent._classify_image_type(test_image, "A bar chart showing data")
        assert img_type1 == 'chart'

        img_type2 = agent._classify_image_type(test_image, "Pie chart with percentages")
        assert img_type2 == 'chart'

        img_type3 = agent._classify_image_type(test_image, "Line graph of temperature")
        assert img_type3 == 'chart'

    def test_image_classification_diagram(self):
        """Test classification of diagram images"""
        from src.agents.image_reader.image_extractor import ImageReaderAgent

        agent = ImageReaderAgent()
        test_image = Image.new('RGB', (100, 100), color='white')

        # Test diagram keywords
        img_type1 = agent._classify_image_type(test_image, "A diagram showing connections")
        assert img_type1 == 'diagram'

        img_type2 = agent._classify_image_type(test_image, "Schematic of circuit")
        assert img_type2 == 'diagram'

        # Test aspect ratio for diagram (very wide)
        wide_image = Image.new('RGB', (300, 100), color='white')
        img_type3 = agent._classify_image_type(wide_image, "")
        assert img_type3 == 'diagram'

    def test_image_classification_photo(self):
        """Test classification of photo images"""
        from src.agents.image_reader.image_extractor import ImageReaderAgent

        agent = ImageReaderAgent()
        test_image = Image.new('RGB', (100, 100), color='white')

        # Test photo keywords
        img_type1 = agent._classify_image_type(test_image, "A photo of a person")
        assert img_type1 == 'photo'

        img_type2 = agent._classify_image_type(test_image, "Picture of a landscape")
        assert img_type2 == 'photo'

    def test_image_classification_other(self):
        """Test classification fallback to 'other'"""
        from src.agents.image_reader.image_extractor import ImageReaderAgent

        agent = ImageReaderAgent()
        test_image = Image.new('RGB', (100, 100), color='white')

        # No keywords, normal aspect ratio
        img_type = agent._classify_image_type(test_image, "Unknown content")
        assert img_type == 'other'

    @patch('src.agents.image_reader.image_extractor.fitz')
    @patch('src.agents.image_reader.image_extractor.ImageCaptioner')
    def test_image_id_format(self, mock_captioner, mock_fitz):
        """Test image ID format is correct"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_fitz.open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page

        mock_page.get_images.return_value = [
            (1234, 0, 100, 100, 0, '', '', '', '')
        ]

        test_image = Image.new('RGB', (100, 100), color='white')
        img_bytes = BytesIO()
        test_image.save(img_bytes, format='PNG')
        mock_doc.extract_image.return_value = {'image': img_bytes.getvalue()}
        mock_captioner.generate_caption.return_value = ('Test', 80.0)

        from src.agents.image_reader.image_extractor import ImageReaderAgent

        agent = ImageReaderAgent()

        # Test page 1, image 0
        images1 = agent.extract_images('/path/to/file.pdf', 1)
        assert images1[0]['image_id'] == 'IMG-001-00'

        # Test page 15, image 0
        images2 = agent.extract_images('/path/to/file.pdf', 15)
        assert images2[0]['image_id'] == 'IMG-015-00'
