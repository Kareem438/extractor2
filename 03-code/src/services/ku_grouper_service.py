"""
KU Grouper Service

Service for grouping Knowledge Units for batch Claude processing.
Implements Requirement 7B: Knowledge Unit Grouping.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text
from src.database.connection import engine
from src.services.claude_batch_service import estimate_tokens, parse_grouped_response
import logging
import json

logger = logging.getLogger(__name__)


class KUGrouperService:
    """Service for grouping Knowledge Units for batch Claude processing"""
    
    def __init__(self, book_id: int, table_prefix: str):
        self.book_id = book_id
        self.table_prefix = table_prefix
        self.ku_table = f"{table_prefix}_knowledge_units"
        self.config_table = f"{table_prefix}_ku_grouping_config"
    
    def get_grouping_config(self) -> Dict[str, Any]:
        """Get the grouping configuration for this book."""
        sql = text(f"""
            SELECT is_enabled, grouping_mode, max_kus_per_group, 
                   max_tokens_per_group, fallback_attribute
            FROM {self.config_table}
            WHERE id = 1
        """)
        
        with engine.connect() as conn:
            result = conn.execute(sql).fetchone()
            
            if not result:
                return {
                    "is_enabled": False,
                    "grouping_mode": "ku_count",
                    "max_kus_per_group": 5,
                    "max_tokens_per_group": 4000,
                    "fallback_attribute": None
                }
            
            return {
                "is_enabled": result[0],
                "grouping_mode": result[1],
                "max_kus_per_group": result[2],
                "max_tokens_per_group": result[3],
                "fallback_attribute": result[4]
            }

    def get_kus_by_l1_l2(self, execution_mode: str = "individual") -> List[Dict[str, Any]]:
        """
        Get KUs grouped by L1 and L2 titles.
        
        Args:
            execution_mode: 'individual', 'grouped', or 'incomplete'
        
        Returns:
            List of KU records with their L1/L2 titles
        """
        # Build WHERE clause based on execution mode
        where_clause = "WHERE (attr8_value = 'enabled' OR attr8_value IS NULL)"
        
        if execution_mode == "incomplete":
            where_clause += " AND is_complete = FALSE"
        
        sql = text(f"""
            SELECT unit_id, text_content, chapter, topic,
                   is_complete, incomplete_reason
            FROM {self.ku_table}
            {where_clause}
            ORDER BY chapter, topic, unit_id
        """)
        
        with engine.connect() as conn:
            results = conn.execute(sql).fetchall()
            
            return [
                {
                    "unit_id": row[0],
                    "text_content": row[1] or "",
                    "l1_title": row[2] or "No Chapter",
                    "l2_title": row[3] or "No Topic",
                    "is_complete": row[4],
                    "incomplete_reason": row[5]
                }
                for row in results
            ]
    
    def create_groups(self, execution_mode: str = "grouped") -> List[Dict[str, Any]]:
        """
        Create KU groups based on configuration.
        
        Groups KUs by L1+L2 title, then splits into smaller groups
        based on max_kus_per_group or max_tokens_per_group.
        
        Args:
            execution_mode: 'individual', 'grouped', or 'incomplete'
        
        Returns:
            List of groups, each containing:
            - group_id: int
            - l1_title: str
            - l2_title: str
            - ku_ids: List[int]
            - kus: List[dict] (full KU data)
            - total_tokens: int
        """
        config = self.get_grouping_config()
        kus = self.get_kus_by_l1_l2(execution_mode)
        
        if not kus:
            return []
        
        # Group by L1+L2 title first
        title_groups = {}
        for ku in kus:
            key = (ku["l1_title"], ku["l2_title"])
            if key not in title_groups:
                title_groups[key] = []
            title_groups[key].append(ku)
        
        # Now split each title group based on config
        groups = []
        group_id = 1
        
        for (l1_title, l2_title), title_kus in title_groups.items():
            if config["grouping_mode"] == "ku_count":
                # Split by KU count
                max_per_group = config["max_kus_per_group"]
                for i in range(0, len(title_kus), max_per_group):
                    chunk = title_kus[i:i + max_per_group]
                    total_tokens = sum(estimate_tokens(ku["text_content"]) for ku in chunk)
                    
                    groups.append({
                        "group_id": group_id,
                        "l1_title": l1_title,
                        "l2_title": l2_title,
                        "ku_ids": [ku["unit_id"] for ku in chunk],
                        "kus": chunk,
                        "total_tokens": total_tokens
                    })
                    group_id += 1
            else:
                # Split by token limit
                max_tokens = config["max_tokens_per_group"]
                current_group = []
                current_tokens = 0
                
                for ku in title_kus:
                    ku_tokens = estimate_tokens(ku["text_content"])
                    
                    if current_tokens + ku_tokens > max_tokens and current_group:
                        # Save current group and start new one
                        groups.append({
                            "group_id": group_id,
                            "l1_title": l1_title,
                            "l2_title": l2_title,
                            "ku_ids": [k["unit_id"] for k in current_group],
                            "kus": current_group,
                            "total_tokens": current_tokens
                        })
                        group_id += 1
                        current_group = []
                        current_tokens = 0
                    
                    current_group.append(ku)
                    current_tokens += ku_tokens
                
                # Don't forget the last group
                if current_group:
                    groups.append({
                        "group_id": group_id,
                        "l1_title": l1_title,
                        "l2_title": l2_title,
                        "ku_ids": [k["unit_id"] for k in current_group],
                        "kus": current_group,
                        "total_tokens": current_tokens
                    })
                    group_id += 1
        
        return groups

    def build_grouped_prompt(
        self, 
        ku_ids: List[int], 
        prompt_template: str,
        include_attributes: Optional[List[str]] = None
    ) -> str:
        """
        Build prompt with multiple KUs wrapped in ID tags.
        
        Format:
            <ku_123>
                <description>KU text...</description>
                <attr_12>existing value...</attr_12>
            </ku_123>
            <ku_124>
                ...
            </ku_124>
        
        Args:
            ku_ids: List of KU IDs to include
            prompt_template: The prompt template with {grouped_kus} placeholder
            include_attributes: Optional list of attribute columns to include
        
        Returns:
            Complete prompt string with KUs embedded
        """
        if not ku_ids:
            return prompt_template
        
        # Build attribute columns to select
        attr_columns = ""
        if include_attributes:
            attr_columns = ", " + ", ".join(include_attributes)
        
        sql = text(f"""
            SELECT unit_id, text_content{attr_columns}
            FROM {self.ku_table}
            WHERE unit_id IN :ku_ids
            ORDER BY unit_id
        """)
        
        with engine.connect() as conn:
            results = conn.execute(sql, {"ku_ids": tuple(ku_ids)}).fetchall()
        
        # Build grouped KU content
        grouped_content = []
        
        for row in results:
            ku_id = row[0]
            text_content = row[1] or ""
            
            ku_xml = f"<ku_{ku_id}>\n"
            ku_xml += f"    <description>{text_content}</description>\n"
            
            # Add any additional attributes
            if include_attributes:
                for i, attr in enumerate(include_attributes):
                    attr_value = row[i + 2]  # +2 because unit_id and text_content are first
                    if attr_value:
                        ku_xml += f"    <{attr}>{attr_value}</{attr}>\n"
            
            ku_xml += f"</ku_{ku_id}>"
            grouped_content.append(ku_xml)
        
        # Replace placeholder in template
        grouped_kus_str = "\n\n".join(grouped_content)
        
        if "{grouped_kus}" in prompt_template:
            return prompt_template.replace("{grouped_kus}", grouped_kus_str)
        else:
            # If no placeholder, append to end
            return prompt_template + "\n\n" + grouped_kus_str
    
    def distribute_response(
        self,
        response: str,
        ku_ids: List[int],
        tag_mappings: List[Dict],
        fallback_attr: Optional[str] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        Parse grouped response and distribute to individual KUs.
        
        Wrapper around parse_grouped_response from claude_batch_service.
        
        Args:
            response: Claude's response with <ku_ID>...</ku_ID> tags
            ku_ids: List of expected KU IDs
            tag_mappings: List of tag-to-attribute mappings
            fallback_attr: Attribute for unmapped tags
        
        Returns:
            Dict mapping KU ID to extracted data
        """
        return parse_grouped_response(response, ku_ids, tag_mappings, fallback_attr)
    
    def save_ku_results(
        self,
        ku_id: int,
        extracted_data: Dict[str, Any],
        is_complete: bool = True,
        incomplete_reason: Optional[str] = None
    ) -> bool:
        """
        Save extracted data to a KU.
        
        Args:
            ku_id: The KU ID to update
            extracted_data: Dict of attribute -> value
            is_complete: Whether the KU is complete
            incomplete_reason: Reason if incomplete
        
        Returns:
            True if successful
        """
        if not extracted_data and is_complete:
            return True  # Nothing to save
        
        # Build UPDATE query
        updates = []
        params = {"ku_id": ku_id}
        
        for attr, value in extracted_data.items():
            if attr.startswith("attr_"):
                # Convert attr_N to attrN_value
                attr_num = attr.replace("attr_", "")
                col_name = f"attr{attr_num}_value"
                updates.append(f"{col_name} = :{attr}")
                params[attr] = value
        
        updates.append("is_complete = :is_complete")
        params["is_complete"] = is_complete
        
        if incomplete_reason:
            updates.append("incomplete_reason = :incomplete_reason")
            params["incomplete_reason"] = incomplete_reason
        
        updates.append("updated_at = NOW()")
        
        sql = text(f"""
            UPDATE {self.ku_table}
            SET {', '.join(updates)}
            WHERE unit_id = :ku_id
        """)
        
        try:
            with engine.connect() as conn:
                conn.execute(sql, params)
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving KU results for {ku_id}: {e}")
            return False


# =============================================================================
# Helper Functions
# =============================================================================

def get_ku_grouper(book_id: int) -> KUGrouperService:
    """
    Factory function to create a KUGrouperService for a book.
    
    Args:
        book_id: The book ID
    
    Returns:
        KUGrouperService instance
    """
    sql = text("""
        SELECT table_prefix
        FROM books_metadata
        WHERE book_id = :book_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(sql, {"book_id": book_id}).fetchone()
        
        if not result:
            raise ValueError(f"Book {book_id} not found")
        
        table_prefix = result[0]
    
    return KUGrouperService(book_id, table_prefix)


def execute_grouped_pipeline(
    book_id: int,
    step_id: int,
    execution_mode: str = "grouped",
    dry_run: bool = False,
    save_preview_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute pipeline step with grouped KUs.
    
    Args:
        book_id: The book ID
        step_id: The pipeline step ID
        execution_mode: 'individual', 'grouped', or 'incomplete'
        dry_run: If True, don't actually call Claude
        save_preview_to: Attribute to save preview (for dry run)
    
    Returns:
        Execution results
    """
    from src.database.connection import engine
    
    # Get table prefix
    sql = text("""
        SELECT table_prefix
        FROM books_metadata
        WHERE book_id = :book_id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(sql, {"book_id": book_id}).fetchone()
        if not result:
            return {"success": False, "error": "Book not found"}
        table_prefix = result[0]
    
    # Get pipeline step config
    config_table = f"{table_prefix}_pipeline_config"
    sql = text(f"""
        SELECT prompt_template, tag_mappings, fallback_attribute, claude_model
        FROM {config_table}
        WHERE id = :step_id
    """)
    
    with engine.connect() as conn:
        step = conn.execute(sql, {"step_id": step_id}).fetchone()
        if not step:
            return {"success": False, "error": "Pipeline step not found"}
    
    prompt_template = step[0]
    tag_mappings = step[1] or []
    fallback_attr = step[2]
    claude_model = step[3]
    
    # Create grouper and get groups
    grouper = KUGrouperService(book_id, table_prefix)
    
    if execution_mode == "individual":
        # Process each KU individually
        kus = grouper.get_kus_by_l1_l2(execution_mode)
        groups = [
            {
                "group_id": i + 1,
                "ku_ids": [ku["unit_id"]],
                "kus": [ku],
                "total_tokens": estimate_tokens(ku["text_content"])
            }
            for i, ku in enumerate(kus)
        ]
    else:
        groups = grouper.create_groups(execution_mode)
    
    results = {
        "success": True,
        "mode": execution_mode,
        "dry_run": dry_run,
        "total_groups": len(groups),
        "total_kus": sum(len(g["ku_ids"]) for g in groups),
        "groups_processed": 0,
        "kus_processed": 0,
        "kus_incomplete": 0,
        "errors": []
    }
    
    if dry_run:
        # Just build prompts and save preview
        for group in groups:
            prompt = grouper.build_grouped_prompt(group["ku_ids"], prompt_template)
            
            if save_preview_to:
                # Save preview to each KU in the group
                for ku_id in group["ku_ids"]:
                    grouper.save_ku_results(ku_id, {save_preview_to: prompt})
            
            results["groups_processed"] += 1
            results["kus_processed"] += len(group["ku_ids"])
        
        return results
    
    # TODO: Actual Claude API calls would go here
    # For now, just return the dry run results
    results["message"] = "Actual Claude execution not yet implemented"
    
    return results
