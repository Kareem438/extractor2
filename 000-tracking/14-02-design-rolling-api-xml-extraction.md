# Design: Rolling API XML Extraction (V2 Cloud Extraction)

**Task:** V2 Cloud-based knowledge extraction using ChatGPT 5 with rolling window
**Date:** 2026-02-15
**Status:** 🔄 Step 2 — Code Impact Review

---

## Step 2: Code Impact Review

### Summary of Changes

This feature touches 5 major areas:
1. **Database** — New V2 tables + global LLM providers table + books_metadata column
2. **Backend Services** — New V2 extraction service + LLM provider service
3. **API Routes** — New V2 extraction routes + LLM provider CRUD routes
4. **Frontend Templates** — Modifications to auto-slicer + pipeline-config + new V2 review page
5. **Frontend JS** — Modifications to auto-slicer.js + new V2 review JS + new pipeline-config JS additions

---

### FILES TO MODIFY (Existing)

#### 1. `03-code/src/database/table_creator.py`
**What:** Add 3 new V2 table creation functions + modify `create_book_tables()` to conditionally create V2 tables
**Impact:** HIGH — Core table creation
**Changes:**
- Add `create_v2_knowledge_pages_table(table_prefix)` — Main V2 table with all queryable columns + raw_xml + parsed_json + 80 attrs
- Add `create_v2_extraction_log_table(table_prefix)` — Per-API-call tracking (window, tokens, cost, timing)
- Add `create_v2_few_shot_examples_table(table_prefix)` — Stores annotated few-shot pages
- Modify `create_book_tables()` — Add V2 table creation calls (always created alongside V1 tables; the extraction_method setting controls which pipeline is used, not which tables exist)
**Existing code to preserve:** All existing table creation functions remain unchanged. The existing `knowledge_pages` and `cloud_ocr_pages` tables from Task 1 remain as-is (they serve the Qwen cloud OCR feature).

#### 2. `03-code/src/database/models/books_metadata.py`
**What:** Add `extraction_method` column (VARCHAR, default 'v2')
**Impact:** LOW — Single column addition
**Migration needed:** Yes — `migrate_add_extraction_method.py`

#### 3. `03-code/src/config.py`
**What:** No changes needed. LLM provider config moves to DB (global `llm_providers` table), not .env file. Existing DASHSCOPE_API_KEY and ANTHROPIC_API_KEY remain for backward compatibility with V1 features.
**Impact:** NONE

#### 4. `03-code/src/frontend/templates/auto-slicer.html`
**What:** Add V2 Cloud Extraction section + modify L3 title section visibility based on extraction method
**Impact:** MEDIUM
**Changes:**
- Add radio button for V1/V2 title definition mode (controls L3 section visibility)
- Add new "V2 Cloud Extraction" section with: provider dropdown, few-shot buttons, dry run area, prompt editor, extraction controls (start/pause/resume/cancel), progress dashboard, cost tracker
- Existing sections remain unchanged

#### 5. `03-code/src/frontend/static/js/auto-slicer.js`
**What:** Add V2 extraction UI logic + L3 visibility toggle
**Impact:** MEDIUM
**Changes:**
- Add extraction method radio button handler (show/hide L3 section)
- Add V2 extraction control functions (already has `startCloudExtraction`, `pauseCloudExtraction`, etc. — these will be EXTENDED, not duplicated)
- Add few-shot review/send functions
- Add dry run functions
- Add prompt editor load/save functions
- Add cost dashboard update functions
- Add pre-requisite validation (L1/L2 defined, API key configured, few-shots sent)

#### 6. `03-code/src/frontend/templates/pipeline-config.html`
**What:** Add "LLM Providers" section
**Impact:** MEDIUM
**Changes:**
- Add new section for LLM provider configuration (API key, base URL, model name, enabled toggle)
- Support for OpenAI, DashScope, Anthropic, Google providers
- CRUD operations for providers

#### 7. `03-code/src/api/routes/cloud_ocr.py`
**What:** Extend with V2-specific routes OR create separate route file
**Impact:** MEDIUM — Decision: Create NEW route file `v2_extraction.py` to keep V1 cloud OCR separate from V2 extraction. The existing cloud_ocr.py serves the Qwen-based Task 1 feature and should not be modified.

#### 8. `03-code/src/main.py`
**What:** Register new route files and page templates
**Impact:** LOW
**Changes:**
- Register `v2_extraction` router
- Register `llm_providers` router
- Add V2 knowledge page review page route

---

### NEW FILES TO CREATE

#### Backend — Services
| # | File | Purpose |
|---|------|---------|
| 1 | `03-code/src/services/v2_extraction_service.py` | Core V2 extraction engine: rolling window algorithm, smart jump logic, L3 boundary detection, XML parsing, L1/L2 title injection, retry logic, cost tracking |
| 2 | `03-code/src/services/llm_provider_service.py` | LLM provider CRUD, API key encryption/decryption, provider-agnostic API call wrapper |
| 3 | `03-code/src/services/few_shot_service.py` | Few-shot example management: annotated image generation (colored outlines + labels), send to LLM, cache management |
| 4 | `03-code/src/services/xml_parser_service.py` | XML schema validation, XML→JSON conversion, field extraction for queryable columns |

#### Backend — API Routes
| # | File | Purpose |
|---|------|---------|
| 5 | `03-code/src/api/routes/v2_extraction.py` | V2 extraction API: start/pause/resume/cancel, status, dry run, prompt management, pre-requisite check |
| 6 | `03-code/src/api/routes/llm_providers.py` | LLM provider CRUD API: list/create/update/delete providers, test connection |

#### Frontend — Templates
| # | File | Purpose |
|---|------|---------|
| 7 | `03-code/src/frontend/templates/v2-knowledge-review.html` | V2 knowledge page review UI: queryable params view, formatted JSON view, formatted XML view, navigation, verify/notes |

#### Frontend — JavaScript
| # | File | Purpose |
|---|------|---------|
| 8 | `03-code/src/frontend/static/js/v2-knowledge-review.js` | V2 review page logic: load/navigate/edit knowledge pages, toggle views, verify, export |
| 9 | `03-code/src/frontend/static/js/llm-providers.js` | LLM provider config UI logic (for pipeline-config page) |

#### Database — Migrations
| # | File | Purpose |
|---|------|---------|
| 10 | `03-code/migrate_add_extraction_method.py` | Add `extraction_method` column to `books_metadata` |
| 11 | `03-code/migrate_add_llm_providers.py` | Create global `llm_providers` table |
| 12 | `03-code/migrate_add_v2_tables.py` | Add V2 tables to existing books (for books created before this feature) |

---

### DATABASE SCHEMA DETAILS

#### Global Table: `llm_providers`
```sql
CREATE TABLE IF NOT EXISTS llm_providers (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR(50) NOT NULL,        -- 'openai', 'dashscope', 'anthropic', 'google'
    display_name VARCHAR(100) NOT NULL,        -- 'OpenAI ChatGPT 5', 'DashScope Qwen', etc.
    api_key TEXT NOT NULL,                     -- Encrypted
    base_url VARCHAR(500),                     -- Default per provider, editable
    model_name VARCHAR(100) NOT NULL,          -- 'gpt-5', 'qwen-vl-max', etc.
    auth_header_style VARCHAR(50) DEFAULT 'bearer',  -- 'bearer', 'x-api-key', 'x-goog-api-key'
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(provider_name)
);
```

#### Per-Book Table: `v2_{prefix}_knowledge_pages`
```sql
CREATE TABLE IF NOT EXISTS v2_{prefix}_knowledge_pages (
    id SERIAL PRIMARY KEY,
    
    -- Title hierarchy (queryable)
    l1_title_id INTEGER,                       -- FK to {prefix}_level1_titles
    l2_title_id INTEGER,                       -- FK to {prefix}_level2_titles
    l3_title_text VARCHAR(500),                -- Start L3 title (from LLM)
    l3_title_end_text VARCHAR(500),            -- End L3 title (from LLM)
    
    -- Page range (queryable)
    start_page INTEGER NOT NULL,
    end_page INTEGER NOT NULL,
    
    -- Summary (queryable)
    summary TEXT,                               -- 2-3 line technical concept summary
    
    -- Classification (queryable)
    difficulty_score INTEGER,                   -- 1-10
    concept_type VARCHAR(50),                   -- law, theorem, definition, etc.
    bloom_taxonomy_level VARCHAR(20),           -- remember, understand, apply, etc.
    physics_domain VARCHAR(50),                 -- mechanics, optics, etc.
    exam_relevance VARCHAR(10),                 -- high, medium, low
    extraction_confidence VARCHAR(10),          -- high, medium, low
    has_worked_example BOOLEAN DEFAULT FALSE,
    has_problem_set BOOLEAN DEFAULT FALSE,
    element_count INTEGER DEFAULT 0,
    
    -- Review (queryable)
    verified BOOLEAN DEFAULT FALSE,
    notes TEXT,
    record_status VARCHAR(20) DEFAULT 'enabled',
    
    -- Full content storage
    raw_xml TEXT,                               -- Complete XML from LLM
    parsed_json JSONB,                          -- Parsed XML as JSON
    
    -- 80 user-defined attributes
    attr1_value TEXT, attr2_value TEXT, ... attr80_value TEXT,
    
    -- Extraction metadata
    llm_provider VARCHAR(50),                   -- 'openai', 'dashscope', etc.
    model_name VARCHAR(100),                    -- 'gpt-5', etc.
    window_pages TEXT,                          -- JSON array of page numbers in the window
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Per-Book Table: `v2_{prefix}_extraction_log`
```sql
CREATE TABLE IF NOT EXISTS v2_{prefix}_extraction_log (
    id SERIAL PRIMARY KEY,
    window_start_page INTEGER NOT NULL,
    window_end_page INTEGER NOT NULL,
    window_pages TEXT,                          -- JSON array of pages sent
    knowledge_page_id INTEGER,                  -- FK to v2_knowledge_pages (NULL if no KP extracted)
    
    -- Token tracking
    input_tokens_cached INTEGER DEFAULT 0,
    input_tokens_uncached INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    
    -- Cost tracking
    cost_input_cached NUMERIC(10,6) DEFAULT 0,
    cost_input_uncached NUMERIC(10,6) DEFAULT 0,
    cost_output NUMERIC(10,6) DEFAULT 0,
    cost_total NUMERIC(10,6) DEFAULT 0,
    
    -- Timing
    processing_time_ms INTEGER,
    
    -- Status
    status VARCHAR(20) DEFAULT 'success',       -- success, retry, failed, skipped
    error_message TEXT,
    attempt_number INTEGER DEFAULT 1,
    retry_phase INTEGER DEFAULT 1,              -- 1 = immediate, 2 = after cooldown
    
    -- Model info
    llm_provider VARCHAR(50),
    model_name VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Per-Book Table: `v2_{prefix}_few_shot_examples`
```sql
CREATE TABLE IF NOT EXISTS v2_{prefix}_few_shot_examples (
    id SERIAL PRIMARY KEY,
    page_number INTEGER NOT NULL,
    annotated_image_path TEXT,                  -- Path to annotated image file
    annotation_data JSONB,                      -- Region annotations (type, bbox, label, color)
    cache_name VARCHAR(200),                    -- User-provided cache identifier
    sent_to_llm BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    llm_provider VARCHAR(50),
    model_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Column Addition: `books_metadata.extraction_method`
```sql
ALTER TABLE books_metadata 
ADD COLUMN IF NOT EXISTS extraction_method VARCHAR(10) DEFAULT 'v2';
```

---

### V2 EXTRACTION ALGORITHM (Pseudocode)

```
function extract_book_v2(book_id, provider, model):
    # Pre-requisite checks
    validate_l1_l2_coverage(book_id)
    validate_api_key(provider)
    validate_few_shots_sent(book_id)
    
    # Load context
    few_shot_images = load_few_shot_examples(book_id)
    system_prompt = load_system_prompt(book_id)  # editable by user
    extraction_prompt = load_extraction_prompt(book_id)  # editable by user
    l1_titles = load_l1_titles(book_id)
    l2_titles = load_l2_titles(book_id)
    
    # Initialize
    current_page = 1
    total_pages = get_total_pages(book_id)
    last_kp_end_page = None
    last_kp_end_l3 = None
    min_delay = get_configured_delay(book_id)  # default 5s
    current_delay = min_delay
    
    while current_page <= total_pages:
        # Check pause/cancel
        if is_paused(): wait_for_resume()
        if is_cancelled(): break
        
        # Determine window
        window_size = 4
        window_pages = [current_page, ..., current_page + window_size - 1]
        window_pages = [p for p in window_pages if p <= total_pages]
        
        # Inject L1/L2 context
        l1_title = find_l1_for_page(l1_titles, current_page)
        l2_title = find_l2_for_page(l2_titles, current_page)
        
        # Build prompt
        prompt = build_extraction_prompt(
            system_prompt, extraction_prompt,
            few_shot_images,  # cached prefix
            window_pages, l1_title, l2_title,
            last_kp_end_l3  # continuation context
        )
        
        # Call LLM with retry logic
        response = call_llm_with_retry(provider, model, prompt)
        # Retry: 3 immediate → 15min cooldown → 3 more → alert user
        
        # Parse XML response
        xml_result = validate_and_parse_xml(response)
        
        # Extract knowledge page(s)
        for kp in xml_result.knowledge_pages:
            # Inject L1/L2 title IDs deterministically
            kp.l1_title_id = find_l1_id_for_pages(l1_titles, kp.start_page, kp.end_page)
            kp.l2_title_id = find_l2_id_for_pages(l2_titles, kp.start_page, kp.end_page)
            
            # Save to DB
            save_v2_knowledge_page(book_id, kp)
            
            # Update tracking
            last_kp_end_page = kp.end_page
            last_kp_end_l3 = kp.l3_title_end_text
        
        # Log extraction call
        log_extraction(book_id, window_pages, response.tokens, response.cost)
        
        # Smart jump: start next window from last KP end page
        if last_kp_end_page:
            current_page = last_kp_end_page
        else:
            # No KP found in window — try 8-page window
            if window_size == 4:
                window_size = 8
                continue  # retry same starting page with bigger window
            else:
                # 8-page window also failed — flag error
                flag_error(book_id, current_page)
                current_page += 1  # skip and continue
        
        # Throttle
        await sleep(current_delay)
        # Adaptive backoff on 429
```

---

### IMPLEMENTATION ORDER (Dependency-Based)

**Phase A — Foundation (no UI dependencies)**
1. `migrate_add_llm_providers.py` — Global LLM providers table
2. `migrate_add_extraction_method.py` — books_metadata column
3. `03-code/src/database/table_creator.py` — V2 table creation functions
4. `migrate_add_v2_tables.py` — Add V2 tables to existing books
5. `03-code/src/services/llm_provider_service.py` — Provider CRUD + API wrapper
6. `03-code/src/api/routes/llm_providers.py` — Provider API routes

**Phase B — LLM Config UI**
7. `03-code/src/frontend/static/js/llm-providers.js` — Provider config UI logic
8. `03-code/src/frontend/templates/pipeline-config.html` — Add LLM Providers section

**Phase C — Core Extraction Engine**
9. `03-code/src/services/xml_parser_service.py` — XML validation + parsing
10. `03-code/src/services/few_shot_service.py` — Few-shot annotation + management
11. `03-code/src/services/v2_extraction_service.py` — Rolling window engine
12. `03-code/src/api/routes/v2_extraction.py` — V2 extraction API routes

**Phase D — Extraction UI**
13. `03-code/src/frontend/templates/auto-slicer.html` — V2 extraction section
14. `03-code/src/frontend/static/js/auto-slicer.js` — V2 extraction UI logic

**Phase E — Review UI**
15. `03-code/src/frontend/templates/v2-knowledge-review.html` — Review page
16. `03-code/src/frontend/static/js/v2-knowledge-review.js` — Review logic
17. `03-code/src/main.py` — Register routes + pages

---

### RISK ASSESSMENT

| Risk | Severity | Mitigation |
|------|----------|------------|
| Existing cloud_ocr.py conflict | LOW | Creating separate v2_extraction.py, not modifying existing |
| Auto-slicer.html too large | MEDIUM | V2 section added as collapsible, minimal HTML changes |
| Auto-slicer.js too large (already 3700+ lines) | MEDIUM | V2 functions follow existing patterns, grouped at end of file |
| XML parsing failures | HIGH | Strict validation + 2-phase retry + user intervention |
| OpenAI rate limits | MEDIUM | Configurable delay (5s default) + adaptive backoff |
| L1/L2 title gaps | LOW | Pre-requisite validation blocks extraction start |
| Cost overruns | LOW | Live cost dashboard + pause capability |
