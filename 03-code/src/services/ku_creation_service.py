"""
Knowledge Unit Creation Service

Creates knowledge_units records from extracted raw_paragraph_images and raw_diagram_images.
This is a separate step that runs AFTER extraction completes.

Workflow:
1. Get all extracted records from raw tables for selected pages
2. Create KU for each paragraph (direct OCR text copy)
3. Create KU for each diagram/table/equation/list (skeleton with image reference)
4. Merge Q&A pairs into single KU (both image references in JSON)
5. Update bidirectional links

Attribute Mapping:
- attr9_value: layout_class_type (paragraph, diagram, table, equation, list_*, question, answer)
- attr10_value: parent_paragraph_text (OCR text of linked parent paragraph)
- attr11_value: answer_text (for Q&A pairs, populated by Claude later)
- attr12_value: raw_entity_reference (JSON: {"question": "diagram:123", "answer": "diagram:456"} or "paragraph:123")
"""

import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy import text

from src.database.connection import SessionLocal
from src.utils.logging_config import logger


def get_book_info(db, book_id: int) -> Dict:
    """Get book metadata including table prefix."""
    result = db.execute(
        text("SELECT table_prefix, book_name, total_pages FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()
    
    if not result:
        raise ValueError(f"Book {book_id} not found")
    
    return {
        "table_prefix": result[0],
        "book_name": result[1],
        "total_pages": result[2]
    }


def get_paragraphs_for_pages(db, table_prefix: str, page_numbers: List[int]) -> List[Dict]:
    """Get all paragraph records for specified pages."""
    placeholders = ','.join([f':p{i}' for i in range(len(page_numbers))])
    params = {f'p{i}': p for i, p in enumerate(page_numbers)}
    
    result = db.execute(
        text(f"""
            SELECT id, page_number, extracted_text, ocr_confidence,
                   level_1_title, level_2_title, level_3_title,
                   selection_x, selection_y, linked_knowledge_unit_id
            FROM raw_{table_prefix}_paragraph_images
            WHERE page_number IN ({placeholders})
            AND is_enabled = TRUE
            AND linked_knowledge_unit_id IS NULL
            ORDER BY page_number, selection_y, selection_x
        """),
        params
    ).fetchall()
    
    return [{
        "id": row[0],
        "page_number": row[1],
        "extracted_text": row[2] or "",
        "ocr_confidence": row[3] or 0.0,
        "level_1_title": row[4],
        "level_2_title": row[5],
        "level_3_title": row[6],
        "position_x": row[7],
        "position_y": row[8],
        "linked_ku_id": row[9]
    } for row in result]


def get_diagrams_for_pages(db, table_prefix: str, page_numbers: List[int]) -> List[Dict]:
    """Get all diagram records for specified pages (includes tables, equations, lists, Q&A)."""
    placeholders = ','.join([f':p{i}' for i in range(len(page_numbers))])
    params = {f'p{i}': p for i, p in enumerate(page_numbers)}
    
    result = db.execute(
        text(f"""
            SELECT id, page_number, diagram_type, extracted_text,
                   level_1_title, level_2_title, level_3_title,
                   selection_x, selection_y, linked_knowledge_unit_id
            FROM raw_{table_prefix}_diagram_images
            WHERE page_number IN ({placeholders})
            AND is_enabled = TRUE
            AND linked_knowledge_unit_id IS NULL
            ORDER BY page_number, selection_y, selection_x
        """),
        params
    ).fetchall()
    
    return [{
        "id": row[0],
        "page_number": row[1],
        "diagram_type": row[2] or "diagram",
        "extracted_text": row[3] or "",
        "level_1_title": row[4],
        "level_2_title": row[5],
        "level_3_title": row[6],
        "position_x": row[7],
        "position_y": row[8],
        "linked_ku_id": row[9]
    } for row in result]


def get_qa_links(db, table_prefix: str, page_numbers: List[int]) -> Dict[int, int]:
    """Get question-answer links for specified pages.
    
    Returns: Dict mapping answer_id -> question_id
    """
    # Q&A links are stored in layout_detection_config
    # We need to get the config and extract links
    result = db.execute(
        text("SELECT layout_detection_config FROM books_metadata WHERE table_prefix = :prefix"),
        {"prefix": table_prefix}
    ).fetchone()
    
    if not result or not result[0]:
        return {}
    
    config = result[0] if isinstance(result[0], dict) else json.loads(result[0])
    qa_links = config.get('qa_links', {})
    
    # qa_links format: {answer_region_id: question_region_id}
    return {int(k): int(v) for k, v in qa_links.items()}


def get_parent_paragraph_text(db, table_prefix: str, paragraph_ku_id: int) -> Optional[str]:
    """Get the OCR text of a parent paragraph by its knowledge_unit_id."""
    if not paragraph_ku_id:
        return None
    
    result = db.execute(
        text(f"""
            SELECT text_content FROM {table_prefix}_knowledge_units
            WHERE unit_id = :ku_id
        """),
        {"ku_id": paragraph_ku_id}
    ).fetchone()
    
    return result[0] if result else None


def get_parent_paragraph_text_from_raw(db, table_prefix: str, raw_paragraph_id: int) -> Optional[str]:
    """Get the OCR text of a parent paragraph from raw_paragraph_images."""
    if not raw_paragraph_id:
        return None
    
    result = db.execute(
        text(f"""
            SELECT extracted_text FROM raw_{table_prefix}_paragraph_images
            WHERE id = :id
        """),
        {"id": raw_paragraph_id}
    ).fetchone()
    
    return result[0] if result else None


def create_paragraph_ku(db, table_prefix: str, paragraph: Dict) -> int:
    """Create a knowledge unit for a paragraph.
    
    Args:
        db: Database session
        table_prefix: Book's table prefix
        paragraph: Dict with paragraph data from raw_paragraph_images
        
    Returns:
        Created knowledge_unit unit_id
    """
    result = db.execute(
        text(f"""
            INSERT INTO {table_prefix}_knowledge_units (
                page_number,
                text_content,
                ocr_method,
                confidence_score,
                position_x,
                position_y,
                chapter,
                topic,
                sub_topic,
                attr2_value,
                attr8_value,
                attr9_value,
                attr12_value,
                created_at,
                updated_at
            ) VALUES (
                :page_number,
                :text_content,
                'surya',
                :confidence,
                :position_x,
                :position_y,
                :chapter,
                :topic,
                :sub_topic,
                :preliminary_ocr,
                'enabled',
                'paragraph',
                :raw_reference,
                NOW(),
                NOW()
            )
            RETURNING unit_id
        """),
        {
            "page_number": paragraph["page_number"],
            "text_content": paragraph["extracted_text"],
            "confidence": paragraph["ocr_confidence"],
            "position_x": paragraph["position_x"],
            "position_y": paragraph["position_y"],
            "chapter": paragraph["level_1_title"],
            "topic": paragraph["level_2_title"],
            "sub_topic": paragraph["level_3_title"],
            "preliminary_ocr": paragraph["extracted_text"],
            "raw_reference": f"paragraph:{paragraph['id']}"
        }
    )
    
    unit_id = result.fetchone()[0]
    
    # Update raw_paragraph_images with linked_knowledge_unit_id
    db.execute(
        text(f"""
            UPDATE raw_{table_prefix}_paragraph_images
            SET linked_knowledge_unit_id = :ku_id, updated_at = NOW()
            WHERE id = :raw_id
        """),
        {"ku_id": unit_id, "raw_id": paragraph["id"]}
    )
    
    return unit_id


def create_diagram_ku(db, table_prefix: str, diagram: Dict, parent_text: Optional[str] = None) -> int:
    """Create a knowledge unit for a diagram/table/equation/list.
    
    Args:
        db: Database session
        table_prefix: Book's table prefix
        diagram: Dict with diagram data from raw_diagram_images
        parent_text: OCR text of parent paragraph (if linked)
        
    Returns:
        Created knowledge_unit unit_id
    """
    result = db.execute(
        text(f"""
            INSERT INTO {table_prefix}_knowledge_units (
                page_number,
                text_content,
                position_x,
                position_y,
                chapter,
                topic,
                sub_topic,
                attr2_value,
                attr8_value,
                attr9_value,
                attr10_value,
                attr12_value,
                created_at,
                updated_at
            ) VALUES (
                :page_number,
                '',
                :position_x,
                :position_y,
                :chapter,
                :topic,
                :sub_topic,
                :preliminary_ocr,
                'enabled',
                :class_type,
                :parent_text,
                :raw_reference,
                NOW(),
                NOW()
            )
            RETURNING unit_id
        """),
        {
            "page_number": diagram["page_number"],
            "position_x": diagram["position_x"],
            "position_y": diagram["position_y"],
            "chapter": diagram["level_1_title"],
            "topic": diagram["level_2_title"],
            "sub_topic": diagram["level_3_title"],
            "preliminary_ocr": diagram["extracted_text"],
            "class_type": diagram["diagram_type"],
            "parent_text": parent_text,
            "raw_reference": f"diagram:{diagram['id']}"
        }
    )
    
    unit_id = result.fetchone()[0]
    
    # Update raw_diagram_images with linked_knowledge_unit_id
    db.execute(
        text(f"""
            UPDATE raw_{table_prefix}_diagram_images
            SET linked_knowledge_unit_id = :ku_id, updated_at = NOW()
            WHERE id = :raw_id
        """),
        {"ku_id": unit_id, "raw_id": diagram["id"]}
    )
    
    return unit_id


def create_qa_ku(db, table_prefix: str, question: Dict, answer: Dict) -> int:
    """Create a single knowledge unit for a question-answer pair.
    
    Both question and answer images are referenced in attr12_value as JSON.
    Claude will later populate text_content (question) and attr11_value (answer).
    
    Args:
        db: Database session
        table_prefix: Book's table prefix
        question: Dict with question data from raw_diagram_images
        answer: Dict with answer data from raw_diagram_images
        
    Returns:
        Created knowledge_unit unit_id
    """
    # Create JSON reference for both images
    raw_reference = json.dumps({
        "question": f"diagram:{question['id']}",
        "answer": f"diagram:{answer['id']}"
    })
    
    # Combine preliminary OCR from both
    preliminary_ocr = f"Q: {question['extracted_text']}\nA: {answer['extracted_text']}"
    
    result = db.execute(
        text(f"""
            INSERT INTO {table_prefix}_knowledge_units (
                page_number,
                text_content,
                position_x,
                position_y,
                chapter,
                topic,
                sub_topic,
                attr2_value,
                attr8_value,
                attr9_value,
                attr11_value,
                attr12_value,
                created_at,
                updated_at
            ) VALUES (
                :page_number,
                '',
                :position_x,
                :position_y,
                :chapter,
                :topic,
                :sub_topic,
                :preliminary_ocr,
                'enabled',
                'question_answer',
                '',
                :raw_reference,
                NOW(),
                NOW()
            )
            RETURNING unit_id
        """),
        {
            "page_number": question["page_number"],
            "position_x": question["position_x"],
            "position_y": question["position_y"],
            "chapter": question["level_1_title"],
            "topic": question["level_2_title"],
            "sub_topic": question["level_3_title"],
            "preliminary_ocr": preliminary_ocr,
            "raw_reference": raw_reference
        }
    )
    
    unit_id = result.fetchone()[0]
    
    # Update both raw_diagram_images records with linked_knowledge_unit_id
    db.execute(
        text(f"""
            UPDATE raw_{table_prefix}_diagram_images
            SET linked_knowledge_unit_id = :ku_id, updated_at = NOW()
            WHERE id IN (:q_id, :a_id)
        """),
        {"ku_id": unit_id, "q_id": question["id"], "a_id": answer["id"]}
    )
    
    return unit_id


def get_diagram_parent_links(db, table_prefix: str) -> Dict[int, int]:
    """Get diagram-to-paragraph links from layout_detection_config.
    
    Returns: Dict mapping diagram_raw_id -> paragraph_raw_id
    """
    result = db.execute(
        text("SELECT layout_detection_config FROM books_metadata WHERE table_prefix = :prefix"),
        {"prefix": table_prefix}
    ).fetchone()
    
    if not result or not result[0]:
        return {}
    
    config = result[0] if isinstance(result[0], dict) else json.loads(result[0])
    links = config.get('links', [])
    
    # links format: [{diagram_region_id: X, paragraph_region_id: Y}, ...]
    return {link['diagram_region_id']: link['paragraph_region_id'] for link in links if 'diagram_region_id' in link}


def create_knowledge_units_for_pages(book_id: int, page_numbers: List[int]) -> Dict[str, Any]:
    """Main function to create knowledge units for specified pages.
    
    This is the entry point called by the API endpoint.
    
    Args:
        book_id: Book ID
        page_numbers: List of page numbers to process
        
    Returns:
        Dict with results: {
            success: bool,
            paragraphs_created: int,
            diagrams_created: int,
            qa_pairs_created: int,
            errors: List[str]
        }
    """
    db = SessionLocal()
    results = {
        "success": True,
        "paragraphs_created": 0,
        "diagrams_created": 0,
        "qa_pairs_created": 0,
        "errors": []
    }
    
    try:
        book_info = get_book_info(db, book_id)
        table_prefix = book_info["table_prefix"]
        
        logger.info(f"Creating KUs for book {book_id}, pages {page_numbers}")
        
        # Get all paragraphs for these pages
        paragraphs = get_paragraphs_for_pages(db, table_prefix, page_numbers)
        logger.info(f"Found {len(paragraphs)} paragraphs to process")
        
        # Create KU for each paragraph
        paragraph_ku_map = {}  # raw_id -> ku_id mapping for parent lookups
        for para in paragraphs:
            try:
                ku_id = create_paragraph_ku(db, table_prefix, para)
                paragraph_ku_map[para["id"]] = ku_id
                results["paragraphs_created"] += 1
            except Exception as e:
                logger.error(f"Error creating KU for paragraph {para['id']}: {e}")
                results["errors"].append(f"Paragraph {para['id']}: {str(e)}")
        
        db.commit()
        logger.info(f"Created {results['paragraphs_created']} paragraph KUs")
        
        # Get all diagrams for these pages
        diagrams = get_diagrams_for_pages(db, table_prefix, page_numbers)
        logger.info(f"Found {len(diagrams)} diagrams to process")
        
        # Get Q&A links and diagram-paragraph links
        qa_links = get_qa_links(db, table_prefix, page_numbers)
        parent_links = get_diagram_parent_links(db, table_prefix)
        
        # Separate questions, answers, and other diagrams
        questions = {d["id"]: d for d in diagrams if d["diagram_type"] == "question"}
        answers = {d["id"]: d for d in diagrams if d["diagram_type"] == "answer"}
        other_diagrams = [d for d in diagrams if d["diagram_type"] not in ("question", "answer")]
        
        # Process Q&A pairs first
        processed_qa_ids = set()
        for answer_id, question_id in qa_links.items():
            if answer_id in answers and question_id in questions:
                try:
                    question = questions[question_id]
                    answer = answers[answer_id]
                    ku_id = create_qa_ku(db, table_prefix, question, answer)
                    results["qa_pairs_created"] += 1
                    processed_qa_ids.add(question_id)
                    processed_qa_ids.add(answer_id)
                except Exception as e:
                    logger.error(f"Error creating KU for Q&A pair {question_id}/{answer_id}: {e}")
                    results["errors"].append(f"Q&A {question_id}/{answer_id}: {str(e)}")
        
        db.commit()
        logger.info(f"Created {results['qa_pairs_created']} Q&A pair KUs")
        
        # Process remaining diagrams (not part of Q&A pairs)
        for diagram in other_diagrams:
            try:
                # Get parent paragraph text if linked
                parent_text = None
                if diagram["id"] in parent_links:
                    parent_raw_id = parent_links[diagram["id"]]
                    parent_text = get_parent_paragraph_text_from_raw(db, table_prefix, parent_raw_id)
                
                ku_id = create_diagram_ku(db, table_prefix, diagram, parent_text)
                results["diagrams_created"] += 1
            except Exception as e:
                logger.error(f"Error creating KU for diagram {diagram['id']}: {e}")
                results["errors"].append(f"Diagram {diagram['id']}: {str(e)}")
        
        # Also process any orphan questions/answers (shouldn't happen with validation)
        for q_id, question in questions.items():
            if q_id not in processed_qa_ids:
                try:
                    ku_id = create_diagram_ku(db, table_prefix, question, None)
                    results["diagrams_created"] += 1
                    logger.warning(f"Created orphan question KU for {q_id}")
                except Exception as e:
                    results["errors"].append(f"Orphan question {q_id}: {str(e)}")
        
        for a_id, answer in answers.items():
            if a_id not in processed_qa_ids:
                try:
                    ku_id = create_diagram_ku(db, table_prefix, answer, None)
                    results["diagrams_created"] += 1
                    logger.warning(f"Created orphan answer KU for {a_id}")
                except Exception as e:
                    results["errors"].append(f"Orphan answer {a_id}: {str(e)}")
        
        db.commit()
        logger.info(f"Created {results['diagrams_created']} diagram KUs")
        
        if results["errors"]:
            results["success"] = False
        
        return results
        
    except Exception as e:
        logger.error(f"Error in create_knowledge_units_for_pages: {e}")
        db.rollback()
        results["success"] = False
        results["errors"].append(str(e))
        return results
    finally:
        db.close()


def get_page_ku_status(book_id: int) -> List[Dict]:
    """Get KU creation status for all pages in a book.
    
    Returns list of page status dicts for Pipeline page display.
    """
    db = SessionLocal()
    try:
        book_info = get_book_info(db, book_id)
        table_prefix = book_info["table_prefix"]
        total_pages = book_info["total_pages"]
        
        # Get extraction status (pages with records in raw tables)
        para_pages = db.execute(
            text(f"SELECT DISTINCT page_number FROM raw_{table_prefix}_paragraph_images WHERE is_enabled = TRUE")
        ).fetchall()
        para_page_set = {row[0] for row in para_pages}
        
        diag_pages = db.execute(
            text(f"SELECT DISTINCT page_number FROM raw_{table_prefix}_diagram_images WHERE is_enabled = TRUE")
        ).fetchall()
        diag_page_set = {row[0] for row in diag_pages}
        
        extracted_pages = para_page_set | diag_page_set
        
        # Get KU creation status (pages with linked KUs)
        para_ku_pages = db.execute(
            text(f"""
                SELECT DISTINCT page_number FROM raw_{table_prefix}_paragraph_images 
                WHERE is_enabled = TRUE AND linked_knowledge_unit_id IS NOT NULL
            """)
        ).fetchall()
        para_ku_set = {row[0] for row in para_ku_pages}
        
        diag_ku_pages = db.execute(
            text(f"""
                SELECT DISTINCT page_number FROM raw_{table_prefix}_diagram_images 
                WHERE is_enabled = TRUE AND linked_knowledge_unit_id IS NOT NULL
            """)
        ).fetchall()
        diag_ku_set = {row[0] for row in diag_ku_pages}
        
        ku_created_pages = para_ku_set | diag_ku_set
        
        # Get Claude analysis status (diagrams with extracted_text from Claude)
        claude_pages = db.execute(
            text(f"""
                SELECT DISTINCT page_number FROM raw_{table_prefix}_diagram_images 
                WHERE is_enabled = TRUE AND analyzed_at IS NOT NULL
            """)
        ).fetchall()
        claude_page_set = {row[0] for row in claude_pages}
        
        # Get layout detection status
        result = db.execute(
            text("SELECT layout_detection_config FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        ).fetchone()
        
        layout_config = {}
        if result and result[0]:
            layout_config = result[0] if isinstance(result[0], dict) else json.loads(result[0])
        
        ready_for_extraction = layout_config.get('ready_for_extraction', {})
        detected_pages = set(layout_config.get('detected_pages', []))
        
        # Build status list for all pages
        page_status = []
        for page_num in range(1, total_pages + 1):
            status = {
                "page_number": page_num,
                "layout_status": "detected" if page_num in detected_pages else "pending",
                "extraction_status": "completed" if page_num in extracted_pages else "pending",
                "ku_status": "completed" if page_num in ku_created_pages else "pending",
                "claude_status": "completed" if page_num in claude_page_set else "pending",
                "ready_for_extraction": ready_for_extraction.get(str(page_num), False)
            }
            
            # Refine layout status
            if ready_for_extraction.get(str(page_num), False):
                status["layout_status"] = "ready"
            elif page_num in detected_pages:
                status["layout_status"] = "detected"
            
            page_status.append(status)
        
        return page_status
        
    except Exception as e:
        logger.error(f"Error getting page KU status: {e}")
        return []
    finally:
        db.close()
