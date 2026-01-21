"""
Diagram Analyzer Service

Analyzes diagrams using Claude Vision API to:
1. Extract text labels from diagrams
2. Identify diagram type (flowchart, hierarchy, graph, table, etc.)
3. Describe diagram structure and relationships
4. Generate structured JSON analysis

Also uses Surya OCR for text extraction as a fallback/supplement.
"""

import base64
import json
from typing import Dict, Any, Optional
from src.utils.logging_config import logger
from src.config import settings

# Load API key from settings
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY


def analyze_diagram_with_claude(image_bytes: bytes, additional_context: str = "", custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Send diagram image to Claude Vision API for comprehensive analysis.

    Args:
        image_bytes: Raw image bytes (PNG/JPEG format)
        additional_context: Optional context about the diagram (e.g., book subject)

    Returns:
        dict: {
            'success': bool,
            'description': str,  # Human-readable description
            'diagram_type': str,  # flowchart, hierarchy, table, graph, etc.
            'components': list,  # List of identified components
            'relationships': list,  # List of relationships between components
            'text_labels': list,  # Text labels found in diagram
            'structured_json': dict,  # Full structured analysis
            'model': str,  # Model used
            'error': str (only if success=False)
        }
    """
    import anthropic

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == 'your-api-key-here':
        logger.warning("ANTHROPIC_API_KEY not configured, skipping Claude Vision analysis")
        return {
            'success': False,
            'description': '',
            'diagram_type': 'unknown',
            'components': [],
            'relationships': [],
            'text_labels': [],
            'structured_json': {},
            'model': 'none',
            'error': 'ANTHROPIC_API_KEY not configured. Please add your API key to .env file.'
        }

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Encode image to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Determine media type (assume PNG, but could detect from bytes)
        media_type = "image/png"
        if image_bytes[:2] == b'\xff\xd8':
            media_type = "image/jpeg"


        # Build context string
        context_str = ""
        if additional_context:
            context_str = f"\n\nAdditional context: {additional_context}"

        # Use custom prompt if provided, otherwise use default
        if custom_prompt:
            # Custom prompt from book settings
            analysis_prompt = f"{custom_prompt}{context_str}"
        else:
            # Default comprehensive prompt
            analysis_prompt = f"""Analyze this diagram image and provide a comprehensive analysis.

Please identify and describe:

1. **Diagram Type**: What kind of diagram is this? (e.g., flowchart, hierarchy/tree, organizational chart, process diagram, data flow diagram, UML diagram, network diagram, Venn diagram, pie chart, bar chart, table, mind map, timeline, other)

2. **Components**: List all distinct components/elements visible in the diagram (boxes, nodes, shapes, labels, etc.)

3. **Relationships**: Describe how components are connected or related (arrows, lines, containment, etc.)

4. **Text Labels**: Extract ALL text visible in the diagram, including labels, titles, annotations, numbers, etc.)

5. **Summary Description**: Provide a clear, concise description of what this diagram represents and the information it conveys.
{context_str}

Please respond in JSON format with the following structure:
{{
    "diagram_type": "type of diagram",
    "components": ["component1", "component2", ...],
    "relationships": ["relationship1", "relationship2", ...],
    "text_labels": ["text1", "text2", ...],
    "summary": "A comprehensive description of the diagram",
    "key_information": ["key point 1", "key point 2", ...]
}}"""

        logger.info("Sending diagram to Claude Vision API for analysis...")

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": analysis_prompt
                        }
                    ]
                }
            ]
        )

        # Extract response text
        response_text = message.content[0].text
        logger.info(f"Claude Vision response received ({len(response_text)} chars)")

        # Try to parse as JSON
        try:
            # Find JSON in response (it might be wrapped in markdown code blocks)
            json_str = response_text
            if '```json' in response_text:
                json_str = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                json_str = response_text.split('```')[1].split('```')[0].strip()

            structured_data = json.loads(json_str)

            return {
                'success': True,
                'description': structured_data.get('summary', ''),
                'diagram_type': structured_data.get('diagram_type', 'unknown'),
                'components': structured_data.get('components', []),
                'relationships': structured_data.get('relationships', []),
                'text_labels': structured_data.get('text_labels', []),
                'structured_json': structured_data,
                'model': 'claude-sonnet-4-20250514'
            }

        except json.JSONDecodeError:
            # If JSON parsing fails, use the raw text as description
            logger.warning("Could not parse Claude response as JSON, using raw text")
            return {
                'success': True,
                'description': response_text,
                'diagram_type': 'unknown',
                'components': [],
                'relationships': [],
                'text_labels': [],
                'structured_json': {'raw_response': response_text},
                'model': 'claude-sonnet-4-20250514'
            }

    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        return {
            'success': False,
            'description': '',
            'diagram_type': 'unknown',
            'components': [],
            'relationships': [],
            'text_labels': [],
            'structured_json': {},
            'model': 'none',
            'error': f'Claude API error: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Error analyzing diagram with Claude: {e}", exc_info=True)
        return {
            'success': False,
            'description': '',
            'diagram_type': 'unknown',
            'components': [],
            'relationships': [],
            'text_labels': [],
            'structured_json': {},
            'model': 'none',
            'error': str(e)
        }


def extract_text_with_surya(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract text from diagram using Surya OCR.

    This provides a fallback/supplement to Claude Vision for text extraction.

    Args:
        image_bytes: Raw image bytes

    Returns:
        dict: {
            'success': bool,
            'text': str,
            'confidence': float,
            'error': str (only if success=False)
        }
    """
    try:
        from src.services.ocr_sequential import run_surya_on_single_image

        result = run_surya_on_single_image(image_bytes)
        return result

    except Exception as e:
        logger.error(f"Error extracting text with Surya: {e}")
        return {
            'success': False,
            'text': '',
            'confidence': 0.0,
            'error': str(e)
        }


def analyze_diagram_full(
    image_bytes: bytes,
    use_claude: bool = True,
    use_surya: bool = True,
    additional_context: str = "",
    custom_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform full diagram analysis combining Claude Vision and Surya OCR.

    Args:
        image_bytes: Raw image bytes
        use_claude: Whether to use Claude Vision for analysis
        use_surya: Whether to use Surya OCR for text extraction
        additional_context: Optional context about the diagram

    Returns:
        dict: Combined analysis results
    """
    result = {
        'success': False,
        'description': '',
        'diagram_type': 'unknown',
        'extracted_text': '',
        'ocr_confidence': 0.0,
        'components': [],
        'relationships': [],
        'text_labels': [],
        'structured_json': {},
        'ai_model': 'none',
        'error': None
    }

    # Step 1: Extract text with Surya OCR
    if use_surya:
        logger.info("Step 1: Extracting text with Surya OCR...")
        surya_result = extract_text_with_surya(image_bytes)

        if surya_result.get('success'):
            result['extracted_text'] = surya_result.get('text', '')
            result['ocr_confidence'] = surya_result.get('confidence', 0.0)
            logger.info(f"Surya OCR extracted {len(result['extracted_text'])} chars")
        else:
            logger.warning(f"Surya OCR failed: {surya_result.get('error')}")

    # Step 2: Analyze with Claude Vision
    if use_claude:
        logger.info("Step 2: Analyzing with Claude Vision...")
        claude_result = analyze_diagram_with_claude(image_bytes, additional_context, custom_prompt)

        if claude_result.get('success'):
            result['success'] = True
            result['description'] = claude_result.get('description', '')
            result['diagram_type'] = claude_result.get('diagram_type', 'unknown')
            result['components'] = claude_result.get('components', [])
            result['relationships'] = claude_result.get('relationships', [])
            result['text_labels'] = claude_result.get('text_labels', [])
            result['structured_json'] = claude_result.get('structured_json', {})
            result['ai_model'] = claude_result.get('model', 'none')
            logger.info(f"Claude Vision analysis complete: {result['diagram_type']}")
        else:
            error_msg = claude_result.get('error', 'Unknown error')
            logger.warning(f"Claude Vision failed: {error_msg}")
            result['error'] = error_msg

            # If Claude failed but we have OCR text, still mark as partial success
            if result['extracted_text']:
                result['success'] = True
                result['description'] = f"OCR extracted text: {result['extracted_text']}"
                result['ai_model'] = 'surya-ocr-only'
    else:
        # Only using Surya OCR
        if result['extracted_text']:
            result['success'] = True
            result['description'] = f"OCR extracted text: {result['extracted_text']}"
            result['ai_model'] = 'surya-ocr-only'

    return result


def format_diagram_description(analysis_result: Dict[str, Any]) -> str:
    """
    Format the analysis result into a human-readable description.

    Args:
        analysis_result: Result from analyze_diagram_full()

    Returns:
        str: Formatted description
    """
    parts = []

    if analysis_result.get('diagram_type') and analysis_result['diagram_type'] != 'unknown':
        parts.append(f"**Diagram Type:** {analysis_result['diagram_type']}")

    if analysis_result.get('description'):
        parts.append(f"\n**Description:**\n{analysis_result['description']}")

    if analysis_result.get('components'):
        components_str = ', '.join(analysis_result['components'][:10])  # Limit to 10
        if len(analysis_result['components']) > 10:
            components_str += f"... (+{len(analysis_result['components']) - 10} more)"
        parts.append(f"\n**Components:** {components_str}")

    if analysis_result.get('text_labels'):
        labels_str = ', '.join(analysis_result['text_labels'][:15])  # Limit to 15
        if len(analysis_result['text_labels']) > 15:
            labels_str += f"... (+{len(analysis_result['text_labels']) - 15} more)"
        parts.append(f"\n**Text Labels:** {labels_str}")

    if analysis_result.get('extracted_text'):
        ocr_text = analysis_result['extracted_text'][:500]  # Limit to 500 chars
        if len(analysis_result['extracted_text']) > 500:
            ocr_text += "..."
        parts.append(f"\n**OCR Text:**\n{ocr_text}")

    return '\n'.join(parts) if parts else "No analysis available."
