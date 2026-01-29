# Requirement 7: Progress Tracker

**Feature:** KU Grouping, Multi-Tag Extraction & YOLO Fine-Tuning  
**Created:** January 29, 2026  
**Last Updated:** January 29, 2026

---

## Overall Status: 🟡 Requirements Gathering

| Phase | Status | Progress |
|-------|--------|----------|
| Requirements | 🟡 In Progress | 60% |
| Design | ⬜ Not Started | 0% |
| Implementation | ⬜ Not Started | 0% |
| Testing | ⬜ Not Started | 0% |

---

## Clarification Questions Completed

| # | Question | Answer | Feature |
|---|----------|--------|---------|
| Q1 | Tag-to-attribute mapping UI | A) Table/grid UI | 7A |
| Q2 | Grouping definition method | C) Group rule with max N | 7B |
| Q3 | Response identification | A) KU ID as XML tags | 7B |
| Q4 | Grouping criteria | B+D) KU count OR token limit with preview | 7B |

## Questions Remaining

| # | Question | Status | Feature |
|---|----------|--------|---------|
| Q5 | Unmapped tags handling | ⬜ Pending | 7A |
| Q6 | Missing tag error handling | ⬜ Pending | 7A |
| Q7 | Grouping scope (per-step or global) | ⬜ Pending | 7B |
| Q8 | Missing KU ID in response | ⬜ Pending | 7B |
| Q9 | Dry run mode | ⬜ Pending | 7B |
| Q10 | Min pages for training | ⬜ Pending | 7C |
| Q11 | Training UI blocking | ⬜ Pending | 7C |
| Q12 | Model backup before training | ⬜ Pending | 7C |

---

## Session Log

### Session 2026-01-29 (Requirements Gathering Started)
- User provided 3 major requirements:
  - 7A: Multi-tag XML extraction to multiple attributes
  - 7B: KU grouping for batch Claude prompts
  - 7C: YOLO fine-tuning with user corrections
- Completed 4 clarification questions
- Key decisions:
  - Table/grid UI for tag mapping
  - Group by L2 title with configurable max
  - KU ID as XML tags in both request and response
  - Both KU count and token limit options with preview
- Found existing YOLO fine-tuning docs in `02-architecture/automatic-boundaries-local-llm-part2.md`
- Created requirement7-grouping-training.md
- Session ending - more questions needed

---

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `01-requirements/requirement7-grouping-training.md` | Full requirements | ✅ Created |
| `01-requirements/requirement7-progress.md` | This tracker | ✅ Created |
| `02-architecture/automatic-boundaries-local-llm-part2.md` | YOLO training reference | 📖 Existing |
| `02-architecture/AUTO-BOUNDARIES-PROGRESS.md` | YOLO progress | 📖 Existing |

---

## Next Session Instructions

1. **Continue clarification questions** (Q5-Q12 in this file)
2. **Review existing code** before design:
   - `03-code/src/api/routes/pipeline.py`
   - `03-code/src/services/claude_batch_service.py`
   - `03-code/src/frontend/templates/pipeline-config.html`
3. **Create design document** after questions complete
4. **Create tasks.md** with implementation plan

---

## Context Summary for Next Session

### 7A: Multi-Tag Extraction
- One Claude prompt → multiple XML tags in response
- Each tag maps to different attribute (e.g., `<summary>` → attr_15)
- UI: Table with Tag Name | Target Attribute dropdown

### 7B: KU Grouping
- Combine multiple KUs into single prompt
- Constraint: Same L1 + L2 title
- User sets: Max KUs per group OR max tokens
- Preview button shows token estimate
- Request format: `<ku_123><description>...</description></ku_123>`
- Response format: `<ku_123><summary>...</summary></ku_123>`
- System parses response and distributes to individual KU attributes
- Need preview table: L1 → L2 → KU count → word count

### 7C: YOLO Fine-Tuning
- Train DocLayout-YOLO with user corrections
- ~20+ pages of corrections needed
- Export to YOLO format, run training script
- Full details in existing architecture docs
