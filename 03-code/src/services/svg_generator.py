"""
SVG Generation Service

Generates SVG code from structured JSON data provided by Claude Sonnet 4.5.
Converts image analysis results into scalable vector graphics.

Aligned with sequential-ocr-svg-processing.md architecture.
"""

from typing import Dict, Any, List
from src.utils.logging_config import logger


def generate_svg_from_json(structured_json: Dict[str, Any]) -> str:
    """
    Generate SVG code from Claude API structured JSON.

    Args:
        structured_json: JSON object from Claude with elements, connections, etc.

    Returns:
        Complete SVG code as string

    Raises:
        ValueError: If structured_json is invalid
    """
    if not structured_json:
        raise ValueError("structured_json cannot be empty")

    try:
        layout = structured_json.get('layout', {})
        width = layout.get('estimated_width', 800)
        height = layout.get('estimated_height', 600)
        bg_color = layout.get('background_color', 'transparent')

        svg_parts = [
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'  <!-- Generated from Claude Sonnet 4.5 analysis -->',
            f'  <rect width="{width}" height="{height}" fill="{bg_color}"/>'
        ]

        # Add arrowhead marker definitions
        svg_parts.append(_generate_arrow_markers())

        # Generate elements
        for elem in structured_json.get('elements', []):
            elem_svg = _generate_element_svg(elem)
            if elem_svg:
                svg_parts.append(f'  {elem_svg}')

        # Generate connections
        elements_dict = {e['id']: e for e in structured_json.get('elements', [])}
        for conn in structured_json.get('connections', []):
            conn_svg = _generate_connection_svg(conn, elements_dict)
            if conn_svg:
                svg_parts.append(f'  {conn_svg}')

        # Generate standalone text labels
        for label in structured_json.get('text_labels', []):
            label_svg = _generate_text_label_svg(label)
            if label_svg:
                svg_parts.append(f'  {label_svg}')

        svg_parts.append('</svg>')

        return '\n'.join(svg_parts)

    except Exception as e:
        logger.error(f"SVG generation failed: {e}")
        raise ValueError(f"Failed to generate SVG: {e}")


def _generate_arrow_markers() -> str:
    """Generate SVG marker definitions for arrows."""
    return """  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <polygon points="0 0, 10 3, 0 6" fill="black"/>
    </marker>
  </defs>"""


def _generate_element_svg(elem: Dict[str, Any]) -> str:
    """
    Generate SVG for a single element.

    Args:
        elem: Element dictionary with type, position, size, style, etc.

    Returns:
        SVG string for the element
    """
    elem_type = elem.get('type')
    style = elem.get('style', {})

    if elem_type == 'rectangle':
        pos = elem.get('position', {})
        size = elem.get('size', {})
        return (
            f'<rect x="{pos.get("x", 0)}" y="{pos.get("y", 0)}" '
            f'width="{size.get("width", 100)}" height="{size.get("height", 100)}" '
            f'fill="{style.get("fill", "none")}" stroke="{style.get("stroke", "black")}" '
            f'stroke-width="{style.get("stroke_width", 1)}"/>'
        )

    elif elem_type == 'circle':
        pos = elem.get('position', {})
        radius = elem.get('radius', 20)
        return (
            f'<circle cx="{pos.get("x", 0)}" cy="{pos.get("y", 0)}" r="{radius}" '
            f'fill="{style.get("fill", "none")}" stroke="{style.get("stroke", "black")}" '
            f'stroke-width="{style.get("stroke_width", 1)}"/>'
        )

    elif elem_type == 'ellipse':
        pos = elem.get('position', {})
        size = elem.get('size', {})
        rx = size.get('width', 50) / 2
        ry = size.get('height', 30) / 2
        return (
            f'<ellipse cx="{pos.get("x", 0)}" cy="{pos.get("y", 0)}" rx="{rx}" ry="{ry}" '
            f'fill="{style.get("fill", "none")}" stroke="{style.get("stroke", "black")}" '
            f'stroke-width="{style.get("stroke_width", 1)}"/>'
        )

    elif elem_type == 'line':
        pos = elem.get('position', {})
        end = elem.get('end_position', pos)
        return (
            f'<line x1="{pos.get("x", 0)}" y1="{pos.get("y", 0)}" '
            f'x2="{end.get("x", 100)}" y2="{end.get("y", 100)}" '
            f'stroke="{style.get("stroke", "black")}" '
            f'stroke-width="{style.get("stroke_width", 2)}"/>'
        )

    elif elem_type == 'text':
        pos = elem.get('position', {})
        text = elem.get('text_content', '')
        return (
            f'<text x="{pos.get("x", 0)}" y="{pos.get("y", 0)}" '
            f'font-size="{style.get("font_size", 14)}" '
            f'font-family="{style.get("font_family", "Arial")}" '
            f'font-weight="{style.get("font_weight", "normal")}" '
            f'fill="{style.get("fill", "black")}" '
            f'text-anchor="{style.get("text_anchor", "start")}">{text}</text>'
        )

    elif elem_type == 'polygon':
        points = elem.get('points', [])
        if points:
            points_str = ' '.join([f'{p.get("x", 0)},{p.get("y", 0)}' for p in points])
            return (
                f'<polygon points="{points_str}" '
                f'fill="{style.get("fill", "none")}" stroke="{style.get("stroke", "black")}" '
                f'stroke-width="{style.get("stroke_width", 1)}"/>'
            )

    elif elem_type == 'path':
        points = elem.get('points', [])
        if points:
            path_data = f'M {points[0].get("x", 0)} {points[0].get("y", 0)}'
            for p in points[1:]:
                path_data += f' L {p.get("x", 0)} {p.get("y", 0)}'
            return (
                f'<path d="{path_data}" '
                f'fill="{style.get("fill", "none")}" stroke="{style.get("stroke", "black")}" '
                f'stroke-width="{style.get("stroke_width", 2)}"/>'
            )

    return ''


def _generate_connection_svg(conn: Dict[str, Any], elements: Dict[str, Any]) -> str:
    """
    Generate SVG for connection between elements.

    Args:
        conn: Connection dictionary
        elements: Dictionary of elements by ID

    Returns:
        SVG string for the connection
    """
    from_elem = elements.get(conn.get('from_element'))
    to_elem = elements.get(conn.get('to_element'))

    if not from_elem or not to_elem:
        return ''

    # Calculate connection points (center of elements)
    from_pos = from_elem.get('position', {})
    to_pos = to_elem.get('position', {})
    from_size = from_elem.get('size', {})
    to_size = to_elem.get('size', {})

    x1 = from_pos.get('x', 0) + from_size.get('width', 0) / 2
    y1 = from_pos.get('y', 0) + from_size.get('height', 0) / 2
    x2 = to_pos.get('x', 0) + to_size.get('width', 0) / 2
    y2 = to_pos.get('y', 0) + to_size.get('height', 0) / 2

    style = conn.get('style', {})
    conn_type = conn.get('type', 'line')
    marker_end = 'url(#arrowhead)' if 'arrow' in conn_type else ''

    svg_line = (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{style.get("stroke", "black")}" '
        f'stroke-width="{style.get("stroke_width", 2)}" '
        f'marker-end="{marker_end}"/>'
    )

    # Add label if present
    label = conn.get('label')
    if label:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        svg_line += f'\n  <text x="{mid_x}" y="{mid_y}" font-size="12" fill="black" text-anchor="middle">{label}</text>'

    return svg_line


def _generate_text_label_svg(label: Dict[str, Any]) -> str:
    """
    Generate SVG for standalone text label.

    Args:
        label: Label dictionary with content, position, style

    Returns:
        SVG string for the label
    """
    pos = label.get('position', {})
    content = label.get('content', '')
    style = label.get('style', {})

    return (
        f'<text x="{pos.get("x", 0)}" y="{pos.get("y", 0)}" '
        f'font-size="{style.get("font_size", 14)}" '
        f'font-family="{style.get("font_family", "Arial")}" '
        f'font-weight="{style.get("font_weight", "normal")}" '
        f'fill="{style.get("fill", "black")}">{content}</text>'
    )
