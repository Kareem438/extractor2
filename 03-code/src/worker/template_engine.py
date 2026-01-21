"""
Template Variable Substitution Engine

Handles variable substitution in prompt templates using data from PostgreSQL or ChromaDB.
Supports both original column names (e.g., attr2_value) and user-defined names (e.g., easyocr_result).
"""

import re
from typing import Dict, Any, Optional, List
from sqlalchemy import text
from src.database.connection import engine


class TemplateEngine:
    """Engine for substituting template variables in prompts"""

    def __init__(self, table_prefix: str):
        """
        Initialize template engine for a specific book.

        Args:
            table_prefix: Table prefix for this book (e.g., 'book1_example')
        """
        self.table_prefix = table_prefix
        self.variable_map: Optional[Dict[str, str]] = None

    def load_variable_map(self) -> Dict[str, str]:
        """
        Load variable mapping from attribute_keys table.

        Returns mapping of both original names and user-defined names to column names.
        Example:
            {
                'text_content': 'text_content',
                'attr2_value': 'attr2_value',
                'easyocr_result': 'attr2_value',  # User-defined alias
                ...
            }
        """
        if self.variable_map is not None:
            return self.variable_map

        attribute_keys_table = f"{self.table_prefix}_attribute_keys"

        sql = text(f"""
        SELECT attr_number, key_name
        FROM {attribute_keys_table}
        WHERE key_name IS NOT NULL
        ORDER BY attr_number
        """)

        variable_map = {}

        # Add standard columns that aren't in attribute_keys
        variable_map['text_content'] = 'text_content'
        variable_map['page_number'] = 'page_number'
        variable_map['chapter'] = 'chapter'
        variable_map['topic'] = 'topic'
        variable_map['sub_topic'] = 'sub_topic'

        with engine.connect() as conn:
            result = conn.execute(sql)
            for row in result:
                attr_number, key_name = row
                column_name = f"attr{attr_number}_value"

                # Map both original column name AND user-defined name to column
                variable_map[column_name] = column_name
                if key_name:
                    variable_map[key_name] = column_name

        self.variable_map = variable_map
        return variable_map

    def find_variables(self, template: str) -> List[str]:
        """
        Extract all template variables from a template string.

        Args:
            template: Template string with {{variable}} placeholders

        Returns:
            List of variable names found in template
        """
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, template)
        return [match.strip() for match in matches]

    def substitute(
        self,
        template: str,
        data: Dict[str, Any],
        raise_on_missing: bool = False
    ) -> str:
        """
        Substitute template variables with actual values.

        Args:
            template: Template string with {{variable}} placeholders
            data: Dictionary of column_name -> value
            raise_on_missing: If True, raise error when variable not found

        Returns:
            Template with all variables substituted

        Raises:
            ValueError: If variable not found and raise_on_missing=True
        """
        # Load variable mapping if not already loaded
        variable_map = self.load_variable_map()

        # Find all variables in template
        variables = self.find_variables(template)

        result = template

        for var_name in variables:
            # Resolve variable name to actual column name
            column_name = variable_map.get(var_name)

            if column_name is None:
                if raise_on_missing:
                    raise ValueError(
                        f"Unknown template variable: {{{{var_name}}}}. "
                        f"Available variables: {list(variable_map.keys())}"
                    )
                # Replace with empty string if variable not found
                value = ""
            else:
                # Get value from data
                value = data.get(column_name, "")

            # Convert to string and substitute
            placeholder = "{{" + var_name + "}}"
            result = result.replace(placeholder, str(value) if value is not None else "")

        return result

    def get_available_variables(self) -> Dict[str, str]:
        """
        Get all available template variables and their descriptions.

        Returns:
            Dictionary mapping variable names to column names
        """
        return self.load_variable_map()

    def validate_template(self, template: str) -> tuple[bool, Optional[str]]:
        """
        Validate a template string.

        Args:
            template: Template string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not template:
            return True, None

        try:
            # Find all variables
            variables = self.find_variables(template)

            # Load variable map
            variable_map = self.load_variable_map()

            # Check for unknown variables
            unknown_vars = [v for v in variables if v not in variable_map]

            if unknown_vars:
                return False, f"Unknown variables: {', '.join(unknown_vars)}"

            return True, None

        except Exception as e:
            return False, f"Template validation error: {str(e)}"


def create_template_engine(table_prefix: str) -> TemplateEngine:
    """
    Factory function to create a template engine.

    Args:
        table_prefix: Table prefix for the book

    Returns:
        Configured TemplateEngine instance
    """
    return TemplateEngine(table_prefix)
