# Testing: Cloud OCR Approach — Phase 1

**Task:** Integrate Qwen VL via DashScope for cloud-based Arabic text extraction
**Date:** 2026-02-12
**Status:** 🔄 Test Cases Review

---

## Test Cases

### Req 1: DashScope API Configuration

#### TC-001: Config fields exist
- **Verify:** `Settings` class has `DASHSCOPE_API_KEY` field with `default=""`
- **Verify:** `Settings` class has `DASHSCOPE_BASE_URL` field with default `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- **API:** N/A (config only)

#### TC-002: Missing API key returns 400
- **API:** `POST /api/cloud-ocr/start/{book_id}` with empty `DASHSCOPE_API_KEY`
- **Verify:** Returns HTTP 400 with message identifying missing `DASHSCOPE_API_KEY`

#### TC-003: .env.example documentation
- **Verify:** `.env.example` contains `DASHSCOPE_API_KEY` and `DASHSCOPE_BASE_URL` with descriptions

---

### Req 2: Qwen Vision-Based Text Extraction

#### TC-004: Qwen service sends correct API format
- **Verify:** Request to DashScope uses OpenAI-compatible chat completions format
- **Verify:** Page image is base64-encoded in the vision message payload
- **Verify:** Model name from user selection is passed in the request

#### TC-005: Qwen returns valid JSON per page
- **Verify:** Response is parsed as JSON array
- **Verify:** Each element has required fields: `text`, `type`, `confidence`, `order`, `bbox`
- **Verify:** `level_3_title` field is present (can be null)

#### TC-006: Sequential page processing
- **Verify:** Pages are processed one at a time (not concurrent)
- **Verify:** Each page waits for the previous to complete before starting

#### TC-007: Rate limit retry (HTTP 429)
- **Verify:** On 429 response, service retries with exponential backoff
- **Verify:** Maximum 3 retry attempts
- **Verify:** After 3 retries, page is marked as `"failed"`

#### TC-008: Non-recoverable error handling
- **Verify:** On HTTP 4xx (not 429) or 5xx after retries, page is marked `"failed"`
- **Verify:** Error is logged at ERROR level with HTTP status and response body
- **Verify:** Processing continues to next page (doesn't abort entire run)

#### TC-009: Few-shot prefix enables caching
- **Verify:** Few-shot images are placed at the START of the prompt (system message or first content block)
- **Verify:** The prefix is identical across all page requests in a run
- **Verify:** Response includes `usage.prompt_cache_hit_tokens` or similar field from DashScope

---

### Req 3: Few-Shot Prompt Construction

#### TC-010: Auto-detect "Ready for Extraction" pages as samples
- **Verify:** Starting cloud OCR automatically collects pages marked "Ready for Extraction"
- **Verify:** Page images and layout detection results are retrieved from DB for each sample

#### TC-011: 1-10 sample pages supported
- **Verify:** 1 sample page works correctly
- **Verify:** 10 sample pages works correctly
- **Verify:** 0 sample pages returns HTTP 400 ("no pages marked Ready for Extraction")

#### TC-012: Skip pages without layout detection
- **Verify:** If a "Ready for Extraction" page has no layout detections, it's skipped
- **Verify:** A warning is logged for the skipped page
- **Verify:** Remaining valid sample pages are still used

#### TC-013: Few-shot example format
- **Verify:** Each example includes: page image + expected JSON output
- **Verify:** Expected JSON output is derived from the page's layout detection results
- **Verify:** Element types match layout detection class names

---

### Req 4: Cloud OCR API Endpoints and Execution Control

#### TC-014: Start extraction endpoint
- **API:** `POST /api/cloud-ocr/start/{book_id}` with `{"model": "qwen-vl-max"}`
- **Verify:** Returns 200 with `success: true`, `status: "processing"`, `total_pages`, `few_shot_pages`
- **Verify:** Background task is started (endpoint returns immediately)
- **Verify:** Returns 400 if `DASHSCOPE_API_KEY` is empty
- **Verify:** Returns 400 if no pages marked "Ready for Extraction"

#### TC-015: Status endpoint
- **API:** `GET /api/cloud-ocr/status/{book_id}`
- **Verify:** Returns `status`, `pages_completed`, `pages_failed`, `pages_pending`, `current_page`, `total_pages`, `failed_pages`
- **Verify:** Status is `"idle"` when no extraction has been run
- **Verify:** Status is `"running"` during active extraction
- **Verify:** Status is `"completed"` after all pages finish

#### TC-016: Pause endpoint
- **API:** `POST /api/cloud-ocr/pause/{book_id}`
- **Verify:** Returns success, status changes to `"paused"` after current page completes
- **Verify:** Returns 400 if no active job for this book
- **Verify:** Returns 400 if job is not running

#### TC-017: Resume endpoint
- **API:** `POST /api/cloud-ocr/resume/{book_id}`
- **Verify:** Continues from last completed page
- **Verify:** Returns 400 if job is not paused

#### TC-018: Cancel endpoint
- **API:** `POST /api/cloud-ocr/cancel/{book_id}`
- **Verify:** Stops processing, status changes to `"cancelled"`
- **Verify:** Completed pages are kept, remaining pages stay as `"pending"`

#### TC-019: Retry failed pages
- **API:** `POST /api/cloud-ocr/retry-failed/{book_id}`
- **Verify:** Only pages with status `"failed"` are retried
- **Verify:** Returns list of retrying page numbers and count
- **Verify:** Returns 400 if no failed pages exist

#### TC-020: Page-level status persistence
- **Verify:** Each page status is stored in `{prefix}_cloud_ocr_pages` table
- **Verify:** Status transitions: `pending` → `processing` → `completed` or `failed`
- **Verify:** Progress survives server restart (read from DB on resume)

---

### Req 5: Knowledge Pages Table and Translation Layer

#### TC-021: Knowledge pages table creation
- **Verify:** Migration creates `{prefix}_knowledge_pages` table with all columns from design
- **Verify:** Migration creates `{prefix}_cloud_ocr_pages` table with all columns from design
- **Verify:** Tables are created for existing books via migration script

#### TC-022: L3 grouping across pages
- **Verify:** Elements with the same `level_3_title` across different physical pages are grouped into one knowledge_page
- **Verify:** `start_page` and `end_page` reflect the actual page range of the grouped elements

#### TC-023: Multiple L3 sections on one page
- **Verify:** If a physical page has elements with 3 different L3 titles, 3 separate knowledge_page records are created

#### TC-024: L3 section spanning multiple pages
- **Verify:** If an L3 section spans pages 5-8, one knowledge_page is created with `start_page=5`, `end_page=8`

#### TC-025: L1/L2 title resolution
- **Verify:** L1 title is resolved from `level1_titles` table by matching page number to page range
- **Verify:** L2 title is resolved from `level2_titles` table by matching page number to page range
- **Verify:** Both `l1_title_id`/`l1_title_text` and `l2_title_id`/`l2_title_text` are populated

#### TC-026: JSONB content structure
- **Verify:** `content` column stores valid JSONB with `{"elements": [...]}`
- **Verify:** Each element has: `type`, `text`, `page_number`, `bbox`, `confidence`, `order`, `metadata`

#### TC-027: Status defaults
- **Verify:** New knowledge_pages have `status = 'extracted'`
- **Verify:** `ocr_engine` defaults to `'qwen-cloud'`
- **Verify:** `model_name` stores the actual model used (e.g., `qwen-vl-max`)

#### TC-028: Token tracking
- **Verify:** `cached_tokens`, `total_input_tokens`, `total_output_tokens` are populated from API response

---

### Req 6: Knowledge Page Review UI

#### TC-029: List knowledge pages
- **API:** `GET /api/cloud-ocr/knowledge-pages/{book_id}`
- **Verify:** Returns list of knowledge_pages with `id`, `l3_title`, `start_page`, `end_page`, `l1_title_text`, `l2_title_text`, `element_count`, `status`

#### TC-030: Get knowledge page detail
- **API:** `GET /api/cloud-ocr/knowledge-pages/{book_id}/{kp_id}`
- **Verify:** Returns full knowledge_page including `content` JSONB

#### TC-031: Update knowledge page
- **API:** `PUT /api/cloud-ocr/knowledge-pages/{book_id}/{kp_id}`
- **Verify:** Updates `content` JSONB and optional `l3_title`
- **Verify:** Sets `updated_at` timestamp
- **Verify:** Returns 404 if knowledge_page not found

#### TC-032: Toggle "Ready to Convert to KU"
- **API:** `POST /api/cloud-ocr/knowledge-pages/{book_id}/{kp_id}/toggle-ready`
- **Verify:** Toggles status between `"reviewed"` and `"ready_to_convert"`
- **Verify:** Returns new status in response

#### TC-033: Review UI renders page image with overlays
- **Verify:** Canvas displays page image with element bounding boxes color-coded by type
- **Verify:** Page navigation (prev/next) works
- **Verify:** Sidebar shows element list with editable fields

#### TC-034: Review UI element editing
- **Verify:** User can edit element text (Arabic content)
- **Verify:** User can change element type via dropdown
- **Verify:** User can change L3 title assignment
- **Verify:** User can reorder elements
- **Verify:** User can add/remove elements
- **Verify:** Changes are saved via PUT API

---

### Req 7: Knowledge Page to KU Conversion

#### TC-035: Convert endpoint
- **API:** `POST /api/cloud-ocr/convert-to-ku/{book_id}`
- **Verify:** Converts all knowledge_pages with status `"ready_to_convert"`
- **Verify:** Returns `knowledge_pages_converted`, `kus_created`, `paragraphs_created`
- **Verify:** Returns 400 if no knowledge_pages are ready to convert

#### TC-036: raw_paragraph_images creation
- **Verify:** Each element creates a `raw_paragraph_images` row
- **Verify:** `selection_x/y/width/height` mapped from element `bbox`
- **Verify:** `extracted_text` mapped from element `text`
- **Verify:** `level_1_title`, `level_2_title`, `level_3_title` populated correctly
- **Verify:** `display_order` mapped from element `order`
- **Verify:** `ocr_confidence` mapped from element `confidence`

#### TC-037: Image cropping from bbox
- **Verify:** `image_data` (BYTEA) is cropped from the page image using the element's bbox coordinates

#### TC-038: KU creation via existing function
- **Verify:** After raw_paragraph_images are created, `create_knowledge_units_for_pages()` is called
- **Verify:** KU records are created with correct `chapter` (L1), `topic` (L2), `sub_topic` (L3)

#### TC-039: Status update after conversion
- **Verify:** Knowledge_page status changes from `"ready_to_convert"` to `"converted"`

#### TC-040: Idempotent conversion
- **Verify:** Re-converting an already-converted knowledge_page deletes previous KU records first
- **Verify:** New KU records are created fresh
- **Verify:** No duplicate KUs after re-conversion

---

### Req 8: Cloud Extraction UI on Auto-Slicer Page

#### TC-041: Cloud Extraction section exists
- **Verify:** Auto-slicer page has a "Cloud Extraction" section visually distinct from local OCR
- **Verify:** Section contains: model dropdown, Start button, Pause/Resume/Cancel buttons

#### TC-042: Model dropdown
- **Verify:** Dropdown lists: `qwen-vl-max`, `qwen3-vl-plus`, `qwen3-vl-flash`
- **Verify:** Selected model is sent in the start request

#### TC-043: Button states
- **Verify:** Start button disabled if no "Ready for Extraction" pages
- **Verify:** Pause/Resume/Cancel buttons disabled when no extraction is running
- **Verify:** Pause button swaps to Resume when paused (same pattern as auto-slicer)

#### TC-044: Progress display
- **Verify:** Shows pages completed, failed, remaining during extraction
- **Verify:** Shows current page being processed
- **Verify:** Updates in real-time via status polling

#### TC-045: Link to review UI
- **Verify:** After extraction completes, a link to knowledge_page review UI is displayed

---

### Req 9: Error Handling and Logging

#### TC-046: Request logging
- **Verify:** Each DashScope API call logs: model, page number, token estimate at INFO level

#### TC-047: Error logging
- **Verify:** Failed API calls log: HTTP status code, response body at ERROR level

#### TC-048: Success logging
- **Verify:** Successful API calls log: tokens used, processing time, cache hit status at INFO level

#### TC-049: Unexpected exception handling
- **Verify:** Unexpected exceptions in cloud processing return HTTP 500 with generic error message
- **Verify:** Exception is logged at ERROR level with full traceback

---

### Edge Cases

#### TC-050: Book with no pages
- **API:** `POST /api/cloud-ocr/start/{book_id}` for a book with 0 pages
- **Verify:** Returns appropriate error (400 or descriptive message)

#### TC-051: All pages fail
- **Verify:** If every page fails, status is `"completed"` (not stuck in `"running"`)
- **Verify:** `pages_failed` equals `total_pages`

#### TC-052: Pause during last page
- **Verify:** If pause is requested while processing the last page, extraction completes normally (no pages left to pause before)

#### TC-053: Resume after server restart
- **Verify:** After server restart, `GET /api/cloud-ocr/status/{book_id}` reads from DB
- **Verify:** Resume picks up from last completed page

#### TC-054: Concurrent extraction attempts
- **API:** `POST /api/cloud-ocr/start/{book_id}` while extraction is already running
- **Verify:** Returns 400 ("extraction already in progress")

#### TC-055: Invalid model name
- **API:** `POST /api/cloud-ocr/start/{book_id}` with `{"model": "invalid-model"}`
- **Verify:** Returns 400 with descriptive error about invalid model

#### TC-056: Knowledge page with empty elements
- **Verify:** A knowledge_page with 0 elements (empty L3 section) is handled gracefully
- **Verify:** Conversion skips empty knowledge_pages

#### TC-057: Malformed Qwen response
- **Verify:** If Qwen returns non-JSON or invalid JSON, page is marked `"failed"` with error message
- **Verify:** Processing continues to next page

---

## Cleanup Section

### Database Objects Created by Tests

- [ ] `{prefix}_knowledge_pages` table rows (created during extraction tests)
- [ ] `{prefix}_cloud_ocr_pages` table rows (created during extraction tests)
- [ ] `raw_{prefix}_paragraph_images` rows (created during KU conversion tests)
- [ ] `{prefix}_knowledge_units` rows (created during KU conversion tests)

### Config Changes

- [ ] `DASHSCOPE_API_KEY` added to `.env` (test value or empty)
- [ ] `DASHSCOPE_BASE_URL` added to `.env`

### Files Created

- [ ] `src/services/qwen_service.py`
- [ ] `src/api/routes/cloud_ocr.py`
- [ ] `src/api/routes/knowledge_pages.py`
- [ ] `src/frontend/templates/knowledge-page-review.html`
- [ ] `src/frontend/static/js/knowledge-page-review.js`
- [ ] `migrate_add_knowledge_pages.py`

### Files Modified

- [ ] `src/config.py` — added DASHSCOPE fields
- [ ] `src/main.py` — registered new routers
- [ ] `src/database/table_creator.py` — added knowledge_pages + cloud_ocr_pages
- [ ] `src/frontend/static/js/auto-slicer.js` — added Cloud Extraction section
- [ ] `src/frontend/templates/auto-slicer.html` — added cloud extraction UI
- [ ] `.env.example` — added DashScope vars

### Post-Test Cleanup Steps

1. Delete test knowledge_page records from DB
2. Delete test cloud_ocr_pages records from DB
3. Delete test raw_paragraph_images records created by conversion tests
4. Delete test knowledge_unit records created by conversion tests
5. Verify no orphaned records remain
