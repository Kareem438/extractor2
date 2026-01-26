"""
Cross-Book Attribute Access API Routes

Allows books to read and write custom attributes of L1/L2 titles from other books.
- Read attributes from any book
- Write to writable range of other books' attributes
- Audit logging for all cross-book writes
- Counter increment operation

Requirement 5: Multi-PDF Upload & Cross-Book Attribute Access
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from datetime import datetime

from src.database.connection import SessionLocal
from src.utils.logging_config import logger

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class AttributeWrite(BaseModel):
    value: Optional[str] = None
    operation: Optional[str] = None  # "write" or "increment"


class CrossBookWriteRequest(BaseModel):
    source_book_id: int
    source_pipeline_rule: Optional[str] = None
    source_pipeline_number: Optional[int] = None
    attributes: Dict[str, AttributeWrite]  # {"attr155": {"value": "...", "operation": "write"}}


class AuditLogQuery(BaseModel):
    source_book_id: Optional[int] = None
    target_book_id: Optional[int] = None
    limit: int = 100


# =============================================================================
# Helper Functions
# =============================================================================

def get_book_info(db, book_id: int) -> dict:
    """Get book information."""
    result = db.execute(
        text("SELECT book_id, book_name, table_prefix FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    
    return {
        "book_id": result[0],
        "book_name": result[1],
        "table_prefix": result[2]
    }


def table_exists(db, table_name: str) -> bool:
    """Check if a table exists."""
    result = db.execute(
        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"),
        {"name": table_name}
    ).scalar()
    return result


def get_writable_range(db, table_prefix: str, level: str, title_id: int) -> tuple:
    """Get the writable range for a title."""
    if level == "L1":
        table_name = f"{table_prefix}_level1_titles"
    else:
        table_name = f"{table_prefix}_level2_titles"
    
    result = db.execute(
        text(f"SELECT external_writable_start, external_writable_end FROM {table_name} WHERE id = :id"),
        {"id": title_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail=f"{level} title {title_id} not found")
    
    return (result[0], result[1])


def is_attribute_writable(attr_num: int, writable_start: int, writable_end: int) -> bool:
    """Check if an attribute is within the writable range."""
    return writable_start <= attr_num <= writable_end


def log_cross_book_access(db, source_book_id: int, source_pipeline_rule: str, 
                          source_pipeline_number: int, target_book_id: int,
                          target_level: str, target_title_id: int, 
                          target_attribute: str, old_value: str, 
                          new_value: str, operation: str):
    """Log a cross-book write operation."""
    db.execute(
        text("""
            INSERT INTO cross_book_access_log (
                source_book_id, source_pipeline_rule, source_pipeline_number,
                target_book_id, target_level, target_title_id, target_attribute,
                old_value, new_value, operation
            ) VALUES (
                :source_book_id, :source_pipeline_rule, :source_pipeline_number,
                :target_book_id, :target_level, :target_title_id, :target_attribute,
                :old_value, :new_value, :operation
            )
        """),
        {
            "source_book_id": source_book_id,
            "source_pipeline_rule": source_pipeline_rule,
            "source_pipeline_number": source_pipeline_number,
            "target_book_id": target_book_id,
            "target_level": target_level,
            "target_title_id": target_title_id,
            "target_attribute": target_attribute,
            "old_value": old_value,
            "new_value": new_value,
            "operation": operation
        }
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/cross-book/books")
async def get_all_books_for_cross_access():
    """List all books available for cross-book access."""
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT book_id, book_name, table_prefix, total_pages
                FROM books_metadata 
                ORDER BY book_name
            """)
        ).fetchall()
        
        books = []
        for row in result:
            book_id, book_name, table_prefix, total_pages = row
            
            # Get L1 titles
            l1_table = f"{table_prefix}_level1_titles"
            l1_titles = []
            if table_exists(db, l1_table):
                l1_result = db.execute(
                    text(f"SELECT id, title_text, start_page, end_page FROM {l1_table} ORDER BY start_page")
                ).fetchall()
                l1_titles = [{"id": r[0], "title_text": r[1], "start_page": r[2], "end_page": r[3]} for r in l1_result]
            
            # Get L2 titles
            l2_table = f"{table_prefix}_level2_titles"
            l2_titles = []
            if table_exists(db, l2_table):
                l2_result = db.execute(
                    text(f"SELECT id, title_text, start_page, end_page, parent_l1_id FROM {l2_table} ORDER BY start_page")
                ).fetchall()
                l2_titles = [{"id": r[0], "title_text": r[1], "start_page": r[2], "end_page": r[3], "parent_l1_id": r[4]} for r in l2_result]
            
            books.append({
                "book_id": book_id,
                "book_name": book_name,
                "total_pages": total_pages,
                "l1_titles": l1_titles,
                "l2_titles": l2_titles
            })
        
        return {"books": books}
    
    except Exception as e:
        logger.error(f"Error getting books for cross-access: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/cross-book/books/{book_id}/titles/{level}/{title_id}/attributes")
async def get_cross_book_attributes(book_id: int, level: str, title_id: int):
    """Get attributes from another book's title."""
    if level not in ["L1", "L2"]:
        raise HTTPException(status_code=400, detail="Level must be 'L1' or 'L2'")
    
    db = SessionLocal()
    try:
        book_info = get_book_info(db, book_id)
        table_prefix = book_info["table_prefix"]
        
        if level == "L1":
            table_name = f"{table_prefix}_level1_titles"
            max_attrs = 200
        else:
            table_name = f"{table_prefix}_level2_titles"
            max_attrs = 150
        
        if not table_exists(db, table_name):
            raise HTTPException(status_code=404, detail=f"{level} titles table not found")
        
        # Build column list
        columns = ["id", "title_text", "external_writable_start", "external_writable_end"]
        for i in range(1, max_attrs + 1):
            columns.append(f"attr{i}_name")
            columns.append(f"attr{i}_value")
        
        result = db.execute(
            text(f"SELECT {', '.join(columns)} FROM {table_name} WHERE id = :id"),
            {"id": title_id}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"{level} title {title_id} not found")
        
        # Build attributes dict
        attributes = {}
        for i in range(1, max_attrs + 1):
            name_idx = 4 + (i - 1) * 2
            value_idx = name_idx + 1
            attributes[f"attr{i}"] = {
                "name": result[name_idx],
                "value": result[value_idx]
            }
        
        return {
            "book_id": book_id,
            "book_name": book_info["book_name"],
            "level": level,
            "title_id": result[0],
            "title_text": result[1],
            "attributes": attributes,
            "writable_range": [result[2], result[3]],
            "total_attributes": max_attrs
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cross-book attributes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/cross-book/books/{book_id}/titles/{level}/{title_id}/attributes")
async def write_cross_book_attributes(book_id: int, level: str, title_id: int, request: CrossBookWriteRequest):
    """
    Write to another book's attributes (within writable range).
    
    Supports:
    - Direct write: {"attr155": {"value": "new value"}}
    - Increment: {"attr160": {"operation": "increment"}}
    """
    if level not in ["L1", "L2"]:
        raise HTTPException(status_code=400, detail="Level must be 'L1' or 'L2'")
    
    db = SessionLocal()
    try:
        # Verify source book exists
        source_book = get_book_info(db, request.source_book_id)
        
        # Verify target book exists
        target_book = get_book_info(db, book_id)
        table_prefix = target_book["table_prefix"]
        
        if level == "L1":
            table_name = f"{table_prefix}_level1_titles"
            max_attrs = 200
        else:
            table_name = f"{table_prefix}_level2_titles"
            max_attrs = 150
        
        if not table_exists(db, table_name):
            raise HTTPException(status_code=404, detail=f"{level} titles table not found")
        
        # Get writable range
        writable_start, writable_end = get_writable_range(db, table_prefix, level, title_id)
        
        # Process each attribute
        updates = []
        params = {"id": title_id}
        written_attrs = []
        
        for attr_key, attr_data in request.attributes.items():
            # Extract attribute number
            if not attr_key.startswith("attr"):
                continue
            try:
                attr_num = int(attr_key[4:])
                if attr_num < 1 or attr_num > max_attrs:
                    continue
            except ValueError:
                continue
            
            # Check if attribute is writable
            if not is_attribute_writable(attr_num, writable_start, writable_end):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Attribute {attr_key} is not writable. Writable range: {writable_start}-{writable_end}"
                )
            
            # Get current value for logging
            current_result = db.execute(
                text(f"SELECT attr{attr_num}_value FROM {table_name} WHERE id = :id"),
                {"id": title_id}
            ).fetchone()
            old_value = current_result[0] if current_result else None
            
            # Determine operation and new value
            operation = attr_data.operation or "write"
            
            if operation == "increment":
                # Read current value and increment
                try:
                    current_val = int(old_value) if old_value else 0
                    new_value = str(current_val + 1)
                except (ValueError, TypeError):
                    new_value = "1"
            else:
                new_value = attr_data.value
            
            # Add to updates
            updates.append(f"attr{attr_num}_value = :attr{attr_num}_value")
            params[f"attr{attr_num}_value"] = new_value
            
            # Log the access
            log_cross_book_access(
                db,
                source_book_id=request.source_book_id,
                source_pipeline_rule=request.source_pipeline_rule,
                source_pipeline_number=request.source_pipeline_number,
                target_book_id=book_id,
                target_level=level,
                target_title_id=title_id,
                target_attribute=attr_key,
                old_value=old_value,
                new_value=new_value,
                operation=operation
            )
            
            written_attrs.append({
                "attribute": attr_key,
                "old_value": old_value,
                "new_value": new_value,
                "operation": operation
            })
        
        if not updates:
            return {"message": "No valid attributes to update", "written": []}
        
        # Execute update
        updates.append("updated_at = NOW()")
        db.execute(
            text(f"UPDATE {table_name} SET {', '.join(updates)} WHERE id = :id"),
            params
        )
        
        db.commit()
        
        logger.info(f"Cross-book write: Book {request.source_book_id} -> Book {book_id} {level} title {title_id}: {len(written_attrs)} attributes")
        
        return {
            "message": f"Updated {len(written_attrs)} attribute(s)",
            "written": written_attrs
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error writing cross-book attributes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/cross-book/audit-log")
async def get_audit_log(
    source_book_id: Optional[int] = None,
    target_book_id: Optional[int] = None,
    limit: int = 100
):
    """Get cross-book write audit log."""
    db = SessionLocal()
    try:
        # Build query with optional filters
        conditions = []
        params = {"limit": limit}
        
        if source_book_id:
            conditions.append("cal.source_book_id = :source_book_id")
            params["source_book_id"] = source_book_id
        
        if target_book_id:
            conditions.append("cal.target_book_id = :target_book_id")
            params["target_book_id"] = target_book_id
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        result = db.execute(
            text(f"""
                SELECT 
                    cal.id, 
                    cal.source_book_id, sb.book_name as source_book_name,
                    cal.source_pipeline_rule, cal.source_pipeline_number,
                    cal.target_book_id, tb.book_name as target_book_name,
                    cal.target_level, cal.target_title_id, cal.target_attribute,
                    cal.old_value, cal.new_value, cal.operation, cal.created_at
                FROM cross_book_access_log cal
                JOIN books_metadata sb ON cal.source_book_id = sb.book_id
                JOIN books_metadata tb ON cal.target_book_id = tb.book_id
                {where_clause}
                ORDER BY cal.created_at DESC
                LIMIT :limit
            """),
            params
        ).fetchall()
        
        logs = [{
            "id": row[0],
            "source_book_id": row[1],
            "source_book": row[2],
            "pipeline_rule": row[3],
            "pipeline_number": row[4],
            "target_book_id": row[5],
            "target_book": row[6],
            "target_level": row[7],
            "target_title_id": row[8],
            "attribute": row[9],
            "old_value": row[10],
            "new_value": row[11],
            "operation": row[12],
            "timestamp": row[13].isoformat() if row[13] else None
        } for row in result]
        
        return {"logs": logs, "count": len(logs)}
    
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
