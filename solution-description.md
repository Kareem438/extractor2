# Knowledge Extraction System — Solution Description

**System:** Knowledge Extraction System (13-extractor2)
**Version:** 1.0
**Server:** http://localhost:8888
**Last Updated:** 2026-02-14

---

## Overview

A web-based system for extracting structured knowledge from Arabic PDF books using AI-powered OCR, layout detection, and semantic analysis. The system transforms scanned documents into searchable, structured knowledge units through a multi-stage pipeline with human verification at each step.

The application runs as a FastAPI server on port 8888 with a PostgreSQL database backend and ChromaDB for vector search. All pages are single-page applications (SPA-style) with vanilla HTML/CSS/JS.

---

## Pages & User Experience

### 1. Book Library (`/library`)

**Purpose:** Central hub for managing all uploaded books.

**Layout:**
- Header with gradient background showing total book count and statistics
- Action bar with search input and "Upload New Book" button
- Book cards grid showing each book with: name, page count, status badge, progress bar, action buttons

**User Experience:**
- User sees all books at a glance with their processing status (Uploaded, Processing, Verified, etc.)
- Search/filter to find specific books
- Click a book card to navigate to its settings or processing pages
- Quick action buttons: Verify, View, Pause, Monitor, Delete
- OCR model status indicators (Surya, EasyOCR, YOLO loaded/unloaded)

---

### 2. Upload (`/upload`)

**Purpose:** Upload PDF documents and configure initial processing settings.

**Layout:**
- Top navigation bar with links to all major pages
- Drag-and-drop upload zone with file browser fallback
- Processing preset selector (Quick / Balanced / Deep)
- Language configuration (Arabic, English, mixed)
- Custom attribute configuration panel (up to 72 user-defined fields)
- Multi-PDF upload modal for batch processing

**User Experience:**
- User drags a PDF file onto the upload zone (or clicks to browse)
- Selects a processing preset that controls OCR quality and depth
- Configures language and any custom attributes needed for this book
- Clicks "Upload" — file is stored, pages are scanned at 600 DPI
- A warning banner appears if page scanning hasn't been run yet, with a "Scan Now" button
- After upload, user is directed to Book Settings or Auto-Slicer

---

### 3. Book Settings (`/book-settings?book_id=X`)

**Purpose:** Per-book configuration including page scanning, OCR areas, and extraction prompts.

**Layout:**
- Header with book name and purple gradient
- Breadcrumb navigation back to Library
- Book info section (name, page count, table prefix)
- Page Scanning section with DPI controls and page range
- OCR Text Area mapping section
- Manual Text Area mapping section
- Extraction prompt configuration
- Danger Zone (delete book)

**User Experience:**
- User selects a book from the dropdown
- Can trigger page scanning (renders PDF pages to 600 DPI images stored in DB)
- Configures which rectangular areas on each page contain text vs. diagrams
- Sets up extraction prompts for AI processing
- Can rename custom attributes (72 user-defined fields)
- Danger zone allows permanent book deletion with confirmation

---

### 4. Auto-Slicer (`/auto-slicer?book_id=X`)

**Purpose:** Bulk page processing with YOLO layout detection, title hierarchy configuration, and cloud extraction.

**Layout:**
- Top navigation with book selector
- Recommended Workflow guide
- Page Viewer with zoom controls and page navigation
- Title Configuration section (L1/L2/L3 title hierarchy)
- Page Range selector
- YOLO Detection Classes configuration (enable/disable detection types)
- Action buttons: Run Detection, Run OCR, Auto-Boundaries
- Cloud Extraction section (Qwen VL) with model dropdown, Start/Pause/Cancel buttons, progress bar

**User Experience:**
- User selects a book and sees the page viewer showing scanned pages
- Configures the title hierarchy (Chapter → Topic → Sub-topic) with page ranges
- Selects which YOLO detection classes to use (paragraph, heading, footnote, verse, diagram, etc.)
- Clicks "Run Detection" to process pages with DocLayout-YOLO
- Can run local OCR on detected regions
- Can run Auto-Boundaries for automatic region detection
- NEW: Cloud Extraction section allows selecting a Qwen VL model and starting cloud-based extraction
- Progress bar shows pages completed/failed/remaining with real-time polling
- After cloud extraction completes, a link appears to the Knowledge Page Review

---

### 5. Layout Review (`/layout-review?book_id=X`)

**Purpose:** Review and edit YOLO-detected regions on each page with a canvas-based interface.

**Layout:**
- Top navigation with book info and page counter
- Three-panel layout:
  - Left sidebar: region list with class labels, selection tools, link mode toggle
  - Center: canvas showing page image with colored bounding box overlays
  - Right sidebar: region details editor, context menu, advanced tools
- Bottom toolbar: zoom, Arabic mode toggle, keyboard shortcuts

**User Experience:**
- User navigates page by page (prev/next or jump to page number)
- Each page shows the scanned image with colored rectangles for detected regions
- Click a region to select it — details appear in the right panel
- Can drag to resize/move regions, right-click for context menu
- Can merge multiple regions, split a region, change class type
- Can link diagrams to paragraphs, link paragraphs to L3 titles
- "Ready for Extraction" toggle per page — marks page as a few-shot example for cloud OCR
- "Skip Page" toggle to exclude pages from processing
- Arabic mode reverses reading order display
- Zoom controls for detailed inspection

---

### 6. Knowledge Page Review (`/knowledge-page-review?book_id=X`) — NEW

**Purpose:** Review cloud OCR results grouped by L3 title (knowledge pages) before converting to KU records.

**Layout:**
- Top navigation with book name, KP count, overall status, "Convert All Ready → KU" button, back link
- Three-panel layout:
  - Left sidebar: Knowledge page navigator (prev/next), status filter dropdown, element cards list, "Add Element" button
  - Center: Canvas with page image and color-coded bounding box overlays per element type, page selector, zoom slider, show/hide boxes and labels toggles
  - Right panel: Element editor with type dropdown, Arabic text textarea, page number, order, confidence, bbox fields, move up/down/delete buttons
- Bottom action bar: Save, Ready toggle, Convert button

**User Experience:**
- User navigates between knowledge pages (grouped by L3 title) using prev/next arrows
- Each knowledge page shows its L3 title, page range, element count, and status (extracted → reviewed → ready_to_convert → converted)
- Filter dropdown to show only pages with a specific status
- Clicking an element card in the sidebar highlights it on the canvas and opens the editor
- Can edit element text (Arabic, RTL), change type, adjust order, modify bounding box
- Can add new elements or remove existing ones
- "Save" persists changes via API (status auto-changes to "reviewed")
- "Ready" toggle marks the knowledge page as "Ready to Convert to KU"
- "Convert All Ready" batch-converts all ready knowledge pages into individual KU + paragraph records
- Toast notifications for save/error feedback

---

### 7. Verify Pages (`/verify-pages?book_id=X`)

**Purpose:** Split-screen verification of OCR results against original page images.

**Layout:**
- Fixed top navigation
- Controls bar: book selector, page navigation, OCR mode selector
- Split-screen view:
  - Left panel: original page image with highlighted extraction regions
  - Right panel: extracted text with editable fields, metadata, confidence scores
- Navigation buttons: Previous, Next, Approve & Next

**User Experience:**
- User selects a book and navigates page by page
- Left side shows the scanned page image with colored highlights showing where text was extracted
- Right side shows the extracted text content, editable in-place
- Can switch between OCR engines (PaddleOCR, Surya, Tesseract) to compare results
- Can merge incorrectly split records or split multi-idea paragraphs
- Can link diagrams to related text paragraphs
- "Approve & Next" confirms the page and moves to the next one

---

### 8. Edit Paragraphs (`/edit-paragraphs?book_id=X`)

**Purpose:** Paragraph-level editing with thumbnail gallery and attribute management.

**Layout:**
- Top navigation
- Book selector with back button
- Paragraph gallery: thumbnail grid showing cropped paragraph images
- Detail modal: full paragraph view with all attributes, text content, hierarchy assignment

**User Experience:**
- User sees a gallery of all extracted paragraph clips as thumbnails
- Click a thumbnail to open the detail modal
- Can edit text content, assign to chapter/topic/sub-topic hierarchy
- Can merge paragraphs or link to diagrams
- Manage all 80 attributes per paragraph
- Confirmation workflow for reviewed paragraphs

---

### 9. Edit Diagrams (`/edit-diagrams?book_id=X`)

**Purpose:** Diagram review, AI description refinement, and text linking.

**Layout:**
- Similar to Edit Paragraphs but focused on diagram images
- Diagram gallery with AI-generated descriptions
- Detail view with description editor and linked text display

**User Experience:**
- User reviews extracted diagrams
- AI-generated descriptions can be edited or regenerated
- Link diagrams to related text paragraphs
- Manage diagram metadata and attributes

---

### 10. Review Raw (`/review-raw?book_id=X`)

**Purpose:** Compare raw OCR results from multiple engines side by side.

**Layout:**
- Book and page selector
- Multi-column comparison view showing results from each OCR engine
- Confidence scores per engine
- Manual correction interface

**User Experience:**
- User selects a page and sees OCR results from all engines side by side
- Confidence scores help identify which engine performed best
- Can manually correct text where all engines failed
- Useful for quality assurance before further processing

---

### 11. Extract Knowledge (`/extract-knowledge?book_id=X`)

**Purpose:** Knowledge unit extraction interface for creating structured KU records from raw data.

**Layout:**
- Book selector
- Extraction controls and configuration
- Results display with created knowledge units

**User Experience:**
- User triggers knowledge unit creation from verified raw data
- System creates structured KU records with chapter/topic/sub-topic hierarchy
- Results show created KUs with their attributes

---

### 12. Extraction Dashboard (`/extraction-dashboard?book_id=X`)

**Purpose:** Real-time monitoring of the extraction process (Phase 3D).

**Layout:**
- Dashboard with progress metrics
- Page-by-page extraction status
- Error log and retry controls

**User Experience:**
- User monitors extraction progress in real-time
- Can see which pages succeeded, failed, or are pending
- Can retry failed pages
- Progress statistics and timing information

---

### 13. Pipeline Configuration (`/pipeline-config?book_id=X`)

**Purpose:** Configure Claude AI multi-step processing workflows.

**Layout:**
- Top navigation with dark theme
- Book selector
- Variables section showing all available template variables
- Pipeline steps editor: ordered list of processing steps
- Each step: name, model selector (Sonnet/Opus/Haiku), prompt template, input/output field mapping
- Tag mapping configuration for XML extraction

**User Experience:**
- User selects a book and configures a multi-step Claude AI pipeline
- Each step defines: which model to use, what prompt to send, which fields to read/write
- Template variables (e.g., `{{text_content}}`, `{{easyocr_result}}`) are available for dynamic prompts
- Can configure tag mapping for structured XML output parsing
- Steps execute sequentially per record, in parallel across records
- Save configuration for reuse across books

---

### 14. Pipeline Dashboard (`/pipeline-dashboard?book_id=X`)

**Purpose:** Real-time monitoring of Claude AI pipeline execution.

**Layout:**
- Top navigation with book info and API mode toggle
- Header with pipeline status and controls
- Worker status section
- KU creation controls and statistics
- Diagram analysis execution panel
- KU grouping preview
- Progress tracking per step and per record

**User Experience:**
- User starts pipeline execution and monitors progress in real-time
- Worker status shows heartbeat, current task, and throughput
- Can create KUs, execute diagram analysis, and run KU grouping
- Per-step progress bars show completion percentage
- Success/failure counts with error details
- Can pause/resume/cancel pipeline execution

---

### 15. L1 Title Attributes (`/l1-title-attributes?book_id=X`)

**Purpose:** Edit Level 1 (Chapter) title attributes and page ranges.

**Layout:**
- Title list with page range editors
- Attribute fields per title

**User Experience:**
- User manages chapter-level titles
- Can set start/end page ranges
- Can edit title text and attributes
- External writable ranges for cross-book access

---

### 16. L2 Title Attributes (`/l2-title-attributes?book_id=X`)

**Purpose:** Edit Level 2 (Topic) title attributes and page ranges.

**Layout:**
- Similar to L1 but for topic-level titles
- Parent L1 title association

**User Experience:**
- User manages topic-level titles within chapters
- Can set page ranges and parent chapter association
- Edit title text and attributes

---

### 17. Cross-Book Audit (`/cross-book-audit`)

**Purpose:** Audit log for cross-book operations and data access.

**Layout:**
- Audit log table with filters
- Operation details per entry

**User Experience:**
- User reviews all cross-book data access operations
- Filter by book, operation type, date range
- See which data was accessed and by whom

---

### 18. Layout Training (`/layout-training`)

**Purpose:** Fine-tune the YOLO layout detection model with custom training data.

**Layout:**
- Training configuration panel
- Dataset management
- Training progress and metrics
- Model evaluation results

**User Experience:**
- User prepares training data from reviewed layout detections
- Configures training parameters (epochs, learning rate, etc.)
- Starts training and monitors progress
- Evaluates new model against test data
- Can deploy improved model for future detections

---

## Data Flow Summary

```
1. Upload PDF → /upload
2. Scan Pages (600 DPI) → /book-settings
3. YOLO Layout Detection → /auto-slicer
4. Review Detected Regions → /layout-review
5a. Local OCR Path:
    → Run OCR on regions → /auto-slicer
    → Verify OCR results → /verify-pages
    → Edit paragraphs/diagrams → /edit-paragraphs, /edit-diagrams
5b. Cloud OCR Path (NEW):
    → Mark sample pages "Ready for Extraction" → /layout-review
    → Start Cloud Extraction (Qwen VL) → /auto-slicer
    → Review Knowledge Pages → /knowledge-page-review
    → Convert to KU records → /knowledge-page-review
6. Configure AI Pipeline → /pipeline-config
7. Execute Pipeline → /pipeline-dashboard
8. Export Structured Knowledge
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.9+, FastAPI |
| Database | PostgreSQL 16 |
| Vector DB | ChromaDB |
| OCR (Local) | Surya (GPU), EasyOCR, Tesseract |
| OCR (Cloud) | Qwen VL via DashScope API |
| Layout Detection | DocLayout-YOLO |
| AI Pipeline | Claude API (Sonnet/Opus/Haiku) |
| Frontend | Vanilla HTML/CSS/JS, Canvas API |
| Server Port | 8888 |
