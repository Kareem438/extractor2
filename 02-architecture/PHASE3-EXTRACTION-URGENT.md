# Phase 3B: Extract Knowledge Units - Urgent Requirements

**Created:** 2026-01-16
**Status:** REQUIREMENTS FINALIZED - Ready for Implementation
**Priority:** URGENT
**Estimated Effort:** ~35-45 hours

---

## Overview

This phase implements a new "Extract Knowledge Units" feature accessible from the Auto-Slicer page. It extracts paragraphs (via Surya OCR) and diagrams/tables/equations/lists (saved as images for Claude decoding) from Layout Review regions into the existing database tables.

---

## Key Features

1. **Extraction Page** (`/extract-knowledge?book_id=X`)
2. **Page Selection Table** - Shows pages ready for extraction
3. **Surya OCR Extraction** - Extract paragraph text at 600 DPI
4. **Image Extraction** - Save diagrams/tables/equations/lists as images
5. **Claude Batch Decoding** - Async batch API (50% cost) or direct API
6. **Diagram Preview** - Test prompts before batch decoding
7. **Per-Class Prompts** - Different prompts for different region classes
8. **Summary Table** - Counts per L3 title with decode status

---

## Detailed Requirements

### 1. Access Point & Button Location

**Location:** Auto-Slicer page, next to "Review Layout Detection" button
**Button Text:** "Extract Knowledge Units"
**Action:** Opens new page at `/extract-knowledge?book_id=X`

---

### 2. Page Selection Table

**Shows:** Only pages marked as "Ready for Extraction" in Layout Review

**Columns:**
| Column | Description |
|--------|-------------|
| Checkbox | Select for extraction |
| Page # | Page number |
| Status | Not Extracted / Extracted |
| Paragraphs | Count of paragraph regions |
| Diagrams | Count of diagram/table/equation/list regions |

**Behaviors:**
- Multi-select with checkboxes
- "Select All" / "Deselect All" buttons
- **Selection persisted in DB** across sessions
- **Extracted pages CANNOT be re-extracted** (checkbox disabled)

---

### 3. Validation: Ready for Extraction Button

**CRITICAL:** When user clicks "Ready for Extraction" in Layout Review:
- Check if ALL diagrams/tables/equations/lists have a linked parent paragraph
- If any region lacks parent paragraph → **Show error message**
- Block marking as ready until all links are created
- This prevents accumulating orphan diagrams

---

### 4. Pre-Extraction Summary

Before extraction starts, show confirmation dialog:
```
Ready to Extract:
- Pages: 5 selected
- Paragraphs: ~42 regions
- Diagrams: ~18 regions
- Tables: ~6 regions
- Equations: ~3 regions
- Lists: ~12 regions

[Cancel] [Extract]
```

---

### 5. Extraction Process

**Processing Order:** Sequential by page number (maintains L3 title scope)

**Progress Display:**
- Progress bar showing current page / total pages
- Live count of extracted items
- Current page number being processed

#### 5.1 Paragraph Extraction (Surya OCR)

**Applies to:** Regions classified as `paragraph` only

**Process:**
1. Load Surya OCR to GPU if not loaded
2. Extract image of region from page (600 DPI)
3. Run Surya OCR to get text
4. Look up L1/L2 titles from `auto_slicer_config` based on page number
5. OCR the linked L3 title region (if any) to get L3 text
6. Save to existing `raw_{prefix}_paragraphs` table with:
   - `level_1_title`, `level_2_title`, `level_3_title`
   - `text_content` (OCR result)
   - `page_number`
   - `source = 'layout_extraction'`

#### 5.2 Diagram/Image Extraction

**Applies to:** Regions classified as:
- `diagram`
- `table`
- `equation`
- `list_bulleted`
- `list_numbered`
- `list_lettered`

**Process:**
1. Extract image of region from page (600 DPI)
2. Get parent paragraph ID from Layout Review links
3. Look up L1/L2/L3 titles (same as parent paragraph)
4. Save to existing `raw_{prefix}_diagrams` table with:
   - `level_1_title`, `level_2_title`, `level_3_title`
   - `image_data` (BYTEA)
   - `diagram_type` (the class: 'diagram', 'table', 'equation', etc.)
   - `parent_paragraph_id`
   - `page_number`
   - `decoded = FALSE`
   - `source = 'layout_extraction'`

#### 5.3 L3 Title Extraction

**Process:**
1. OCR all `Title L3` regions using Surya OCR
2. Store in existing titles structure
3. Also store L3 text with each paragraph/diagram record

---

### 6. Summary Table (After Extraction)

**Columns:**
| L3 Title | Pages | Paragraphs | Diagrams (Decoded/Total) | Tables (D/T) | Equations (D/T) | Lists (D/T) |
|----------|-------|------------|--------------------------|--------------|-----------------|-------------|
| "1.1 Introduction" | 5-8 | 12 | 2/5 | 0/1 | 1/2 | 0/3 |

**Features:**
- Click on count to expand/link to full-details page
- Filter by class type
- Shows decode status (decoded count / total count)

---

### 7. Claude Decoding

#### 7.1 Decode Button

**Location:** Above summary table
**Text:** "Decode All Diagrams"
**Scope:** Decodes ALL un-decoded diagrams/tables/equations/lists at once

#### 7.2 API Mode Selection

**Options:**
| Mode | Description | Default |
|------|-------------|---------|
| Batch API (50% cost) | Async processing, up to 24h, half price | **YES** |
| Direct API (full cost) | Synchronous, immediate results, full price | No |

**UI:** Radio buttons or dropdown to select mode before clicking Decode

#### 7.3 Batch Processing Status

- Show "Batch Processing..." status with batch ID
- Page polls API periodically for status
- User can leave and return - status persists
- When complete, summary table updates with decoded counts

---

### 8. Diagram Preview Feature

#### 8.1 Access

**Button:** "Preview Diagram Decoding" (near Decode All button)
**Opens:** Preview page/modal

#### 8.2 Preview Layout

- **One diagram at a time** display
- Navigation: Previous / Next buttons
- Filter by class type (diagram, table, equation, lists)

#### 8.3 Preview Components

```
┌─────────────────────────────────────────────────────────────┐
│ Preview Diagram Decoding                    [Class: Table ▼]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐   ┌─────────────────────────────┐ │
│  │                     │   │ Prompt:                      │ │
│  │   [Diagram Image]   │   │ ┌─────────────────────────┐ │ │
│  │                     │   │ │ Analyze this table and  │ │ │
│  │                     │   │ │ extract all data in     │ │ │
│  │                     │   │ │ structured format...    │ │ │
│  │                     │   │ └─────────────────────────┘ │ │
│  └─────────────────────┘   │                             │ │
│                            │ [Test Prompt]               │ │
│  Page: 15                  │                             │ │
│  Class: table              │ Claude Response:            │ │
│  L3: "1.2 Data Analysis"   │ ┌─────────────────────────┐ │ │
│                            │ │ The table contains...   │ │ │
│                            │ │                         │ │ │
│                            │ └─────────────────────────┘ │ │
│                            └─────────────────────────────┘ │
│                                                             │
│  [< Previous]  [Next >]           [Save as Default Prompt] │
└─────────────────────────────────────────────────────────────┘
```

#### 8.4 Prompt Management

**Per-Class Prompts (6 total):**
1. `diagram` - For general diagrams/images
2. `table` - For tabular data
3. `equation` - For mathematical formulas
4. `list_bulleted` - For bullet point lists
5. `list_numbered` - For numbered lists
6. `list_lettered` - For lettered lists (a, b, c)

**Prompt Storage:**
- Stored per book in `book_settings` or `auto_slicer_config`
- System provides default prompts for each class type
- User can customize per book

**"Save as Default Prompt" Button:**
- Saves current prompt as default for this class type for this book
- Updates book settings
- Only applies to **future** decoded diagrams (not retroactive)

---

### 9. Default Prompts (System-Provided)

```json
{
  "extraction_prompts": {
    "diagram": "Analyze this diagram and provide a detailed description of what it shows, including any labels, relationships, and key information conveyed.",
    "table": "Extract all data from this table in a structured format. Include column headers, row labels, and all cell values. Preserve the table structure.",
    "equation": "Identify and transcribe this mathematical equation or formula. Explain what it represents and define any variables used.",
    "list_bulleted": "Extract all items from this bulleted list. Preserve the hierarchy if there are nested items.",
    "list_numbered": "Extract all items from this numbered list in order. Preserve numbering and any sub-items.",
    "list_lettered": "Extract all items from this lettered list (a, b, c, etc.). Preserve the lettering sequence and any sub-items."
  }
}
```

---

### 10. Database Updates

#### 10.1 Book Settings / Config Updates

Add to `auto_slicer_config` or `books_metadata`:
```json
{
  "extraction_prompts": {
    "diagram": "...",
    "table": "...",
    "equation": "...",
    "list_bulleted": "...",
    "list_numbered": "...",
    "list_lettered": "..."
  },
  "extraction_page_selection": [1, 2, 5, 6, 7],
  "last_batch_id": "batch_abc123",
  "last_batch_status": "completed"
}
```

#### 10.2 Diagrams Table Updates

Ensure `raw_{prefix}_diagrams` has:
- `diagram_type VARCHAR(50)` - Class type (diagram, table, equation, etc.)
- `decoded BOOLEAN DEFAULT FALSE` - Whether Claude has decoded it
- `decode_prompt TEXT` - The prompt used for decoding
- `source VARCHAR(50)` - 'layout_extraction' or 'manual'

---

### 11. API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/extract-knowledge` | GET | Render extraction page |
| `/api/extraction/{book_id}/ready-pages` | GET | Get pages ready for extraction |
| `/api/extraction/{book_id}/extract` | POST | Start extraction for selected pages |
| `/api/extraction/{book_id}/extraction-status` | GET | Get extraction progress |
| `/api/extraction/{book_id}/summary` | GET | Get summary by L3 title |
| `/api/extraction/{book_id}/decode-batch` | POST | Start Claude batch decoding |
| `/api/extraction/{book_id}/decode-direct` | POST | Start Claude direct decoding |
| `/api/extraction/{book_id}/batch-status` | GET | Get batch decode status |
| `/api/extraction/{book_id}/preview-decode` | POST | Preview single diagram decode |
| `/api/extraction/{book_id}/prompts` | GET/PUT | Get/update extraction prompts |
| `/api/extraction/{book_id}/page-selection` | GET/PUT | Get/save page selection |

---

### 12. Files to Create

| File | Purpose |
|------|---------|
| `src/frontend/templates/extract-knowledge.html` | Extraction page template |
| `src/frontend/static/js/extract-knowledge.js` | Extraction page JavaScript |
| `src/api/routes/extraction.py` | Extraction API endpoints |
| `src/services/extraction_service.py` | Extraction business logic |
| `src/services/claude_batch_service.py` | Claude batch API integration |

### 13. Files to Modify

| File | Changes |
|------|---------|
| `src/main.py` | Add extraction routes |
| `src/frontend/templates/auto-slicer.html` | Add "Extract Knowledge Units" button |
| `src/frontend/static/js/auto-slicer.js` | Add navigation to extraction page |
| `src/api/routes/layout_detection.py` | Add validation in "Ready for Extraction" |
| `src/frontend/templates/book-settings.html` | Add extraction prompts section |

---

### 14. Testing Checklist

- [ ] "Extract Knowledge Units" button visible on Auto-Slicer
- [ ] Extraction page loads with correct book
- [ ] Only "Ready for Extraction" pages shown
- [ ] Orphan diagram validation works (blocks "Ready" if no parent)
- [ ] Extracted pages cannot be re-selected
- [ ] Pre-extraction summary shows correct counts
- [ ] Surya OCR extracts paragraphs correctly
- [ ] Diagrams saved as images with correct metadata
- [ ] L1/L2/L3 titles populated correctly
- [ ] Summary table shows correct counts per L3
- [ ] Batch decode starts and polls correctly
- [ ] Direct decode works as alternative
- [ ] Preview feature shows diagram + prompt + response
- [ ] Saving prompt updates book settings
- [ ] Page selection persists across sessions
- [ ] Progress bar updates during extraction

---

## UI Mockups

### Auto-Slicer Button Location
```
┌─────────────────────────────────────────────────────────────┐
│ Layout Detection                                             │
├─────────────────────────────────────────────────────────────┤
│ [Detect Layout (YOLO)]  [Review Layout]  [Extract Knowledge] │
└─────────────────────────────────────────────────────────────┘
```

### Extraction Page Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Extract Knowledge Units - Book: "Advanced Mathematics"       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Pages Ready for Extraction:                                  │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ☑ │ Page │ Status        │ Paragraphs │ Diagrams │      │ │
│ ├───┼──────┼───────────────┼────────────┼──────────┤      │ │
│ │ ☑ │ 1    │ Not Extracted │ 5          │ 2        │      │ │
│ │ ☑ │ 2    │ Not Extracted │ 8          │ 3        │      │ │
│ │ ☐ │ 3    │ Extracted     │ 6          │ 1        │ (disabled)│
│ │ ☑ │ 4    │ Not Extracted │ 4          │ 4        │      │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [Select All] [Deselect All]              [Extract Selected] │
│                                                             │
│ ─────────────────────────────────────────────────────────── │
│                                                             │
│ Extraction Summary by L3 Title:                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ L3 Title      │Pages│Para│Diagrams│Tables│Eq │Lists    │ │
│ ├───────────────┼─────┼────┼────────┼──────┼───┼─────────┤ │
│ │ 1.1 Intro     │ 1-3 │ 12 │ 2/5    │ 0/1  │1/2│ 0/3     │ │
│ │ 1.2 Methods   │ 4-8 │ 24 │ 5/8    │ 2/3  │0/1│ 1/4     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Decode Mode: ○ Batch API (50% cost)  ○ Direct API          │
│ [Decode All Diagrams]  [Preview Diagram Decoding]           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Session Resume Instructions

1. Read this file first
2. Check `PHASE3-EXTRACTION-PROGRESS.md` for implementation status
3. Continue from last incomplete task
4. Update progress every ~50 lines of code

---
