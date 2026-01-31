# Requirement 7: KU Grouping, Multi-Tag Extraction & YOLO Fine-Tuning

## Requirements Document

**Created:** January 29, 2026
**Status:** ✅ Complete

---

## Overview

Three major features to enhance the pipeline and layout detection:

1. **7A: Multi-Tag XML Extraction** - Extract multiple XML tags from Claude responses into different attributes
2. **7B: Knowledge Unit Grouping** - Combine multiple KUs into single prompts for efficiency  
3. **7C: YOLO Fine-Tuning** - Train DocLayout-YOLO with user corrections

---

## User Stories

### 7A: Multi-Tag XML Extraction

**US-7A.1:** As a user, I want to configure multiple XML tags in a single pipeline step so that one Claude prompt can extract multiple pieces of information into different attributes.

**Acceptance Criteria:**
- Table/grid UI for tag-to-attribute mapping
- Support 1-10 tag mappings per pipeline step
- Validate tag names (alphanumeric, underscores)
- Parse Claude response for configured XML tags
- Store unmapped tags in user-specified fallback attribute
- Mark KU as "incomplete" if expected tag is missing

### 7B: Knowledge Unit Grouping

**US-7B.1:** As a user, I want to combine multiple KUs into a single Claude prompt so that I can reduce API costs and provide better context across related KUs.

**Acceptance Criteria:**
- Group KUs by same L1 AND L2 title (mandatory constraint)
- User defines max KUs per group OR max tokens per group
- Preview table showing: L1 Title → L2 Title → KU Count → Word Count
- Preview button shows estimated Claude tokens before execution
- KU ID as XML tags in request/response (`<ku_123>...</ku_123>`)
- 3 execution modes: Individual KUs (default), Grouped KUs, Incomplete KUs only
- Dry run mode with save-to-attribute option
- 80 custom attributes for grouped KU results
- Global scope for entire pipeline
- Store unmapped tags in user-specified fallback attribute

### 7C: YOLO Fine-Tuning

**US-7C.1:** As a user, I want to fine-tune the DocLayout-YOLO model with my corrections so that layout detection improves for my specific document types.

**Acceptance Criteria:**
- Store BOTH original YOLO-detected regions AND user-corrected regions
- No hard minimum pages, warning if < 20 pages
- Show quality metrics (corrections/page, class distribution)
- User chooses foreground/background training
- Auto-backup model before training to `models/backups/` with timestamp
- Export to YOLO format (images/ + labels/)
- Training progress display with metrics visualization

---

## Clarification Answers Summary

| # | Question | Answer |
|---|----------|--------|
| Q1 | Tag-to-attribute mapping UI | A) Table/grid UI |
| Q2 | Grouping definition method | C) Group rule with max N |
| Q3 | Response identification | A) KU ID as XML tags |
| Q4 | Grouping criteria | B+D) KU count OR token limit with preview |
| Q5 | Unmapped tags handling | B) Store in user-specified fallback attribute |
| Q6 | Missing expected tag | C) Mark KU as "incomplete" |
| Q7 | Grouping scope | B) Global for entire pipeline |
| Q8 | Missing KU ID in response | A) Mark as "incomplete" + 3 execution modes |
| Q9 | Dry run mode | C) Optional toggle + save preview to attribute |
| Q10 | Min pages for training | D) No hard minimum, warning if < 20 |
| Q11 | Training UI blocking | C) User choice |
| Q12 | Model backup | A) Always auto-backup + store original & corrected regions |

---

## Reference Documents

- `01-requirements/requirement7-grouping-training.md` - Full requirements
- `01-requirements/requirement7-progress.md` - Progress tracker
- `02-architecture/automatic-boundaries-local-llm-part2.md` - YOLO training reference
