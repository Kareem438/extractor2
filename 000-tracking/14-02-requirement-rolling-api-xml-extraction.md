# Requirements: Rolling API XML Extraction

**Task:** Call APIs with 3 pages of the book in a rolling fashion, receiving XML output
**Date:** 2026-02-14
**Status:** 🔄 Requirements Gathering

---

## Requirements Q&A

### Q1: Which API provider are you calling with the 3 pages?
**Answer:** ChatGPT 5 (OpenAI). Use ChatGPT 5's caching capability for the few-shot prompt. Also build the ability to export layout preview images for user-selected pages, with regions classified/annotated so ChatGPT 5 can understand each region. The XML output is the extraction result.

**Key points captured:**
- Provider: OpenAI ChatGPT 5 (gpt-5 model family: gpt-5, gpt-5-mini, gpt-5-nano)
- Caching: Use OpenAI's automatic prompt caching for few-shot prefix
- Few-shot: Export annotated layout preview images from user-selected pages as training examples
- Layout preview export: Page images with classified regions (bounding boxes + labels) so the model understands what each region is
- Output format: XML
- Rolling window: 3 pages per API call

**OpenAI Prompt Caching Research:**
- Automatic for prompts >1024 tokens — no code changes needed
- Caches longest prefix match, in increments of 128 tokens
- Images are cached if identical images appear in the same order at the start of the prompt
- 90% discount on cached input tokens for GPT-5 family models
- Cache is scoped at organization level, evicted if not used regularly
- Few-shot images placed at the START of the messages array will be cached automatically
- No explicit cache control needed — just ensure few-shot examples are a stable prefix

**Layout Detections Data Available (from `raw_{prefix}_layout_detections`):**
- page_number, class_name, class_id
- x, y, width, height (bounding box coordinates)
- confidence
- ocr_text (OCR result for the region)
- review_status
- l1_title_id, l2_title_id (title hierarchy links)


### Q2: What is the rolling window pattern for the 3-page API calls?
**Answer:** Option A — Sliding window with overlap. Pages 1-2-3, then 2-3-4, then 3-4-5, etc.

**Additional clarifications from user:**
- Each page's knowledge must be extracted as a single extraction (not split across calls)
- Window size should be increased to 4 pages to handle L3 titles that span up to 4 pages
- So the pattern is: pages 1-2-3-4, then 2-3-4-5, then 3-4-5-6, etc.
- The overlap ensures context continuity — neighboring pages provide context for the extraction
- The extraction result for each page should be a complete, self-contained unit regardless of which window it appeared in
- Need deduplication logic: since each page appears in up to 4 windows, must decide which window's extraction to keep (or merge)


### Q3: How should we handle duplicate extractions for the same page across multiple windows?
**Answer:** User redirected the question — the unit of extraction is NOT the physical PDF page, it's the **knowledge page** (all content between consecutive L3 titles).

**Revised understanding:**
- A knowledge page = all content between two consecutive L3 title boundaries
- A knowledge page can span 1-4 physical pages
- The rolling window should operate on knowledge pages, not physical pages
- Each API call sends the physical page images that contain the knowledge page(s) being extracted
- The sliding window provides context from neighboring knowledge pages
- L3 title boundaries are already detected by YOLO (class_name = 'title_level_3') and stored in `raw_{prefix}_layout_detections`
- L3 title text is available via OCR in the `ocr_text` field of the detection record

**Revised rolling window concept:**
- Window = N consecutive knowledge pages (not physical pages)
- Each knowledge page maps to a range of physical pages (start_page → end_page)
- The API call sends all physical page images that cover the knowledge pages in the window
- The model extracts structured XML for each knowledge page in the window
- Sliding: move by 1 knowledge page at a time, keeping overlap for context


### Q3 (Revised): User clarified the complete rolling window algorithm

**The algorithm (as described by user):**

1. Send 4 physical pages to the LLM (e.g., pages 5, 6, 7, 8)
2. The LLM scans the pages and identifies L3 titles within them
3. The LLM captures and analyzes ALL content (paragraphs, diagrams, equations, lists, tables) between consecutive L3 titles — this forms a "knowledge page"
4. A knowledge page is recorded with: start_page, end_page, starting L3 title, ending L3 title
5. **Smart jump logic:** When a knowledge page is completed (e.g., L3 title found on page 7 ends it), the NEXT rolling window starts from that ending page (page 7), NOT from page 6. No need to re-scan pages already fully consumed.
6. **Continuation logic:** Before extracting, check the last completed knowledge page. If it ended at page 7 with a specific L3 title, the new window starts at page 7 and begins capturing from that ending L3 title (which becomes the starting L3 title of the new knowledge page).
7. **Spanning knowledge pages:** If no next L3 title is found within the 4-page window (e.g., the KP spans pages 7-10 but window only covers 7-8-9-10 and L3 is on page 10), the window naturally extends until the next L3 title is found. If the L3 title is beyond the 4-page window, the system sends the next batch of pages continuing from where it left off.
8. **No redundant extraction:** Pages already fully consumed by a completed knowledge page are never re-sent.

**Example walkthrough:**
- Window 1: pages 1,2,3,4 → LLM finds L3 at page 1, next L3 at page 3 → KP1 recorded (pages 1-3, L3_start, L3_end)
- Window 2: jumps to page 3 → sends pages 3,4,5,6 → LLM finds L3 at page 3 (continuation), next L3 at page 5 → KP2 recorded (pages 3-5)
- Window 3: jumps to page 5 → sends pages 5,6,7,8 → LLM finds L3 at page 5, but next L3 not found in window → no KP completed yet
- Window 4: continues from page 5 → sends pages 5,6,7,8,9,10? Or extends? → finds L3 at page 10 → KP3 recorded (pages 5-10)

**Key design implications:**
- The window start page is DYNAMIC — determined by where the last KP ended
- Window size is 4 pages but the knowledge page can span MORE than 4 pages
- The LLM does the L3 title identification AND content extraction in a single call
- Need to handle: KP spanning more than 4 pages (requires multiple API calls for same KP)
- Need to track: current position (next page to scan), last completed KP boundary


### Q4: When a knowledge page spans more than 4 physical pages (no second L3 title found in the window), what should happen?
**Answer:** Option B — Re-send from the starting L3 title page with a bigger window (8 pages) in a single call. If still no closing L3 title found in 8 pages, report an error and raise a red flag.

**Key points:**
- First attempt: 4 pages from the starting L3 title
- If no closing L3 found: retry with 8 pages from the same starting L3 title
- If still no closing L3 in 8 pages: ERROR — flag the knowledge page as failed, report to user
- This means max knowledge page span = 8 physical pages (practical limit)
- Error should be visible in the UI (red flag / error status)


### Q5: What XML structure should the LLM output for each knowledge page?
**Answer:** Option A (flat element list) PLUS a comprehensive XML schema with 9 categories and ~70+ tags that the LLM must populate.

**Full XML Schema (9 Categories):**

#### A — Text Extraction (Raw Content from Page)
| # | Tag | Description |
|---|-----|-------------|
| A1 | `<arabic_text>` | Raw Arabic text extracted from page |
| A2 | `<english_text>` | Raw English text extracted from page |
| A3 | `<equation>` | Mathematical equation in LaTeX format |
| A4 | `<diagram_image>` | Reference to extracted diagram image file (path/base64) |
| A5 | `<diagram_description>` | AI-generated natural language description of diagram |
| A6 | `<diagram_physics_interpretation>` | Physics-specific interpretation (force directions, circuit behavior, wave properties) |

#### B — Structural Metadata (Document Organization)
| # | Tag | Description |
|---|-----|-------------|
| B1 | `<l1_title>` | Level 1 title (chapter name) |
| B2 | `<l2_title>` | Level 2 title (section name) |
| B3 | `<l3_title>` | Level 3 title (individual point/example/problem) |
| B4 | `<element_type>` | Type: paragraph, heading, equation, diagram, problem, solution, example, definition, law, proof, table, footnote |
| B5 | `<page_number>` | Source page number in original PDF |
| B6 | `<page_range>` | Start-end pages for this L3 unit |
| B7 | `<confidence>` | OCR/extraction confidence score (0.0-1.0) |
| B8 | `<source_book>` | Book identifier/name |
| B9 | `<reading_order>` | Sequential order of elements within the L3 unit |
| B10 | `<bbox>` | Bounding box coordinates on source page (x, y, width, height) |

#### C — Classification & Scoring (LLM-Assigned Metadata)
| # | Tag | Description |
|---|-----|-------------|
| C1 | `<difficulty_score>` | Difficulty rating (1-10 scale) |
| C2 | `<concept_type>` | Classification: law, theorem, definition, derivation, application, experiment, problem_solving, historical_context |
| C3 | `<prerequisites>` | List of concepts the student must know before this one |
| C4 | `<exam_relevance>` | How likely this appears on Thanawiya Amma exams: high, medium, low |
| C5 | `<complexity_score>` | Combined score: multi-concept integration + math steps + non-obvious reasoning, weighted by uniqueness |
| C6 | `<is_top_5_percent>` | Boolean — is this among the top 5% most challenging/unique problems? |
| C7 | `<uniqueness_score>` | How different this problem's solving approach is vs. other problems in the book |
| C8 | `<bloom_taxonomy_level>` | Cognitive level: remember, understand, apply, analyze, evaluate, create |

#### D — Content Enrichment (LLM-Generated Additions)
| # | Tag | Description |
|---|-----|-------------|
| D1 | `<explanation_enrichment>` | Simplified explanation from Khan Academy, MIT OCW, top university resources |
| D2 | `<deep_understanding>` | WHY-focused explanation — physical intuition, not just equations |
| D3 | `<student_pain_points>` | Common misconceptions and difficulties for this specific concept |
| D4 | `<hardest_problems>` | Hardest problems from international sources beyond Egyptian books |
| D5 | `<teaching_methodology>` | Best teaching approaches promoting critical thinking and engineering mindset |
| D6 | `<critical_thinking_coaching>` | Coaching on decomposing complex problems, engineering mindset |
| D7 | `<faq>` | Anticipated student questions with answers and explanations |
| D8 | `<knowledge_gap_backfill>` | Questions/explanations extending backward to Grade 4 to address foundational gaps |
| D9 | `<real_world_scene>` | AI-generated real-world scene description for video generation (no human/animal faces) |
| D10 | `<web_research_sources>` | URLs and summaries of web sources used for enrichment |

#### E — Video Transformation (Pipeline Preparation)
| # | Tag | Description |
|---|-----|-------------|
| E1 | `<video_script_arabic>` | Arabic narration script for the video |
| E2 | `<video_script_english>` | English narration script for the video |
| E3 | `<subtitle_arabic>` | Arabic subtitle text (burned into video) |
| E4 | `<subtitle_english>` | English subtitle text (burned into video) |
| E5 | `<simulation_parameters>` | Physics simulation params (gravity, objects, initial conditions) for Antigravity/Rapier.js |
| E6 | `<visual_style>` | Whether concept needs 2d_diagram, 3d_simulation, mixed, or real_world_scene |
| E7 | `<video_duration_estimate>` | Estimated video length in seconds (target: 60-300s) |
| E8 | `<controlnet_reference>` | Reference image/diagram for ControlNet-guided video generation |

#### F — Validation & Quality Assurance
| # | Tag | Description |
|---|-----|-------------|
| F1 | `<physics_accuracy_check>` | LLM validation: does the content make physical sense? Pass/fail + reasoning |
| F2 | `<concept_coverage_check>` | Does this L3 unit cover all concepts from source pages? Pass/fail + missing items |
| F3 | `<subtitle_correctness_check>` | Are subtitles accurate translations of narration? Pass/fail + issues |
| F4 | `<equation_verification>` | Are equations balanced and physically correct? Pass/fail + specific errors |
| F5 | `<extraction_confidence>` | Overall confidence in extraction quality: high, medium, low |
| F6 | `<depth_rmse>` | Video validation: depth map comparison score (target < 0.05) |
| F7 | `<motion_deviation>` | Video validation: optical flow deviation % (target < 10%) |

#### G — Spaced Repetition & Learning Optimization
| # | Tag | Description |
|---|-----|-------------|
| G1 | `<spaced_repetition_interval>` | Calculated review interval in days for this concept |
| G2 | `<recap_content>` | Short recap text/visual for embedding at start of later videos |
| G3 | `<quiz_questions>` | Review quiz questions for spaced repetition review mode |
| G4 | `<notification_trigger>` | Push notification text for spaced repetition reminders |
| G5 | `<retention_difficulty>` | How hard this concept is to retain (affects repetition scheduling) |

#### H — Cross-Reference & Linking
| # | Tag | Description |
|---|-----|-------------|
| H1 | `<linked_diagrams>` | List of diagram IDs linked to this text element |
| H2 | `<linked_equations>` | List of equation IDs referenced in this text |
| H3 | `<related_l3_units>` | Other L3 units covering related/prerequisite concepts |
| H4 | `<cross_book_references>` | References to same concept in other books |

#### I — Extended Attributes (Remaining of 72)
| # | Tag | Description |
|---|-----|-------------|
| I1 | `<topic_keywords>` | Searchable keywords for this concept |
| I2 | `<formula_count>` | Number of equations in this L3 unit |
| I3 | `<diagram_count>` | Number of diagrams in this L3 unit |
| I4 | `<word_count_arabic>` | Arabic text word count |
| I5 | `<word_count_english>` | English text word count |
| I6 | `<has_worked_example>` | Boolean — contains a worked example? |
| I7 | `<has_problem_set>` | Boolean — contains practice problems? |
| I8 | `<physics_domain>` | Domain: mechanics, thermodynamics, electromagnetism, optics, modern_physics, waves |
| I9 | `<mathematical_tools>` | Math tools needed: algebra, trigonometry, calculus, vectors, matrices |
| I10 | `<real_world_application>` | Real-world application of this concept (for engagement) |
| I11 | `<historical_context>` | Who discovered this, when, why it matters |
| I12 | `<common_exam_question_types>` | Types of exam questions that test this concept |
| I13 | `<estimated_study_time>` | Minutes a student should spend on this concept |
| I14 | `<visual_complexity>` | How visually complex the concept is (affects video style choice) |

**Total: ~70+ XML tags across 9 categories**


### Q6: How should images be sent to ChatGPT 5, and what about YOLO misclassification impact?

**User's concern:** YOLO can generate wrong classifications (e.g., labeling an equation as a diagram). Manual review of YOLO output is a major bottleneck the user wants to avoid. The hope is that sending everything to ChatGPT 5 will eliminate the need for YOLO review.

**Research Findings:**

#### GPT-5 Vision Capabilities for Document Extraction
- GPT-5 achieves ~95% OCR accuracy on benchmarks ([source: aimultiple.com](https://research.aimultiple.com/ocr-accuracy/))
- GPT-5.1 leads document parsing at 73.2% accuracy with ~$0.00054/document ([source: theagilemonkeys.com](https://labs.theagilemonkeys.com/posts/state-of-ai-document-parsing/index.html))
- KITAB-Bench (Arabic OCR benchmark) shows VLMs like GPT-4o, Gemini, Qwen outperform traditional OCR (EasyOCR, PaddleOCR, Surya) by ~60% in Character Error Rate ([source: arxiv.org](https://arxiv.org/html/2502.14949))
- GPT-5 shows notable gains in table parsing accuracy and document structure understanding ([source: box.com](https://blog.box.com/now-available-open-ais-gpt-5-premiere-thinking-model-box-ai))
- GPT-5 can extract text, tables, equations, diagrams from a single full-page image in one call

#### Image Token Cost Calculation (GPT-5 Vision)
- High-detail mode: image scaled to fit 2048x2048, then shortest side to 768px, then split into 512x512 tiles
- Each tile = 170 tokens + 85 base tokens
- Typical textbook page (~1200x1600px): ~6 tiles = (6 × 170) + 85 = **~1,105 tokens per image**
- 4 full pages per window = ~4,420 image tokens
- With cropped regions (e.g., 10 crops per page × 4 pages = 40 crops): ~40 × ~300 tokens = ~12,000 additional tokens
- GPT-5 pricing: $1.25/M input tokens, $10/M output tokens
- With caching (90% discount): $0.125/M cached input tokens

#### Cost Comparison (per 4-page window call)

| Option | Images Sent | Input Tokens (est.) | Cost/Call (uncached) | Cost/Call (cached) | Accuracy |
|--------|------------|--------------------|--------------------|-------------------|----------|
| A: Full pages only | 4 images | ~4,420 img + ~2K prompt = ~6.4K | $0.008 | $0.003 | Good for text, weaker for small diagrams/equations |
| B: Full pages + all crops | 4 + ~40 crops = 44 images | ~16.4K img + ~2K prompt = ~18.4K | $0.023 | $0.005 | Highest accuracy, but depends on YOLO bbox quality |
| C: Full pages + diagram/equation crops only | 4 + ~8 crops = 12 images | ~6.8K img + ~2K prompt = ~8.8K | $0.011 | $0.003 | Good balance, but still YOLO-dependent for crop selection |
| D: Annotated full pages (bbox overlays) | 4 images | ~4,420 img + ~2K prompt = ~6.4K | $0.008 | $0.003 | Good, but YOLO errors in annotations could mislead |

*Estimates assume ~200-page book = ~50 windows × cost/call*

| Option | Total Book Cost (uncached) | Total Book Cost (cached) |
|--------|--------------------------|------------------------|
| A | ~$0.40 | ~$0.15 |
| B | ~$1.15 | ~$0.25 |
| C | ~$0.55 | ~$0.15 |
| D | ~$0.40 | ~$0.15 |

#### Impact of Wrong YOLO Classifications on ChatGPT 5

**Research on VLM modality conflict** ([source: arxiv.org/2509.02805](https://arxiv.org/html/2509.02805v1)):
- When text labels conflict with visual content, VLMs exhibit a **bias toward textual input**
- Models are more likely to trust text metadata when it is longer or more detailed
- This means: if you tell GPT-5 "this cropped region is a diagram" but it's actually an equation, GPT-5 will likely **lean toward the text label** and try to describe it as a diagram rather than extract the equation

**Practical impact per option:**

| Option | YOLO Error Impact |
|--------|------------------|
| A: Full pages only | **ZERO impact** — no YOLO data sent, GPT-5 classifies everything itself |
| B: Full + all crops | **HIGH impact** — wrong crops sent (e.g., cropping half an equation because YOLO bbox was wrong), GPT-5 may misinterpret the cropped content |
| C: Full + selective crops | **MEDIUM impact** — fewer wrong crops, but wrong classification of what to crop means missing important regions |
| D: Annotated pages | **MEDIUM impact** — wrong bbox labels drawn on the image could bias GPT-5 toward wrong classification, but GPT-5 can still see the full page and potentially override |

#### Recommendation

Given the user's constraint (no time for YOLO review), **Option A (full pages only)** is the clear winner:
1. **Zero YOLO dependency** — GPT-5 does its own layout analysis and classification
2. **Lowest cost** — fewest image tokens
3. **No misclassification risk** — GPT-5 sees the raw page and decides what each region is
4. **95% OCR accuracy** — GPT-5 is already state-of-the-art for document extraction
5. **Simplest implementation** — just send page images, no cropping/annotation pipeline needed

The only downside is slightly lower accuracy on very small diagrams or dense equations, but GPT-5's vision capabilities are strong enough that this is a minor concern for textbook-quality pages.


### Q7: Confirmed Option A (full pages only) + few-shot examples from reviewed pages

**Answer:** Yes, Option A + few-shot reviewed pages as examples.

**User's detailed requirements captured:**

#### 1. "Review Few-Shot Examples" Button
- Opens the existing layout review UI for user-selected pages
- User reviews and corrects YOLO region detections on 5-10 pages
- Saving follows a special style optimized for ChatGPT 5 understanding (annotated image format — see research below)
- These corrected pages become the few-shot training examples

#### 2. "Send Few-Shot Examples" Button
- Sends the reviewed/annotated few-shot pages to ChatGPT 5
- Includes special instructions for the model to understand the annotation style
- User must specify a **cache name** in a text field — this name is used in every subsequent prompt to reference the cached examples
- The few-shot images are placed at the START of the prompt to maximize OpenAI's automatic prefix caching

#### 3. Dry Run / Test Section
- User specifies a page range from the book
- System shows the full prompt BEFORE sending (preview mode)
- User can review the prompt content
- User triggers the test send
- Response is displayed for review before committing to the full extraction run
- This allows the user to validate the prompt quality and model response format

#### 4. Cache Name Mechanism
- User provides a text name (e.g., "physics-grade12-book1")
- This name is included in the prompt as a reference identifier
- Note: OpenAI's caching is automatic prefix-based, NOT named. The "name" serves as a human-readable identifier in the prompt and helps with routing consistency (using the `user` parameter for cache affinity)

---

### Research: Best Annotation Style for Few-Shot Example Images

**Research source:** VRPTest benchmark paper — "Evaluating Visual Referring Prompting in Large Multimodal Models" ([arxiv.org/2312.04087](https://arxiv.org/html/2312.04087))

**Key findings from the paper:**

1. **Visual referring prompting significantly impacts accuracy** — variations from -17.5% to +7.3% depending on strategy
2. **Full-intervention (annotations + text labels on image) outperforms Partial-intervention (just bounding boxes)** — Full-intervention ranked #1 in 9 out of 14 strategy combinations
3. **Color matters:** Red and blue outlines were tested. Impact varies by model but both are effective
4. **Shape matters:** Both circles and rectangles (bounding boxes) were tested. Rectangles are more standard for document regions
5. **Position of labels matters:** Labels placed near the region improve understanding
6. **GPT-4V benefits MORE from visual prompting than open-source models** — suggesting GPT-5 will also benefit strongly
7. **Critical insight:** When using visual prompts, you MUST tell the model in the text prompt that the image contains annotations. Otherwise the model may ask "what is the red box?" instead of understanding it as a region marker

**Additional research on VLM modality conflict:**
- VLMs tend to trust text labels over visual content when they conflict
- For few-shot examples where labels are CORRECT (user-reviewed), this text bias is actually BENEFICIAL — the model will strongly follow the correct labels

**Recommended annotation style for few-shot examples:**

| Element | Style |
|---------|-------|
| Bounding boxes | 3px colored outline (NOT filled) — preserves readability of content underneath |
| Color coding | Different color per region type: Red = Title L1, Orange = Title L2, Yellow = Title L3, Green = Paragraph, Blue = Diagram, Purple = Equation, Cyan = Table, Pink = List |
| Labels | Small text label OUTSIDE the bounding box (top-left corner), white text on colored background matching the outline color |
| Label format | `[TYPE] #N` e.g., "Paragraph #1", "Equation #2", "Title L3 #1" |
| Numbering | Sequential reading order within the page |
| Font | Small, clear sans-serif (Arial 10-12px) to minimize occlusion |
| No fill | Transparent fill — the model needs to see the content inside the box |

**Why this style:**
- Colored outlines with labels = Full-intervention (best accuracy per VRPTest)
- No fill = content remains readable for extraction
- Color coding = instant visual type classification
- Sequential numbering = reading order is explicit
- Labels outside box = no occlusion of content
- Text prompt will explicitly describe the annotation convention

**Alternative considered but rejected:**
- Filled/highlighted regions: Occludes content, makes text unreadable
- Numbered-only (no type label): Model has to guess region type from visual alone
- No annotations (just text coordinates): Partial-intervention, lower accuracy


### OpenAI Prompt Caching — Important Clarification

**Research findings on OpenAI caching (from community forums and docs):**

1. **OpenAI caching is AUTOMATIC and prefix-based** — there is NO named cache store/retrieve API
2. Cache works by matching the longest prefix of the prompt (system + messages) that was seen recently
3. Cache hits require >1024 tokens of identical prefix, in increments of 128 tokens
4. The `user` parameter can be combined with the prefix hash for routing affinity (improves cache hit rate)
5. **GPT-5 caching works reliably** — community reports confirm GPT-5 hits cache consistently (unlike some GPT-4.1 issues)
6. Images ARE cached if they appear in the same order at the start of the prompt
7. Cache is scoped at organization level, evicted after 5-10 minutes of inactivity
8. 90% discount on cached input tokens

**Implication for our design:**
- The "cache name" the user provides is NOT sent to OpenAI as a cache key
- Instead, it serves as: (a) a human-readable label in our system, (b) used as the `user` parameter for routing affinity
- The actual caching happens automatically because the few-shot images + system prompt form a stable prefix
- Every extraction call starts with the SAME few-shot images + system prompt → automatic cache hit
- The variable part (the 4 actual page images being extracted) comes AFTER the cached prefix


### Q8: Where should the UI for this feature live?
**Answer:** Option A — New section on the Auto-Slicer page. BUT with a major addition: a provider-agnostic LLM configuration system.

**User's requirements:**
- Build a configuration page/section where the user specifies API keys for LLM providers
- Each provider needs: API key, model name, and provider-specific fields
- On the Cloud Extraction section, a combo box lists only the LLMs that have API keys configured
- If only ChatGPT 5 is configured → only ChatGPT 5 appears in the dropdown
- If ChatGPT 5 + Qwen are configured → both appear in the dropdown
- This replaces the hardcoded Qwen-only approach from Task 3

**Research: Minimum API Configuration Per Provider**

| Provider | Auth Header | API Key Format | Base URL | Additional Fields |
|----------|------------|---------------|----------|-------------------|
| **OpenAI (ChatGPT 5)** | `Authorization: Bearer <key>` | `sk-...` | `https://api.openai.com/v1` (default) | Organization ID (optional) |
| **DashScope (Qwen)** | `Authorization: Bearer <key>` | DashScope key | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` (intl) or `https://dashscope.aliyuncs.com/compatible-mode/v1` (China) | Region selection |
| **Anthropic (Claude)** | `x-api-key: <key>` | `sk-ant-...` | `https://api.anthropic.com` (default) | Anthropic-Version header |
| **Google (Gemini)** | `x-goog-api-key: <key>` | Google API key | `https://generativelanguage.googleapis.com/v1beta` | Project ID (optional) |

**Common fields for all providers:**
1. **Provider Name** (display label, e.g., "OpenAI", "DashScope", "Anthropic", "Google")
2. **API Key** (required, masked input)
3. **Base URL** (with sensible default per provider, editable for custom endpoints/proxies)
4. **Model Name** (text field, e.g., "gpt-5", "qwen-vl-max", "claude-4-opus")
5. **Enabled** (toggle — allows disabling without deleting the key)

**Storage:** Database table (global, not per-book) — `llm_providers` table with columns: id, provider_name, display_name, api_key (encrypted), base_url, model_name, enabled, auth_header_style, created_at, updated_at

**UI Location:** Could be on Book Settings page or a new global "LLM Configuration" page accessible from the sidebar. Since API keys are global (not per-book), a global config page makes more sense.


### Q9: Where should the LLM provider configuration UI live?
**Answer:** Option C — On the Pipeline Config page. Add an "LLM Providers" section to the existing pipeline configuration page.


### Q10: How should the XML extraction results be stored in the database?
**Answer:** Mix of C and B, with a V1/V2 extraction architecture.

**User's detailed requirements:**

#### V1 vs V2 Extraction Architecture

**V1 (existing):** YOLO DocLayout → manual layout review → separate entities per region (paragraph_images, diagram_images) → KU creation → knowledge_units table
- Pros: Most accurate, flexible, granular
- Cons: Requires manual classification review (major bottleneck)

**V2 (new):** Cloud LLM extraction → few-shot examples → rolling window → knowledge_page stored directly with full XML/JSON
- Pros: No manual review needed, end-to-end automated
- Cons: Less granular (knowledge_page level, not individual region level)

#### Storage Design (V2)
- **Dedicated columns for queryable key fields** (option C)
- **Raw XML stored separately** (for debugging/audit)
- **Parsed JSONB stored separately** (for enrichment pipeline)
- Both XML and JSON kept in the DB as separate columns

#### Extraction Method Selection
- **Book Settings:** User can choose default extraction method (V1 or V2)
- **Default for new books:** V2 (cloud extraction)
- **User can change before uploading** — if user switches to V1, the V1 tables are created instead
- **Existing books remain on V1** — no migration needed
- **Both V1 and V2 can coexist** — different books can use different methods

#### New Tables Needed for V2
- `v2_{prefix}_knowledge_pages` — main table with key columns + raw XML + parsed JSON
- `v2_{prefix}_extraction_log` — tracks each API call (window, pages sent, response time, tokens used, cost)
- `v2_{prefix}_few_shot_examples` — stores the reviewed/annotated few-shot pages for this book

#### Key Fields to Define as Dedicated Columns (queryable)
Need to determine which of the ~70 XML tags deserve their own column vs. staying in JSONB.



### Q11: Summary column and V1 feature evaluation for V2
**Answer:** Option B — User wants:
- A `summary` column (2-3 lines) mentioning the specific technical concept of the knowledge page for quick reference
- Additional attributes system similar to V1's attr1-attr80 pattern
- Research V1 features and evaluate which need duplication for V2

**V1 Features Researched (from code):**
- `knowledge_units` table: 80 attributes (8 system-reserved + 72 user-defined), text columns attr1_value through attr80_value
- `attribute_keys` table: maps attr_number to key_name, system vs user-defined
- System attrs: related_image, easyocr_text, surya_ocr_text, tesseract_text, easyocr_confidence, surya_ocr_confidence, tesseract_confidence, record_status
- Features: merge records, split records, export (JSON/CSV), ChromaDB embedding sync, cross-book references, verified flag, notes
- Hierarchy: chapter, topic, sub_topic columns
- Embedding: embedding_vector VECTOR(384)


### Q12: V1 Feature Duplication Decisions for V2

**Feature-by-feature decisions:**

| # | Feature | Decision | Notes |
|---|---------|----------|-------|
| 1 | 80 Attributes System | **YES** | User confirmed — needed for V2 knowledge pages |
| 2 | Merge Records | **NO** | V2 knowledge pages are complete L3-bounded units; merging would break the definition |
| 3 | Split Records | **NO** | Same reasoning — splitting contradicts the L3-boundary model |
| 4 | Export (JSON/CSV) | **YES** | Needed for downstream pipeline use |
| 5 | ChromaDB Embedding Sync | **NOT NOW** | Not needed for V2 initially, but may be added in the future. Design should not block future addition. |
| 6 | Cross-Book References | **NOT NOW** | Not needed for V2 initially, but may be added in the future. Design should not block future addition. |
| 7 | Verified Flag + Notes | **YES** | User confirmed |
| 8 | Record Status (enabled/disabled) | **YES** | User confirmed |
| 9 | Hierarchy (L1/L2/L3 titles) | **YES — as dedicated queryable columns with FK IDs** | See detailed requirement below |
| 10 | Summary (2-3 lines) | **YES** | New for V2 — summary mentioning the specific technical concept |
| 11 | Embedding Vector | **NOT NOW** | Tied to ChromaDB — not needed initially |
| 12 | Position (x, y) | **NO** | V2 knowledge pages span multiple regions/pages |

---

### Additional Requirements Captured from Q12 Discussion

#### REQ-12A: Full Content Fidelity in Prompts
The prompts sent to ChatGPT 5 MUST include instructions to capture the **full details** of the content being extracted, to the extent that:
- The same content can be **re-generated by the LLM** if required
- Even the **same styles** (formatting, emphasis, structure) can be reproduced
- The initial prompts should ask for this level of accuracy by default
- The user can review and modify the prompts before sending, but the default prompts must aim for maximum fidelity

#### REQ-12B: L1/L2 Title Injection from Auto-Slicer (NOT from LLM)
- L1 titles and L2 titles are **already defined by the user** on the Auto-Slicer page with page ranges
- The system already has `{prefix}_level1_titles` (with `start_page`, `end_page`) and `{prefix}_level2_titles` (with `start_page`, `end_page`, `parent_l1_id`)
- The cloud extraction system must **NOT rely on the LLM** to extract L1 or L2 titles
- Instead, the system will **deterministically inject** the correct L1 and L2 title IDs into each V2 knowledge page record based on the page numbers
- Logic: For a knowledge page spanning pages X to Y, look up which L1 title's `start_page ≤ X` and `end_page ≥ Y`, and which L2 title's `start_page ≤ X` and `end_page ≥ Y`
- The LLM prompt should still mention the current L1/L2 context (title text) so the LLM understands the chapter/section context, but the **stored FK IDs come from the database, not from the LLM response**

#### REQ-12C: Pre-requisites for Starting Cloud Extraction
Before the user can start the V2 cloud extraction rolling window, the system must enforce these pre-requisites (all must be satisfied):

1. **L1 titles defined for the entire book** — All pages must be covered by L1 title page ranges (no gaps)
2. **L2 titles defined for the entire book** — All pages must be covered by L2 title page ranges (no gaps)
3. **API key configured** for the selected cloud LLM provider (on Pipeline Config page)
4. **Few-shot examples sent** — At least one set of reviewed/annotated few-shot pages must have been sent to the LLM

If any pre-requisite is not met, the "Start Extraction" button should be disabled with a clear message indicating which pre-requisites are missing.

#### REQ-12D: L1/L2/L3 Title Columns in V2 Table — FK IDs with Text Display
- The `v2_{prefix}_knowledge_pages` table must have dedicated queryable columns:
  - `l1_title_id INTEGER` — FK to `{prefix}_level1_titles.id`
  - `l2_title_id INTEGER` — FK to `{prefix}_level2_titles.id`
  - `l3_title_text VARCHAR(500)` — The L3 title text (start of the knowledge page). L3 titles don't have their own table, so we store the text directly.
  - `l3_title_end_text VARCHAR(500)` — The ending L3 title text (marks the end of this knowledge page / start of next)
- In the GUI, when the user queries or filters by L1/L2 title, the UI shows the **title text** (resolved via JOIN) rather than the raw IDs
- This is transparent to the user — they see and search by title text, but the DB stores efficient FK IDs


#### REQ-12E: L3 Title Definition Restricted by Extraction Method
- **V2 books:** L3 title definition on the Auto-Slicer page is **DISABLED/HIDDEN**. The cloud LLM extracts L3 titles as part of the rolling window extraction — this is a core differentiator of V2.
- **V1 books:** L3 title definition remains enabled on the Auto-Slicer page (existing behavior).
- **Books with both V1 and V2 enabled:** The Auto-Slicer page shows a **radio button** to toggle between "V1 Title Definition" and "V2 Title Definition" modes:
  - V1 mode: L1 + L2 + L3 title definition all enabled
  - V2 mode: Only L1 + L2 title definition enabled, L3 section hidden
  - Default selection: V2
- The user MUST still define L1 and L2 titles with page numbers for V2 — these are pre-requisites for cloud extraction (REQ-12C).
- L3 titles are extracted by the LLM and stored in the `v2_{prefix}_knowledge_pages` table as `l3_title_text` and `l3_title_end_text`.



### Q13a: Pause/Resume/Cancel during rolling extraction
**Answer:** Option A — Full control (Pause, Resume, Cancel).

**Details:**
- **Pause:** Stop after the current window completes, save progress. The system records the last completed knowledge page so it knows exactly where to continue.
- **Resume:** Continue from the last completed knowledge page. The next window starts from the ending page of the last KP.
- **Cancel:** Stop and keep whatever was extracted so far. Already-extracted knowledge pages remain in the DB.

**Additional requirement — V2 Knowledge Page Review UI:**
- A review page similar to the existing layout review page
- The presentation layer shows 3 views for each knowledge page:
  1. **Queryable parameters view** — Shows the dedicated columns (L1 title, L2 title, L3 title text, summary, page range, difficulty score, concept type, etc.) in a structured form layout
  2. **Formatted JSON view** — The parsed JSONB column displayed in a formatted/pretty-printed JSON viewer
  3. **Formatted XML view** — The raw XML column displayed in a formatted/syntax-highlighted XML viewer
- User can navigate between knowledge pages (previous/next)
- User can mark as verified, add notes, enable/disable records



### Q13b: Error handling for malformed XML responses
**Answer:** Option D (modified) — Strict mode with two-phase retry and cooldown.

**Error handling flow:**
1. ChatGPT 5 returns malformed XML
2. **Phase 1:** Auto-retry the same window up to 3 times immediately
3. If all 3 retries fail → **Cooldown:** Pause extraction for 15 minutes (the LLM may be overloaded or having transient issues)
4. **Phase 2:** After 15-minute cooldown, retry the same window up to 3 more times
5. If all Phase 2 retries also fail → **STOP:** Pause extraction entirely, flag the knowledge page as "failed", alert the user to intervene before continuing
6. The user can then: review the failed window, modify the prompt, manually re-trigger, or skip the page

**Total max retries per window:** 6 (3 immediate + 3 after cooldown)
**Cooldown duration:** 15 minutes (configurable?)
**UI indication:** Show retry count, cooldown timer, and error details in the extraction dashboard



### Q13c: Rate limiting / throttling between API calls
**Answer:** Option C — Configurable minimum delay + adaptive backoff.

**Details:**
- **Minimum delay:** 5 seconds between API calls (default). User can change this via a text field in the extraction UI.
- **Adaptive backoff on 429 errors:** If the API returns HTTP 429 (rate limited), the system applies exponential backoff: 5s → 10s → 20s → 40s → max 60s. Once a successful response is received, the delay resets to the user-configured minimum.
- The system never fires faster than the user-configured minimum delay, but slows down further when rate-limited.
- The current delay and any backoff status should be visible in the extraction dashboard.



### Q13d: Cost tracking during extraction
**Answer:** Option A — Full cost dashboard.

**Details:**
- Track per API call: input tokens (cached vs uncached), output tokens, cost per call
- Calculate and display live in the extraction dashboard:
  - Cost per window/call
  - Running total cost for the book
  - Total tokens used (input cached, input uncached, output)
  - Cache hit rate percentage
  - Estimated remaining cost (based on pages left × average cost per window)
- All data logged in `v2_{prefix}_extraction_log` table per API call for historical review
- The extraction dashboard shows this as a live-updating cost panel alongside the progress indicators



### Q14: Dedicated queryable columns in V2 knowledge_pages table
**Answer:** Option A — Approved list.

**Dedicated queryable columns (beyond title FKs from REQ-12D):**

| Column | Type | From Tag | Purpose |
|--------|------|----------|---------|
| `summary` | TEXT | New (REQ-11) | 2-3 line summary mentioning specific technical concept |
| `start_page` | INTEGER | B5/B6 | Filter by page range |
| `end_page` | INTEGER | B6 | Filter by page range |
| `difficulty_score` | INTEGER | C1 | Filter/sort by difficulty (1-10) |
| `concept_type` | VARCHAR(50) | C2 | Filter by type (law, theorem, definition, etc.) |
| `bloom_taxonomy_level` | VARCHAR(20) | C8 | Filter by cognitive level |
| `physics_domain` | VARCHAR(50) | I8 | Filter by domain (mechanics, optics, etc.) |
| `exam_relevance` | VARCHAR(10) | C4 | Filter by exam importance (high/medium/low) |
| `extraction_confidence` | VARCHAR(10) | F5 | Filter by quality (high/medium/low) |
| `has_worked_example` | BOOLEAN | I6 | Boolean filter |
| `has_problem_set` | BOOLEAN | I7 | Boolean filter |
| `element_count` | INTEGER | Computed | Total elements in the knowledge page |

**Plus the title columns from REQ-12D:**
| `l1_title_id` | INTEGER FK | Deterministic from page range |
| `l2_title_id` | INTEGER FK | Deterministic from page range |
| `l3_title_text` | VARCHAR(500) | From LLM extraction |
| `l3_title_end_text` | VARCHAR(500) | From LLM extraction |

**Plus V1-inherited columns:**
| `verified` | BOOLEAN | Review status |
| `notes` | TEXT | User notes |
| `record_status` | VARCHAR(20) | enabled/disabled |

**Plus storage columns:**
| `raw_xml` | TEXT | Full XML response from LLM |
| `parsed_json` | JSONB | Parsed XML as JSON for enrichment queries |

**Plus 80 attribute columns:**
| `attr1_value` through `attr80_value` | TEXT | User-defined attributes |

All other ~70+ XML tags remain accessible via JSONB queries on the `parsed_json` column.



### Q15: Prompt template management
**Answer:** Option A — Editable in the UI.

**Details:**
- The system prompt and extraction prompt are displayed as editable text areas on the extraction section of the Auto-Slicer page
- Default prompts are generated by the system (with full-fidelity instructions per REQ-12A)
- The user can modify the prompts before starting extraction
- Modified prompts are saved per-book in the DB (in the book's settings or a dedicated prompt storage)
- The dry run feature (from Q7) uses the current prompt text, so the user can iterate: edit prompt → dry run → review response → edit again → start extraction
- A "Reset to Default" option should be available to restore the system-generated prompts



---

## Step 2: Code Impact Review — COMPLETED

**Date:** 2026-02-15
**Design file:** `000-tracking/14-02-design-rolling-api-xml-extraction.md`

**Summary:**
- 8 existing files to modify (table_creator.py, books_metadata.py, auto-slicer.html, auto-slicer.js, pipeline-config.html, main.py, + 2 minor)
- 12 new files to create (4 services, 2 route files, 2 templates, 3 JS files, 3 migrations)
- 3 new per-book DB tables (v2_knowledge_pages, v2_extraction_log, v2_few_shot_examples)
- 1 new global DB table (llm_providers)
- 1 new column on books_metadata (extraction_method)
- 5-phase implementation order (Foundation → LLM Config UI → Core Engine → Extraction UI → Review UI)

**Confidence level:** 95%
**Next step:** Step 3 (Test Cases) → Step 4 (Design Review) → Step 5 (Design Verification) → Step 8 (Shall I proceed?)



---

## Step 3: Test Cases — COMPLETED

**Date:** 2026-02-15
**Test file:** `000-tracking/14-02-testing-rolling-api-xml-extraction.md`
**Total test cases:** 33 (6 Foundation + 2 LLM Config UI + 10 Core Engine + 8 Extraction Controls + 7 Review UI + 3 Integration)

---

## Step 4: Design Review Summary

The design covers all 15 requirements (Q1-Q15) with:
- 5-phase implementation (Foundation → LLM Config → Engine → Extraction UI → Review UI)
- 12 new files + 8 modified files
- 4 new DB tables (1 global + 3 per-book)
- Provider-agnostic LLM configuration
- Rolling window with smart jump algorithm
- 2-phase retry with 15-min cooldown
- Full cost tracking dashboard
- Editable prompt templates per-book
- V1/V2 coexistence with radio button toggle

---

## Step 5: Design Verification Questions

### DV1: V2 table naming convention
The design uses `v2_{prefix}_knowledge_pages` (e.g., `v2_book1_physics_knowledge_pages`). This differs from the existing convention where tables are `{prefix}_knowledge_units` (no version prefix). 

**Question:** Are you OK with the `v2_` prefix to clearly distinguish V2 tables from V1 tables? Or would you prefer a different naming approach?

### DV2: Existing cloud_ocr.py — keep or merge?
The design creates a NEW `v2_extraction.py` route file, leaving the existing `cloud_ocr.py` (Qwen-based Task 1) untouched. This means two separate cloud extraction systems coexist.

**Question:** Is this correct? Or should V2 extraction REPLACE the existing cloud_ocr.py entirely (since V2 is provider-agnostic and supersedes the Qwen-only approach)?

### DV3: Attribute keys table for V2
V1 has a separate `{prefix}_attribute_keys` table mapping attr numbers to names. Should V2 have its own `v2_{prefix}_attribute_keys` table, or share the same attribute_keys table as V1?

### DV4: Book Settings page — extraction method toggle
The design adds `extraction_method` to `books_metadata`. Should the V1/V2 toggle be on the Book Settings page (where other book-level configs live), or on the Auto-Slicer page only?

### DV5: Implementation scope for this session
This is a large feature (12 new files). Should I implement all 5 phases in one go, or would you prefer to start with Phase A+B (Foundation + LLM Config) first, test it, then continue with Phases C-E?



---

## Design Verification Answers

### DV1: V2 table naming → Option A
Use `v2_` prefix: `v2_{prefix}_knowledge_pages`, `v2_{prefix}_extraction_log`, `v2_{prefix}_few_shot_examples`, `v2_{prefix}_attribute_keys`

### DV2: Existing cloud_ocr.py → Option B (Replace)
Delete `cloud_ocr.py` and `qwen_service.py`. V2 extraction system (`v2_extraction.py`) is provider-agnostic and replaces the Qwen-only approach entirely. Also delete/archive `knowledge-page-review.html` and `knowledge-page-review.js` (Task 1 UI) since V2 review UI supersedes them.

### DV3: Attribute keys table → Option B (Separate) + Critical Clarifications

**User clarifications:**
1. New books default to V2 extraction → V1 tables may NOT exist for new books. V2 must be fully self-contained.
2. Must review `create_book_tables()` to ensure V2-only books get only V2 tables (no V1 tables created unnecessarily).
3. V2 attribute keys need BOTH key names AND values — each attribute has a key_name that is referenced in subsequent LLM invocations via the TemplateEngine pattern (`{{key_name}}` → resolves to `attrN_value` column).
4. The `v2_{prefix}_attribute_keys` table follows the same pattern as V1's `{prefix}_attribute_keys` but is independent.

**TemplateEngine pattern (from code review):**
- `TemplateEngine` loads key_name → column_name mappings from `attribute_keys` table
- Prompt templates use `{{key_name}}` placeholders (e.g., `{{easyocr_result}}` → `attr2_value`)
- V2 will need its own TemplateEngine variant that reads from `v2_{prefix}_attribute_keys`
- This allows V2 LLM prompts to reference extracted attributes by name (e.g., `{{difficulty_score}}`, `{{concept_type}}`)

**Impact on table creation:**
- `create_book_tables()` must be modified to check `extraction_method`:
  - If 'v2' (default): Create V2 tables + L1/L2 title tables + settings + pages (for page images). Skip V1-only tables (raw_knowledge_units, raw_paragraph_images, raw_diagram_images, knowledge_units, attribute_keys, pipeline_config, etc.)
  - If 'v1': Create V1 tables as before
  - If 'both': Create all tables



### DV4: Extraction method toggle location → Option D
- Upload page: User chooses V1 or V2 at upload time (default V2)
- Can be changed later on Book Settings page
- Auto-Slicer reads the setting and shows/hides sections accordingly

### DV5: Implementation scope → Option A (all phases, sequential with testing)
- Implement all 5 phases in one go
- Test each phase thoroughly before moving to the next
- Fix bugs within each phase before proceeding
- Follow API-first approach (backend routes before frontend UI)

---

## Step 8: Shall I proceed? → YES (user confirmed)

**Implementation plan:**
1. Phase A: Foundation (migrations + table creation + model changes) → test
2. Phase B: LLM Config (provider service + routes + UI) → test
3. Phase C: Core Engine (XML parser + few-shot + extraction service + routes) → test
4. Phase D: Extraction UI (auto-slicer modifications) → test
5. Phase E: Review UI (v2-knowledge-review page) → test

**Files to delete (DV2 — Replace):**
- `03-code/src/api/routes/cloud_ocr.py`
- `03-code/src/services/qwen_service.py`
- `03-code/src/frontend/templates/knowledge-page-review.html`
- `03-code/src/frontend/static/js/knowledge-page-review.js`

