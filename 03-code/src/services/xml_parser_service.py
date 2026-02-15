"""
XML Parser Service

Validates, parses, and extracts fields from LLM XML responses
for V2 cloud extraction. Converts XML to JSON and maps fields
to queryable database columns.
"""

import re
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List, Tuple
from src.utils.logging_config import logger


# XML categories and their tags
XML_CATEGORIES = {
    "A": ["arabic_text", "english_text", "equation", "diagram_image",
          "diagram_description", "diagram_physics_interpretation"],
    "B": ["l1_title", "l2_title", "l3_title", "element_type", "page_number",
          "page_range", "confidence", "source_book", "reading_order", "bbox"],
    "C": ["difficulty_score", "concept_type", "prerequisites", "exam_relevance",
          "complexity_score", "is_top_5_percent", "uniqueness_score", "bloom_taxonomy_level"],
    "D": ["explanation_enrichment", "deep_understanding", "student_pain_points",
          "hardest_problems", "teaching_methodology", "critical_thinking_coaching",
          "faq", "knowledge_gap_backfill", "real_world_scene", "web_research_sources"],
    "E": ["video_script_arabic", "video_script_english", "subtitle_arabic",
          "subtitle_english", "simulation_parameters", "visual_style",
          "video_duration_estimate", "controlnet_reference"],
    "F": ["physics_accuracy_check", "concept_coverage_check", "subtitle_correctness_check",
          "equation_verification", "extraction_confidence", "depth_rmse", "motion_deviation"],
    "G": ["spaced_repetition_interval", "recap_content", "quiz_questions",
          "notification_trigger", "retention_difficulty"],
    "H": ["linked_diagrams", "linked_equations", "related_l3_units", "cross_book_references"],
    "I": ["topic_keywords", "formula_count", "diagram_count", "word_count_arabic",
          "word_count_english", "has_worked_example", "has_problem_set", "physics_domain",
          "mathematical_tools", "real_world_application", "historical_context",
          "common_exam_question_types", "estimated_study_time", "visual_complexity"]
}

# All valid tags (flattened)
ALL_VALID_TAGS = set()
for tags in XML_CATEGORIES.values():
    ALL_VALID_TAGS.update(tags)

# Tags that map to queryable DB columns
QUERYABLE_FIELD_MAP = {
    "l3_title": "l3_title_text",
    "difficulty_score": "difficulty_score",
    "concept_type": "concept_type",
    "bloom_taxonomy_level": "bloom_taxonomy_level",
    "physics_domain": "physics_domain",
    "exam_relevance": "exam_relevance",
    "extraction_confidence": "extraction_confidence",
    "has_worked_example": "has_worked_example",
    "has_problem_set": "has_problem_set",
}


class XMLParserService:
    """Service for parsing and validating LLM XML responses."""

    def validate_xml(self, xml_string: str) -> Tuple[bool, str]:
        """
        Validate that the XML string is well-formed and contains expected structure.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not xml_string or not xml_string.strip():
            return False, "Empty XML response"

        # Extract XML from markdown code blocks if present
        xml_string = self._extract_xml_from_response(xml_string)

        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            return False, f"XML parse error: {str(e)}"

        # Check for knowledge_page root or wrapper
        if root.tag not in ("knowledge_page", "knowledge_pages", "response", "extraction"):
            # Try to find knowledge_page inside
            kp = root.find(".//knowledge_page")
            if kp is None:
                return False, f"No <knowledge_page> element found (root tag: {root.tag})"

        return True, ""

    def parse_xml_response(self, xml_string: str) -> List[Dict[str, Any]]:
        """
        Parse LLM XML response into list of knowledge page dicts.
        
        Each dict contains:
        - All extracted tag values (tag_name -> text_content)
        - queryable_fields: mapped to DB column names
        - raw_xml: the original XML for this knowledge page
        - summary: extracted or generated summary
        - element_count: number of elements found
        
        Returns:
            List of knowledge page dicts (usually 1, sometimes 2+ if window spans boundary)
        """
        xml_string = self._extract_xml_from_response(xml_string)

        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            raise ValueError(f"XML parse error: {str(e)}")

        # Find all knowledge_page elements
        kp_elements = root.findall(".//knowledge_page")
        if not kp_elements:
            # If root itself is knowledge_page
            if root.tag == "knowledge_page":
                kp_elements = [root]
            else:
                raise ValueError("No <knowledge_page> elements found in response")

        results = []
        for kp_elem in kp_elements:
            parsed = self._parse_single_knowledge_page(kp_elem)
            results.append(parsed)

        return results

    def _parse_single_knowledge_page(self, kp_elem) -> Dict[str, Any]:
        """Parse a single <knowledge_page> element into a dict."""
        result = {
            "tags": {},
            "queryable_fields": {},
            "element_count": 0,
            "summary": "",
            "raw_xml": ET.tostring(kp_elem, encoding="unicode"),
        }

        element_count = 0
        for child in kp_elem:
            tag_name = child.tag
            text_content = self._get_element_text(child)
            
            result["tags"][tag_name] = text_content
            element_count += 1

            # Map to queryable fields
            if tag_name in QUERYABLE_FIELD_MAP:
                db_field = QUERYABLE_FIELD_MAP[tag_name]
                result["queryable_fields"][db_field] = self._coerce_value(tag_name, text_content)

        result["element_count"] = element_count

        # Build summary from available fields
        result["summary"] = self._build_summary(result["tags"])

        return result

    def _get_element_text(self, elem) -> str:
        """Get full text content of an element, including nested elements."""
        # If element has children, serialize inner XML
        if len(elem) > 0:
            parts = []
            if elem.text:
                parts.append(elem.text)
            for child in elem:
                parts.append(ET.tostring(child, encoding="unicode"))
            return "".join(parts).strip()
        return (elem.text or "").strip()

    def _coerce_value(self, tag_name: str, value: str) -> Any:
        """Coerce string value to appropriate type for DB storage."""
        if not value:
            return None

        # Integer fields
        if tag_name in ("difficulty_score", "formula_count", "diagram_count",
                        "word_count_arabic", "word_count_english", "estimated_study_time"):
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return None

        # Boolean fields
        if tag_name in ("has_worked_example", "has_problem_set", "is_top_5_percent"):
            return value.lower() in ("true", "yes", "1")

        # Float fields
        if tag_name in ("confidence", "complexity_score", "uniqueness_score"):
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        return value

    def _build_summary(self, tags: Dict[str, str]) -> str:
        """Build a 2-3 line summary from extracted tags."""
        parts = []
        
        if tags.get("l3_title"):
            parts.append(tags["l3_title"])
        
        if tags.get("concept_type"):
            parts.append(f"Type: {tags['concept_type']}")
        
        if tags.get("physics_domain"):
            parts.append(f"Domain: {tags['physics_domain']}")

        if tags.get("deep_understanding"):
            # Take first sentence
            text = tags["deep_understanding"]
            first_sentence = text.split(".")[0] + "." if "." in text else text[:200]
            parts.append(first_sentence)

        return " | ".join(parts) if parts else ""

    def _extract_xml_from_response(self, response: str) -> str:
        """Extract XML from LLM response that may contain markdown code blocks."""
        response = response.strip()

        # Check for ```xml ... ``` blocks
        xml_block_match = re.search(r"```xml\s*(.*?)\s*```", response, re.DOTALL)
        if xml_block_match:
            return xml_block_match.group(1).strip()

        # Check for ``` ... ``` blocks
        code_block_match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)
        if code_block_match:
            content = code_block_match.group(1).strip()
            if content.startswith("<"):
                return content

        # If starts with <, assume it's raw XML
        if response.startswith("<"):
            return response

        # Try to find XML-like content
        xml_match = re.search(r"(<\?xml.*?\?>.*|<knowledge_page.*?>.*</knowledge_page>|<extraction.*?>.*</extraction>)", response, re.DOTALL)
        if xml_match:
            return xml_match.group(1)

        return response

    def xml_to_json(self, xml_string: str) -> Dict[str, Any]:
        """Convert XML string to a JSON-serializable dict."""
        xml_string = self._extract_xml_from_response(xml_string)
        
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            return {"error": f"XML parse error: {str(e)}"}

        return self._element_to_dict(root)

    def _element_to_dict(self, elem) -> Dict[str, Any]:
        """Recursively convert an XML element to a dict."""
        result = {}
        
        # Add attributes
        if elem.attrib:
            result["@attributes"] = dict(elem.attrib)

        # Add children
        children = {}
        for child in elem:
            child_dict = self._element_to_dict(child)
            if child.tag in children:
                # Multiple children with same tag -> list
                if not isinstance(children[child.tag], list):
                    children[child.tag] = [children[child.tag]]
                children[child.tag].append(child_dict)
            else:
                children[child.tag] = child_dict

        if children:
            result.update(children)
        elif elem.text and elem.text.strip():
            result["#text"] = elem.text.strip()

        return result if result else (elem.text or "").strip()

    def extract_l3_boundary(self, xml_string: str) -> Optional[str]:
        """Extract the L3 title from parsed XML (used for smart jump logic)."""
        try:
            parsed = self.parse_xml_response(xml_string)
            if parsed:
                return parsed[-1]["tags"].get("l3_title")
        except Exception:
            pass
        return None

    def get_page_range(self, xml_string: str) -> Optional[Tuple[int, int]]:
        """Extract start/end page from parsed XML."""
        try:
            parsed = self.parse_xml_response(xml_string)
            if parsed:
                page_range = parsed[-1]["tags"].get("page_range", "")
                if "-" in page_range:
                    parts = page_range.split("-")
                    return int(parts[0].strip()), int(parts[1].strip())
                page_num = parsed[-1]["tags"].get("page_number")
                if page_num:
                    p = int(page_num)
                    return p, p
        except Exception:
            pass
        return None
