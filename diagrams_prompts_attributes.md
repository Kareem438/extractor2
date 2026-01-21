# Diagrams, Prompts, and Attributes Requirements

**Date:** 2026-01-07
**Status:** Requirements Gathering - COMPLETE
**Confidence Level:** 95%

---

## Overview

Four new requirements to enhance the Knowledge Extraction System's handling of diagrams, prompts, and attributes.

---

## Requirement 1: Scanning 3 Additional Texts per Paragraph/Diagram (OCR-Based)

**Original Statement:**
"Allow scanning 3 additional texts for each paragraph or diagram, which will take 3 attributes from the list"

### Clarified Details:
✅ **When:** During verify-pages stage (user triggers manually)
✅ **Where:** Fields available on verify pages for both paragraphs and diagrams
✅ **What:** 3 multi-line text areas where user can SELECT/CROP text regions to be SCANNED using OCR
✅ **Process:** User draws rectangles on PDF image → OCR extracts text → Text stored in attributes
✅ **Different from Req 3:** These 3 boxes are for SCANNED text (OCR extraction), NOT manual entry
✅ **Related Enhancement:** Make Surya OCR with 600 dpi the default text (no click needed)
✅ **Attribute Selection:** User selects which 3 attributes to use in book settings page (Set 1 of 6 total)
✅ **Storage:** OCR-extracted text is stored in the 3 selected custom attributes
✅ **UI Interaction:** User draws rectangles directly on the PDF page image (like existing diagram selection)
✅ **Labels:** User can define custom labels in book settings separate from attribute names
✅ **Text Box Type:** Multi-line text areas (like textareas) - Answer: B

### Complete Workflow:
1. User views paragraph/diagram on verify-pages
2. User draws 3 rectangles on PDF image to select text regions
3. OCR automatically extracts text from each region
4. Extracted text appears in 3 labeled multi-line text areas
5. User can edit OCR results if needed
6. Text is saved to the 3 configured attributes when user saves the item

---

## Requirement 2: Pipeline Workflow with Title-Based Attributes

**Original Statement:**
"The pipeline workflow can include attributes from all records under a specific title"

### Clarified Details:
✅ **What:** When running pipeline processing, Claude can read/access attributes from all paragraphs/diagrams under a specific title
✅ **Purpose:** Provide context awareness - Claude sees all related content under a hierarchical title
✅ **Use Case:** When processing a paragraph, Claude can see attributes from sibling/related items under the same title structure
✅ **Title Levels:** ALL levels - Claude sees everything under any matching title at any level
✅ **Scope:** Very powerful context feature - provides complete hierarchical context
✅ **Record Types:** Includes BOTH paragraphs AND diagrams - Answer: A

### Complete Workflow:
1. User runs pipeline processing on a specific paragraph/diagram
2. System identifies the hierarchical title structure (levels 1-5) for that item
3. System retrieves ALL paragraphs and diagrams under matching titles at ANY level
4. Claude receives all attributes from these related items as context
5. Claude generates better, context-aware responses using this comprehensive information

### Questions Remaining:
- Does this apply to ALL attributes or specific selected attributes?
- Is this configured per pipeline or globally enabled?

---

## Requirement 3: Adding Specific Text on Verify Pages (Manual Entry)

**Original Statement:**
"Allow adding specific text on the verify pages for a specific paragraph"

### Clarified Details:
✅ **What:** 3 multi-line text areas on verify page for user to MANUALLY ENTER text (no scanning)
✅ **Different from Req 1:** These 3 boxes are for MANUAL text entry WITHOUT scanning
✅ **Process:** User types/pastes text directly into text areas → Text stored in attributes
✅ **Storage:** Stored in custom attributes selected by user in book settings page (Set 2 of 6 total)
✅ **Applies to:** Paragraphs AND diagrams (same as Req 1)
✅ **Labels:** User can define custom labels in book settings separate from attribute names
✅ **Text Box Type:** Multi-line text areas (like textareas) - Answer: B

### CRITICAL DISTINCTION:
**Requirements 1 and 3 use DIFFERENT sets of 3 attributes (6 attributes total):**
- **Requirement 1:** 3 attributes for OCR-scanned text (user draws rectangles → OCR extracts)
- **Requirement 3:** 3 different attributes for manual text entry (user types directly)
- **Total:** 6 attributes configured in book settings (3 for scanning + 3 for manual entry)

### Complete Workflow:
1. User views paragraph/diagram on verify-pages
2. User sees 3 labeled multi-line text areas for manual entry
3. User types or pastes text directly into these areas
4. Text is saved to the 3 configured attributes when user saves the item

---

## Requirement 4: Book Settings with 3 Diagram Analysis Prompts

**Original Statement:**
"For adding diagrams, the book should have 3 prompts in settings for analyzing diagrams, with titles: diagram, equation, and table"

### Clarified Details:
✅ **When Used:** During verify-pages stage when adding diagrams
✅ **Workflow:**
  1. User clicks "Add Diagram"
  2. Dropdown appears with options: Diagram / Equation / Table
  3. User selects prompt type from dropdown
  4. Claude API call is made with selected prompt from book settings
  5. Claude generates text analysis
  6. User can modify the generated text
  7. User clicks "Add Diagram" to save
✅ **Storage Location:** Book settings page (prompts are per-book configuration)
✅ **Prompt Selection:** User manually selects from dropdown when adding a diagram
✅ **API Behavior:** Only ONE selected prompt is sent to Claude per diagram
✅ **Dropdown Location:** Appears in the "Add Diagram" modal/form
✅ **Prompt Type Saved:** Yes, saved in database so user can see which prompt was used - Answer: A

### Complete Workflow:
1. User configures 3 prompts in book settings:
   - Diagram prompt (for flowcharts, architecture diagrams, etc.)
   - Equation prompt (for mathematical formulas)
   - Table prompt (for tabular data)
2. When adding a diagram on verify-pages:
   - User selects diagram region
   - Dropdown appears with 3 options
   - User selects appropriate prompt type
   - Claude analyzes using that specific prompt
   - Result is saved along with the prompt type used

---

## Clarification Sessions

### Session 1 - 2026-01-07 - Batch 1

**Questions Asked:**
1. When do the "3 additional text scans" happen?
2. How are the "3 additional texts" provided?
3. When are the 3 diagram prompts used?

**Answers Received:**
1. **B** - During verify-pages stage (user triggers manually). Fields on verify pages. Also: Make Surya OCR 600 dpi the default text.
2. **Clarification:** Two separate things:
   - 3 text fields: User manually provides on verify-page when adding paragraph/diagram
   - 3 prompts: Specified in book settings, used to analyze diagrams via Claude API
3. **B** - During verify-pages when reviewing diagrams. Also: When adding diagrams, Claude API call analyzes diagram → generates text → user modifies → clicks "Add Diagram"

### Session 1 - 2026-01-07 - Batch 2

**Questions Asked:**
4. Which 3 attributes will store the "3 additional texts"?
5. How does the user choose which prompt to use (diagram vs equation vs table)?
6. What is the "specific text" that needs to be added on verify pages?

**Answers Received:**
4. **B** - User selects which 3 attributes to use in the book settings page (configurable per book)
5. **B** - User manually selects from a dropdown when adding a diagram
6. **D** - 3 text boxes that user enters manually in verify page, stored in custom attributes selected in book settings

### Session 1 - 2026-01-07 - Batch 3

**Questions Asked:**
7. Are Requirements 1 and 3 actually the same thing, or are they different?
8. What does "pipeline workflow can include attributes" mean?
9. Where does the dropdown for diagram prompts appear?

**Answers Received:**
7. **C** - They are DIFFERENT and use different sets of 3 attributes (6 attributes total):
   - **Req 1:** 3 text boxes for SCANNED text (OCR extraction)
   - **Req 3:** 3 text boxes for MANUAL text entry (no scanning)
8. **A** - When running pipeline, Claude can read/access attributes from all paragraphs/diagrams under a specific title for better context
9. **A** - Dropdown appears in the "Add Diagram" modal/form when user clicks "Add Diagram"

### Session 1 - 2026-01-07 - Batch 4

**Questions Asked:**
10. How does the user select/crop text regions for OCR scanning?
11. Which title level determines the grouping for pipeline context?
12. For the 6 text boxes (3 OCR + 3 manual) - do they have custom labels?

**Answers Received:**
10. **A** - User draws rectangles directly on the PDF page image (like existing diagram selection)
11. **C** - All levels - Claude sees everything under any matching title at any level
12. **B** - Yes, user can define custom labels in book settings separate from attribute names

### Session 1 - 2026-01-07 - Batch 5 (FINAL)

**Questions Asked:**
13. For ALL 6 text boxes (3 OCR + 3 manual) - are they single-line or multi-line?
14. Does pipeline context include BOTH paragraphs and diagrams?
15. Is the selected prompt type (diagram/equation/table) saved with the diagram record?

**Answers Received:**
13. **B** - All 6 are multi-line text areas (like textareas)
14. **A** - Yes, Claude sees attributes from BOTH paragraphs AND diagrams under matching titles
15. **A** - Yes, saved in database so user can see which prompt was used

**FINAL KEY INSIGHTS:**
- All text boxes are multi-line for better content entry
- Pipeline context is truly comprehensive - includes both types of records
- Diagram prompt type is tracked for reference and audit purposes

---

## Summary of Requirements

### Book Settings Page Changes:

1. **3 Diagram Analysis Prompts (large text areas):**
   - Diagram prompt - for flowcharts, architecture diagrams, illustrations
   - Equation prompt - for mathematical formulas, equations
   - Table prompt - for tabular data, matrices

2. **6 Attribute Selections (dropdowns):**
   - 3 attributes for OCR-scanned text (Req 1)
   - 3 attributes for manual text entry (Req 3)

3. **6 Custom Label Fields (text inputs):**
   - 3 labels for OCR text boxes (displayed on verify pages)
   - 3 labels for manual text boxes (displayed on verify pages)
   - Labels are separate from attribute names for better UX

**Total New Fields in Book Settings:** 15 fields
- 3 large text areas (prompts)
- 6 dropdowns (attribute selections)
- 6 text inputs (custom labels)

### Verify Pages Changes:

**For Paragraphs:**
- Make Surya OCR 600 dpi the default text (no click needed)
- Add 3 multi-line text areas for OCR scanning (user draws rectangles on image → OCR extracts)
- Add 3 multi-line text areas for manual text entry

**For Diagrams:**
- Add "Analyze Diagram" feature with dropdown (diagram/equation/table)
- Add 3 multi-line text areas for OCR scanning (user draws rectangles on image → OCR extracts)
- Add 3 multi-line text areas for manual text entry

**Total New UI Elements per Paragraph/Diagram:** 6 multi-line text areas

### Pipeline Changes:

- Enable Claude to access attributes from ALL records (paragraphs AND diagrams) under matching titles at ANY hierarchical level
- Provides complete hierarchical context awareness for better AI responses
- When processing any item, Claude can see all related content in the same title hierarchy

### Database Changes:

**For Diagrams Table:**
- Add new column: `prompt_type` (VARCHAR) - stores "diagram", "equation", or "table"
- This tracks which prompt was used for analysis

---

## Implementation Checklist

### Phase 1: Book Settings Page
- [ ] Add 3 large text area fields for diagram prompts
- [ ] Add 6 dropdown fields for attribute selection (OCR + Manual)
- [ ] Add 6 text input fields for custom labels (OCR + Manual)
- [ ] Update book settings API to save/load new fields
- [ ] Update book settings table schema

### Phase 2: Verify Pages UI
- [ ] Make Surya OCR 600 dpi the default (remove click requirement)
- [ ] Add rectangle-drawing UI for 3 OCR regions
- [ ] Add 3 labeled multi-line text areas for OCR results
- [ ] Add 3 labeled multi-line text areas for manual entry
- [ ] Wire up OCR extraction on rectangle completion
- [ ] Update save logic to store 6 new attribute values

### Phase 3: Diagram Analysis
- [ ] Add dropdown to "Add Diagram" modal (diagram/equation/table)
- [ ] Implement Claude API call with selected prompt
- [ ] Save prompt type with diagram record
- [ ] Update diagrams table schema (add prompt_type column)

### Phase 4: Pipeline Context Enhancement
- [ ] Modify pipeline to query all records under matching titles (all levels)
- [ ] Include both paragraphs AND diagrams in context
- [ ] Format attributes for Claude consumption
- [ ] Test context awareness improvements

### Phase 5: Testing
- [ ] Test OCR extraction workflow
- [ ] Test manual entry workflow
- [ ] Test diagram analysis with all 3 prompt types
- [ ] Test pipeline context with hierarchical titles
- [ ] Verify all 6 attributes save correctly

---

## Database Schema Changes

### New Table: book_settings (extend existing)
```sql
-- Add to existing book_settings table
ALTER TABLE {prefix}_book_settings ADD COLUMN diagram_prompt TEXT;
ALTER TABLE {prefix}_book_settings ADD COLUMN equation_prompt TEXT;
ALTER TABLE {prefix}_book_settings ADD COLUMN table_prompt TEXT;

ALTER TABLE {prefix}_book_settings ADD COLUMN ocr_attr1_id INTEGER;
ALTER TABLE {prefix}_book_settings ADD COLUMN ocr_attr2_id INTEGER;
ALTER TABLE {prefix}_book_settings ADD COLUMN ocr_attr3_id INTEGER;

ALTER TABLE {prefix}_book_settings ADD COLUMN manual_attr1_id INTEGER;
ALTER TABLE {prefix}_book_settings ADD COLUMN manual_attr2_id INTEGER;
ALTER TABLE {prefix}_book_settings ADD COLUMN manual_attr3_id INTEGER;

ALTER TABLE {prefix}_book_settings ADD COLUMN ocr_label1 VARCHAR(100);
ALTER TABLE {prefix}_book_settings ADD COLUMN ocr_label2 VARCHAR(100);
ALTER TABLE {prefix}_book_settings ADD COLUMN ocr_label3 VARCHAR(100);

ALTER TABLE {prefix}_book_settings ADD COLUMN manual_label1 VARCHAR(100);
ALTER TABLE {prefix}_book_settings ADD COLUMN manual_label2 VARCHAR(100);
ALTER TABLE {prefix}_book_settings ADD COLUMN manual_label3 VARCHAR(100);
```

### Update Table: diagrams
```sql
-- Add to existing diagrams table
ALTER TABLE {prefix}_diagrams ADD COLUMN prompt_type VARCHAR(20);
-- Valid values: 'diagram', 'equation', 'table'
```

---

## API Changes

### Book Settings API
**GET /book-settings/{book_id}**
- Returns 15 new fields

**PUT /book-settings/{book_id}**
- Accepts 15 new fields

### Verify Pages API
**POST /paragraphs**
- Accepts 6 new attribute values (from OCR + manual text areas)

**POST /diagrams**
- Accepts `prompt_type` field
- Accepts 6 new attribute values (from OCR + manual text areas)

### Pipeline API
**No changes needed** - pipeline will automatically access new attributes

---

## UI/UX Considerations

1. **Text Area Sizing:** Multi-line text areas should be at least 3-4 rows high for usability
2. **Label Clarity:** Custom labels should clearly indicate OCR vs Manual entry
3. **OCR Feedback:** Show loading indicator while OCR is processing
4. **Error Handling:** Handle OCR failures gracefully
5. **Prompt Selection:** Make dropdown prominent and clear for diagram analysis
6. **Context Indicator:** Consider showing pipeline context scope to users

---

**Status:** ✅ Requirements gathering COMPLETE
**Confidence Level:** 95%
**Last Updated:** 2026-01-07
**Ready for:** Implementation planning

