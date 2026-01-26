"""
Title Hierarchy API Routes

Manages Level 1 and Level 2 titles with custom attributes.
- L1 Titles: Chapter-level with 200 custom attributes
- L2 Titles: Section-level with 150 custom attributes

Provides:
- CRUD operations for L1/L2 titles
- Attribute management
- Validation for page coverage
- Auto-linking support
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy import text
import json

from src.database.connection import SessionLocal
from src.utils.logging_config import logger

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class L1TitleCreate(BaseModel):
    title_text: str
    start_page: int
    end_page: int
    display_order: Optional[int] = 0


class L1TitleUpdate(BaseModel):
    title_text: Optional[str] = None
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    display_order: Optional[int] = None


class L2TitleCreate(BaseModel):
    title_text: str
    start_page: int
    end_page: int
    parent_l1_id: Optional[int] = None
    display_order: Optional[int] = 0


class L2TitleUpdate(BaseModel):
    title_text: Optional[str] = None
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    parent_l1_id: Optional[int] = None
    display_order: Optional[int] = None


class AttributeUpdate(BaseModel):
    attributes: Dict[str, Dict[str, Optional[str]]]  # {"attr1": {"name": "...", "value": "..."}, ...}


class ValidationRequest(BaseModel):
    start_page: int
    end_page: int


# =============================================================================
# Helper Functions
# =============================================================================

def get_book_table_prefix(db, book_id: int) -> str:
    """Get the table prefix for a book."""
    result = db.execute(
        text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
        {"book_id": book_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return result[0]


def table_exists(db, table_name: str) -> bool:
    """Check if a table exists."""
    result = db.execute(
        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"),
        {"name": table_name}
    ).scalar()
    return result


# =============================================================================
# L1 Title Endpoints
# =============================================================================

@router.get("/books/{book_id}/l1-titles")
async def get_l1_titles(book_id: int):
    """Get all L1 titles for a book."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level1_titles"
        
        if not table_exists(db, table_name):
            return {"titles": [], "message": "L1 titles table not created yet"}
        
        result = db.execute(
            text(f"SELECT id, title_text, start_page, end_page, display_order, created_at FROM {table_name} ORDER BY display_order, start_page")
        ).fetchall()
        
        titles = [{
            "id": row[0],
            "title_text": row[1],
            "start_page": row[2],
            "end_page": row[3],
            "display_order": row[4],
            "created_at": row[5].isoformat() if row[5] else None
        } for row in result]
        
        return {"titles": titles}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting L1 titles: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/books/{book_id}/l1-titles")
async def create_l1_title(book_id: int, title: L1TitleCreate):
    """Create a new L1 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level1_titles"
        
        if not table_exists(db, table_name):
            raise HTTPException(status_code=400, detail="L1 titles table not created. Run migration first.")
        
        # Validate page range
        if title.start_page > title.end_page:
            raise HTTPException(status_code=400, detail="start_page must be <= end_page")
        
        result = db.execute(
            text(f"""
                INSERT INTO {table_name} (title_text, start_page, end_page, display_order)
                VALUES (:title_text, :start_page, :end_page, :display_order)
                RETURNING id
            """),
            {
                "title_text": title.title_text,
                "start_page": title.start_page,
                "end_page": title.end_page,
                "display_order": title.display_order
            }
        )
        
        new_id = result.fetchone()[0]
        db.commit()
        
        return {"id": new_id, "message": "L1 title created successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating L1 title: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/books/{book_id}/l1-titles/{title_id}")
async def update_l1_title(book_id: int, title_id: int, title: L1TitleUpdate):
    """Update an L1 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level1_titles"
        
        # Build update query
        updates = []
        params = {"id": title_id}
        
        if title.title_text is not None:
            updates.append("title_text = :title_text")
            params["title_text"] = title.title_text
        if title.start_page is not None:
            updates.append("start_page = :start_page")
            params["start_page"] = title.start_page
        if title.end_page is not None:
            updates.append("end_page = :end_page")
            params["end_page"] = title.end_page
        if title.display_order is not None:
            updates.append("display_order = :display_order")
            params["display_order"] = title.display_order
        
        if not updates:
            return {"message": "No updates provided"}
        
        updates.append("updated_at = NOW()")
        
        result = db.execute(
            text(f"UPDATE {table_name} SET {', '.join(updates)} WHERE id = :id RETURNING id"),
            params
        )
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="L1 title not found")
        
        db.commit()
        return {"message": "L1 title updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating L1 title: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/books/{book_id}/l1-titles/{title_id}")
async def delete_l1_title(book_id: int, title_id: int):
    """Delete an L1 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level1_titles"
        
        result = db.execute(
            text(f"DELETE FROM {table_name} WHERE id = :id RETURNING id"),
            {"id": title_id}
        )
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="L1 title not found")
        
        db.commit()
        return {"message": "L1 title deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting L1 title: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/books/{book_id}/l1-titles/{title_id}/attributes")
async def get_l1_attributes(book_id: int, title_id: int):
    """Get all attributes for an L1 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level1_titles"
        
        # Build column list for 200 attributes
        columns = ["id", "title_text"]
        for i in range(1, 201):
            columns.append(f"attr{i}_name")
            columns.append(f"attr{i}_value")
        
        result = db.execute(
            text(f"SELECT {', '.join(columns)} FROM {table_name} WHERE id = :id"),
            {"id": title_id}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="L1 title not found")
        
        # Build attributes dict
        attributes = {}
        for i in range(1, 201):
            name_idx = 2 + (i - 1) * 2
            value_idx = name_idx + 1
            attributes[f"attr{i}"] = {
                "name": result[name_idx],
                "value": result[value_idx]
            }
        
        return {
            "id": result[0],
            "title_text": result[1],
            "attributes": attributes,
            "total_attributes": 200
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting L1 attributes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/books/{book_id}/l1-titles/{title_id}/attributes")
async def update_l1_attributes(book_id: int, title_id: int, data: AttributeUpdate):
    """Update attributes for an L1 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level1_titles"
        
        # Build update query
        updates = []
        params = {"id": title_id}
        
        for attr_key, attr_data in data.attributes.items():
            # Extract attribute number (e.g., "attr1" -> 1)
            if not attr_key.startswith("attr"):
                continue
            try:
                attr_num = int(attr_key[4:])
                if attr_num < 1 or attr_num > 200:
                    continue
            except ValueError:
                continue
            
            if "name" in attr_data:
                updates.append(f"attr{attr_num}_name = :attr{attr_num}_name")
                params[f"attr{attr_num}_name"] = attr_data["name"]
            if "value" in attr_data:
                updates.append(f"attr{attr_num}_value = :attr{attr_num}_value")
                params[f"attr{attr_num}_value"] = attr_data["value"]
        
        if not updates:
            return {"message": "No valid attributes to update"}
        
        updates.append("updated_at = NOW()")
        
        result = db.execute(
            text(f"UPDATE {table_name} SET {', '.join(updates)} WHERE id = :id RETURNING id"),
            params
        )
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="L1 title not found")
        
        db.commit()
        return {"message": f"Updated {len(data.attributes)} attributes"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating L1 attributes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# L2 Title Endpoints
# =============================================================================

@router.get("/books/{book_id}/l2-titles")
async def get_l2_titles(book_id: int):
    """Get all L2 titles for a book."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level2_titles"
        
        if not table_exists(db, table_name):
            return {"titles": [], "message": "L2 titles table not created yet"}
        
        result = db.execute(
            text(f"SELECT id, title_text, start_page, end_page, parent_l1_id, display_order, created_at FROM {table_name} ORDER BY display_order, start_page")
        ).fetchall()
        
        titles = [{
            "id": row[0],
            "title_text": row[1],
            "start_page": row[2],
            "end_page": row[3],
            "parent_l1_id": row[4],
            "display_order": row[5],
            "created_at": row[6].isoformat() if row[6] else None
        } for row in result]
        
        return {"titles": titles}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting L2 titles: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/books/{book_id}/l2-titles")
async def create_l2_title(book_id: int, title: L2TitleCreate):
    """Create a new L2 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level2_titles"
        
        if not table_exists(db, table_name):
            raise HTTPException(status_code=400, detail="L2 titles table not created. Run migration first.")
        
        # Validate page range
        if title.start_page > title.end_page:
            raise HTTPException(status_code=400, detail="start_page must be <= end_page")
        
        result = db.execute(
            text(f"""
                INSERT INTO {table_name} (title_text, start_page, end_page, parent_l1_id, display_order)
                VALUES (:title_text, :start_page, :end_page, :parent_l1_id, :display_order)
                RETURNING id
            """),
            {
                "title_text": title.title_text,
                "start_page": title.start_page,
                "end_page": title.end_page,
                "parent_l1_id": title.parent_l1_id,
                "display_order": title.display_order
            }
        )
        
        new_id = result.fetchone()[0]
        db.commit()
        
        return {"id": new_id, "message": "L2 title created successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating L2 title: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/books/{book_id}/l2-titles/{title_id}")
async def update_l2_title(book_id: int, title_id: int, title: L2TitleUpdate):
    """Update an L2 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level2_titles"
        
        # Build update query
        updates = []
        params = {"id": title_id}
        
        if title.title_text is not None:
            updates.append("title_text = :title_text")
            params["title_text"] = title.title_text
        if title.start_page is not None:
            updates.append("start_page = :start_page")
            params["start_page"] = title.start_page
        if title.end_page is not None:
            updates.append("end_page = :end_page")
            params["end_page"] = title.end_page
        if title.parent_l1_id is not None:
            updates.append("parent_l1_id = :parent_l1_id")
            params["parent_l1_id"] = title.parent_l1_id
        if title.display_order is not None:
            updates.append("display_order = :display_order")
            params["display_order"] = title.display_order
        
        if not updates:
            return {"message": "No updates provided"}
        
        updates.append("updated_at = NOW()")
        
        result = db.execute(
            text(f"UPDATE {table_name} SET {', '.join(updates)} WHERE id = :id RETURNING id"),
            params
        )
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="L2 title not found")
        
        db.commit()
        return {"message": "L2 title updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating L2 title: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/books/{book_id}/l2-titles/{title_id}")
async def delete_l2_title(book_id: int, title_id: int):
    """Delete an L2 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level2_titles"
        
        result = db.execute(
            text(f"DELETE FROM {table_name} WHERE id = :id RETURNING id"),
            {"id": title_id}
        )
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="L2 title not found")
        
        db.commit()
        return {"message": "L2 title deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting L2 title: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/books/{book_id}/l2-titles/{title_id}/attributes")
async def get_l2_attributes(book_id: int, title_id: int):
    """Get all attributes for an L2 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level2_titles"
        
        # Build column list for 150 attributes
        columns = ["id", "title_text"]
        for i in range(1, 151):
            columns.append(f"attr{i}_name")
            columns.append(f"attr{i}_value")
        
        result = db.execute(
            text(f"SELECT {', '.join(columns)} FROM {table_name} WHERE id = :id"),
            {"id": title_id}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="L2 title not found")
        
        # Build attributes dict
        attributes = {}
        for i in range(1, 151):
            name_idx = 2 + (i - 1) * 2
            value_idx = name_idx + 1
            attributes[f"attr{i}"] = {
                "name": result[name_idx],
                "value": result[value_idx]
            }
        
        return {
            "id": result[0],
            "title_text": result[1],
            "attributes": attributes,
            "total_attributes": 150
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting L2 attributes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/books/{book_id}/l2-titles/{title_id}/attributes")
async def update_l2_attributes(book_id: int, title_id: int, data: AttributeUpdate):
    """Update attributes for an L2 title."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        table_name = f"{prefix}_level2_titles"
        
        # Build update query
        updates = []
        params = {"id": title_id}
        
        for attr_key, attr_data in data.attributes.items():
            # Extract attribute number (e.g., "attr1" -> 1)
            if not attr_key.startswith("attr"):
                continue
            try:
                attr_num = int(attr_key[4:])
                if attr_num < 1 or attr_num > 150:
                    continue
            except ValueError:
                continue
            
            if "name" in attr_data:
                updates.append(f"attr{attr_num}_name = :attr{attr_num}_name")
                params[f"attr{attr_num}_name"] = attr_data["name"]
            if "value" in attr_data:
                updates.append(f"attr{attr_num}_value = :attr{attr_num}_value")
                params[f"attr{attr_num}_value"] = attr_data["value"]
        
        if not updates:
            return {"message": "No valid attributes to update"}
        
        updates.append("updated_at = NOW()")
        
        result = db.execute(
            text(f"UPDATE {table_name} SET {', '.join(updates)} WHERE id = :id RETURNING id"),
            params
        )
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="L2 title not found")
        
        db.commit()
        return {"message": f"Updated {len(data.attributes)} attributes"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating L2 attributes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()



# =============================================================================
# Validation Endpoints
# =============================================================================

@router.get("/books/{book_id}/validate-title-coverage")
async def validate_title_coverage(book_id: int, start_page: int, end_page: int):
    """
    Validate that all pages in the range have L1 and L2 title coverage.
    
    Returns validation status and list of uncovered pages.
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        l1_table = f"{prefix}_level1_titles"
        l2_table = f"{prefix}_level2_titles"
        
        # Check if tables exist
        if not table_exists(db, l1_table) or not table_exists(db, l2_table):
            return {
                "valid": False,
                "l1_valid": False,
                "l2_valid": False,
                "message": "Title tables not created. Run migration first.",
                "uncovered_l1_pages": list(range(start_page, end_page + 1)),
                "uncovered_l2_pages": list(range(start_page, end_page + 1))
            }
        
        # Get L1 titles
        l1_result = db.execute(
            text(f"SELECT start_page, end_page FROM {l1_table} ORDER BY start_page")
        ).fetchall()
        
        # Get L2 titles
        l2_result = db.execute(
            text(f"SELECT start_page, end_page FROM {l2_table} ORDER BY start_page")
        ).fetchall()
        
        # Check L1 coverage
        l1_covered = set()
        for row in l1_result:
            for page in range(row[0], row[1] + 1):
                l1_covered.add(page)
        
        # Check L2 coverage
        l2_covered = set()
        for row in l2_result:
            for page in range(row[0], row[1] + 1):
                l2_covered.add(page)
        
        # Find uncovered pages
        requested_pages = set(range(start_page, end_page + 1))
        uncovered_l1 = sorted(requested_pages - l1_covered)
        uncovered_l2 = sorted(requested_pages - l2_covered)
        
        l1_valid = len(uncovered_l1) == 0
        l2_valid = len(uncovered_l2) == 0
        
        return {
            "valid": l1_valid and l2_valid,
            "l1_valid": l1_valid,
            "l2_valid": l2_valid,
            "uncovered_l1_pages": uncovered_l1,
            "uncovered_l2_pages": uncovered_l2,
            "message": "All pages covered" if (l1_valid and l2_valid) else "Some pages lack title coverage"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating title coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/books/{book_id}/validate-l3-links")
async def validate_l3_links(book_id: int, page_numbers: str):
    """
    Validate that all paragraphs on the specified pages are linked to L3 titles.
    
    Args:
        page_numbers: Comma-separated list of page numbers (e.g., "1,2,3,4,5")
    
    Returns validation status and list of unlinked paragraphs.
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        detections_table = f"raw_{prefix}_layout_detections"
        
        # Parse page numbers
        try:
            pages = [int(p.strip()) for p in page_numbers.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid page_numbers format. Use comma-separated integers.")
        
        if not table_exists(db, detections_table):
            return {
                "valid": True,
                "message": "No layout detections table exists yet",
                "pages_without_l3": [],
                "unlinked_paragraphs": []
            }
        
        # Check for l3_title_id column
        col_exists = db.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = :table_name AND column_name = 'l3_title_id'
                )
            """),
            {"table_name": detections_table}
        ).scalar()
        
        if not col_exists:
            return {
                "valid": False,
                "message": "l3_title_id column not found. Run migration first.",
                "pages_without_l3": pages,
                "unlinked_paragraphs": []
            }
        
        # Find pages with paragraphs but no L3 titles
        pages_without_l3 = []
        unlinked_paragraphs = []
        
        for page in pages:
            # Check if page has any L3 titles
            l3_count = db.execute(
                text(f"""
                    SELECT COUNT(*) FROM {detections_table}
                    WHERE page_number = :page AND class_name IN ('title_level_3', 'Title L3', 'title_l3')
                """),
                {"page": page}
            ).scalar()
            
            # Check if page has paragraphs
            para_result = db.execute(
                text(f"""
                    SELECT id, l3_title_id FROM {detections_table}
                    WHERE page_number = :page AND class_name = 'paragraph'
                """),
                {"page": page}
            ).fetchall()
            
            if para_result and l3_count == 0:
                pages_without_l3.append(page)
            
            # Check for unlinked paragraphs
            for row in para_result:
                if row[1] is None:  # l3_title_id is NULL
                    unlinked_paragraphs.append({
                        "page": page,
                        "region_id": row[0]
                    })
        
        valid = len(pages_without_l3) == 0 and len(unlinked_paragraphs) == 0
        
        return {
            "valid": valid,
            "pages_without_l3": pages_without_l3,
            "unlinked_paragraphs": unlinked_paragraphs,
            "message": "All paragraphs linked to L3 titles" if valid else "Some paragraphs are not linked to L3 titles"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating L3 links: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/books/{book_id}/auto-link-paragraphs")
async def auto_link_paragraphs(book_id: int, page_numbers: str):
    """
    Auto-link paragraphs to the nearest L3 title above them (by Y position).
    
    Args:
        page_numbers: Comma-separated list of page numbers (e.g., "1,2,3,4,5")
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        detections_table = f"raw_{prefix}_layout_detections"
        
        # Parse page numbers
        try:
            pages = [int(p.strip()) for p in page_numbers.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid page_numbers format. Use comma-separated integers.")
        
        if not table_exists(db, detections_table):
            raise HTTPException(status_code=400, detail="Layout detections table not found")
        
        linked_count = 0
        skipped_count = 0
        
        for page in pages:
            # Get all L3 titles on this page, ordered by Y position
            l3_titles = db.execute(
                text(f"""
                    SELECT id, y FROM {detections_table}
                    WHERE page_number = :page AND class_name IN ('title_level_3', 'Title L3', 'title_l3')
                    ORDER BY y
                """),
                {"page": page}
            ).fetchall()
            
            if not l3_titles:
                skipped_count += 1
                continue
            
            # Get all paragraphs on this page
            paragraphs = db.execute(
                text(f"""
                    SELECT id, y, l3_title_id FROM {detections_table}
                    WHERE page_number = :page AND class_name = 'paragraph'
                    ORDER BY y
                """),
                {"page": page}
            ).fetchall()
            
            for para in paragraphs:
                para_id, para_y, current_l3_id = para
                
                # Skip if already linked (manual override)
                if current_l3_id is not None:
                    continue
                
                # Find the nearest L3 title above this paragraph
                best_l3_id = None
                for l3 in l3_titles:
                    l3_id, l3_y = l3
                    if l3_y < para_y:  # L3 is above paragraph
                        best_l3_id = l3_id
                    else:
                        break  # L3 is below paragraph, stop
                
                # If no L3 above, use the first L3 on the page
                if best_l3_id is None and l3_titles:
                    best_l3_id = l3_titles[0][0]
                
                if best_l3_id:
                    db.execute(
                        text(f"UPDATE {detections_table} SET l3_title_id = :l3_id WHERE id = :para_id"),
                        {"l3_id": best_l3_id, "para_id": para_id}
                    )
                    linked_count += 1
        
        db.commit()
        
        return {
            "linked_count": linked_count,
            "skipped_pages": skipped_count,
            "message": f"Auto-linked {linked_count} paragraphs to L3 titles"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error auto-linking paragraphs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


class ParagraphL3LinkRequest(BaseModel):
    paragraph_region_id: int
    l3_title_id: int


@router.put("/books/{book_id}/paragraph-l3-link")
async def update_paragraph_l3_link(book_id: int, request: ParagraphL3LinkRequest):
    """
    Manually link a paragraph to an L3 title (override auto-link).
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        detections_table = f"raw_{prefix}_layout_detections"
        
        # Verify paragraph exists
        para = db.execute(
            text(f"SELECT id, class_name FROM {detections_table} WHERE id = :id"),
            {"id": request.paragraph_region_id}
        ).fetchone()
        
        if not para:
            raise HTTPException(status_code=404, detail="Paragraph region not found")
        
        if para[1] != 'paragraph':
            raise HTTPException(status_code=400, detail=f"Region {request.paragraph_region_id} is not a paragraph (class: {para[1]})")
        
        # Verify L3 title exists
        l3 = db.execute(
            text(f"SELECT id, class_name FROM {detections_table} WHERE id = :id"),
            {"id": request.l3_title_id}
        ).fetchone()
        
        if not l3:
            raise HTTPException(status_code=404, detail="L3 title region not found")
        
        if l3[1] not in ('title_level_3', 'Title L3', 'title_l3'):
            raise HTTPException(status_code=400, detail=f"Region {request.l3_title_id} is not an L3 title (class: {l3[1]})")
        
        # Update the link
        db.execute(
            text(f"UPDATE {detections_table} SET l3_title_id = :l3_id, updated_at = NOW() WHERE id = :para_id"),
            {"l3_id": request.l3_title_id, "para_id": request.paragraph_region_id}
        )
        
        db.commit()
        
        return {
            "message": "Paragraph linked to L3 title successfully",
            "paragraph_id": request.paragraph_region_id,
            "l3_title_id": request.l3_title_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating paragraph L3 link: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# Sync Endpoints (JSON to Database)
# =============================================================================

class TitleSyncRequest(BaseModel):
    titles: Dict[str, List[Dict[str, Any]]]  # {"level1": [...], "level2": [...]}


@router.post("/books/{book_id}/sync-titles-to-db")
async def sync_titles_to_database(book_id: int, request: TitleSyncRequest):
    """
    Sync titles from JSON config to database tables.
    
    This endpoint:
    1. Clears existing L1/L2 titles in database
    2. Inserts new titles from the provided JSON structure
    3. Preserves existing attributes (if title text matches)
    
    Used when saving Auto-Slicer config to keep JSON and DB in sync.
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        l1_table = f"{prefix}_level1_titles"
        l2_table = f"{prefix}_level2_titles"
        
        # Check if tables exist
        if not table_exists(db, l1_table) or not table_exists(db, l2_table):
            raise HTTPException(status_code=400, detail="Title tables not created. Run migration first.")
        
        l1_synced = 0
        l2_synced = 0
        
        # Get existing L1 titles (to preserve attributes)
        existing_l1 = {}
        result = db.execute(text(f"SELECT id, title_text FROM {l1_table}")).fetchall()
        for row in result:
            existing_l1[row[1]] = row[0]  # title_text -> id
        
        # Get existing L2 titles (to preserve attributes)
        existing_l2 = {}
        result = db.execute(text(f"SELECT id, title_text FROM {l2_table}")).fetchall()
        for row in result:
            existing_l2[row[1]] = row[0]  # title_text -> id
        
        # Process L1 titles
        l1_titles = request.titles.get('level1', [])
        new_l1_ids = {}  # title_text -> new_id (for L2 parent linking)
        
        # Delete L1 titles that are no longer in the list
        current_l1_texts = {t.get('title', '') for t in l1_titles}
        for title_text, title_id in existing_l1.items():
            if title_text not in current_l1_texts:
                db.execute(text(f"DELETE FROM {l1_table} WHERE id = :id"), {"id": title_id})
        
        # Insert/update L1 titles
        for idx, t in enumerate(l1_titles):
            title_text = t.get('title', '').strip()
            start_page = t.get('start_page', 1)
            end_page = t.get('end_page', 1)
            
            if not title_text:
                continue
            
            if title_text in existing_l1:
                # Update existing
                db.execute(
                    text(f"""
                        UPDATE {l1_table} 
                        SET start_page = :start_page, end_page = :end_page, display_order = :order, updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": existing_l1[title_text], "start_page": start_page, "end_page": end_page, "order": idx}
                )
                new_l1_ids[title_text] = existing_l1[title_text]
            else:
                # Insert new
                result = db.execute(
                    text(f"""
                        INSERT INTO {l1_table} (title_text, start_page, end_page, display_order)
                        VALUES (:title_text, :start_page, :end_page, :order)
                        RETURNING id
                    """),
                    {"title_text": title_text, "start_page": start_page, "end_page": end_page, "order": idx}
                )
                new_l1_ids[title_text] = result.fetchone()[0]
            
            l1_synced += 1
        
        # Process L2 titles
        l2_titles = request.titles.get('level2', [])
        
        # Delete L2 titles that are no longer in the list
        current_l2_texts = {t.get('title', '') for t in l2_titles}
        for title_text, title_id in existing_l2.items():
            if title_text not in current_l2_texts:
                db.execute(text(f"DELETE FROM {l2_table} WHERE id = :id"), {"id": title_id})
        
        # Insert/update L2 titles
        for idx, t in enumerate(l2_titles):
            title_text = t.get('title', '').strip()
            start_page = t.get('start_page', 1)
            end_page = t.get('end_page', 1)
            
            if not title_text:
                continue
            
            # Find parent L1 based on page range
            parent_l1_id = None
            for l1_text, l1_id in new_l1_ids.items():
                # Get L1 page range
                l1_range = db.execute(
                    text(f"SELECT start_page, end_page FROM {l1_table} WHERE id = :id"),
                    {"id": l1_id}
                ).fetchone()
                if l1_range and l1_range[0] <= start_page and l1_range[1] >= end_page:
                    parent_l1_id = l1_id
                    break
            
            if title_text in existing_l2:
                # Update existing
                db.execute(
                    text(f"""
                        UPDATE {l2_table} 
                        SET start_page = :start_page, end_page = :end_page, parent_l1_id = :parent, display_order = :order, updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": existing_l2[title_text], "start_page": start_page, "end_page": end_page, "parent": parent_l1_id, "order": idx}
                )
            else:
                # Insert new
                db.execute(
                    text(f"""
                        INSERT INTO {l2_table} (title_text, start_page, end_page, parent_l1_id, display_order)
                        VALUES (:title_text, :start_page, :end_page, :parent, :order)
                    """),
                    {"title_text": title_text, "start_page": start_page, "end_page": end_page, "parent": parent_l1_id, "order": idx}
                )
            
            l2_synced += 1
        
        db.commit()
        
        return {
            "success": True,
            "l1_synced": l1_synced,
            "l2_synced": l2_synced,
            "message": f"Synced {l1_synced} L1 titles and {l2_synced} L2 titles to database"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error syncing titles to database: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# Page Status Endpoints (Skip Pages / Ready for Extraction)
# =============================================================================

class PageStatusUpdate(BaseModel):
    page_number: int
    is_skipped: Optional[bool] = None
    is_ready_for_extraction: Optional[bool] = None


@router.put("/books/{book_id}/page-status")
async def update_page_status(book_id: int, request: PageStatusUpdate):
    """
    Update page status (skip or ready for extraction).
    
    When setting is_ready_for_extraction=True, validates that the page
    is covered by both L1 and L2 titles.
    """
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        pages_table = f"raw_{prefix}_pages"
        l1_table = f"{prefix}_level1_titles"
        l2_table = f"{prefix}_level2_titles"
        
        # Check if page exists
        page = db.execute(
            text(f"SELECT id, is_skipped, is_ready_for_extraction FROM {pages_table} WHERE page_number = :page_num"),
            {"page_num": request.page_number}
        ).fetchone()
        
        if not page:
            raise HTTPException(status_code=404, detail=f"Page {request.page_number} not found")
        
        # If setting ready for extraction, validate L1/L2 coverage
        if request.is_ready_for_extraction:
            # Check L1 coverage
            l1_covered = db.execute(
                text(f"""
                    SELECT COUNT(*) FROM {l1_table}
                    WHERE start_page <= :page_num AND end_page >= :page_num
                """),
                {"page_num": request.page_number}
            ).scalar()
            
            if l1_covered == 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Page {request.page_number} is not covered by any L1 title. Please update L1 title page ranges in Auto-Slicer."
                )
            
            # Check L2 coverage
            l2_covered = db.execute(
                text(f"""
                    SELECT COUNT(*) FROM {l2_table}
                    WHERE start_page <= :page_num AND end_page >= :page_num
                """),
                {"page_num": request.page_number}
            ).scalar()
            
            if l2_covered == 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Page {request.page_number} is not covered by any L2 title. Please update L2 title page ranges in Auto-Slicer."
                )
        
        # Build update query
        updates = []
        params = {"page_num": request.page_number}
        
        if request.is_skipped is not None:
            updates.append("is_skipped = :is_skipped")
            params["is_skipped"] = request.is_skipped
            
            # If skipping, also clear ready for extraction
            if request.is_skipped:
                updates.append("is_ready_for_extraction = FALSE")
        
        if request.is_ready_for_extraction is not None:
            updates.append("is_ready_for_extraction = :is_ready")
            params["is_ready"] = request.is_ready_for_extraction
            
            # If marking ready, also clear skip status
            if request.is_ready_for_extraction:
                updates.append("is_skipped = FALSE")
        
        if updates:
            db.execute(
                text(f"UPDATE {pages_table} SET {', '.join(updates)} WHERE page_number = :page_num"),
                params
            )
            db.commit()
        
        return {
            "success": True,
            "page_number": request.page_number,
            "message": "Page status updated"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating page status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/books/{book_id}/page-statuses")
async def get_page_statuses(book_id: int):
    """Get skip and ready status for all pages."""
    db = SessionLocal()
    try:
        prefix = get_book_table_prefix(db, book_id)
        pages_table = f"raw_{prefix}_pages"
        
        result = db.execute(
            text(f"""
                SELECT page_number, is_skipped, is_ready_for_extraction 
                FROM {pages_table} 
                ORDER BY page_number
            """)
        ).fetchall()
        
        pages = [{
            "page_number": row[0],
            "is_skipped": row[1] if row[1] is not None else False,
            "is_ready_for_extraction": row[2] if row[2] is not None else False
        } for row in result]
        
        return {"pages": pages}
    
    except Exception as e:
        logger.error(f"Error getting page statuses: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
