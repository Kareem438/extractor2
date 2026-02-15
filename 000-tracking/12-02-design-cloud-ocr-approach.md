# Design: Cloud OCR Approach — Phase 1 (Qwen VL + Knowledge Pages)

**Task:** Integrate Qwen VL via DashScope for cloud-based Arabic text extraction
**Date:** 2026-02-12
**Status:** 🔄 Design Verification
**Scope:** Phase 1 only (Qwen extraction → knowledge_pages → review UI → KU conversion)

---

## Overview

Qwen VL vision models via Alibaba Cloud DashScope replace the local OCR workflow. User-annotated pages (marked "Ready for Extraction" in layout-review) become few-shot examples. Qwen processes remaining pages, returning structured JSON per page. Results are stored as knowledge_pages (grouped by L3 title), reviewed in a layout-review-style UI, then converted to individual KU records that feed the existing pipeline.

### Provider: DashScope Only
- API: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` (OpenAI-compatible)
- Implicit prompt caching: cached tokens billed at 20% of standard price
- Models: `qwen-vl-max`, `qwen3-vl-plus`, `qwen3-vl-flash` (user-selectable per run)

### Phase 2 (NOT in scope):
- DeepSeek-R1 reasoning integration
- Pipeline engine cloud model routing
- Cost tracking with per-model pricing
- Fallback to local OCR for cloud-failed pages

---

## API Key Configuration

```python
# In config.py (follows existing ANTHROPIC_API_KEY pattern)
DASHSCOPE_API_KEY: str = Field(default="", description="DashScope API key for Qwen VL models")
DASHSCOPE_BASE_URL: str = Field(default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
```
- 1 key per provider, shared across all books
- Validated at request time (not startup)
- Phase 2 adds: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`

---

## Data Model

### New Table: `{prefix}_knowledge_pages`

```sql
CREATE TABLE {prefix}_knowledge_pages (
    id SERIAL PRIMARY KEY,
    
    -- L3 section boundaries
    l3_title TEXT,
    start_page INTEGER NOT NULL,
    end_page INTEGER NOT NULL,
    
    -- Parent title hierarchy (resolved server-side from title tables)
    l1_title_id INTEGER,
    l2_title_id INTEGER,
    l1_title_text VARCHAR(500),
    l2_title_text VARCHAR(500),
    
    -- The full structured content as JSON
    content JSONB NOT NULL,
    -- JSON structure: {
    --   "elements": [
    --     {
    --       "type": "paragraph|heading|diagram|question|answer|equation|footnote|verse",
    --       "text": "Arabic text content",
    --       "page_number": 42,
    --       "bbox": [x, y, width, height],
    --       "confidence": 0.95,
    --       "order": 1,
    --       "metadata": {}
    --     }
    --   ]
    -- }
    
    -- Processing metadata
    ocr_engine VARCHAR(50) DEFAULT 'qwen-cloud',
    model_name VARCHAR(100),
    cached_tokens INTEGER DEFAULT 0,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    
    -- Status: extracted → reviewed → ready_to_convert → converted
    status VARCHAR(30) DEFAULT 'extracted',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### New Table: `{prefix}_cloud_ocr_pages` (per-page tracking)

```sql
CREATE TABLE {prefix}_cloud_ocr_pages (
    id SERIAL PRIMARY KEY,
    page_number INTEGER NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    error_message TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cached_tokens INTEGER,
    processing_time_ms INTEGER,
    model_name VARCHAR(100),
    attempt_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Contracts

### Cloud OCR Endpoints (`/api/cloud-ocr/`)

#### Start Extraction
```
POST /api/cloud-ocr/start/{book_id}
Body: {
    "model": "qwen-vl-max",           // required: Qwen model name
    "start_page": 1,                   // optional: default = first non-sample page
    "end_page": 600                    // optional: default = last page
}
Response: {
    "success": true,
    "message": "Cloud extraction started",
    "total_pages": 594,
    "few_shot_pages": [5, 12, 45, 78, 120, 200],
    "status": "processing"
}
```
- Few-shot pages auto-detected from "Ready for Extraction" flags
- Returns 400 if DASHSCOPE_API_KEY is empty
- Returns 400 if no pages are marked "Ready for Extraction"

#### Status
```
GET /api/cloud-ocr/status/{book_id}
Response: {
    "status": "running|paused|completed|failed|idle",
    "pages_completed": 150,
    "pages_failed": 3,
    "pages_pending": 441,
    "current_page": 156,
    "total_pages": 594,
    "failed_pages": [42, 88, 201]
}
```

#### Pause / Resume / Cancel
```
POST /api/cloud-ocr/pause/{book_id}
POST /api/cloud-ocr/resume/{book_id}
POST /api/cloud-ocr/cancel/{book_id}
Response: { "success": true, "message": "..." }
```

#### Retry Failed Pages
```
POST /api/cloud-ocr/retry-failed/{book_id}
Response: {
    "success": true,
    "retrying_pages": [42, 88, 201],
    "count": 3
}
```

#### Convert Knowledge Pages to KUs
```
POST /api/cloud-ocr/convert-to-ku/{book_id}
Response: {
    "success": true,
    "knowledge_pages_converted": 45,
    "kus_created": 312,
    "paragraphs_created": 312
}
```

### Knowledge Page Review Endpoints

#### List Knowledge Pages
```
GET /api/cloud-ocr/knowledge-pages/{book_id}
Response: {
    "knowledge_pages": [
        {
            "id": 1,
            "l3_title": "Section title",
            "start_page": 5,
            "end_page": 7,
            "l1_title_text": "Chapter 1",
            "l2_title_text": "Topic A",
            "element_count": 12,
            "status": "extracted"
        }
    ]
}
```

#### Get Knowledge Page Detail
```
GET /api/cloud-ocr/knowledge-pages/{book_id}/{kp_id}
Response: {
    "id": 1,
    "l3_title": "...",
    "content": { "elements": [...] },
    "status": "extracted",
    ...
}
```

#### Update Knowledge Page (edit elements)
```
PUT /api/cloud-ocr/knowledge-pages/{book_id}/{kp_id}
Body: {
    "content": { "elements": [...] },  // updated elements
    "l3_title": "Updated title"        // optional
}
```

#### Toggle "Ready to Convert to KU"
```
POST /api/cloud-ocr/knowledge-pages/{book_id}/{kp_id}/toggle-ready
Response: {
    "success": true,
    "new_status": "ready_to_convert"  // or "reviewed" if toggling off
}
```

---

## Service Layer

### New Files

| File | Purpose |
|------|---------|
| `src/services/qwen_service.py` | DashScope API client, few-shot prompt builder, page extraction |
| `src/api/routes/cloud_ocr.py` | Cloud OCR endpoints (start, pause, resume, cancel, retry, status) |
| `src/api/routes/knowledge_pages.py` | Knowledge page CRUD + review endpoints |
| `src/frontend/templates/knowledge-page-review.html` | Review UI template |
| `src/frontend/static/js/knowledge-page-review.js` | Review UI JavaScript |
| `migrate_add_knowledge_pages.py` | Migration script for new tables |

### Modified Files

| File | Change |
|------|--------|
| `src/config.py` | Add `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL` |
| `src/main.py` | Register new routers |
| `src/database/table_creator.py` | Add knowledge_pages + cloud_ocr_pages table creation |
| `src/frontend/static/js/auto-slicer.js` | Add "Cloud Extraction" section |
| `src/frontend/templates/auto-slicer.html` | Add cloud extraction UI elements |
| `.env` / `.env.example` | Add DashScope env vars |

### Qwen_Service Design

```python
class QwenService:
    def __init__(self, api_key: str, base_url: str):
        self.client = httpx.AsyncClient(...)  # OpenAI-compatible
    
    async def build_few_shot_prompt(self, book_id, sample_pages) -> list[dict]:
        """Build message prefix from annotated pages."""
        # 1. Load page images for sample pages
        # 2. Load layout detection results for each
        # 3. Build expected JSON output from layout detections
        # 4. Return messages: [system_msg, *few_shot_examples]
    
    async def extract_page(self, few_shot_prefix, page_image, page_number, model) -> dict:
        """Extract text from a single page using Qwen VL."""
        # 1. Append page image to few_shot_prefix
        # 2. Call DashScope API
        # 3. Parse JSON response
        # 4. Return {elements: [...], tokens: {...}}
    
    async def run_extraction(self, book_id, model, page_range, on_page_complete):
        """Process all pages with pause/resume support."""
        # 1. Build few-shot prefix once
        # 2. Loop through pages
        # 3. Check pause_requested between pages
        # 4. Track per-page status in DB
        # 5. Call on_page_complete callback for progress updates
```

### Translation Layer

```python
async def translate_to_knowledge_pages(book_id, page_results: dict[int, list]):
    """Group Qwen results by L3 title into knowledge_pages."""
    # 1. Collect all elements across all pages
    # 2. Group by level_3_title (elements with same L3 form one knowledge_page)
    # 3. For each group:
    #    a. Determine start_page, end_page from element page numbers
    #    b. Resolve L1/L2 from title tables by page range
    #    c. Insert into {prefix}_knowledge_pages
```

### Pause/Resume Pattern (mirrors auto-slicer)

```python
_active_cloud_jobs: dict[int, dict] = {}

# Job dict structure:
# {
#     "status": "running|paused|completed|failed|cancelled",
#     "pause_requested": False,
#     "current_page": 42,
#     "pages_completed": 150,
#     "pages_failed": 3,
#     "task": <asyncio.Task>
# }
```

---

## UI Design

### Auto-Slicer Page — Cloud Extraction Section
New section below existing OCR controls:
- Model dropdown: `qwen-vl-max`, `qwen3-vl-plus`, `qwen3-vl-flash`
- "Start Cloud Extraction" button (disabled if no "Ready for Extraction" pages)
- Pause / Resume / Cancel buttons (same pattern as existing auto-slicer)
- Progress: `Pages: 150/594 completed, 3 failed`
- Link to knowledge_page review when done

### Knowledge Page Review UI
Reuses layout-review patterns:
- Page navigation (prev/next, page number input)
- Canvas with page image + element bbox overlays (color-coded by type)
- Sidebar: element list with editable text, type dropdown, L3 title, order
- "Ready to Convert to KU" toggle per knowledge_page
- "Convert All Ready" button for batch conversion
- Arabic mode, zoom controls

---

## Existing Patterns Followed

| Pattern | Source | Reused For |
|---------|--------|------------|
| External API client | `claude_batch_service.py` | `qwen_service.py` |
| Background task + pause/resume | `auto_slicer.py` routes | Cloud OCR execution |
| Per-page flag toggle | `layout-review.js` "Ready for Extraction" | "Ready to Convert to KU" |
| Config with API key | `config.py` ANTHROPIC_API_KEY | DASHSCOPE_API_KEY |
| Canvas + overlay UI | `layout-review.js` | Knowledge page review |
| Table creation per book | `table_creator.py` | knowledge_pages + cloud_ocr_pages |
