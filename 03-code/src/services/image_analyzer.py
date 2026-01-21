"""
Claude Sonnet 4.5 Image Analysis Service

Analyzes images using Claude Sonnet 4.5 API for comprehensive description
and structured data extraction for SVG generation.

Aligned with sequential-ocr-svg-processing.md architecture.
"""

import json
from typing import Dict, Any, Optional
import base64
from src.utils.logging_config import logger

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK not available - Claude image analysis disabled")


CLAUDE_COMPREHENSIVE_IMAGE_ANALYSIS_PROMPT = """
Analyze this image comprehensively. It may be a diagram, flowchart, screenshot, photo,
technical illustration, chart, graph, table, or any other visual content from a document.

Your analysis should be detailed enough to allow SVG reconstruction of the image.

Please provide:

1. **Image Type Classification:**
   Identify the primary type from: diagram, flowchart, architecture_diagram, UML_diagram,
   network_diagram, process_flow, mind_map, screenshot, photo, bar_chart, line_graph,
   pie_chart, table, technical_illustration, schematic, other

2. **Human-Readable Description:**
   Provide a comprehensive textual description that captures:
   - What the image shows (main subject/purpose)
   - All visible elements and their arrangement
   - All text content and labels
   - Colors, styles, and visual characteristics
   - Spatial relationships between elements
   - Any notable details or annotations

   This description should be detailed enough that someone could understand the
   image's content and purpose without seeing it.

3. **Structured Data for SVG Generation:**
   Provide a JSON object with this structure:

   {
     "diagram_type": "string (from classification above)",
     "layout": {
       "estimated_width": number (pixels),
       "estimated_height": number (pixels),
       "orientation": "landscape" | "portrait" | "square",
       "background_color": "#hex or 'transparent'"
     },
     "elements": [
       {
         "id": "unique_element_id",
         "type": "rectangle" | "circle" | "ellipse" | "polygon" | "line" | "arrow" | "text" | "image" | "path",
         "position": {"x": number, "y": number},
         "size": {"width": number, "height": number} (for shapes),
         "radius": number (for circles),
         "points": [{"x": number, "y": number}, ...] (for polygons/paths),
         "text_content": "string" (if element contains text),
         "style": {
           "fill": "#color or 'none'",
           "stroke": "#color",
           "stroke_width": number,
           "font_size": number (for text),
           "font_family": "string" (for text),
           "font_weight": "normal" | "bold",
           "text_anchor": "start" | "middle" | "end",
           "opacity": number (0-1)
         },
         "children": [] (nested elements if applicable)
       }
     ],
     "connections": [
       {
         "id": "unique_connection_id",
         "from_element": "element_id",
         "to_element": "element_id",
         "type": "arrow" | "line" | "double_arrow" | "dashed_arrow",
         "label": "connection label text (optional)",
         "label_position": "middle" | "start" | "end",
         "style": {
           "stroke": "#color",
           "stroke_width": number,
           "stroke_dasharray": "5,5" (for dashed lines, optional),
           "marker_end": "arrow" | "circle" | "none"
         }
       }
     ],
     "text_labels": [
       {
         "content": "standalone text content",
         "position": {"x": number, "y": number},
         "style": {
           "font_size": number,
           "font_family": "string",
           "font_weight": "normal" | "bold",
           "fill": "#color"
         }
       }
     ],
     "additional_details": {
       "title": "diagram title (if present)",
       "legend_items": ["item1", "item2"],
       "notes": "any annotations or notes",
       "data_values": {} (for charts/graphs - key data points)
     }
   }

For non-diagram images (photos, screenshots without diagrams):
- Provide best-effort structured data describing key regions and visual elements
- Focus on layout, text content, and identifiable components

**IMPORTANT:** Return ONLY valid JSON in this exact format:
{
  "image_type": "...",
  "description": "...",
  "structured_json": { ... }
}

Do not include any explanatory text outside the JSON structure.
"""


class ClaudeImageAnalyzer:
    """Analyze images using Claude Sonnet 4.5 API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude image analyzer.

        Args:
            api_key: Anthropic API key (if None, reads from environment)
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic SDK not installed. Run: pip install anthropic")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

    def analyze_image(
        self,
        image_data: bytes,
        image_type_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze image using Claude Sonnet 4.5 API.

        Args:
            image_data: Image binary data
            image_type_hint: Optional hint about image type (e.g., "diagram", "photo")

        Returns:
            Dict with keys:
                - image_type: Classified image type
                - description: Human-readable description
                - structured_json: Structured data for SVG generation
                - confidence_score: Confidence in analysis (0-100)

        Raises:
            Exception: If API call fails
        """
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # Prepare message
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",  # Adjust if needed
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": CLAUDE_COMPREHENSIVE_IMAGE_ANALYSIS_PROMPT
                            }
                        ]
                    }
                ]
            )

            # Extract response
            response_text = message.content[0].text

            # Parse JSON response
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_text = response_text[json_start:json_end].strip()
                    result = json.loads(json_text)
                else:
                    raise ValueError(f"Failed to parse JSON from Claude response: {response_text[:200]}")

            # Validate required fields
            if "image_type" not in result or "description" not in result or "structured_json" not in result:
                raise ValueError(f"Missing required fields in Claude response: {result.keys()}")

            # Add confidence score (placeholder - could be enhanced)
            result["confidence_score"] = 85.0

            logger.info(f"Image analyzed successfully: type={result['image_type']}")
            return result

        except Exception as e:
            logger.error(f"Claude image analysis failed: {e}")
            raise


# Singleton instance (will be initialized with API key when needed)
_image_analyzer: Optional[ClaudeImageAnalyzer] = None


def get_image_analyzer(api_key: Optional[str] = None) -> ClaudeImageAnalyzer:
    """
    Get or create Claude image analyzer singleton.

    Args:
        api_key: Anthropic API key (if None, reads from environment)

    Returns:
        ClaudeImageAnalyzer instance
    """
    global _image_analyzer
    if _image_analyzer is None:
        _image_analyzer = ClaudeImageAnalyzer(api_key=api_key)
    return _image_analyzer
