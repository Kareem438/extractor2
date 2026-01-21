# Sequential OCR + Integrated SVG Processing Architecture

**Project:** Knowledge Extraction System (12-extractor)
**Date:** 2025-11-07
**Status:** ✅ APPROVED - Updated Architecture
**Type:** Major Architecture Change (Replaces Decision 3 fallback approach)

---

## 📋 Overview

This document describes the **Sequential OCR Processing** architecture combined with **Integrated SVG Generation** for comprehensive document and diagram extraction.

**Key Principles:**
1. ✅ **Sequential OCR**: User-controlled, one OCR engine at a time (GPU memory safety)
2. ✅ **Integrated Processing**: Text + images processed together, page-by-page
3. ✅ **One-Time Image Analysis**: Diagrams/images analyzed once, text can be re-analyzed
4. ✅ **SVG Generation**: All images get comprehensive analysis for SVG reconstruction
5. ✅ **Best-Confidence Selection**: System picks highest quality OCR result

---

## 🎯 System-Reserved Attributes (1-8)

The first 8 attributes are **system-reserved** for OCR results, confidence scores, and record management:

| Attribute | Key Name | Purpose | Populated By |
|-----------|----------|---------|--------------|
| 1 | `related_image` | Image linking (unchanged from original design) | System |
| 2 | `paddleocr_text` | PaddleOCR full text result | PaddleOCR Engine |
| 3 | `surya_ocr_text` | Surya OCR full text result | Surya OCR Engine |
| 4 | `tesseract_text` | Tesseract full text result | Tesseract Engine |
| 5 | `paddleocr_confidence` | PaddleOCR confidence score (0-100) | PaddleOCR Engine |
| 6 | `surya_ocr_confidence` | Surya OCR confidence score (0-100) | Surya OCR Engine |
| 7 | `tesseract_confidence` | Tesseract confidence score (0-100) | Tesseract Engine |
| 8 | `record_status` | Record status: "enabled" or "disabled" (merged) | System / User |

**User-Defined Attributes:** 9-40 (32 custom attributes available)

---

## 🔄 Complete Processing Workflow

### **Phase 1: OCR Processing (User-Initiated, Sequential)**

User can run any of these buttons independently, in any order:

#### **Button 1: "Start with PaddleOCR"**

**Triggered:** User clicks "Start with PaddleOCR" on upload page

**Processing:**
```
FOR each page (1 to N):
    ┌─ Step 1: Text Analysis (PaddleOCR GPU)
    │  ├─ Load PaddleOCR into GPU (6GB VRAM)
    │  ├─ Render page to 300 DPI image
    │  ├─ Run PaddleOCR on image
    │  ├─ Extract: text, confidence
    │  └─ Store: attr2_value = text, attr5_value = confidence
    │
    ├─ Step 2: Image Analysis (Claude API) - ONE TIME ONLY
    │  ├─ Extract all images from page
    │  ├─ FOR each image:
    │  │  ├─ Check: if image already processed → SKIP
    │  │  ├─ Send image to Claude Sonnet 4.5 API
    │  │  ├─ Receive: description + structured_json
    │  │  ├─ Generate SVG from structured_json
    │  │  └─ Store in book_images table:
    │  │     ├─ image_data (BYTEA - original)
    │  │     ├─ ai_description (TEXT)
    │  │     ├─ structured_json (JSONB)
    │  │     ├─ svg_code (TEXT)
    │  │     └─ image_type (diagram/photo/screenshot/etc.)
    │  │
    │  └─ Update processing_state: page N complete
    │
    └─ WebSocket update: Progress (every 5 seconds)

Unload PaddleOCR from GPU
Status: "PaddleOCR Complete, Images Analyzed"
```

**Key Points:**
- ✅ Text and images processed together on each page
- ✅ Images analyzed ONCE (first OCR run only)
- ✅ Sequential storage: all page 1 data, then page 2, etc.

#### **Button 2: "Start with Surya OCR"** (Later, Optional)

**Triggered:** User clicks "Start with Surya OCR" after PaddleOCR

**Processing:**
```
FOR each page (1 to N):
    ┌─ Step 1: Text Analysis (Surya OCR GPU)
    │  ├─ Load Surya OCR into GPU (2GB+ VRAM)
    │  ├─ Render page to 300 DPI image
    │  ├─ Run Surya OCR on image
    │  ├─ Extract: text, confidence
    │  └─ UPDATE existing record:
    │     ├─ attr3_value = text
    │     └─ attr6_value = confidence
    │
    ├─ Step 2: Image Analysis SKIPPED
    │  └─ Images already processed during first OCR run
    │
    └─ WebSocket update: Progress (every 5 seconds)

Unload Surya OCR from GPU
Status: "Surya OCR Complete"
```

#### **Button 3: "Start with Tesseract"** (Later, Optional)

**Triggered:** User clicks "Start with Tesseract"

**Processing:**
```
FOR each page (1 to N):
    ┌─ Step 1: Text Analysis (Tesseract CPU)
    │  ├─ Load Tesseract (CPU-based, no GPU)
    │  ├─ Render page to 300 DPI image
    │  ├─ Run Tesseract on image
    │  ├─ Extract: text, confidence
    │  └─ UPDATE existing record:
    │     ├─ attr4_value = text
    │     └─ attr7_value = confidence
    │
    ├─ Step 2: Image Analysis SKIPPED
    │  └─ Images already processed during first OCR run
    │
    └─ WebSocket update: Progress (every 5 seconds)

Status: "Tesseract Complete"
```

---

### **Phase 2: Evaluation and Full Pipeline (User-Initiated)**

#### **Button 4: "Evaluate, Split and Mark"**

**Triggered:** User clicks "Evaluate, Split and Mark" after one or more OCR engines complete

**Processing:**
```
Step 1: Evaluation (Best Confidence Selection)
├─ FOR each page record:
│  ├─ Read confidence scores:
│  │  ├─ attr5_value (PaddleOCR confidence)
│  │  ├─ attr6_value (Surya OCR confidence)
│  │  └─ attr7_value (Tesseract confidence)
│  │
│  ├─ Compare confidence scores
│  ├─ Select highest confidence
│  ├─ Copy winning text to main `text` field
│  └─ Store winning method in `ocr_method` field
│
Step 2: Splitter Agent
├─ Read `text` field (best OCR result)
├─ Split into 3-5 line semantic chunks
├─ Use sentence-transformers for semantic boundaries
├─ Assign confidence scores to splits
└─ Create knowledge units (one per chunk)

Step 3: Marker Agent
├─ Read page images
├─ Generate marked images with green rectangles around text
├─ Generate marked images with orange rectangles for linked text
└─ Store marked page images to book_pages table

Step 4: Image-Reader Agent (Linking Only)
├─ Images already analyzed and stored
├─ Update knowledge_units records with image links
└─ Set attr1_value = "image_id:IMG-68, page:136, figure:5.3"

Status: "Processing Complete - Ready for Verification"
```

---

## 📊 Database Schema

### **`book{N}_{name}_attribute_keys` Table (UPDATED)**

```sql
CREATE TABLE book1_mybook_attribute_keys (
    id SERIAL PRIMARY KEY,
    attr_number INTEGER NOT NULL UNIQUE CHECK (attr_number BETWEEN 1 AND 40),
    key_name VARCHAR(100),
    is_system_reserved BOOLEAN DEFAULT false,
    is_editable BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Pre-populate with system-reserved attributes
INSERT INTO book1_mybook_attribute_keys (attr_number, key_name, is_system_reserved, is_editable) VALUES
(1, 'related_image', true, false),
(2, 'paddleocr_text', true, false),
(3, 'surya_ocr_text', true, false),
(4, 'tesseract_text', true, false),
(5, 'paddleocr_confidence', true, false),
(6, 'surya_ocr_confidence', true, false),
(7, 'tesseract_confidence', true, false),
(8, NULL, false, true),  -- User-defined
(9, NULL, false, true),  -- User-defined
...
(30, NULL, false, true); -- User-defined
```

### **`book{N}_{name}_knowledge_units` Table (UPDATED)**

```sql
CREATE TABLE book1_mybook_knowledge_units (
    id SERIAL PRIMARY KEY,

    -- Primary text (best OCR result after evaluation)
    text TEXT NOT NULL,

    -- OCR metadata
    ocr_method VARCHAR(20),  -- NEW: "paddleocr" | "surya" | "tesseract"
    confidence_score DECIMAL(5,2),  -- Best confidence from selected OCR

    -- Page information
    page_number INTEGER NOT NULL,
    position_x INTEGER,
    position_y INTEGER,

    -- Language
    language VARCHAR(20),  -- "english" | "arabic" | "mixed"

    -- Hierarchy
    chapter VARCHAR(255),
    topic VARCHAR(255),
    sub_topic VARCHAR(255),

    -- Verification
    verified BOOLEAN DEFAULT false,
    notes TEXT,

    -- System-reserved attributes (1-7)
    attr1_value TEXT,  -- related_image
    attr2_value TEXT,  -- paddleocr_text (FULL TEXT)
    attr3_value TEXT,  -- surya_ocr_text (FULL TEXT)
    attr4_value TEXT,  -- tesseract_text (FULL TEXT)
    attr5_value TEXT,  -- paddleocr_confidence
    attr6_value TEXT,  -- surya_ocr_confidence
    attr7_value TEXT,  -- tesseract_confidence
    attr8_value TEXT DEFAULT 'enabled',  -- record_status ('enabled' or 'disabled')

    -- User-defined attributes (9-40)
    attr9_value TEXT,
    attr10_value TEXT,
    attr11_value TEXT,
    ...
    attr40_value TEXT,

    -- Record merging/splitting tracking
    merged_into_record_id INTEGER REFERENCES book1_mybook_knowledge_units(id),
    original_record_ids TEXT[],  -- Array of original IDs if this is a merged record

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_page_number (page_number),
    INDEX idx_verified (verified),
    INDEX idx_ocr_method (ocr_method),
    INDEX idx_record_status (attr8_value)
);
```

### **`book{N}_{name}_images` Table (UPDATED WITH SVG)**

```sql
CREATE TABLE book1_mybook_images (
    id SERIAL PRIMARY KEY,

    -- Image identification
    image_id VARCHAR(50) UNIQUE NOT NULL,  -- e.g., "IMG-68"
    page_number INTEGER NOT NULL,

    -- Original image
    image_data BYTEA NOT NULL,

    -- Image metadata
    image_type VARCHAR(50),  -- "diagram" | "flowchart" | "photo" | "screenshot" | "technical_illustration" | "chart" | "graph" | "table"
    dimensions VARCHAR(20),  -- "800x600"
    file_size INTEGER,       -- bytes

    -- AI Analysis Results (Claude Sonnet 4.5)
    ai_description TEXT,     -- Human-readable description
    structured_json JSONB,   -- Structured data for SVG generation
    svg_code TEXT,           -- NEW: Generated SVG code

    -- Processing metadata
    confidence_score DECIMAL(5,2),
    analyzed_at TIMESTAMP DEFAULT NOW(),
    analyzed_during_ocr VARCHAR(20),  -- "paddleocr" | "surya" | "tesseract" (which OCR run triggered this)

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_page_number (page_number),
    INDEX idx_image_type (image_type)
);
```

### **`book{N}_{name}_processing_state` Table (UPDATED)**

```sql
CREATE TABLE book1_mybook_processing_state (
    id SERIAL PRIMARY KEY,

    -- Progress tracking
    current_page INTEGER NOT NULL,
    total_pages INTEGER NOT NULL,

    -- OCR completion flags
    paddleocr_complete BOOLEAN DEFAULT false,
    surya_ocr_complete BOOLEAN DEFAULT false,
    tesseract_complete BOOLEAN DEFAULT false,

    -- Image processing flag
    images_processed BOOLEAN DEFAULT false,

    -- Pipeline completion
    evaluation_complete BOOLEAN DEFAULT false,
    splitter_complete BOOLEAN DEFAULT false,
    marker_complete BOOLEAN DEFAULT false,

    -- Current agent
    current_agent VARCHAR(50),  -- "paddleocr" | "surya" | "tesseract" | "image_reader" | "splitter" | "marker"

    -- Overall status
    status VARCHAR(20),  -- "ocr_pending" | "ocr_running" | "ocr_partial" | "ocr_complete" | "evaluation_complete" | "processing" | "complete"

    -- Timestamps
    last_updated TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

---

## 🖼️ Image Analysis with Claude Sonnet 4.5

### **Claude API Prompt (Comprehensive)**

```python
CLAUDE_COMPREHENSIVE_IMAGE_ANALYSIS_PROMPT = """
Analyze this image comprehensively. It may be a diagram, flowchart, screenshot, photo,
technical illustration, chart, graph, table, or any other visual content from a document.

Your analysis should be detailed enough to allow SVG reconstruction of the image.

Please provide:

1. **Image Type Classification:**
   Identify the primary type from: diagram, flowchart, architecture_diagram, UML_diagram,
   network_diagram, process_flow, mind_map, screenshot, photo, bar_chart, line_graph,
   pie_chart, table, technical_illustration, schematic, other

2. **Human-Readable Description:**
   Provide a comprehensive textual description that captures:
   - What the image shows (main subject/purpose)
   - All visible elements and their arrangement
   - All text content and labels
   - Colors, styles, and visual characteristics
   - Spatial relationships between elements
   - Any notable details or annotations

   This description should be detailed enough that someone could understand the
   image's content and purpose without seeing it.

3. **Structured Data for SVG Generation:**
   Provide a JSON object with this structure:

   {
     "diagram_type": "string (from classification above)",
     "layout": {
       "estimated_width": number (pixels),
       "estimated_height": number (pixels),
       "orientation": "landscape" | "portrait" | "square",
       "background_color": "#hex or 'transparent'"
     },
     "elements": [
       {
         "id": "unique_element_id",
         "type": "rectangle" | "circle" | "ellipse" | "polygon" | "line" | "arrow" | "text" | "image" | "path",
         "position": {"x": number, "y": number},
         "size": {"width": number, "height": number} (for shapes),
         "radius": number (for circles),
         "points": [{"x": number, "y": number}, ...] (for polygons/paths),
         "text_content": "string" (if element contains text),
         "style": {
           "fill": "#color or 'none'",
           "stroke": "#color",
           "stroke_width": number,
           "font_size": number (for text),
           "font_family": "string" (for text),
           "font_weight": "normal" | "bold",
           "text_anchor": "start" | "middle" | "end",
           "opacity": number (0-1)
         },
         "children": [] (nested elements if applicable)
       }
     ],
     "connections": [
       {
         "id": "unique_connection_id",
         "from_element": "element_id",
         "to_element": "element_id",
         "type": "arrow" | "line" | "double_arrow" | "dashed_arrow",
         "label": "connection label text (optional)",
         "label_position": "middle" | "start" | "end",
         "style": {
           "stroke": "#color",
           "stroke_width": number,
           "stroke_dasharray": "5,5" (for dashed lines, optional),
           "marker_end": "arrow" | "circle" | "none"
         }
       }
     ],
     "text_labels": [
       {
         "content": "standalone text content",
         "position": {"x": number, "y": number},
         "style": {
           "font_size": number,
           "font_family": "string",
           "font_weight": "normal" | "bold",
           "fill": "#color"
         }
       }
     ],
     "additional_details": {
       "title": "diagram title (if present)",
       "legend_items": ["item1", "item2"],
       "notes": "any annotations or notes",
       "data_values": {} (for charts/graphs - key data points)
     }
   }

For non-diagram images (photos, screenshots without diagrams):
- Provide best-effort structured data describing key regions and visual elements
- Focus on layout, text content, and identifiable components

**IMPORTANT:** Return ONLY valid JSON in this exact format:
{
  "image_type": "...",
  "description": "...",
  "structured_json": { ... }
}

Do not include any explanatory text outside the JSON structure.
"""
```

### **SVG Generation Implementation**

```python
async def generate_svg_from_json(structured_json: dict) -> str:
    """
    Generate SVG code from Claude API structured JSON

    Args:
        structured_json: JSON object from Claude with elements, connections, etc.

    Returns:
        Complete SVG code as string
    """
    layout = structured_json.get('layout', {})
    width = layout.get('estimated_width', 800)
    height = layout.get('estimated_height', 600)
    bg_color = layout.get('background_color', 'transparent')

    svg_parts = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="{bg_color}"/>'
    ]

    # Generate elements
    for elem in structured_json.get('elements', []):
        elem_svg = _generate_element_svg(elem)
        if elem_svg:
            svg_parts.append(elem_svg)

    # Generate connections
    elements_dict = {e['id']: e for e in structured_json.get('elements', [])}
    for conn in structured_json.get('connections', []):
        conn_svg = _generate_connection_svg(conn, elements_dict)
        if conn_svg:
            svg_parts.append(conn_svg)

    # Generate standalone text labels
    for label in structured_json.get('text_labels', []):
        label_svg = _generate_text_label_svg(label)
        if label_svg:
            svg_parts.append(label_svg)

    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)


def _generate_element_svg(elem: dict) -> str:
    """Generate SVG for a single element"""
    elem_type = elem.get('type')
    style = elem.get('style', {})

    if elem_type == 'rectangle':
        pos = elem['position']
        size = elem['size']
        return f'''<rect x="{pos['x']}" y="{pos['y']}" width="{size['width']}" height="{size['height']}"
                   fill="{style.get('fill', 'none')}" stroke="{style.get('stroke', 'black')}"
                   stroke-width="{style.get('stroke_width', 1)}"/>'''

    elif elem_type == 'circle':
        pos = elem['position']
        radius = elem.get('radius', 20)
        return f'''<circle cx="{pos['x']}" cy="{pos['y']}" r="{radius}"
                   fill="{style.get('fill', 'none')}" stroke="{style.get('stroke', 'black')}"
                   stroke-width="{style.get('stroke_width', 1)}"/>'''

    elif elem_type == 'text':
        pos = elem['position']
        text = elem.get('text_content', '')
        return f'''<text x="{pos['x']}" y="{pos['y']}"
                   font-size="{style.get('font_size', 14)}"
                   font-family="{style.get('font_family', 'Arial')}"
                   fill="{style.get('fill', 'black')}"
                   text-anchor="{style.get('text_anchor', 'start')}">{text}</text>'''

    # Add more element types (ellipse, polygon, line, arrow, path)
    # ...

    return ''


def _generate_connection_svg(conn: dict, elements: dict) -> str:
    """Generate SVG for connection between elements"""
    from_elem = elements.get(conn['from_element'])
    to_elem = elements.get(conn['to_element'])

    if not from_elem or not to_elem:
        return ''

    # Calculate connection points (center of elements)
    x1 = from_elem['position']['x'] + from_elem.get('size', {}).get('width', 0) / 2
    y1 = from_elem['position']['y'] + from_elem.get('size', {}).get('height', 0) / 2
    x2 = to_elem['position']['x'] + to_elem.get('size', {}).get('width', 0) / 2
    y2 = to_elem['position']['y'] + to_elem.get('size', {}).get('height', 0) / 2

    style = conn.get('style', {})
    marker_end = 'url(#arrowhead)' if conn.get('type') in ['arrow', 'double_arrow'] else ''

    svg_line = f'''<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"
                   stroke="{style.get('stroke', 'black')}"
                   stroke-width="{style.get('stroke_width', 2)}"
                   marker-end="{marker_end}"/>'''

    # Add label if present
    label = conn.get('label')
    if label:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        svg_line += f'''<text x="{mid_x}" y="{mid_y}" font-size="12" fill="black">{label}</text>'''

    return svg_line
```

---

## 🎨 Verification Interface - Side-by-Side View

### **Image Detail View (UPDATED)**

When user clicks on an image in verification interface:

```
┌─────────────────────────────────────────────────────────────┐
│  Image Detail View - IMG-68 (Page 136)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────┐  ┌───────────────────┐             │
│  │  Original Image   │  │  Generated SVG    │             │
│  │  (from BYTEA)     │  │  (from svg_code)  │             │
│  │                   │  │                   │             │
│  │  [Image preview]  │  │  [SVG rendering]  │             │
│  │                   │  │                   │             │
│  │                   │  │                   │             │
│  └───────────────────┘  └───────────────────┘             │
│                                                              │
│  Type: Flowchart                                            │
│  Dimensions: 800x600                                        │
│  Confidence: 95%                                            │
│                                                              │
│  Description:                                               │
│  ┌────────────────────────────────────────────────────────┐│
│  │ This flowchart shows a decision-making process with    ││
│  │ 5 main steps: Input validation → Process data →        ││
│  │ Decision point → Output results or Error handling.     ││
│  │ Contains 3 rectangular process boxes, 1 diamond        ││
│  │ decision box, and directional arrows connecting them.  ││
│  └────────────────────────────────────────────────────────┘│
│                                                              │
│  [✅ Approve] [❌ Flag for Review] [🔄 Regenerate SVG]      │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚡ GPU Memory Management

### **Sequential Loading with Safety Checks**

```python
import torch
import gc

class GPUMemoryManager:
    """Manage GPU memory for sequential OCR model loading"""

    @staticmethod
    def get_available_gpu_memory() -> int:
        """Returns available GPU memory in MB"""
        if torch.cuda.is_available():
            free_memory, total_memory = torch.cuda.mem_get_info()
            return free_memory / 1024 / 1024  # Convert to MB
        return 0

    @staticmethod
    def unload_model_safely(model, model_name: str = "Model"):
        """Safely unload model and clear GPU cache"""
        logger.info(f"Unloading {model_name} from GPU...")

        del model
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

        available_after = GPUMemoryManager.get_available_gpu_memory()
        logger.info(f"{model_name} unloaded. Available GPU memory: {available_after:.0f} MB")

    @staticmethod
    def check_sufficient_memory(required_mb: int, model_name: str) -> bool:
        """Check if sufficient GPU memory available"""
        available = GPUMemoryManager.get_available_gpu_memory()

        if available < required_mb:
            logger.error(f"Insufficient GPU memory for {model_name}. Required: {required_mb} MB, Available: {available:.0f} MB")
            return False

        logger.info(f"Sufficient GPU memory for {model_name}. Required: {required_mb} MB, Available: {available:.0f} MB")
        return True

    @staticmethod
    def log_gpu_usage():
        """Log current GPU memory usage"""
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024 / 1024
            reserved = torch.cuda.memory_reserved() / 1024 / 1024
            available = GPUMemoryManager.get_available_gpu_memory()

            logger.info(f"GPU Memory - Allocated: {allocated:.0f} MB, Reserved: {reserved:.0f} MB, Available: {available:.0f} MB")
```

---

## 📋 Upload Page UI (4 Buttons)

```html
<!-- Step 5: Start OCR Processing -->
<div class="section">
    <h2>Step 5: Start OCR Processing</h2>

    <div class="ocr-info-box">
        <strong>📖 How Sequential OCR Works:</strong><br>
        • Run one or more OCR engines to extract text<br>
        • Images are analyzed automatically during the FIRST OCR run<br>
        • Click "Evaluate, Split and Mark" when ready to finalize<br>
        • System will select the best OCR result based on confidence scores
    </div>

    <div class="ocr-buttons-section">
        <h3>⚡ OCR Engines (Run independently):</h3>

        <button class="btn-ocr btn-paddleocr">
            🚀 Start with PaddleOCR (GPU)
        </button>
        <p class="ocr-note">Fast, GPU-accelerated, good for clean text. ~30 mins for 500 pages.</p>

        <button class="btn-ocr btn-surya">
            🎯 Start with Surya OCR (GPU)
        </button>
        <p class="ocr-note">Slower, higher quality, excellent multilingual support. ~60 mins for 500 pages.</p>

        <button class="btn-ocr btn-tesseract">
            🛡️ Start with Tesseract (CPU)
        </button>
        <p class="ocr-note">CPU-based fallback, very reliable. ~45 mins for 500 pages.</p>
    </div>

    <div class="evaluation-section">
        <h3>After OCR engines complete:</h3>

        <button class="btn-evaluate">
            ✅ Evaluate, Split and Mark
        </button>
        <p class="ocr-note">Compares OCR results, selects best text, runs splitter and marker agents.</p>
    </div>

    <div class="tip-box">
        💡 <strong>Tip:</strong> Run all 3 OCR engines for best quality comparison,
        then click "Evaluate, Split and Mark" to let the system pick the best result.
    </div>
</div>
```

---

## ✅ Summary of Changes

### **From Original Design:**
- ❌ Automatic 3-tier fallback (PaddleOCR → Surya → Tesseract)
- ❌ Single "Start Processing" button
- ❌ Basic image analysis (description only)

### **To New Design:**
- ✅ User-controlled sequential OCR (4 buttons)
- ✅ Integrated text + image processing (page-by-page)
- ✅ One-time image analysis (during first OCR run)
- ✅ Comprehensive SVG generation for all images
- ✅ Best-confidence automatic selection
- ✅ GPU memory safety (sequential loading/unloading)
- ✅ 7 system-reserved attributes (OCR results + confidence)
- ✅ 23 user-defined attributes (down from 29)

---

**Status:** ✅ DOCUMENTED AND APPROVED
**Ready for:** Implementation
