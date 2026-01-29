# Requirement 7: KU Grouping, Multi-Tag Extraction & YOLO Fine-Tuning

**Created:** January 29, 2026  
**Status:** Requirements Gathering (In Progress)

---

## Overview

Three major features to enhance the pipeline and layout detection:

1. **7A: Multi-Tag XML Extraction** - Extract multiple XML tags from Claude responses into different attributes
2. **7B: Knowledge Unit Grouping** - Combine multiple KUs into single prompts for efficiency
3. **7C: YOLO Fine-Tuning** - Train DocLayout-YOLO with user corrections

---

## Requirement 7A: Multi-Tag XML Extraction

### Summary
Enhance pipeline-config to extract different XML tags from Claude's response into specific custom attributes. One prompt can retrieve 3-4 results stored in various attributes.

### Clarification Answers
| Question | Answer |
|----------|--------|
| UI for tag-to-attribute mapping | **A) Table/grid UI** - Each row: XML Tag Name → Target Attribute dropdown |

### Functional Requirements

1. **Tag-to-Attribute Mapping UI**
   - Table/grid interface in pipeline-config
   - Each row: `[XML Tag Name] → [Target Attribute Dropdown]`
   - Support 1-10 tag mappings per pipeline step
   - Validate tag names (alphanumeric, underscores)

2. **Response Parsing**
   - Parse Claude response for configured XML tags
   - Extract content between `<tag>...</tag>`
   - Store each extracted value in mapped attribute
   - Handle missing tags gracefully (null or default value)

3. **Example Flow**
   ```
   Prompt: "Analyze this text and provide..."
   
   Response:
   <summary>Brief overview of the content...</summary>
   <keywords>keyword1, keyword2, keyword3</keywords>
   <difficulty>intermediate</difficulty>
   
   Mapping:
   - summary → attr_15
   - keywords → attr_16
   - difficulty → attr_17
   ```

---

## Requirement 7B: Knowledge Unit Grouping

### Summary
Combine multiple knowledge units into a single Claude prompt, with responses distributed back to individual KU attributes. Reduces API calls and provides context across related KUs.

### Clarification Answers
| Question | Answer |
|----------|--------|
| Grouping definition | **C) Group rule** - "Group by L2 title with max N units per group" |
| Response identification | **A) KU ID as XML tags** - `<ku_123>answer</ku_123>` |
| Grouping criteria | **B+D) Both KU count AND token limit** - User chooses, with preview |

### Functional Requirements

1. **Grouping Rules**
   - Group KUs by same L1 AND L2 title (mandatory constraint)
   - User defines max KUs per group OR max tokens per group
   - Preview button shows estimated Claude tokens before execution

2. **Preview Table UI**
   - Display hierarchical table: L1 Title → L2 Title → KU Count → Word Count
   - Show total words/tokens per L2 section
   - Help user decide optimal group size

3. **Prompt Structure with KU IDs**
   ```xml
   <!-- REQUEST FORMAT -->
   <ku_123>
     <description>Original KU description text...</description>
     <attr_12>Existing attribute value...</attr_12>
     <attr_16>Another attribute...</attr_16>
   </ku_123>
   <ku_124>
     <description>Second KU description...</description>
     <attr_12>...</attr_12>
   </ku_124>
   
   <!-- RESPONSE FORMAT -->
   <ku_123>
     <summary>Generated summary for KU 123...</summary>
     <keywords>keyword1, keyword2</keywords>
   </ku_123>
   <ku_124>
     <summary>Generated summary for KU 124...</summary>
     <keywords>keyword3, keyword4</keywords>
   </ku_124>
   ```

4. **Response Distribution**
   - Parse response by KU ID tags (`<ku_XXX>...</ku_XXX>`)
   - Extract nested tags within each KU block
   - Map to configured attributes for each KU
   - Update database with distributed values

5. **Token Estimation**
   - "Preview" button calculates estimated tokens
   - Uses tiktoken or similar for Claude token estimation
   - Shows: "Selected: 5 KUs, ~3,200 tokens (input) + ~1,500 tokens (output estimate)"

---

## Requirement 7C: YOLO Fine-Tuning

### Summary
Fine-tune DocLayout-YOLO model using user corrections from layout review. After reviewing ~20+ pages, export corrections and train improved model.

### Reference Documentation
- Full technical details in: `02-architecture/automatic-boundaries-local-llm-part2.md`
- Progress tracking in: `02-architecture/AUTO-BOUNDARIES-PROGRESS.md`

### Key Features (from existing docs)
1. **Correction Tracking** - Store original + corrected bounding boxes
2. **Training Data Export** - Export to YOLO format (images/ + labels/)
3. **Training Script** - Fine-tune on RTX 4070 (8GB VRAM)
4. **Training UI** - Progress display, metrics visualization
5. **Model Management** - Version control, activation, inheritance

### Hardware Requirements
- RTX 4070 Laptop (8GB VRAM) - Confirmed feasible
- Batch size: 4 (with AMP enabled)
- ~50-100 corrected pages recommended for improvement

---

## Questions Still Needed (Continue in Next Session)

### 7A Questions
- [ ] Q5: Should unmapped tags in response be ignored or stored somewhere?
- [ ] Q6: Error handling if expected tag is missing from response?

### 7B Questions
- [ ] Q7: Should grouping be per-pipeline-step or global setting?
- [ ] Q8: What happens if a KU ID is missing from Claude's response?
- [ ] Q9: Should there be a "dry run" mode to preview without executing?

### 7C Questions
- [ ] Q10: Minimum pages required before training button is enabled?
- [ ] Q11: Should training run in background or block UI?
- [ ] Q12: Auto-backup current model before training?

---

## Implementation Priority

| Feature | Priority | Complexity | Dependencies |
|---------|----------|------------|--------------|
| 7A Multi-Tag Extraction | HIGH | Medium | Pipeline config UI |
| 7B KU Grouping | HIGH | High | 7A (tag extraction), Title hierarchy |
| 7C YOLO Fine-Tuning | MEDIUM | High | Layout review corrections |

---

## Files to Review Before Implementation

- `03-code/src/api/routes/pipeline.py` - Current pipeline config
- `03-code/src/services/claude_batch_service.py` - Claude API integration
- `03-code/src/frontend/templates/pipeline-config.html` - Pipeline UI
- `02-architecture/automatic-boundaries-local-llm-part2.md` - YOLO training details
- `02-architecture/AUTO-BOUNDARIES-PROGRESS.md` - YOLO progress tracking
