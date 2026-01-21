"""
Diagram Context Builder for Phase 6

Provides context building and custom prompt selection for diagram processing.
Integrates sequential OCR texts and manual texts into Claude API pipeline.

PIPELINE EXECUTION NOTE:
- First step: Translate paragraphs to English
- Second step: Decode all diagrams with basic prompts before executing any further logic
"""

from typing import Dict, Any, Optional
from sqlalchemy import text
from src.database.connection import engine
from src.database.utils import get_table_name
import json
import logging

logger = logging.getLogger(__name__)

# Default prompts (same as claude_batch_service.py)
DEFAULT_PROMPTS = {
    "diagram": "Analyze this diagram and provide a detailed description of what it shows, including any labels, relationships, and key information conveyed.",
    "table": "Extract all data from this table in a structured format. Include column headers, row labels, and all cell values. Preserve the table structure.",
    "equation": "Identify and transcribe this mathematical equation or formula. Explain what it represents and define any variables used.",
    "list_bulleted": "Extract all items from this bulleted list. Preserve the hierarchy if there are nested items.",
    "list_numbered": "Extract all items from this numbered list in order. Preserve numbering and any sub-items.",
    "list_lettered": "Extract all items from this lettered list (a, b, c, etc.). Preserve the lettering sequence and any sub-items."
}


def get_extraction_prompts(book_id: int) -> Dict[str, str]:
    """
    Fetch extraction prompts from auto_slicer_config (unified prompt storage).

    Args:
        book_id: Book ID

    Returns:
        Dictionary of prompts by type (diagram, table, equation, list_*)
    """
    sql = text("""
        SELECT auto_slicer_config
        FROM books_metadata
        WHERE book_id = :book_id
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"book_id": book_id})
        row = result.fetchone()

        if row is None or not row[0]:
            return DEFAULT_PROMPTS.copy()

        config = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        prompts = DEFAULT_PROMPTS.copy()

        # Override with custom prompts if set
        custom_prompts = config.get('extraction_prompts', {})
        for key, value in custom_prompts.items():
            if value:  # Only override if not empty
                prompts[key] = value

        return prompts


def build_diagram_context(
    entity_type: str,
    input_data: Dict[str, Any]
) -> Optional[str]:
    """
    Build context string from sequential OCR and manual texts for diagrams.

    Args:
        entity_type: 'diagram' or 'paragraph'
        input_data: Entity data from database

    Returns:
        Context string or None if no sequential texts
    """
    if entity_type != "diagram":
        return None

    # Collect all sequential texts
    texts = []

    # OCR texts (from rectangle extractions)
    for i in range(1, 4):
        key = f"ocr_text_{i}"
        if input_data.get(key):
            texts.append(f"OCR Area {i}: {input_data[key]}")

    # Manual texts (user-typed)
    for i in range(1, 4):
        key = f"manual_text_{i}"
        if input_data.get(key):
            texts.append(f"Manual Text {i}: {input_data[key]}")

    if not texts:
        return None

    # Build context string
    context = "\n\nAdditional Context:\n" + "\n".join(texts)

    logger.info(f"Built diagram context with {len(texts)} text(s)")

    return context


def get_custom_prompt_for_diagram(
    book_id: int,
    prompt_type: Optional[str]
) -> Optional[str]:
    """
    Get custom prompt based on diagram type from extraction_prompts.

    Args:
        book_id: Book ID
        prompt_type: 'diagram', 'equation', 'table', 'list_bulleted', 'list_numbered', 'list_lettered'

    Returns:
        Custom prompt or default prompt for the type
    """
    valid_types = ['diagram', 'equation', 'table', 'list_bulleted', 'list_numbered', 'list_lettered']

    if not prompt_type or prompt_type not in valid_types:
        return None

    prompts = get_extraction_prompts(book_id)
    prompt = prompts.get(prompt_type)

    if prompt:
        logger.info(f"Using {prompt_type} prompt for book {book_id}")
        return prompt

    return DEFAULT_PROMPTS.get(prompt_type)


def enhance_prompt_with_context(
    base_prompt: str,
    context: Optional[str],
    custom_prompt: Optional[str]
) -> str:
    """
    Enhance base prompt with context and custom prompt.

    Args:
        base_prompt: Original template-substituted prompt
        context: Additional context from sequential texts
        custom_prompt: Custom prompt from book settings

    Returns:
        Enhanced prompt string
    """
    enhanced = base_prompt

    # Add context if available
    if context:
        enhanced = enhanced + context

    # Prepend custom prompt if available
    if custom_prompt:
        enhanced = f"{custom_prompt}\n\n{enhanced}"

    return enhanced
