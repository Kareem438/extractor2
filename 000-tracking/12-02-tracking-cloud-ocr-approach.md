# Tracking: Cloud OCR Approach (Qwen 2.5-VL + DeepSeek-R1)

**Task:** Integrate cloud-based AI models as alternative OCR/analysis engines
**Date:** 2026-02-12
**Status:** 🔄 Implementation (Phase 1 Code Complete)

---

## Progress Log

### 2026-02-12 — Session Start
- Read "NEW Approach.rtf" — extracted plain text from RTF format
- Analyzed existing codebase: ocr_sequential.py, claude_batch_service.py, pipeline.py, config.py, table_creator.py
- Identified integration points: OCR service layer, external API pattern, config, API routes, database schema
- Created 4 tracking files per framework v2
- Starting requirements Q&A

### 2026-02-12 — Requirements Q&A Progress
- Q1: Answered — Qwen replaces OCR, DeepSeek replaces Claude for reasoning
- Q2: Answered — User manually selects few-shot pages. Caching research: DashScope implicit cache (20% cost), explicit cache (10% cost). OpenRouter has no Qwen caching.
- Q3: Answered — B (JSON). Qwen returns JSON array per page. L1/L2 resolved server-side. Reuses existing KU creation flow.
- Q4: Answered — C (Both). Drop-in for simple prompts, reasoning chain mode for DeepSeek. DeepSeek V3.2 pricing: $0.028-$0.28/1M input, $0.42/1M output.
- Q5: Answered — Custom. Buttons on auto-slicer page. Critical finding: Qwen VL model-level KV caching does NOT support multimodal prefix reuse, but DashScope API-level caching DOES work. Translation layer needed (Qwen JSON → raw_paragraph_images rows).
- Q6: Answered — A (DashScope only). Simpler, guaranteed caching, lower cost.
- Q6b: Answered — knowledge_page concept introduced. Logical grouping between L3 titles, stored as JSONB. Changes translation layer design.
- Q7: Answered — B (On-demand). User reviews knowledge_pages in layout-review-style UI first, marks "Ready to Convert to KU", then triggers conversion. Reuse layout-review code patterns.
- Q8: Answered — B (Page-level granularity). Each page tracked independently. Plus pause/resume capability following auto-slicer pattern.
- Q9: Answered — 1 API key per provider (DASHSCOPE_API_KEY, DEEPSEEK_API_KEY), shared across all books. Follows existing ANTHROPIC_API_KEY pattern.
- Q10: Answered — C (Two phases). Phase 1 = Qwen + knowledge_page review UI + KU conversion. Phase 2 = DeepSeek + pipeline integration + cost tracking.

### 2026-02-12 — Requirements Complete, Design Verification
- All 10 questions answered
- Updated Kiro spec requirements.md with finalized Phase 1 scope (9 requirements)
- Updated design doc with full Phase 1 design: API contracts, data model, service layer, UI design
- Awaiting user design verification before implementation

### 2026-02-12 — Design Approved, Test Cases Complete
- User approved design
- Built comprehensive testing file: 57 test cases across 9 requirements + edge cases
- Cleanup section with all DB objects, config changes, files created/modified
- Ready for execution summary and user go-ahead

### 2026-02-12 — Phase 1 Implementation Complete
- All 11 files created/modified (see table below)
- Backend: config.py, table_creator.py, migrate_add_knowledge_pages.py, qwen_service.py, cloud_ocr.py, main.py
- Frontend: auto-slicer.html + auto-slicer.js (cloud extraction section), knowledge-page-review.html + knowledge-page-review.js
- All Python files pass diagnostics (0 errors)
- Pending: server startup test, migration run, manual UI testing

---

## Files Created/Modified

| File | Action | Lines |
|------|--------|-------|
| `000-tracking/12-02-requirement-cloud-ocr-approach.md` | Created | ~30 |
| `000-tracking/12-02-design-cloud-ocr-approach.md` | Created | ~40 |
| `000-tracking/12-02-tracking-cloud-ocr-approach.md` | Created | ~30 |
| `000-tracking/12-02-testing-cloud-ocr-approach.md` | Created | ~20 |
| `03-code/src/config.py` | Modified | +2 fields |
| `03-code/.env.example` | Modified | +2 vars |
| `03-code/migrate_add_knowledge_pages.py` | Created | ~80 |
| `03-code/src/database/table_creator.py` | Modified | +2 functions |
| `03-code/src/services/qwen_service.py` | Created | ~350 |
| `03-code/src/api/routes/cloud_ocr.py` | Created | ~810 |
| `03-code/src/main.py` | Modified | +router +page route |
| `03-code/src/frontend/templates/auto-slicer.html` | Modified | +cloud section |
| `03-code/src/frontend/static/js/auto-slicer.js` | Modified | +cloud functions |
| `03-code/src/frontend/templates/knowledge-page-review.html` | Created | ~170 |
| `03-code/src/frontend/static/js/knowledge-page-review.js` | Created | ~380 |
