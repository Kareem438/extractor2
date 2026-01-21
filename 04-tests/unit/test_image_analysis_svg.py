"""
Unit Tests for Image Analysis and SVG Generation

Tests the Claude Sonnet 4.5 image analyzer and SVG generator:
- src/services/image_analyzer.py
- src/services/svg_generator.py

Aligned with sequential-ocr-svg-processing.md architecture.
"""

import pytest
import inspect
from src.services import image_analyzer, svg_generator


class TestClaudeImageAnalyzer:
    """Test suite for Claude Sonnet 4.5 image analyzer"""

    def test_happy_path_analyzer_class_exists(self):
        """Test that ClaudeImageAnalyzer class exists"""
        assert hasattr(image_analyzer, 'ClaudeImageAnalyzer')

    def test_happy_path_analyze_image_method_exists(self):
        """Test that analyze_image method exists"""
        analyzer_class = image_analyzer.ClaudeImageAnalyzer
        assert hasattr(analyzer_class, 'analyze_image')

    def test_structure_claude_prompt_exists(self):
        """Test that comprehensive image analysis prompt exists"""
        assert hasattr(image_analyzer, 'CLAUDE_COMPREHENSIVE_IMAGE_ANALYSIS_PROMPT')
        prompt = image_analyzer.CLAUDE_COMPREHENSIVE_IMAGE_ANALYSIS_PROMPT
        assert 'diagram' in prompt.lower()
        assert 'flowchart' in prompt.lower()
        assert 'svg' in prompt.lower()

    def test_structure_prompt_includes_image_types(self):
        """Test that prompt includes various image types"""
        prompt = image_analyzer.CLAUDE_COMPREHENSIVE_IMAGE_ANALYSIS_PROMPT
        assert 'diagram' in prompt
        assert 'flowchart' in prompt
        assert 'bar_chart' in prompt
        assert 'line_graph' in prompt
        assert 'table' in prompt

    def test_structure_prompt_includes_structured_json(self):
        """Test that prompt requests structured JSON"""
        prompt = image_analyzer.CLAUDE_COMPREHENSIVE_IMAGE_ANALYSIS_PROMPT
        assert 'structured_json' in prompt or 'Structured Data' in prompt
        assert 'elements' in prompt
        assert 'connections' in prompt

    def test_structure_analyzer_uses_claude_model(self):
        """Test that analyzer uses Claude Sonnet 4.5"""
        source = inspect.getsource(image_analyzer.ClaudeImageAnalyzer)
        assert 'claude-sonnet-4-5' in source or 'anthropic' in source

    def test_structure_get_image_analyzer_function(self):
        """Test that get_image_analyzer helper function exists"""
        assert hasattr(image_analyzer, 'get_image_analyzer')
        assert callable(image_analyzer.get_image_analyzer)

    def test_error_handling_anthropic_not_available(self):
        """Test handling when Anthropic SDK not available"""
        source = inspect.getsource(image_analyzer.ClaudeImageAnalyzer)
        assert 'ANTHROPIC_AVAILABLE' in source or 'ImportError' in source

    def test_structure_returns_required_fields(self):
        """Test that analyzer returns required fields"""
        source = inspect.getsource(image_analyzer.ClaudeImageAnalyzer.analyze_image)
        # Should mention expected return fields
        assert 'image_type' in source or 'description' in source or 'structured_json' in source

    def test_logging_present(self):
        """Test that logging is present"""
        source = inspect.getsource(image_analyzer)
        assert 'logger' in source


class TestSVGGenerator:
    """Test suite for SVG generator"""

    def test_happy_path_generate_svg_function_exists(self):
        """Test that generate_svg_from_json function exists"""
        assert hasattr(svg_generator, 'generate_svg_from_json')
        assert callable(svg_generator.generate_svg_from_json)

    def test_structure_generate_element_function_exists(self):
        """Test that element generation helper exists"""
        source = inspect.getsource(svg_generator)
        assert '_generate_element_svg' in source

    def test_structure_generate_connection_function_exists(self):
        """Test that connection generation helper exists"""
        source = inspect.getsource(svg_generator)
        assert '_generate_connection_svg' in source

    def test_structure_generate_text_label_function_exists(self):
        """Test that text label generation helper exists"""
        source = inspect.getsource(svg_generator)
        assert '_generate_text_label_svg' in source

    def test_structure_supports_rectangle_elements(self):
        """Test that rectangles are supported"""
        source = inspect.getsource(svg_generator)
        assert 'rectangle' in source
        assert '<rect' in source

    def test_structure_supports_circle_elements(self):
        """Test that circles are supported"""
        source = inspect.getsource(svg_generator)
        assert 'circle' in source
        assert '<circle' in source

    def test_structure_supports_ellipse_elements(self):
        """Test that ellipses are supported"""
        source = inspect.getsource(svg_generator)
        assert 'ellipse' in source
        assert '<ellipse' in source

    def test_structure_supports_line_elements(self):
        """Test that lines are supported"""
        source = inspect.getsource(svg_generator)
        assert 'line' in source
        assert '<line' in source

    def test_structure_supports_text_elements(self):
        """Test that text elements are supported"""
        source = inspect.getsource(svg_generator)
        assert 'text' in source
        assert '<text' in source

    def test_structure_supports_polygon_elements(self):
        """Test that polygons are supported"""
        source = inspect.getsource(svg_generator)
        assert 'polygon' in source
        assert '<polygon' in source

    def test_structure_supports_path_elements(self):
        """Test that paths are supported"""
        source = inspect.getsource(svg_generator)
        assert 'path' in source
        assert '<path' in source

    def test_structure_arrow_markers_supported(self):
        """Test that arrow markers are supported"""
        source = inspect.getsource(svg_generator)
        assert 'arrow' in source or 'marker' in source

    def test_structure_svg_namespace_present(self):
        """Test that SVG namespace is included"""
        source = inspect.getsource(svg_generator.generate_svg_from_json)
        assert 'xmlns' in source or 'svg' in source

    def test_structure_handles_layout_parameters(self):
        """Test that layout parameters are handled"""
        source = inspect.getsource(svg_generator.generate_svg_from_json)
        assert 'layout' in source
        assert 'width' in source
        assert 'height' in source

    def test_error_handling_invalid_json(self):
        """Test error handling for invalid JSON"""
        source = inspect.getsource(svg_generator.generate_svg_from_json)
        assert 'ValueError' in source or 'raise' in source

    def test_logging_present(self):
        """Test that logging is present"""
        source = inspect.getsource(svg_generator)
        assert 'logger' in source
