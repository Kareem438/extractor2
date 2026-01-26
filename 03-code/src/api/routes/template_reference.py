"""
Template Reference API Routes

Provides autocomplete and tree browsing for template references.
- Search for attribute references
- Get full tree structure for modal browser
- Support for @BookName.Level.TitleName.attrN(AttributeName) syntax

Requirement 5: Multi-PDF Upload & Cross-Book Attribute Access
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from sqlalchemy import text

from src.database.connection import SessionLocal
from src.utils.logging_config import logger

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================

def table_exists(db, table_name: str) -> bool:
    """Check if a table exists."""
    result = db.execute(
        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"),
        {"name": table_name}
    ).scalar()
    return result


def sanitize_book_name_for_reference(book_name: str) -> str:
    """Sanitize book name for use in reference syntax."""
    # Remove spaces and special characters, keep alphanumeric and underscores
    sanitized = ''.join(c if c.isalnum() or c == '_' else '' for c in book_name)
    return sanitized


def format_reference(book_name: str, level: str, title_text: str, attr_num: int, attr_name: str = None) -> str:
    """Format a complete reference string."""
    sanitized_book = sanitize_book_name_for_reference(book_name)
    sanitized_title = sanitize_book_name_for_reference(title_text)
    
    if attr_name:
        return f"@{sanitized_book}.{level}.{sanitized_title}.attr{attr_num}({attr_name})"
    else:
        return f"@{sanitized_book}.{level}.{sanitized_title}.attr{attr_num}"


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/template-reference/search")
async def search_references(
    query: str = "",
    current_book_id: Optional[int] = None,
    limit: int = 20
):
    """
    Search for attribute references (for autocomplete).
    
    Args:
        query: Search query (e.g., "Physics.L1.Energy")
        current_book_id: Current book ID (to exclude from results if needed)
        limit: Maximum number of results
    """
    db = SessionLocal()
    try:
        # Get all books
        books_result = db.execute(
            text("SELECT book_id, book_name, table_prefix FROM books_metadata ORDER BY book_name")
        ).fetchall()
        
        results = []
        query_lower = query.lower()
        
        for book_row in books_result:
            book_id, book_name, table_prefix = book_row
            sanitized_book = sanitize_book_name_for_reference(book_name)
            
            # Check L1 titles
            l1_table = f"{table_prefix}_level1_titles"
            if table_exists(db, l1_table):
                # Get titles with their attributes
                l1_result = db.execute(
                    text(f"""
                        SELECT id, title_text, external_writable_start, external_writable_end,
                               {', '.join([f'attr{i}_name' for i in range(1, 201)])}
                        FROM {l1_table}
                        ORDER BY start_page
                    """)
                ).fetchall()
                
                for title_row in l1_result:
                    title_id = title_row[0]
                    title_text = title_row[1]
                    writable_start = title_row[2]
                    writable_end = title_row[3]
                    sanitized_title = sanitize_book_name_for_reference(title_text)
                    
                    # Check each attribute
                    for i in range(1, 201):
                        attr_name = title_row[3 + i]  # Offset by 4 (id, title_text, writable_start, writable_end)
                        
                        # Build reference
                        reference = format_reference(book_name, "L1", title_text, i, attr_name)
                        
                        # Check if matches query
                        if query_lower in reference.lower():
                            results.append({
                                "reference": reference,
                                "book_id": book_id,
                                "book_name": book_name,
                                "level": "L1",
                                "title_id": title_id,
                                "title_text": title_text,
                                "attribute_num": i,
                                "attribute_name": attr_name,
                                "is_writable": writable_start <= i <= writable_end if writable_start and writable_end else False
                            })
                            
                            if len(results) >= limit:
                                return {"results": results}
            
            # Check L2 titles
            l2_table = f"{table_prefix}_level2_titles"
            if table_exists(db, l2_table):
                l2_result = db.execute(
                    text(f"""
                        SELECT id, title_text, external_writable_start, external_writable_end,
                               {', '.join([f'attr{i}_name' for i in range(1, 151)])}
                        FROM {l2_table}
                        ORDER BY start_page
                    """)
                ).fetchall()
                
                for title_row in l2_result:
                    title_id = title_row[0]
                    title_text = title_row[1]
                    writable_start = title_row[2]
                    writable_end = title_row[3]
                    sanitized_title = sanitize_book_name_for_reference(title_text)
                    
                    for i in range(1, 151):
                        attr_name = title_row[3 + i]
                        
                        reference = format_reference(book_name, "L2", title_text, i, attr_name)
                        
                        if query_lower in reference.lower():
                            results.append({
                                "reference": reference,
                                "book_id": book_id,
                                "book_name": book_name,
                                "level": "L2",
                                "title_id": title_id,
                                "title_text": title_text,
                                "attribute_num": i,
                                "attribute_name": attr_name,
                                "is_writable": writable_start <= i <= writable_end if writable_start and writable_end else False
                            })
                            
                            if len(results) >= limit:
                                return {"results": results}
        
        return {"results": results}
    
    except Exception as e:
        logger.error(f"Error searching references: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/template-reference/tree")
async def get_reference_tree():
    """
    Get full tree structure for modal browser.
    
    Returns hierarchical structure:
    - Books
      - L1 Titles
        - Attributes
      - L2 Titles
        - Attributes
    """
    db = SessionLocal()
    try:
        # Get all books
        books_result = db.execute(
            text("SELECT book_id, book_name, table_prefix FROM books_metadata ORDER BY book_name")
        ).fetchall()
        
        books = []
        
        for book_row in books_result:
            book_id, book_name, table_prefix = book_row
            
            book_data = {
                "book_id": book_id,
                "book_name": book_name,
                "sanitized_name": sanitize_book_name_for_reference(book_name),
                "levels": {
                    "L1": [],
                    "L2": []
                }
            }
            
            # Get L1 titles with attributes
            l1_table = f"{table_prefix}_level1_titles"
            if table_exists(db, l1_table):
                l1_result = db.execute(
                    text(f"""
                        SELECT id, title_text, start_page, end_page, 
                               external_writable_start, external_writable_end,
                               {', '.join([f'attr{i}_name' for i in range(1, 201)])}
                        FROM {l1_table}
                        ORDER BY start_page
                    """)
                ).fetchall()
                
                for title_row in l1_result:
                    title_id = title_row[0]
                    title_text = title_row[1]
                    start_page = title_row[2]
                    end_page = title_row[3]
                    writable_start = title_row[4] or 151
                    writable_end = title_row[5] or 200
                    
                    # Build attributes list (only include named ones for tree view)
                    attributes = []
                    for i in range(1, 201):
                        attr_name = title_row[5 + i]  # Offset by 6
                        attributes.append({
                            "num": i,
                            "name": attr_name,
                            "is_writable": writable_start <= i <= writable_end
                        })
                    
                    book_data["levels"]["L1"].append({
                        "title_id": title_id,
                        "title_text": title_text,
                        "sanitized_title": sanitize_book_name_for_reference(title_text),
                        "start_page": start_page,
                        "end_page": end_page,
                        "writable_range": [writable_start, writable_end],
                        "attributes": attributes
                    })
            
            # Get L2 titles with attributes
            l2_table = f"{table_prefix}_level2_titles"
            if table_exists(db, l2_table):
                l2_result = db.execute(
                    text(f"""
                        SELECT id, title_text, start_page, end_page, parent_l1_id,
                               external_writable_start, external_writable_end,
                               {', '.join([f'attr{i}_name' for i in range(1, 151)])}
                        FROM {l2_table}
                        ORDER BY start_page
                    """)
                ).fetchall()
                
                for title_row in l2_result:
                    title_id = title_row[0]
                    title_text = title_row[1]
                    start_page = title_row[2]
                    end_page = title_row[3]
                    parent_l1_id = title_row[4]
                    writable_start = title_row[5] or 101
                    writable_end = title_row[6] or 150
                    
                    attributes = []
                    for i in range(1, 151):
                        attr_name = title_row[6 + i]  # Offset by 7
                        attributes.append({
                            "num": i,
                            "name": attr_name,
                            "is_writable": writable_start <= i <= writable_end
                        })
                    
                    book_data["levels"]["L2"].append({
                        "title_id": title_id,
                        "title_text": title_text,
                        "sanitized_title": sanitize_book_name_for_reference(title_text),
                        "start_page": start_page,
                        "end_page": end_page,
                        "parent_l1_id": parent_l1_id,
                        "writable_range": [writable_start, writable_end],
                        "attributes": attributes
                    })
            
            books.append(book_data)
        
        return {"books": books}
    
    except Exception as e:
        logger.error(f"Error getting reference tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/template-reference/books/{book_id}/titles/{level}")
async def get_book_titles_for_reference(book_id: int, level: str):
    """Get titles for a specific book and level (for lazy loading in tree)."""
    if level not in ["L1", "L2"]:
        raise HTTPException(status_code=400, detail="Level must be 'L1' or 'L2'")
    
    db = SessionLocal()
    try:
        # Get book info
        book_result = db.execute(
            text("SELECT book_name, table_prefix FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        ).fetchone()
        
        if not book_result:
            raise HTTPException(status_code=404, detail="Book not found")
        
        book_name, table_prefix = book_result
        
        if level == "L1":
            table_name = f"{table_prefix}_level1_titles"
            max_attrs = 200
        else:
            table_name = f"{table_prefix}_level2_titles"
            max_attrs = 150
        
        if not table_exists(db, table_name):
            return {"titles": []}
        
        # Get titles
        result = db.execute(
            text(f"""
                SELECT id, title_text, start_page, end_page,
                       external_writable_start, external_writable_end
                FROM {table_name}
                ORDER BY start_page
            """)
        ).fetchall()
        
        titles = [{
            "title_id": row[0],
            "title_text": row[1],
            "sanitized_title": sanitize_book_name_for_reference(row[1]),
            "start_page": row[2],
            "end_page": row[3],
            "writable_range": [row[4] or (151 if level == "L1" else 101), 
                              row[5] or (200 if level == "L1" else 150)]
        } for row in result]
        
        return {
            "book_id": book_id,
            "book_name": book_name,
            "level": level,
            "titles": titles
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting book titles: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/template-reference/books/{book_id}/titles/{level}/{title_id}/attributes")
async def get_title_attributes_for_reference(book_id: int, level: str, title_id: int):
    """Get attributes for a specific title (for lazy loading in tree)."""
    if level not in ["L1", "L2"]:
        raise HTTPException(status_code=400, detail="Level must be 'L1' or 'L2'")
    
    db = SessionLocal()
    try:
        # Get book info
        book_result = db.execute(
            text("SELECT book_name, table_prefix FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        ).fetchone()
        
        if not book_result:
            raise HTTPException(status_code=404, detail="Book not found")
        
        book_name, table_prefix = book_result
        
        if level == "L1":
            table_name = f"{table_prefix}_level1_titles"
            max_attrs = 200
        else:
            table_name = f"{table_prefix}_level2_titles"
            max_attrs = 150
        
        if not table_exists(db, table_name):
            raise HTTPException(status_code=404, detail="Title table not found")
        
        # Build column list
        columns = ["id", "title_text", "external_writable_start", "external_writable_end"]
        for i in range(1, max_attrs + 1):
            columns.append(f"attr{i}_name")
        
        result = db.execute(
            text(f"SELECT {', '.join(columns)} FROM {table_name} WHERE id = :id"),
            {"id": title_id}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Title not found")
        
        title_text = result[1]
        writable_start = result[2] or (151 if level == "L1" else 101)
        writable_end = result[3] or (200 if level == "L1" else 150)
        
        # Build attributes list
        attributes = []
        for i in range(1, max_attrs + 1):
            attr_name = result[3 + i]  # Offset by 4
            reference = format_reference(book_name, level, title_text, i, attr_name)
            
            attributes.append({
                "num": i,
                "name": attr_name,
                "reference": reference,
                "is_writable": writable_start <= i <= writable_end
            })
        
        return {
            "book_id": book_id,
            "book_name": book_name,
            "level": level,
            "title_id": title_id,
            "title_text": title_text,
            "writable_range": [writable_start, writable_end],
            "attributes": attributes
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting title attributes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
