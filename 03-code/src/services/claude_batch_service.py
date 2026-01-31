"""
Claude Batch Service (3B.9)

Handles Claude API integration for diagram/table/equation/list decoding:
- Message Batches API (50% cost, async processing)
- Direct API (immediate results, full cost)
- Result retrieval and database updates
- Multi-tag XML extraction (Requirement 7A)
- KU Grouping for batch processing (Requirement 7B)

PIPELINE EXECUTION NOTE:
- First step: Translate paragraphs to English
- Second step: Decode all diagrams with basic prompts before executing any further logic

Each diagram decode request includes:
- The diagram/table/equation/list image
- The parent paragraph text (for context)
- The appropriate prompt based on diagram type
"""

import json
import base64
import time
import re
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

import anthropic
from sqlalchemy import text

from src.database.connection import SessionLocal
from src.config import settings
from src.utils.logging_config import logger


# =============================================================================
# Multi-Tag XML Extraction (Requirement 7A)
# =============================================================================

def parse_multi_tag_response(
    response: str, 
    tag_mappings: List[Dict], 
    fallback_attr: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parse Claude response for multiple XML tags.
    
    Args:
        response: Claude's response text
        tag_mappings: List of {"tag_name": str, "target_attribute": str, "is_required": bool}
        fallback_attr: Attribute to store unmapped tags (e.g., "attr_20")
    
    Returns:
        {
            "extracted": {"attr_15": "summary content", "attr_16": "keywords"},
            "unmapped": {"unknown_tag": "content"},
            "missing_required": ["tag_name"],
            "is_complete": True/False
        }
    """
    extracted = {}
    unmapped = {}
    missing_required = []
    
    # Map tag names to attributes
    tag_to_attr = {m["tag_name"]: m["target_attribute"] for m in tag_mappings}
    required_tags = {m["tag_name"] for m in tag_mappings if m.get("is_required", False)}
    
    # Find all XML tags in response (handles multiline content)
    pattern = r'<(\w+)>(.*?)</\1>'
    matches = re.findall(pattern, response, re.DOTALL)
    
    found_tags = set()
    for tag_name, content in matches:
        found_tags.add(tag_name)
        if tag_name in tag_to_attr:
            extracted[tag_to_attr[tag_name]] = content.strip()
        else:
            unmapped[tag_name] = content.strip()
    
    # Check for missing required tags
    missing_required = list(required_tags - found_tags)
    
    # Store unmapped in fallback attribute if configured
    if unmapped and fallback_attr:
        extracted[fallback_attr] = json.dumps(unmapped)
    
    return {
        "extracted": extracted,
        "unmapped": unmapped,
        "missing_required": missing_required,
        "is_complete": len(missing_required) == 0
    }


def parse_grouped_response(
    response: str,
    ku_ids: List[int],
    tag_mappings: List[Dict],
    fallback_attr: Optional[str] = None
) -> Dict[int, Dict[str, Any]]:
    """
    Parse grouped Claude response and distribute to individual KUs.
    
    Response format:
        <ku_123>
            <summary>Generated summary...</summary>
            <keywords>keyword1, keyword2</keywords>
        </ku_123>
        <ku_124>
            <summary>Another summary...</summary>
        </ku_124>
    
    Args:
        response: Claude's grouped response
        ku_ids: List of KU IDs that were in the request
        tag_mappings: Tag-to-attribute mappings
        fallback_attr: Fallback attribute for unmapped tags
    
    Returns:
        {
            123: {"extracted": {...}, "is_complete": True},
            124: {"extracted": {...}, "is_complete": True},
            125: {"is_complete": False, "error": "Missing from response"}
        }
    """
    results = {}
    
    # Find all KU blocks in response
    ku_pattern = r'<ku_(\d+)>(.*?)</ku_\1>'
    ku_matches = re.findall(ku_pattern, response, re.DOTALL)
    
    found_ku_ids = set()
    for ku_id_str, ku_content in ku_matches:
        ku_id = int(ku_id_str)
        found_ku_ids.add(ku_id)
        
        # Parse tags within this KU block
        parsed = parse_multi_tag_response(ku_content, tag_mappings, fallback_attr)
        results[ku_id] = parsed
    
    # Mark missing KUs as incomplete
    for ku_id in ku_ids:
        if ku_id not in found_ku_ids:
            results[ku_id] = {
                "extracted": {},
                "unmapped": {},
                "missing_required": [],
                "is_complete": False,
                "error": "Missing from response"
            }
    
    return results


# =============================================================================
# Token Estimation
# =============================================================================

def estimate_tokens(text: str) -> int:
    """
    Estimate Claude tokens for text.
    Uses simple heuristic (~4 chars per token for English).
    For more accuracy, install tiktoken: pip install tiktoken
    """
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        # Fallback: ~4 chars per token
        return len(text) // 4


# =============================================================================
# Default Prompts (fallback if not configured)
# =============================================================================

DEFAULT_PROMPTS = {
    "diagram": "Analyze this diagram and provide a detailed description of what it shows, including any labels, relationships, and key information conveyed.",
    "table": "Extract all data from this table in a structured format. Include column headers, row labels, and all cell values. Preserve the table structure.",
    "equation": "Identify and transcribe this mathematical equation or formula. Explain what it represents and define any variables used.",
    "list_bulleted": "Extract all items from this bulleted list. Preserve the hierarchy if there are nested items.",
    "list_numbered": "Extract all items from this numbered list in order. Preserve numbering and any sub-items.",
    "list_lettered": "Extract all items from this lettered list (a, b, c, etc.). Preserve the lettering sequence and any sub-items.",
    "question": "Analyze this question image. Extract the full question text, identify any sub-questions or parts, and note any diagrams or figures referenced.",
    "answer": "Analyze this answer image. Extract the complete answer or solution, including any steps, explanations, formulas, or diagrams shown."
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_anthropic_client() -> anthropic.Anthropic:
    """Get Anthropic client instance."""
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured in .env file")
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def get_book_table_prefix(db, book_id: int) -> str:
    """Get the table prefix for a book."""
    result = db.execute(
        text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()

    if not result:
        raise ValueError(f"Book {book_id} not found")

    return result[0]


def get_extraction_prompts(db, book_id: int) -> Dict[str, str]:
    """Get extraction prompts for a book, with defaults."""
    result = db.execute(
        text("SELECT auto_slicer_config FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()

    prompts = {**DEFAULT_PROMPTS}

    if result and result[0]:
        config = result[0] if isinstance(result[0], dict) else json.loads(result[0])
        custom_prompts = config.get('extraction_prompts', {})
        prompts.update({k: v for k, v in custom_prompts.items() if v})

    return prompts


def save_batch_info(db, book_id: int, batch_id: str, status: str, diagram_count: int):
    """Save batch information to book config."""
    result = db.execute(
        text("SELECT auto_slicer_config FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()

    config = {}
    if result and result[0]:
        config = result[0] if isinstance(result[0], dict) else json.loads(result[0])

    config['last_batch_id'] = batch_id
    config['last_batch_status'] = status
    config['last_batch_started'] = datetime.now().isoformat()
    config['last_batch_diagram_count'] = diagram_count

    db.execute(
        text("UPDATE books_metadata SET auto_slicer_config = :config WHERE book_id = :book_id"),
        {"book_id": book_id, "config": json.dumps(config)}
    )
    db.commit()


def get_batch_info(db, book_id: int) -> Dict[str, Any]:
    """Get batch information from book config."""
    result = db.execute(
        text("SELECT auto_slicer_config FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()

    if not result or not result[0]:
        return {}

    config = result[0] if isinstance(result[0], dict) else json.loads(result[0])

    return {
        'batch_id': config.get('last_batch_id'),
        'status': config.get('last_batch_status'),
        'started': config.get('last_batch_started'),
        'diagram_count': config.get('last_batch_diagram_count', 0)
    }


# =============================================================================
# Batch API Functions
# =============================================================================

def submit_batch(book_id: int, diagram_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Submit visual elements for batch processing via Claude Message Batches API.

    Handles all visual classes: diagram, table, equation, list_*, question, answer.
    - diagram/table/equation/list: includes parent paragraph context
    - answer: includes parent question context

    Args:
        book_id: Book ID
        diagram_ids: Optional list of specific diagram IDs. If None, process all undecoded.

    Returns:
        Dictionary with batch_id and status
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        diagrams_table = f"raw_{prefix}_diagram_images"
        paragraphs_table = f"raw_{prefix}_paragraph_images"
        prompts = get_extraction_prompts(db, book_id)

        # Build query for visual elements to decode with parent context
        # - For diagram/table/equation/list: join with paragraph_images for parent paragraph text
        # - For answer: join with diagram_images itself for parent question text
        query = f"""
            SELECT d.id, d.image_data, d.diagram_type, d.page_number, d.level_3_title,
                   CASE
                       WHEN d.diagram_type = 'answer' THEN q.extracted_text
                       ELSE p.extracted_text
                   END as parent_text
            FROM {diagrams_table} d
            LEFT JOIN {paragraphs_table} p ON d.linked_knowledge_unit_id = p.id AND d.diagram_type != 'answer'
            LEFT JOIN {diagrams_table} q ON d.linked_knowledge_unit_id = q.id AND d.diagram_type = 'answer'
            WHERE d.analyzed_at IS NULL
        """

        if diagram_ids:
            query += f" AND d.id IN ({','.join(map(str, diagram_ids))})"

        query += " ORDER BY d.page_number, d.id"

        diagrams = db.execute(text(query)).fetchall()

        if not diagrams:
            return {"error": "No visual elements to decode", "batch_id": None}

        logger.info(f"Preparing batch for {len(diagrams)} visual elements")

        # Build batch requests
        requests = []
        for diagram in diagrams:
            diagram_id = diagram[0]
            image_data = diagram[1]
            diagram_type = diagram[2]
            page_number = diagram[3]
            l3_title = diagram[4]
            parent_text = diagram[5]  # Parent context (paragraph or question)

            # Get base prompt for this diagram type
            base_prompt = prompts.get(diagram_type, prompts.get('diagram', DEFAULT_PROMPTS['diagram']))

            # Build full prompt with parent context
            if parent_text:
                context_type = "parent question" if diagram_type == 'answer' else "parent paragraph"
                full_prompt = f"""Context from {context_type}:
\"\"\"
{parent_text}
\"\"\"

{base_prompt}"""
            else:
                full_prompt = base_prompt

            # Encode image to base64
            if isinstance(image_data, memoryview):
                image_data = bytes(image_data)
            image_b64 = base64.b64encode(image_data).decode('utf-8')

            # Create request for batch
            requests.append({
                "custom_id": f"diagram_{diagram_id}",
                "params": {
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4096,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_b64
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": full_prompt
                                }
                            ]
                        }
                    ]
                }
            })

        # Submit batch to Anthropic
        client = get_anthropic_client()

        batch = client.messages.batches.create(requests=requests)

        logger.info(f"Batch submitted: {batch.id}, status: {batch.processing_status}")

        # Save batch info
        save_batch_info(db, book_id, batch.id, batch.processing_status, len(diagrams))

        return {
            "batch_id": batch.id,
            "status": batch.processing_status,
            "diagram_count": len(diagrams),
            "message": f"Batch submitted with {len(diagrams)} diagrams"
        }

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return {"error": f"API error: {str(e)}", "batch_id": None}
    except Exception as e:
        logger.error(f"Error submitting batch: {e}")
        return {"error": str(e), "batch_id": None}
    finally:
        db.close()


def check_batch_status(book_id: int, batch_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Check status of a batch job.

    Args:
        book_id: Book ID
        batch_id: Optional batch ID. If None, use last batch from config.

    Returns:
        Dictionary with batch status information
    """
    db = SessionLocal()
    try:
        # Get batch ID if not provided
        if not batch_id:
            batch_info = get_batch_info(db, book_id)
            batch_id = batch_info.get('batch_id')
            if not batch_id:
                return {"error": "No batch ID found", "status": None}

        client = get_anthropic_client()
        batch = client.messages.batches.retrieve(batch_id)

        # Update stored status
        save_batch_info(db, book_id, batch_id, batch.processing_status,
                       get_batch_info(db, book_id).get('diagram_count', 0))

        result = {
            "batch_id": batch.id,
            "status": batch.processing_status,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "ended_at": batch.ended_at.isoformat() if batch.ended_at else None,
            "request_counts": {
                "processing": batch.request_counts.processing,
                "succeeded": batch.request_counts.succeeded,
                "errored": batch.request_counts.errored,
                "canceled": batch.request_counts.canceled,
                "expired": batch.request_counts.expired
            }
        }

        # If ended, include results URL info
        if batch.processing_status == "ended":
            result["completed"] = True
            result["results_available"] = True
        else:
            result["completed"] = False
            result["results_available"] = False

        return result

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error checking batch: {e}")
        return {"error": f"API error: {str(e)}", "status": None}
    except Exception as e:
        logger.error(f"Error checking batch status: {e}")
        return {"error": str(e), "status": None}
    finally:
        db.close()


def retrieve_batch_results(book_id: int, batch_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve and process batch results, updating database with decoded content.

    Args:
        book_id: Book ID
        batch_id: Optional batch ID. If None, use last batch from config.

    Returns:
        Dictionary with processing results
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        diagrams_table = f"raw_{prefix}_diagram_images"

        # Get batch ID if not provided
        if not batch_id:
            batch_info = get_batch_info(db, book_id)
            batch_id = batch_info.get('batch_id')
            if not batch_id:
                return {"error": "No batch ID found"}

        client = get_anthropic_client()

        # Check if batch is complete
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status != "ended":
            return {
                "error": "Batch not yet complete",
                "status": batch.processing_status,
                "batch_id": batch_id
            }

        # Retrieve results
        results_processed = 0
        results_errored = 0

        # Iterate through batch results
        for result in client.messages.batches.results(batch_id):
            custom_id = result.custom_id

            # Extract diagram ID from custom_id (format: "diagram_123")
            try:
                diagram_id = int(custom_id.split('_')[1])
            except (IndexError, ValueError):
                logger.warning(f"Could not parse diagram ID from custom_id: {custom_id}")
                results_errored += 1
                continue

            if result.result.type == "succeeded":
                # Extract text content from response
                message = result.result.message
                decoded_text = ""

                for content_block in message.content:
                    if content_block.type == "text":
                        decoded_text += content_block.text

                # Update diagram in database
                db.execute(
                    text(f"""
                        UPDATE {diagrams_table}
                        SET extracted_text = :content,
                            ai_model = 'claude-sonnet-4',
                            analyzed_at = NOW()
                        WHERE id = :diagram_id
                    """),
                    {"diagram_id": diagram_id, "content": decoded_text}
                )
                results_processed += 1

            elif result.result.type == "errored":
                logger.error(f"Diagram {diagram_id} decoding error: {result.result.error}")
                results_errored += 1
            else:
                logger.warning(f"Diagram {diagram_id} unexpected result type: {result.result.type}")
                results_errored += 1

        db.commit()

        # Update batch status
        save_batch_info(db, book_id, batch_id, "results_retrieved", results_processed + results_errored)

        return {
            "batch_id": batch_id,
            "status": "completed",
            "results_processed": results_processed,
            "results_errored": results_errored,
            "message": f"Processed {results_processed} diagrams, {results_errored} errors"
        }

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error retrieving results: {e}")
        return {"error": f"API error: {str(e)}"}
    except Exception as e:
        logger.error(f"Error retrieving batch results: {e}")
        return {"error": str(e)}
    finally:
        db.close()


# =============================================================================
# Direct API Functions
# =============================================================================

def decode_single_diagram(book_id: int, diagram_id: int, prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Decode a single visual element using Claude direct API.

    Handles all visual classes: diagram, table, equation, list_*, question, answer.

    Args:
        book_id: Book ID
        diagram_id: Element ID to decode
        prompt: Optional custom prompt. If None, use configured prompt for element type.

    Returns:
        Dictionary with decoded content
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        diagrams_table = f"raw_{prefix}_diagram_images"
        paragraphs_table = f"raw_{prefix}_paragraph_images"

        # Get visual element data with parent context (paragraph or question)
        result = db.execute(
            text(f"""
                SELECT d.image_data, d.diagram_type,
                       CASE
                           WHEN d.diagram_type = 'answer' THEN q.extracted_text
                           ELSE p.extracted_text
                       END as parent_text
                FROM {diagrams_table} d
                LEFT JOIN {paragraphs_table} p ON d.linked_knowledge_unit_id = p.id AND d.diagram_type != 'answer'
                LEFT JOIN {diagrams_table} q ON d.linked_knowledge_unit_id = q.id AND d.diagram_type = 'answer'
                WHERE d.id = :diagram_id
            """),
            {"diagram_id": diagram_id}
        ).fetchone()

        if not result:
            return {"error": "Visual element not found"}

        image_data = result[0]
        diagram_type = result[1]
        parent_text = result[2]

        # Get base prompt
        if not prompt:
            prompts = get_extraction_prompts(db, book_id)
            prompt = prompts.get(diagram_type, DEFAULT_PROMPTS.get('diagram'))

        # Build full prompt with parent context
        if parent_text:
            context_type = "parent question" if diagram_type == 'answer' else "parent paragraph"
            full_prompt = f"""Context from {context_type}:
\"\"\"
{parent_text}
\"\"\"

{prompt}"""
        else:
            full_prompt = prompt

        # Encode image
        if isinstance(image_data, memoryview):
            image_data = bytes(image_data)
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        # Call Claude API
        client = get_anthropic_client()

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": full_prompt
                        }
                    ]
                }
            ]
        )

        # Extract response text
        decoded_text = ""
        for content_block in message.content:
            if content_block.type == "text":
                decoded_text += content_block.text

        return {
            "diagram_id": diagram_id,
            "decoded_content": decoded_text,
            "prompt_used": prompt,
            "usage": {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens
            }
        }

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return {"error": f"API error: {str(e)}"}
    except Exception as e:
        logger.error(f"Error decoding diagram: {e}")
        return {"error": str(e)}
    finally:
        db.close()


def start_direct_decode(book_id: int, diagram_ids: Optional[List[int]] = None,
                        websocket_callback=None) -> Dict[str, Any]:
    """
    Decode visual elements directly (synchronously) using Claude API.

    Handles all visual classes: diagram, table, equation, list_*, question, answer.

    Args:
        book_id: Book ID
        diagram_ids: Optional list of specific element IDs. If None, process all undecoded.
        websocket_callback: Optional callback for progress updates

    Returns:
        Dictionary with processing results
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        diagrams_table = f"raw_{prefix}_diagram_images"
        paragraphs_table = f"raw_{prefix}_paragraph_images"
        prompts = get_extraction_prompts(db, book_id)

        # Build query for visual elements with parent context (paragraph or question)
        query = f"""
            SELECT d.id, d.image_data, d.diagram_type, d.page_number,
                   CASE
                       WHEN d.diagram_type = 'answer' THEN q.extracted_text
                       ELSE p.extracted_text
                   END as parent_text
            FROM {diagrams_table} d
            LEFT JOIN {paragraphs_table} p ON d.linked_knowledge_unit_id = p.id AND d.diagram_type != 'answer'
            LEFT JOIN {diagrams_table} q ON d.linked_knowledge_unit_id = q.id AND d.diagram_type = 'answer'
            WHERE d.analyzed_at IS NULL
        """

        if diagram_ids:
            query += f" AND d.id IN ({','.join(map(str, diagram_ids))})"

        query += " ORDER BY d.page_number, d.id"

        diagrams = db.execute(text(query)).fetchall()

        if not diagrams:
            return {"error": "No visual elements to decode", "processed": 0}

        total = len(diagrams)
        processed = 0
        errored = 0

        client = get_anthropic_client()

        for diagram in diagrams:
            diagram_id = diagram[0]
            image_data = diagram[1]
            diagram_type = diagram[2]
            page_number = diagram[3]
            parent_text = diagram[4]  # Parent context (paragraph or question)

            try:
                # Get base prompt
                base_prompt = prompts.get(diagram_type, prompts.get('diagram', DEFAULT_PROMPTS['diagram']))

                # Build full prompt with parent context
                if parent_text:
                    context_type = "parent question" if diagram_type == 'answer' else "parent paragraph"
                    full_prompt = f"""Context from {context_type}:
\"\"\"
{parent_text}
\"\"\"

{base_prompt}"""
                else:
                    full_prompt = base_prompt

                # Encode image
                if isinstance(image_data, memoryview):
                    image_data = bytes(image_data)
                image_b64 = base64.b64encode(image_data).decode('utf-8')

                # Call Claude API
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_b64
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": full_prompt
                                }
                            ]
                        }
                    ]
                )

                # Extract response
                decoded_text = ""
                for content_block in message.content:
                    if content_block.type == "text":
                        decoded_text += content_block.text

                # Update database
                db.execute(
                    text(f"""
                        UPDATE {diagrams_table}
                        SET extracted_text = :content,
                            ai_model = 'claude-sonnet-4',
                            analyzed_at = NOW()
                        WHERE id = :diagram_id
                    """),
                    {"diagram_id": diagram_id, "content": decoded_text}
                )
                db.commit()

                processed += 1

                # Send progress update via WebSocket callback
                if websocket_callback:
                    websocket_callback({
                        "type": "decode_progress",
                        "current": processed,
                        "total": total,
                        "diagram_id": diagram_id,
                        "page_number": page_number,
                        "diagram_type": diagram_type
                    })

                logger.info(f"Decoded diagram {diagram_id} ({processed}/{total})")

            except anthropic.APIError as e:
                logger.error(f"API error decoding diagram {diagram_id}: {e}")
                errored += 1
            except Exception as e:
                logger.error(f"Error decoding diagram {diagram_id}: {e}")
                errored += 1

        return {
            "status": "completed",
            "processed": processed,
            "errored": errored,
            "total": total,
            "message": f"Decoded {processed}/{total} diagrams, {errored} errors"
        }

    except Exception as e:
        logger.error(f"Error in direct decode: {e}")
        return {"error": str(e), "processed": 0}
    finally:
        db.close()


# =============================================================================
# Preview Functions
# =============================================================================

def preview_decode(book_id: int, diagram_id: int, prompt: str) -> Dict[str, Any]:
    """
    Preview decode a diagram without saving to database.
    Used for testing prompts before batch processing.

    Args:
        book_id: Book ID
        diagram_id: Diagram ID
        prompt: Prompt to test

    Returns:
        Dictionary with Claude response
    """
    return decode_single_diagram(book_id, diagram_id, prompt)


def save_decode_result(book_id: int, diagram_id: int, content: str) -> Dict[str, Any]:
    """
    Save a decode result to the database.
    Used after preview to persist the result.

    Args:
        book_id: Book ID
        diagram_id: Diagram ID
        content: Decoded content to save

    Returns:
        Success/error status
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        diagrams_table = f"raw_{prefix}_diagram_images"

        db.execute(
            text(f"""
                UPDATE {diagrams_table}
                SET extracted_text = :content,
                    ai_model = 'claude-sonnet-4',
                    analyzed_at = NOW()
                WHERE id = :diagram_id
            """),
            {"diagram_id": diagram_id, "content": content}
        )
        db.commit()

        return {"status": "ok", "message": "Decode result saved"}

    except Exception as e:
        logger.error(f"Error saving decode result: {e}")
        return {"error": str(e)}
    finally:
        db.close()


# =============================================================================
# Q&A Knowledge Unit Processing Functions
# =============================================================================

def process_qa_knowledge_units(book_id: int, ku_ids: Optional[List[int]] = None,
                               websocket_callback=None) -> Dict[str, Any]:
    """
    Process Q&A Knowledge Units by sending both question and answer images to Claude.
    
    For each Q&A KU:
    1. Parse attr12_value JSON to get question and answer image references
    2. Retrieve both images from raw_diagram_images
    3. Send question image to Claude -> store response in text_content
    4. Send answer image to Claude -> store response in attr11_value
    
    Args:
        book_id: Book ID
        ku_ids: Optional list of specific KU IDs. If None, process all Q&A KUs.
        websocket_callback: Optional callback for progress updates
        
    Returns:
        Dictionary with processing results
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        ku_table = f"{prefix}_knowledge_units"
        diagrams_table = f"raw_{prefix}_diagram_images"
        prompts = get_extraction_prompts(db, book_id)
        
        # Get Q&A KUs that need processing
        query = f"""
            SELECT unit_id, attr12_value, chapter, topic, sub_topic
            FROM {ku_table}
            WHERE attr9_value = 'question_answer'
            AND (text_content IS NULL OR text_content = '')
        """
        
        if ku_ids:
            query += f" AND unit_id IN ({','.join(map(str, ku_ids))})"
        
        qa_kus = db.execute(text(query)).fetchall()
        
        if not qa_kus:
            return {"error": "No Q&A Knowledge Units to process", "processed": 0}
        
        total = len(qa_kus)
        processed = 0
        errored = 0
        
        client = get_anthropic_client()
        question_prompt = prompts.get('question', DEFAULT_PROMPTS['question'])
        answer_prompt = prompts.get('answer', DEFAULT_PROMPTS['answer'])
        
        for ku in qa_kus:
            ku_id = ku[0]
            attr12_value = ku[1]
            
            try:
                # Parse JSON reference
                if isinstance(attr12_value, str):
                    refs = json.loads(attr12_value)
                else:
                    refs = attr12_value
                
                question_ref = refs.get('question', '')
                answer_ref = refs.get('answer', '')
                
                # Extract IDs from references (format: "diagram:123")
                question_id = int(question_ref.split(':')[1]) if question_ref else None
                answer_id = int(answer_ref.split(':')[1]) if answer_ref else None
                
                if not question_id or not answer_id:
                    logger.warning(f"KU {ku_id} missing question or answer reference")
                    errored += 1
                    continue
                
                # Get question image
                q_result = db.execute(
                    text(f"SELECT image_data FROM {diagrams_table} WHERE id = :id"),
                    {"id": question_id}
                ).fetchone()
                
                # Get answer image
                a_result = db.execute(
                    text(f"SELECT image_data FROM {diagrams_table} WHERE id = :id"),
                    {"id": answer_id}
                ).fetchone()
                
                if not q_result or not a_result:
                    logger.warning(f"KU {ku_id} missing image data")
                    errored += 1
                    continue
                
                q_image_data = q_result[0]
                a_image_data = a_result[0]
                
                # Encode images
                if isinstance(q_image_data, memoryview):
                    q_image_data = bytes(q_image_data)
                if isinstance(a_image_data, memoryview):
                    a_image_data = bytes(a_image_data)
                
                q_image_b64 = base64.b64encode(q_image_data).decode('utf-8')
                a_image_b64 = base64.b64encode(a_image_data).decode('utf-8')
                
                # Process question image
                q_message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": q_image_b64}},
                            {"type": "text", "text": question_prompt}
                        ]
                    }]
                )
                
                question_text = ""
                for block in q_message.content:
                    if block.type == "text":
                        question_text += block.text
                
                # Process answer image
                a_message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": a_image_b64}},
                            {"type": "text", "text": answer_prompt}
                        ]
                    }]
                )
                
                answer_text = ""
                for block in a_message.content:
                    if block.type == "text":
                        answer_text += block.text
                
                # Update KU with both responses
                db.execute(
                    text(f"""
                        UPDATE {ku_table}
                        SET text_content = :question_text,
                            attr11_value = :answer_text,
                            updated_at = NOW()
                        WHERE unit_id = :ku_id
                    """),
                    {"ku_id": ku_id, "question_text": question_text, "answer_text": answer_text}
                )
                
                # Also update raw_diagram_images with analyzed_at
                db.execute(
                    text(f"""
                        UPDATE {diagrams_table}
                        SET extracted_text = :text, ai_model = 'claude-sonnet-4', analyzed_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": question_id, "text": question_text}
                )
                db.execute(
                    text(f"""
                        UPDATE {diagrams_table}
                        SET extracted_text = :text, ai_model = 'claude-sonnet-4', analyzed_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": answer_id, "text": answer_text}
                )
                
                db.commit()
                processed += 1
                
                if websocket_callback:
                    websocket_callback({
                        "type": "qa_progress",
                        "current": processed,
                        "total": total,
                        "ku_id": ku_id
                    })
                
                logger.info(f"Processed Q&A KU {ku_id} ({processed}/{total})")
                
            except anthropic.APIError as e:
                logger.error(f"API error processing Q&A KU {ku_id}: {e}")
                errored += 1
            except Exception as e:
                logger.error(f"Error processing Q&A KU {ku_id}: {e}")
                errored += 1
        
        return {
            "status": "completed",
            "processed": processed,
            "errored": errored,
            "total": total,
            "message": f"Processed {processed}/{total} Q&A KUs, {errored} errors"
        }
        
    except Exception as e:
        logger.error(f"Error in process_qa_knowledge_units: {e}")
        return {"error": str(e), "processed": 0}
    finally:
        db.close()


def update_ku_from_diagram_analysis(book_id: int) -> Dict[str, Any]:
    """
    Update Knowledge Units with text from Claude diagram analysis.
    
    After Claude processes raw_diagram_images, this function copies the
    extracted_text to the corresponding knowledge_units.text_content.
    
    For Q&A pairs, this is handled separately by process_qa_knowledge_units().
    
    Args:
        book_id: Book ID
        
    Returns:
        Dictionary with update results
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        ku_table = f"{prefix}_knowledge_units"
        diagrams_table = f"raw_{prefix}_diagram_images"
        
        # Update non-Q&A KUs from diagram analysis
        result = db.execute(
            text(f"""
                UPDATE {ku_table} ku
                SET text_content = d.extracted_text,
                    updated_at = NOW()
                FROM {diagrams_table} d
                WHERE ku.attr12_value = CONCAT('diagram:', d.id::text)
                AND ku.attr9_value != 'question_answer'
                AND d.analyzed_at IS NOT NULL
                AND (ku.text_content IS NULL OR ku.text_content = '')
                RETURNING ku.unit_id
            """)
        )
        
        updated_ids = [row[0] for row in result.fetchall()]
        db.commit()
        
        return {
            "status": "completed",
            "updated_count": len(updated_ids),
            "message": f"Updated {len(updated_ids)} Knowledge Units from diagram analysis"
        }
        
    except Exception as e:
        logger.error(f"Error updating KUs from diagram analysis: {e}")
        db.rollback()
        return {"error": str(e), "updated_count": 0}
    finally:
        db.close()
