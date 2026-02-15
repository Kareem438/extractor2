# Requirements: Cloud OCR Approach (Qwen 2.5-VL + DeepSeek-R1)

**Task:** Integrate cloud-based AI models as alternative OCR/analysis engines
**Date:** 2026-02-12
**Status:** 🔄 In Progress

---

## Context

The "New Approach" document proposes a 2-tier cloud AI workflow:
- **Tier 1 — Qwen 2.5-VL (72B)** via OpenRouter: Vision model for Arabic PDF text extraction (OCR replacement)
- **Tier 2 — DeepSeek-R1** via DeepSeek API: Reasoning model for deep analysis of extracted text

Estimated cost: ~$60 for 600 pages (vs ~$376 with Claude Opus 4.5).

The existing system already has:
- Multiple local OCR engines (EasyOCR, Surya, PaddleOCR, Tesseract) in `ocr_sequential.py`
- Claude batch service for diagram analysis in `claude_batch_service.py`
- Pipeline config system for multi-step processing
- `raw_{prefix}_knowledge_units` table with `ocr_engine` column

---

## Requirements Q&A Log

### Q1: What is the primary goal of integrating these cloud models?
**Options:**
- A) Replace existing local OCR engines entirely
- B) Add as additional options alongside existing engines
- C) Qwen replaces local OCR only, Claude stays for diagrams
- D) Different scope — new workflow, not existing OCR pipeline

**Answer:** Custom — Two distinct roles:

**Qwen 2.5-VL:** An option to replace the entire OCR workflow. The user performs layout extraction on 5-6 pages (using existing DocLayout-YOLO), and those annotated pages become few-shot prompts for Qwen. Qwen then processes remaining pages and returns structured output matching the format needed for KU creation — so the existing KU creation APIs are reused as-is.

**DeepSeek-R1:** Two roles:
1. Diagram analysis (replacing/alongside Claude)
2. Pipeline execution as the main reasoning engine (replacing Claude in pipeline steps)

User requested detailed research on the most accurate/capable DeepSeek version and pricing.

---

### Q2: How should the few-shot prompt workflow work?
**Options:**
- A) User manually selects which annotated pages to use as few-shot examples from the UI
- B) System automatically picks the first N annotated pages
- C) User selects pages, system also suggests "best" candidates based on layout diversity
- D) Different approach

**Answer:** A — User manually selects which annotated pages to use as few-shot examples from the UI.

**Additional request:** Investigate whether few-shot samples can be cached to reduce input token costs.

**Research findings — Prompt Caching for Qwen VL:**

1. **Alibaba Cloud (DashScope) — Implicit caching:** Available for `qwen-vl-max`, `qwen-vl-plus`, `qwen3-vl-plus`, `qwen3-vl-flash`. Automatic, no config needed. Cached tokens billed at 20% of standard input price. Minimum 256 tokens. Works by prefix matching — if few-shot examples are placed at the start of the prompt (before the target page), subsequent requests sharing the same prefix will hit the cache. Not guaranteed but likely for our use case since all pages in a book share the same few-shot prefix.

2. **Alibaba Cloud (DashScope) — Explicit caching:** Available for `qwen3-vl-plus` (Chinese mainland only). Uses `cache_control: {"type": "ephemeral"}` tags. Cache creation costs 125% of input price, but hits cost only 10%. 5-minute TTL (resets on hit). Guaranteed hits. Up to 4 cache breakpoints per request.

3. **OpenRouter — Prompt caching:** OpenRouter supports prompt caching for OpenAI, Anthropic, DeepSeek, Google Gemini, and Grok models. Qwen models via OpenRouter do NOT currently have explicit caching support documented. However, if the underlying provider (e.g., Alibaba Cloud) has implicit caching, it may still apply transparently.

4. **Key insight for our design:** If we use Qwen via OpenRouter, we get no guaranteed caching. If we use Qwen via Alibaba Cloud DashScope directly (OpenAI-compatible API), we get implicit caching automatically (20% cost for cached tokens) and potentially explicit caching for newer models (10% cost). This is a significant cost consideration — for 600 pages sharing the same 5-6 few-shot examples, caching could reduce input costs by ~80%.

5. **Recommendation:** Support both OpenRouter and DashScope as provider options. For cost optimization, prefer DashScope when caching is important. Structure prompts with few-shot examples as a fixed prefix (system message or first user message) so they are cacheable.

6. **Note from user:** Newer Qwen versions (beyond 2.5) can be used. Design should support model selection (e.g., `qwen3-vl-plus`, `qwen3-vl-flash`) not just `qwen2.5-vl-72b-instruct`.

---

### Q3: What structured output format should Qwen return for each page?
**Options:**
- A) Raw Markdown, parsed server-side into KUs
- B) JSON array of KU objects matching the DB schema
- C) Hybrid Markdown with special markers
- D) Different approach

**Answer:** B (JSON) — determined from code analysis.

**User clarification:** L1 (chapter) and L2 (topic) titles are already configured by the user in the titles tables (`level1_titles`, `level2_titles`) with page ranges. Qwen does NOT need to extract L1/L2 titles. Qwen extracts everything else.

**Code analysis findings:**

The existing KU creation pipeline is:
1. `raw_knowledge_units` — full page text per OCR engine (raw dump)
2. `raw_paragraph_images` — individual paragraph crops with: `extracted_text`, `ocr_confidence`, `level_1_title`, `level_2_title`, `level_3_title`, `selection_x/y/width/height`, `display_order`, `is_enabled`
3. `knowledge_units` — final KUs created by `create_knowledge_units_for_pages()` which reads from `raw_paragraph_images` and maps: `level_1_title` → `chapter`, `level_2_title` → `topic`, `level_3_title` → `sub_topic`

**Design decision:** Qwen should return a JSON array per page. Each element represents a text block (paragraph, heading, etc.) with:
- `text`: The extracted Arabic text
- `type`: Element type (paragraph, heading, footnote, etc.) — maps to `attr9_value` (KU type)
- `level_3_title`: Sub-topic heading if applicable (Qwen extracts this)
- `confidence`: Estimated confidence (0-1)
- `order`: Reading order on the page (maps to `display_order`)
- `bbox`: Approximate bounding box `[x, y, width, height]` (maps to `selection_x/y/width/height`)

L1/L2 titles are resolved server-side by looking up the page number against the existing `level1_titles` and `level2_titles` tables (page range matching). This data is injected into the `raw_paragraph_images` records before KU creation.

This approach reuses the existing `create_knowledge_units_for_pages()` function as-is — Qwen's output is inserted into `raw_paragraph_images` and the existing KU creation flow takes over.

---

### Q4: How should DeepSeek-R1 integrate with the existing pipeline system?
**Options:**
- A) Drop-in replacement — same prompt templates, swap model name
- B) Separate pipeline step type with own prompt templates
- C) Both — drop-in for simple text prompts, separate step type for reasoning chain tasks
- D) Different approach

**Answer:** C — Both. Drop-in for simple text prompts, separate step type when reasoning chain is needed.

**Code analysis findings:**

The existing pipeline system:
- `pipeline_config` table stores steps with: `prompt_template`, `tag_mappings`, `fallback_attribute`, `claude_model`
- `claude_model` field currently accepts: `'sonnet-4'`, `'opus-4.5'`, `'haiku'`
- `execute_grouped_pipeline()` reads the step config, builds prompts via `build_grouped_prompt()`, and calls Claude (currently TODO — actual Claude execution not yet fully implemented)
- `PipelineStepCreate` model has `claude_model: Optional[str]` field

**Design decision:**
1. **Drop-in mode:** Extend `claude_model` field to accept `"deepseek-r1"`, `"deepseek-v3"`, `"qwen-vl"`, etc. The service layer routes to the appropriate API client based on model name. Same prompt templates, same variable substitution. Response is the final `content` only.
2. **Reasoning chain mode:** New step type or flag (e.g., `include_reasoning: true`) that returns both `reasoning_content` and `content` from DeepSeek-R1. The reasoning chain can be stored in a separate attribute (e.g., `attr10_value`) while the final answer goes to the configured output field.
3. The `claude_model` field should be renamed conceptually to `ai_model` (or kept as-is for backward compat but documented to accept non-Claude models).

**DeepSeek Research (requested in Q1):**

DeepSeek has consolidated to a single model: **DeepSeek-V3.2** (as of 2026), accessible via two API endpoints:
- `deepseek-chat` — V3.2 in non-thinking mode (general text, fast)
- `deepseek-reasoner` — V3.2 in thinking mode (reasoning chain, slower but more accurate)

**Pricing (per 1M tokens, via api.deepseek.com):**
| | Cache Hit | Cache Miss | Output |
|---|---|---|---|
| Both models | $0.028 | $0.28 | $0.42 |

Key facts:
- Context length: 128K tokens
- Max output: 8K (chat) / 64K (reasoner)
- Features: JSON output, tool calls, chat prefix completion
- Caching is automatic (like OpenAI) — 90% discount on cache hits ($0.028 vs $0.28)
- Off-peak pricing discounts during 16:30-00:30 UTC daily

**Comparison for 600 pages (estimated):**
- Claude Opus 4.5: ~$376
- DeepSeek-R1 (cache miss): ~$30-50
- DeepSeek-R1 (cache hit): ~$3-5
- Qwen via DashScope (cache hit): ~$12-20

Source: [DeepSeek API Pricing](https://api-docs.deepseek.com/quick_start/pricing/)

---

### Q5: Where should the cloud OCR UI live and how does the execution flow work?
**Options:**
- A) New tab in processing dashboard
- B) Integrated into existing OCR page
- C) Separate dedicated page
- D) Different approach

**Answer:** Custom — integrated into the existing auto-slicer page.

**User's workflow description:**
1. User reviews layout detection on the layout-review page (existing)
2. User fixes errors and clicks "Ready for Extraction" per page (existing)
3. On the auto-slicer page, a new button triggers cloud extraction
4. User specifies number of pages to extract
5. Pages marked "Ready for Extraction" become the few-shot samples (sent to Qwen as cache)
6. Remaining pages are sent one-by-one; Qwen reads the cached samples and applies the same regions/categorization
7. Results appear on the existing auto-slicer pages with a "Cloud Extraction" header

**Research 1: Button Placement**

From code analysis:
- The auto-slicer page (`auto-slicer.js`) has the main OCR execution controls: `runAutoSlicer()`, `pauseAutoSlicer()`, `resumeAutoSlicer()`, `cancelAutoSlicer()`
- The layout-review page (`layout-review.js`) has the "Ready for Extraction" button per page (`toggleReadyForExtraction()`)
- The "Ready for Extraction" status is stored in the layout detection config JSON under `ready_for_extraction[page_number]`

**Recommended button placement:**
- "Send Samples to Cloud" button: On the auto-slicer page, near the existing "Run Auto-Slicer" button. This collects all pages marked "Ready for Extraction" and sends them as few-shot samples.
- "Start Cloud Extraction" button: Also on the auto-slicer page, next to "Send Samples". User specifies page range to extract. This triggers the cloud OCR for the remaining pages.
- Both buttons should be in a new "Cloud Extraction" section on the auto-slicer page, visually distinct from the local OCR section.

**Research 2: Qwen VL Caching — CRITICAL FINDING**

Detailed research reveals a significant limitation:

**Self-hosted Qwen (HuggingFace/vLLM):** Multimodal prefix caching with images is NOT supported. The model architecture is designed for "one multimodal prefill, then text-only decode." Images in the KV cache cannot be reused across calls. The `prepare_inputs_for_generation` function explicitly drops `pixel_values` when `cache_position > 0`. This is confirmed for Qwen2-VL, Qwen2.5-VL, Qwen3-VL, and Gemma-3.

**Alibaba Cloud DashScope API:** Implicit caching IS available for `qwen-vl-max`, `qwen-vl-plus`, `qwen3-vl-plus`, `qwen3-vl-flash`. The API-level caching works differently from model-level KV caching — it caches the entire prefill computation (including vision encoding) at the infrastructure level. Cached tokens cost 20% of standard price. The key requirement: few-shot images must be placed at the START of the prompt as a fixed prefix, and subsequent requests must share that exact prefix.

**Practical implications for our design:**
1. Via DashScope API: Caching WORKS for our use case. Place few-shot page images as the system message prefix. All subsequent page requests share this prefix → cache hit → 80% cost reduction on the few-shot portion.
2. Via OpenRouter: No guaranteed caching for Qwen VL models.
3. The cache is at the API/infrastructure level, not model KV level — so it works transparently.
4. Minimum 256 tokens for implicit cache, 1024 for explicit cache.
5. Cache validity: implicit = not guaranteed (system manages), explicit = 5 minutes (resets on hit).

**Workaround if caching doesn't hit:** Convert few-shot page images to detailed text descriptions once (using Qwen), then use those text descriptions as the cached prefix for subsequent pages. This guarantees text-only caching works but loses raw pixel access.

Sources: [HuggingFace Discussion](https://discuss.huggingface.co/t/multimodal-prefix-caching-with-qwen3-vl/170849), [Alibaba Cloud Context Cache](https://www.alibabacloud.com/help/en/model-studio/context-cache)

**Research 3: How Regions/Paragraphs Are Stored in DB**

From code analysis of the existing data flow:

**Layout detections** (`raw_{prefix}_layout_detections` table):
- Stored as individual rows, NOT JSON objects
- Each row: `page_number`, `class_name`, `class_id`, `x`, `y`, `width`, `height`, `confidence`
- Also has: `l1_title_id`, `l2_title_id`, `ocr_text`, `ocr_confidence`, `review_status`
- Linked to paragraphs/diagrams via `linked_paragraph_id`, `linked_diagram_id`

**Paragraph images** (`raw_{prefix}_paragraph_images` table):
- Stored as individual rows, NOT JSON objects
- Each row: `page_number`, `selection_x`, `selection_y`, `selection_width`, `selection_height`, `image_data` (BYTEA), `extracted_text`, `ocr_confidence`
- Title hierarchy: `level_1_title`, `level_2_title`, `level_3_title` (VARCHAR), `l1_title_id`, `l2_title_id` (INTEGER FK)
- Created by `create_paragraph_image()` in `auto_slicer_service.py`

**Knowledge units** (`{prefix}_knowledge_units` table):
- Stored as individual rows, NOT JSON objects
- Each row: `page_number`, `text_content`, `ocr_method`, `confidence_score`, `position_x`, `position_y`, `chapter` (L1), `topic` (L2), `sub_topic` (L3)
- Created by `create_knowledge_unit()` in `auto_slicer_service.py` or `create_paragraph_ku()` in `ku_creation_service.py`

**Title resolution** (`get_titles_for_page()` in `auto_slicer_service.py`):
- Reads from config JSON (auto-slicer config), NOT from the DB title tables
- Returns: `{level_1_title: str, level_2_title: str, level_3_title: str}`
- The KU creation service (`ku_creation_service.py`) reads titles from `raw_paragraph_images` columns directly

**OCR boundaries** (auto-slicer config JSON):
- Stored as JSON in the auto-slicer config (not in a DB table)
- Each boundary: `{start_page, end_page, rectangles: [{label, x, y, width, height, target}]}`

**CONCLUSION: A translation layer IS needed.**
Qwen will return JSON objects per page. The server must:
1. Parse Qwen's JSON response (array of text blocks with bbox, type, confidence, order)
2. For each text block, create a `raw_paragraph_images` row (with `image_data` cropped from the page image using the bbox)
3. Resolve L1/L2 titles from the DB title tables by page number
4. Set `created_by = 'qwen-cloud'` to distinguish from local OCR
5. The existing `create_knowledge_units_for_pages()` then creates KUs from these records

---

### Q6: Should we support both DashScope and OpenRouter, or just DashScope?
**Options:**
- A) DashScope only
- B) Both, DashScope as default
- C) Both + auto-select
- D) Different approach

**Answer:** A — DashScope only. Simpler, guaranteed caching, lower cost.

---

### Q6b (clarification): Knowledge Page concept

**User introduced a new concept:** `knowledge_page`

A knowledge_page is everything between two consecutive L3 titles — a logical grouping (not physical page). It contains all elements in that L3 section: paragraphs, diagrams, questions, equations, etc. Stored as a single JSON object in the DB.

Key properties:
- One physical page can contain multiple knowledge_pages (if multiple L3 sections start/end on it)
- One knowledge_page can span multiple physical pages (if an L3 section is long)
- The boundary is defined by L3 titles, not physical page breaks

**This changes the translation layer design from Q5:**
- Instead of: Qwen JSON → individual `raw_paragraph_images` rows
- Now: Qwen JSON → stored as-is in a new `knowledge_pages` table as a JSON column
- The JSON object contains all elements (paragraphs, diagrams, questions, equations) within that L3 section
- A separate step can later "explode" the knowledge_page JSON into individual KU records if needed

---

### Q7: When should knowledge_pages be "exploded" into individual KU records?
**Options:**
- A) Automatically right after cloud extraction — knowledge_pages are stored AND immediately exploded into individual KU records. The knowledge_page is kept as an archive/reference.
- B) On-demand — user reviews the knowledge_pages first (in a new review UI), then triggers "explode" when satisfied. This allows editing the JSON before it becomes individual KUs.
- C) Never — knowledge_pages replace the existing KU model entirely for cloud-extracted books. The pipeline and other features are updated to work with knowledge_pages directly.
- D) Different approach

**Answer:** B — On-demand, with review first.

**User details:**
1. The knowledge_page review UI should reuse the existing `layout-review` code as much as possible (same page navigation, canvas rendering, sidebar pattern, dual-page view, etc.)
2. After reviewing/editing knowledge_pages, a new button allows the user to convert knowledge_pages to KUs
3. A per-page flag similar to "Ready for Extraction" will be used, but called **"Ready to Convert to KU"**
4. The flow: Cloud extraction → knowledge_pages stored → user reviews in layout-review-style UI → marks pages "Ready to Convert to KU" → triggers conversion → individual KU records created

**Research — Layout Review Code Reuse:**

The existing `layout-review.js` (~4200 lines) provides:
- Page navigation (prev/next, page number input)
- Canvas-based image rendering with overlay regions (bounding boxes)
- Region selection, editing, resizing, moving
- Dual-page view (primary + secondary canvas)
- Sidebar with region list, class editor, links section
- "Ready for Extraction" toggle per page (`toggleReadyForExtraction()`)
- "Skip Page" toggle per page (`toggleSkipPage()`)
- Context menu with merge, split, reorder, class change
- Arabic mode (RTL reading order)
- Zoom controls
- L3 title linking

**Reusable components for knowledge_page review:**
- Page navigation system (prev/next, page number)
- Canvas rendering with page image + overlay
- Sidebar layout pattern
- Per-page flag toggle pattern ("Ready to Convert to KU" mirrors "Ready for Extraction")
- Arabic mode / zoom controls
- Dual-page view

**New/modified components needed:**
- Instead of bounding box regions, show knowledge_page JSON elements as overlays on the page image
- Editable text fields for each element in the sidebar (edit Arabic text, type, L3 title)
- Element reordering within the knowledge_page
- Add/remove elements from the knowledge_page
- "Ready to Convert to KU" button (replaces "Ready for Extraction")
- Conversion trigger button (batch convert all "ready" pages)

---

### Q8: How should error recovery and partial results work during cloud extraction?
**Options:**
- A) All-or-nothing — if any page fails, the entire batch is marked as failed
- B) Page-level granularity — each page tracked independently, failed pages marked individually, user can retry just failed pages, successful pages kept
- C) Batch-level with checkpointing — pages processed in batches, failed batches retried
- D) Different approach

**Answer:** B — Page-level granularity. Plus pause/resume capability.

**User details:**
1. Each page is tracked independently with its own status (pending, processing, completed, failed)
2. Failed pages are marked individually — user can retry just the failed pages
3. Successfully extracted pages are kept regardless of other page failures
4. Pause/resume capability should be included, following the existing auto-slicer pattern

**Research — Existing Auto-Slicer Pause/Resume Pattern:**

The auto-slicer uses an in-memory job tracking pattern:
- `_active_jobs[book_id]` dict stores: `status`, `pause_requested`, progress info
- `POST /api/auto-slicer/{book_id}/pause` — sets `job["pause_requested"] = True`, job pauses after current page completes
- `POST /api/auto-slicer/{book_id}/resume` — reads `execution_state` from config JSON, calls `start_execution()` which continues from last completed page
- Frontend: single button toggles between "Pause" / "Resume" text, swaps onclick handler
- Status polling: frontend polls status endpoint to update progress display

**Design for cloud extraction pause/resume:**
- Same pattern: `_active_cloud_jobs[book_id]` in-memory dict
- `POST /api/cloud-ocr/{book_id}/pause` — sets `pause_requested = True`, current page finishes, then stops
- `POST /api/cloud-ocr/{book_id}/resume` — reads last completed page from DB, continues from next pending page
- `POST /api/cloud-ocr/{book_id}/retry-failed` — retries only pages with status `"failed"`
- Per-page status stored in DB (not just in-memory) so progress survives server restarts
- Frontend mirrors auto-slicer UI: Run / Pause / Resume / Cancel buttons + progress bar

---

### Q9: How should the system handle API authentication and model selection?
**Options:**
- A) Single API key in `.env`, single model hardcoded
- B) Single API key in `.env`, model selectable per-book from UI dropdown
- C) Single API key in `.env`, model selectable per-extraction-run
- D) Different approach

**Answer:** 1 API key per provider, shared across all books. Model selectable per run.

**User details:**
- All Qwen models share 1 DashScope API key (`DASHSCOPE_API_KEY`)
- All DeepSeek models share 1 DeepSeek API key (`DEEPSEEK_API_KEY`)
- Existing pattern: `ANTHROPIC_API_KEY` already in `config.py` for Claude
- Keys are per-provider, not per-model or per-book

**Research — Existing Config Pattern:**

Current `config.py` uses `pydantic_settings.BaseSettings` with:
- `ANTHROPIC_API_KEY: str = Field(default="", description="...")` — optional, empty default
- `.env` file loading via `env_file = ".env"`
- Singleton `settings = Settings()`

**Design for new provider keys:**
```python
# DashScope (Qwen VL models)
DASHSCOPE_API_KEY: str = Field(default="", description="DashScope API key for Qwen VL models")
DASHSCOPE_BASE_URL: str = Field(default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1", description="DashScope API base URL")

# DeepSeek
DEEPSEEK_API_KEY: str = Field(default="", description="DeepSeek API key")
DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com", description="DeepSeek API base URL")
```

Follows the same pattern as `ANTHROPIC_API_KEY` — optional with empty default, validated at request time (not startup).

---

### Q10: What's the scope for the initial implementation — phasing?
**Options:**
- A) Full implementation — all requirements in one go
- B) Phase 1 first — just Qwen extraction + knowledge_page storage + basic status tracking
- C) Phase 1 = Qwen + knowledge_page review UI + KU conversion (full cloud OCR → review → KU flow). Phase 2 = DeepSeek + pipeline integration + cost tracking.
- D) Different phasing

**Answer:** C — Two phases.

**Phase 1 (implement now):**
1. Config: `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL` in `.env` / `config.py`
2. Qwen_Service: DashScope API client, few-shot prompt builder, page-by-page extraction
3. Cloud OCR endpoints: start, pause, resume, cancel, retry-failed, status
4. `{prefix}_knowledge_pages` table + migration
5. Translation layer: Qwen JSON → knowledge_pages (grouped by L3 title)
6. Knowledge_page review UI (reusing layout-review patterns)
7. "Ready to Convert to KU" flag + conversion to individual KU records
8. Error recovery: page-level tracking, retry failed pages
9. Basic logging (request/response metadata)

**Phase 2 (later):**
1. DeepSeek_Service: `DEEPSEEK_API_KEY`, chat + reasoner modes
2. Pipeline engine cloud model support (model routing for deepseek-r1, qwen-vl in pipeline steps)
3. Cost tracking: token usage recording, per-model pricing, cost summary endpoints
4. Fallback to local OCR for cloud-failed pages
5. Reasoning chain storage (DeepSeek `reasoning_content` in separate attribute)

---

## Requirements Gathering: ✅ COMPLETE (Q1-Q10 answered)
