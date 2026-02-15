# Test Cases: Rolling API XML Extraction (V2 Cloud Extraction)

**Task:** V2 Cloud-based knowledge extraction using ChatGPT 5 with rolling window
**Date:** 2026-02-15
**Status:** 🔄 Step 3 — Test Cases

---

## Phase A — Foundation Tests

### T-A1: LLM Providers Table Migration
- Run `migrate_add_llm_providers.py` → `llm_providers` table created with correct schema
- Run migration twice → no errors (idempotent)

### T-A2: Extraction Method Column Migration
- Run `migrate_add_extraction_method.py` → `extraction_method` column added to `books_metadata` with default 'v2'
- Existing books get 'v2' as default value
- Run migration twice → no errors

### T-A3: V2 Table Creation
- Call `create_v2_knowledge_pages_table(prefix)` → table created with all columns (title FKs, queryable fields, raw_xml, parsed_json, 80 attrs)
- Call `create_v2_extraction_log_table(prefix)` → table created with token/cost tracking columns
- Call `create_v2_few_shot_examples_table(prefix)` → table created with annotation data columns
- Verify indexes created on queryable columns

### T-A4: V2 Tables in Book Creation
- Upload new book → V2 tables created alongside V1 tables
- Verify `extraction_method` defaults to 'v2' for new books

### T-A5: LLM Provider CRUD
- POST `/api/llm-providers` with OpenAI config → provider created, API key stored (encrypted)
- GET `/api/llm-providers` → returns list of configured providers (API key masked)
- PUT `/api/llm-providers/{id}` → updates provider config
- DELETE `/api/llm-providers/{id}` → removes provider
- POST `/api/llm-providers/{id}/test` → tests connection to provider API

### T-A6: LLM Provider Validation
- POST with missing API key → 400 error
- POST with missing model name → 400 error
- POST with duplicate provider_name → 409 conflict
- GET enabled providers only → returns only providers with `enabled=true`

---

## Phase B — LLM Config UI Tests

### T-B1: Pipeline Config Page — LLM Providers Section
- Load pipeline config page → LLM Providers section visible
- Add OpenAI provider → form submits, provider appears in list
- Edit provider → fields update correctly
- Delete provider → removed from list with confirmation
- Toggle enabled/disabled → provider grayed out when disabled
- API key field → masked (shows ****) after save

### T-B2: Provider Dropdown on Auto-Slicer
- No providers configured → dropdown empty, extraction disabled
- 1 provider configured (OpenAI) → dropdown shows only OpenAI
- 2 providers configured → dropdown shows both
- Disabled provider → not shown in dropdown

---

## Phase C — Core Extraction Engine Tests

### T-C1: XML Parser — Valid XML
- Parse well-formed XML with all 9 categories → returns complete JSON
- Extract queryable fields → correct values for difficulty_score, concept_type, etc.
- Verify summary field extracted correctly

### T-C2: XML Parser — Malformed XML
- Missing closing tags → returns parse error with details
- Wrong nesting → returns specific error
- Empty response → returns error
- Partial XML (truncated) → returns error indicating truncation

### T-C3: XML to JSON Conversion
- Convert full XML → JSON structure matches, all tags preserved
- Verify JSONB storage → can query nested fields with PostgreSQL JSON operators

### T-C4: Few-Shot Annotation
- Generate annotated image for page with regions → colored outlines (3px) + text labels
- Verify color coding: Red=L1, Orange=L2, Yellow=L3, Green=Paragraph, Blue=Diagram, Purple=Equation, Cyan=Table, Pink=List
- Labels positioned outside bounding box, no fill
- Save annotated image to disk → file exists at expected path

### T-C5: Few-Shot Send to LLM
- Send annotated pages to OpenAI → successful response
- Verify `user` parameter set to cache name
- Verify few-shot images placed at START of messages array
- Mark examples as `sent_to_llm=true` in DB

### T-C6: Rolling Window — Basic Flow
- Book with 20 pages, L3 titles at pages 1, 5, 10, 15, 20
- Window 1: pages 1-4 → finds L3 at 1 and 5 → KP1 (pages 1-5)
- Smart jump to page 5
- Window 2: pages 5-8 → finds L3 at 5 and 10 → KP2 (pages 5-10)
- Smart jump to page 10
- Continue until all KPs extracted

### T-C7: Rolling Window — No L3 in 4 Pages
- L3 titles at pages 1 and 9 (8-page span)
- Window 1: pages 1-4 → no closing L3 found
- Retry with 8 pages: pages 1-8 → still no closing L3
- ERROR flagged, red flag on this knowledge page

### T-C8: Rolling Window — 8-Page Retry Success
- L3 titles at pages 1 and 6
- Window 1: pages 1-4 → no closing L3
- Retry with 8 pages: pages 1-8 → finds L3 at 6 → KP1 (pages 1-6)
- Smart jump to page 6, continue normally

### T-C9: L1/L2 Title Injection
- L1 title "Mechanics" covers pages 1-50
- L2 title "Newton's Laws" covers pages 10-25
- KP extracted at pages 12-14 → l1_title_id points to "Mechanics", l2_title_id points to "Newton's Laws"
- Verify FK IDs are from DB lookup, NOT from LLM response

### T-C10: Prompt Context Injection
- Verify L1/L2 title TEXT included in prompt for context
- Verify last KP's ending L3 title included as continuation context
- Verify few-shot images are the stable prefix (for caching)

---

## Phase D — Extraction Controls Tests

### T-D1: Pre-requisite Validation
- No L1 titles defined → "Start Extraction" disabled, message shows "L1 titles required"
- L1 defined but L2 missing → disabled, "L2 titles required"
- L1+L2 defined but no API key → disabled, "API key required"
- L1+L2+API key but no few-shots sent → disabled, "Few-shot examples required"
- All pre-requisites met → button enabled

### T-D2: Start Extraction
- Click Start → extraction begins, status changes to "running"
- Progress bar updates with each window
- Cost dashboard shows live token/cost data

### T-D3: Pause/Resume
- Click Pause during extraction → stops after current window, status "paused"
- Click Resume → continues from last completed KP, status "running"
- Verify no duplicate KPs after resume

### T-D4: Cancel
- Click Cancel → stops extraction, keeps completed KPs
- Verify partial results accessible in review UI

### T-D5: Error Handling — Malformed XML
- LLM returns malformed XML → Phase 1: 3 immediate retries
- All 3 fail → 15-minute cooldown timer shown in UI
- Phase 2: 3 more retries after cooldown
- All 6 fail → extraction paused, user alerted with error details

### T-D6: Rate Limiting — Adaptive Backoff
- Configure 5s minimum delay → verify 5s between calls
- Simulate 429 response → delay increases (5→10→20→40→60s max)
- Next successful response → delay resets to 5s

### T-D7: Dry Run
- Specify page range → preview prompt shown (not sent)
- Click "Send Dry Run" → response displayed for review
- Response NOT saved to DB (dry run only)

### T-D8: Prompt Editor
- Load default prompts → system prompt and extraction prompt shown in text areas
- Edit prompts → save per-book
- Reset to Default → restores original prompts
- Dry run uses edited prompts

---

## Phase E — Review UI Tests

### T-E1: Knowledge Page List
- Load V2 review page → list of extracted knowledge pages shown
- Each entry shows: L3 title, page range, summary, status indicators

### T-E2: Three-View Display
- Select a knowledge page → 3 views available:
  1. Queryable Parameters: structured form with L1/L2/L3 titles, summary, difficulty, etc.
  2. Formatted JSON: pretty-printed JSON viewer with syntax highlighting
  3. Formatted XML: syntax-highlighted XML viewer
- All 3 views show data for the same knowledge page

### T-E3: Navigation
- Previous/Next buttons → navigate between knowledge pages
- Page counter shows current position (e.g., "3 of 47")

### T-E4: Review Actions
- Mark as verified → `verified` flag updated in DB
- Add notes → `notes` field saved
- Toggle enabled/disabled → `record_status` updated

### T-E5: Filter/Query
- Filter by L1 title (shows text, queries by ID) → correct results
- Filter by difficulty score range → correct results
- Filter by concept type → correct results
- Filter by physics domain → correct results

### T-E6: Cost Dashboard
- Shows per-window cost breakdown
- Running total matches sum of individual calls
- Cache hit rate percentage displayed
- Estimated remaining cost shown during extraction

### T-E7: Export
- Export to JSON → all knowledge pages with full data
- Export to CSV → queryable fields only (flat structure)

---

## Integration Tests

### T-I1: Full Book Extraction Flow
1. Configure OpenAI provider on Pipeline Config
2. Upload book, verify extraction_method = 'v2'
3. Define L1 + L2 titles on Auto-Slicer
4. Review few-shot examples (5 pages)
5. Send few-shot examples to LLM
6. Dry run on pages 1-4 → review prompt and response
7. Start full extraction → monitor progress + cost
8. Pause at 50% → verify partial results in review UI
9. Resume → extraction completes
10. Review all knowledge pages in V2 review UI
11. Export to JSON

### T-I2: V1/V2 Coexistence
- Book with extraction_method='v1' → L3 title section visible on Auto-Slicer, V2 extraction section hidden
- Book with extraction_method='v2' → L3 title section hidden, V2 extraction section visible
- Book with both → radio button toggles between V1/V2 title modes

### T-I3: Existing Book Migration
- Run `migrate_add_v2_tables.py` → V2 tables created for all existing books
- Existing V1 data untouched
- Existing books get extraction_method='v2' default (but V1 pipeline still works)
