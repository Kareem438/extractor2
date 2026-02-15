# Tracking: Rolling API XML Extraction (V2 Cloud Extraction)

**Date:** 2026-02-15
**Status:** 🔄 Step 9 — Implementation (Phase E complete, cleanup done)

---

## Progress

| Phase | Status | Files | Notes |
|-------|--------|-------|-------|
| A — Foundation | ✅ Complete | migrations, table_creator, books_metadata | 3 migrations run & verified |
| B — LLM Config | ✅ Complete | llm_provider_service, llm_providers routes, pipeline-config UI | All CRUD tested via HTTP |
| C — Core Engine | ✅ Complete | xml_parser, few_shot, v2_extraction service+routes | 14 endpoints tested |
| D — Extraction UI | ✅ Complete | auto-slicer.html, auto-slicer.js modifications | V2 section added |
| E — Review UI | ✅ Complete | v2-knowledge-review.html, v2-knowledge-review.js, KP update endpoint | 3-view tabs, verify, notes, keyboard nav |
| Cleanup | ✅ Complete | Deleted cloud_ocr.py, qwen_service.py, knowledge-page-review.* | Old V1 cloud files removed |

---

## Phase A — Foundation ✅

### A1: migrate_add_llm_providers.py ✅
- [x] Create global `llm_providers` table (10 columns)
- [x] Test: run migration, verify table exists
- [x] Test: run twice (idempotent)

### A2: migrate_add_extraction_method.py ✅
- [x] Add `extraction_method` column to `books_metadata`
- [x] Test: run migration, verify column exists with default 'v2'

### A3: table_creator.py — V2 table functions ✅
- [x] `create_v2_knowledge_pages_table()` (107 columns, 36 indexes)
- [x] `create_v2_extraction_log_table()`
- [x] `create_v2_few_shot_examples_table()`
- [x] `create_v2_attribute_keys_table()`
- [x] `insert_default_v2_attribute_keys()` (80 keys)
- [x] Modify `create_book_tables()` — conditional V1/V2 table creation
- [x] Test: create tables for 2 existing books, verified schema

### A4: books_metadata.py ✅
- [x] Add extraction_method column to SQLAlchemy model

### A5: Upload route ✅
- [x] Add extraction_method parameter to upload
- [x] Conditional table creation based on method

---

## Phase B — LLM Config ✅

### B1: llm_provider_service.py ✅
- [x] Full CRUD (create, read, update, delete)
- [x] test_connection() — provider-agnostic (OpenAI, Anthropic, Google, DashScope)
- [x] call_llm() — unified interface
- [x] API key masking (e.g., `sk-t****2345`)
- [x] Enable/disable toggle

### B2: llm_providers.py routes ✅
- [x] 7 endpoints: list, get, create, update, delete, toggle, enabled-only
- [x] All tested via HTTP on port 8888

### B3: pipeline-config.html ✅
- [x] LLM Providers UI section with add/edit/delete/test/toggle

---

## Phase C — Core Engine ✅

### C1: xml_parser_service.py ✅
- [x] XML validation, parsing, XML→JSON conversion
- [x] Field extraction: 9 categories, ~70+ tags

### C2: few_shot_service.py ✅
- [x] CRUD: add, list, delete examples
- [x] Page image base64 encoding
- [x] Mark-as-sent tracking

### C3: v2_extraction_service.py ✅
- [x] Rolling window engine with smart jump
- [x] Retry logic (3→cooldown 15min→3→alert)
- [x] Cost tracking per API call
- [x] Pause/resume/cancel state machine
- [x] Dry run mode
- [x] Prompt management (get/save/reset defaults)

### C4: v2_extraction.py routes ✅
- [x] 14 endpoints: extraction control, dry run, prompts, few-shots, knowledge pages
- [x] All tested via HTTP

---

## Phase D — Extraction UI ✅

### D1: auto-slicer.html ✅
- [x] V2 Cloud Extraction section after V1 section
- [x] Provider dropdown, min delay, start/pause/cancel buttons
- [x] Progress dashboard (KPs, API calls, cost, cache hit rate)
- [x] Few-shot panel, dry run panel, prompt editor panel

### D2: auto-slicer.js ✅
- [x] V2 functions: init, toggle visibility, load providers, check prerequisites
- [x] Start/pause/resume/cancel extraction
- [x] Poll status, update UI
- [x] Few-shot management, dry run, prompt editor
- [x] Hooked into onBookSelect via wrapper

### D3: books.py ✅
- [x] Added `extraction_method` to list_books and get_book responses

---

## Phase E — Review UI ✅

### E1: v2-knowledge-review.html ✅
- [x] Sidebar KP list with pagination
- [x] 3-view tabs (Queryable Parameters, JSON, XML)
- [x] Actions bar (verify, notes, KP navigation)
- [x] Stats bar (total, verified, unverified, cost)

### E2: v2-knowledge-review.js ✅
- [x] Initialization, loadBookInfo, loadKnowledgePages, loadStats
- [x] renderKPList, selectKP, renderCurrentKP
- [x] renderParamsView, renderJSONView, renderXMLView
- [x] syntaxHighlightJSON, syntaxHighlightXML
- [x] switchView (params/json/xml tab switching)
- [x] prevKP, nextKP (KP navigation with scroll-into-view)
- [x] prevPage, nextPage (pagination)
- [x] toggleVerify (mark/unmark verified via API)
- [x] toggleNotes, saveNotes (notes via API)
- [x] Keyboard navigation (↑↓/jk, v=verify, 1/2/3=views)

### E3: v2_extraction.py — KP update endpoint ✅
- [x] PUT `/api/v2/books/{book_id}/knowledge-pages/{kp_id}`
- [x] Supports: verified, notes, record_status fields

### E4: main.py — Page route ✅
- [x] `/v2-knowledge-review` page route registered

---

## Cleanup ✅

- [x] Deleted `03-code/src/api/routes/cloud_ocr.py`
- [x] Deleted `03-code/src/services/qwen_service.py`
- [x] Deleted `03-code/src/frontend/templates/knowledge-page-review.html`
- [x] Deleted `03-code/src/frontend/static/js/knowledge-page-review.js`
- [x] Removed cloud_ocr import and router from `main.py`
- [x] Replaced `/knowledge-page-review` route with `/v2-knowledge-review`

---

## All Implementation Files

| File | Type | Phase |
|------|------|-------|
| `03-code/migrate_add_llm_providers.py` | New | A |
| `03-code/migrate_add_extraction_method.py` | New | A |
| `03-code/migrate_add_v2_tables.py` | New | A |
| `03-code/src/database/table_creator.py` | Modified | A |
| `03-code/src/database/models/books_metadata.py` | Modified | A |
| `03-code/src/api/routes/upload.py` | Modified | A |
| `03-code/src/services/llm_provider_service.py` | New | B |
| `03-code/src/api/routes/llm_providers.py` | New | B |
| `03-code/src/frontend/templates/pipeline-config.html` | Modified | B |
| `03-code/src/services/xml_parser_service.py` | New | C |
| `03-code/src/services/few_shot_service.py` | New | C |
| `03-code/src/services/v2_extraction_service.py` | New | C |
| `03-code/src/api/routes/v2_extraction.py` | New | C+E |
| `03-code/src/frontend/templates/auto-slicer.html` | Modified | D |
| `03-code/src/frontend/static/js/auto-slicer.js` | Modified | D |
| `03-code/src/api/routes/books.py` | Modified | D |
| `03-code/src/frontend/templates/v2-knowledge-review.html` | New | E |
| `03-code/src/frontend/static/js/v2-knowledge-review.js` | New | E |
| `03-code/src/main.py` | Modified | B+E+Cleanup |
