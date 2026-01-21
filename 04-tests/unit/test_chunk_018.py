"""
Unit tests for CHUNK-018: BLIP Image Captioning

Tests blip image captioning functionality.

Test Coverage:
- Model loading
- Caption generation
- Confidence calculation
- Multiple images
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image


class TestChunk018BLIPImageCaptioning:
    """Test suite for CHUNK-018: BLIP Image Captioning"""

    def setup_method(self):
        """Reset singleton before each test"""
        from src.agents.image_reader.image_captioner import ImageCaptioner
        ImageCaptioner.reset_model()

    @patch('src.agents.image_reader.image_captioner.BlipProcessor.from_pretrained')
    @patch('src.agents.image_reader.image_captioner.BlipForConditionalGeneration.from_pretrained')
    @patch('src.agents.image_reader.image_captioner.logger')
    def test_happy_path_model_loading(self, mock_logger, mock_model_pretrained, mock_proc_pretrained):
        """Test model loading"""
        mock_processor = Mock()
        mock_model = Mock()
        mock_proc_pretrained.return_value = mock_processor
        mock_model_pretrained.return_value = mock_model

        from src.agents.image_reader.image_captioner import ImageCaptioner

        processor, model = ImageCaptioner.get_model()

        assert processor == mock_processor
        assert model == mock_model
        mock_logger.info.assert_called()
        mock_proc_pretrained.assert_called_once()
        mock_model_pretrained.assert_called_once()

    @patch('src.agents.image_reader.image_captioner.BlipProcessor.from_pretrained')
    @patch('src.agents.image_reader.image_captioner.BlipForConditionalGeneration.from_pretrained')
    def test_singleton_pattern(self, mock_model_pretrained, mock_proc_pretrained):
        """Test that model is loaded only once (singleton)"""
        mock_processor = Mock()
        mock_model = Mock()
        mock_proc_pretrained.return_value = mock_processor
        mock_model_pretrained.return_value = mock_model

        from src.agents.image_reader.image_captioner import ImageCaptioner

        # Call get_model twice
        proc1, model1 = ImageCaptioner.get_model()
        proc2, model2 = ImageCaptioner.get_model()

        # Should be same instances
        assert proc1 is proc2
        assert model1 is model2
        # Should be called only once
        assert mock_proc_pretrained.call_count == 1
        assert mock_model_pretrained.call_count == 1

    @patch('src.agents.image_reader.image_captioner.BlipProcessor.from_pretrained')
    @patch('src.agents.image_reader.image_captioner.BlipForConditionalGeneration.from_pretrained')
    def test_caption_generation(self, mock_model_pretrained, mock_proc_pretrained):
        """Test caption generation"""
        mock_processor = Mock()
        mock_model = Mock()
        mock_proc_pretrained.return_value = mock_processor
        mock_model_pretrained.return_value = mock_model

        # Mock processor behavior
        mock_processor.return_value = {"pixel_values": Mock()}
        mock_model.generate.return_value = [Mock()]
        mock_processor.decode.return_value = "A beautiful landscape"

        from src.agents.image_reader.image_captioner import ImageCaptioner

        test_image = Mock(spec=Image.Image)
        caption, confidence = ImageCaptioner.generate_caption(test_image)

        assert caption == "A beautiful landscape"
        assert 0.0 <= confidence <= 100.0
        mock_processor.assert_called_with(test_image, return_tensors="pt")
        mock_model.generate.assert_called_once()
        mock_processor.decode.assert_called_once()

    @patch('src.agents.image_reader.image_captioner.BlipProcessor.from_pretrained')
    @patch('src.agents.image_reader.image_captioner.BlipForConditionalGeneration.from_pretrained')
    def test_confidence_calculation(self, mock_model_pretrained, mock_proc_pretrained):
        """Test confidence calculation"""
        mock_processor = Mock()
        mock_model = Mock()
        mock_proc_pretrained.return_value = mock_processor
        mock_model_pretrained.return_value = mock_model

        mock_processor.return_value = {"pixel_values": Mock()}
        mock_model.generate.return_value = [Mock()]
        mock_processor.decode.return_value = "Test caption"

        from src.agents.image_reader.image_captioner import ImageCaptioner

        test_image = Mock(spec=Image.Image)
        _, confidence = ImageCaptioner.generate_caption(test_image)

        # Confidence should be in valid range
        assert 0.0 <= confidence <= 100.0
        assert isinstance(confidence, float)

    @patch('src.agents.image_reader.image_captioner.BlipProcessor.from_pretrained')
    @patch('src.agents.image_reader.image_captioner.BlipForConditionalGeneration.from_pretrained')
    def test_model_name(self, mock_model_pretrained, mock_proc_pretrained):
        """Test that correct model name is used"""
        mock_processor = Mock()
        mock_model = Mock()
        mock_proc_pretrained.return_value = mock_processor
        mock_model_pretrained.return_value = mock_model

        from src.agents.image_reader.image_captioner import ImageCaptioner

        ImageCaptioner.get_model()

        # Verify model name
        proc_call_args = mock_proc_pretrained.call_args[0]
        model_call_args = mock_model_pretrained.call_args[0]
        assert proc_call_args[0] == "Salesforce/blip-image-captioning-base"
        assert model_call_args[0] == "Salesforce/blip-image-captioning-base"

    @patch('src.agents.image_reader.image_captioner.BlipProcessor.from_pretrained')
    @patch('src.agents.image_reader.image_captioner.BlipForConditionalGeneration.from_pretrained')
    @patch('src.agents.image_reader.image_captioner.settings')
    def test_cache_directory(self, mock_settings, mock_model_pretrained, mock_proc_pretrained):
        """Test that cache directory from settings is used"""
        mock_settings.MODEL_CACHE_DIR = '/test/cache/dir'
        mock_processor = Mock()
        mock_model = Mock()
        mock_proc_pretrained.return_value = mock_processor
        mock_model_pretrained.return_value = mock_model

        from src.agents.image_reader.image_captioner import ImageCaptioner

        ImageCaptioner.get_model()

        # Verify cache_dir was passed
        proc_call_kwargs = mock_proc_pretrained.call_args[1]
        model_call_kwargs = mock_model_pretrained.call_args[1]
        assert proc_call_kwargs['cache_dir'] == '/test/cache/dir'
        assert model_call_kwargs['cache_dir'] == '/test/cache/dir'

    @patch('src.agents.image_reader.image_captioner.BlipProcessor.from_pretrained')
    @patch('src.agents.image_reader.image_captioner.BlipForConditionalGeneration.from_pretrained')
    def test_reset_model(self, mock_model_pretrained, mock_proc_pretrained):
        """Test that reset_model clears singleton"""
        mock_proc1 = Mock()
        mock_model1 = Mock()
        mock_proc2 = Mock()
        mock_model2 = Mock()
        mock_proc_pretrained.side_effect = [mock_proc1, mock_proc2]
        mock_model_pretrained.side_effect = [mock_model1, mock_model2]

        from src.agents.image_reader.image_captioner import ImageCaptioner

        # Load model
        proc1, model1 = ImageCaptioner.get_model()
        assert proc1 == mock_proc1
        assert model1 == mock_model1

        # Reset
        ImageCaptioner.reset_model()

        # Load again - should create new instances
        proc2, model2 = ImageCaptioner.get_model()
        assert proc2 == mock_proc2
        assert model2 == mock_model2
        assert proc1 is not proc2
        assert model1 is not model2
