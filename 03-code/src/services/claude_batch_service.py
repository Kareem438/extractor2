"""
Claude Batch Service (3B.9)

Handles Claude API integration for diagram/table/equation/list decoding:
- Message Batches API (50% cost, async processing)
- Direct API (immediate results, full cost)
- Result retrieval and database updates

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
from typing import List, Dict, Optional, Any
from datetime import datetime

import anthropic
from sqlalchemy import text

from src.database.connection import SessionLocal
from src.config import settings
from src.utils.logging_config import logger


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
