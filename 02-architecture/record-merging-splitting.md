# Record Merging and Splitting Architecture

**Project:** Knowledge Extraction System (12-extractor)
**Date:** 2025-11-08
**Status:** ✅ APPROVED - New Feature
**Type:** Verification Interface Enhancement

---

## 📋 Overview

This document describes the **Record Merging and Splitting** feature that allows users to combine or divide knowledge units during the verification process. This addresses the common OCR issue where sentences are split incorrectly or combined inappropriately.

**Key Principles:**
1. ✅ **Context View**: Show 5 records before + current + 5 records after (11 total)
2. ✅ **Flexible Merging**: Merge forward (up to 5) or backward (up to 5)
3. ✅ **Flexible Splitting**: Split current record into multiple records
4. ✅ **Disabled Records**: Merged records marked as "disabled" but kept in database
5. ✅ **Full Undo**: Complete history tracking for unmerge/unsplit operations
6. ✅ **Filter Toggle**: Show/hide disabled records in verification interface

---

## 🎯 System-Reserved Attribute 8: Record Status

**Attribute 8** is now **system-reserved** for record status management:

| Attribute | Key Name | Default Value | Possible Values | Purpose |
|-----------|----------|---------------|-----------------|---------|
| 8 | `record_status` | `enabled` | `enabled`, `disabled` | Track if record is active or merged into another |

**Updated Attribute Allocation:**
- **Attributes 1-8**: System-reserved (7 OCR + 1 record status)
- **Attributes 9-40**: User-defined (32 custom attributes)

---

## 🔄 Record Merging Workflow

### **Scenario: Merge Current Record with 2 Following Records**

**Before Merge:**
```
Record 150: "Neural networks consist of"        [enabled]
Record 151: "interconnected layers"             [enabled]
Record 152: "with weighted connections."        [enabled]
```

**User Action:** Select "Merge with Next 2"

**After Merge:**
```
Record 150: "Neural networks consist of interconnected layers with weighted connections."  [enabled]
Record 151: ""  (text moved to 150)             [disabled, merged_into_record_id=150]
Record 152: ""  (text moved to 150)             [disabled, merged_into_record_id=152]
```

**Database Changes:**
```sql
-- Update Record 150 (target record)
UPDATE book1_mybook_knowledge_units SET
  text = text || ' ' || (SELECT text FROM ... WHERE id=151) || ' ' || (SELECT text FROM ... WHERE id=152),
  original_record_ids = ARRAY[150, 151, 152],
  updated_at = NOW()
WHERE id = 150;

-- Disable Record 151
UPDATE book1_mybook_knowledge_units SET
  attr8_value = 'disabled',
  merged_into_record_id = 150,
  updated_at = NOW()
WHERE id = 151;

-- Disable Record 152
UPDATE book1_mybook_knowledge_units SET
  attr8_value = 'disabled',
  merged_into_record_id = 150,
  updated_at = NOW()
WHERE id = 152;
```

---

## ✂️ Record Splitting Workflow

### **Scenario: Split Current Record into 3 Parts**

**Before Split:**
```
Record 200: "Neural networks learn patterns. They use backpropagation. Training requires large datasets."  [enabled]
```

**User Action:**
1. User defines 2 split points:
   - After "patterns."
   - After "backpropagation."
2. System creates 3 new records

**After Split:**
```
Record 200: "Neural networks learn patterns."                [enabled, original_record_ids=[200]]
Record 201: "They use backpropagation."                      [enabled, created from split]
Record 202: "Training requires large datasets."              [enabled, created from split]
```

**Database Changes:**
```sql
-- Update original record (keep first segment)
UPDATE book1_mybook_knowledge_units SET
  text = 'Neural networks learn patterns.',
  original_record_ids = ARRAY[200],
  updated_at = NOW()
WHERE id = 200;

-- Insert new record for second segment
INSERT INTO book1_mybook_knowledge_units
  (text, page_number, position, chapter, topic, sub_topic,
   attr1_value, attr2_value, ..., attr8_value,
   original_record_ids, created_at)
VALUES
  ('They use backpropagation.', 45, '200,650', 'Chapter 5', 'Neural Networks', 'Training',
   NULL, 'original_ocr_text_here', ..., 'enabled',
   ARRAY[200], NOW());

-- Insert new record for third segment
INSERT INTO book1_mybook_knowledge_units
  (text, page_number, position, chapter, topic, sub_topic,
   attr1_value, attr2_value, ..., attr8_value,
   original_record_ids, created_at)
VALUES
  ('Training requires large datasets.', 45, '200,720', 'Chapter 5', 'Neural Networks', 'Training',
   NULL, 'original_ocr_text_here', ..., 'enabled',
   ARRAY[200], NOW());
```

---

## 🖥️ Verification Interface Design

### **Context View Layout (11 Records Displayed)**

```
┌─────────────────────────────────────────────────────────┐
│  CONTEXT VIEW: 5 Before + Current + 5 After             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Record 145 (5 before)                                  │
│  "In supervised learning, the model is trained..."      │
│  [Merge Backward ↑]                                      │
│                                                          │
│  Record 146 (4 before)                                  │
│  "using labeled data where..."                          │
│  [Merge Backward ↑]                                      │
│                                                          │
│  Record 147 (3 before)                                  │
│  "each input has a corresponding output."               │
│  [Merge Backward ↑]                                      │
│                                                          │
│  Record 148 (2 before)                                  │
│  "The algorithm learns by minimizing..."                │
│  [Merge Backward ↑]                                      │
│                                                          │
│  Record 149 (1 before)                                  │
│  "the difference between predictions and..."            │
│  [Merge Backward ↑]                                      │
│                                                          │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│  ┃ Record 150 (CURRENT) ★                            ┃ │
│  ┃ "actual values, iteratively adjusting weights."  ┃ │
│  ┃                                                    ┃ │
│  ┃ [← Merge with Previous 1-5]                       ┃ │
│  ┃ [→ Merge with Next 1-5]                           ┃ │
│  ┃ [✂️ Split this Record]                            ┃ │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                          │
│  Record 151 (1 after)                                   │
│  "This iterative process continues..."                  │
│  [Merge Forward ↓]                                       │
│                                                          │
│  Record 152 (2 after)                                   │
│  "until the model reaches acceptable accuracy."         │
│  [Merge Forward ↓]                                       │
│                                                          │
│  Record 153 (3 after)                                   │
│  "Common optimization algorithms include..."            │
│  [Merge Forward ↓]                                       │
│                                                          │
│  Record 154 (4 after)                                   │
│  "gradient descent and its variants."                   │
│  [Merge Forward ↓]                                       │
│                                                          │
│  Record 155 (5 after)                                   │
│  "Learning rate is a critical hyperparameter."          │
│  [Merge Forward ↓]                                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### **Merge Actions UI**

**Merge Backward (with Previous):**
```
[← Merge with Previous]
  └─ Dropdown: [1][2][3][4][5] records
```
- Click button → Dropdown shows options 1-5
- User selects how many previous records to merge
- Current record becomes the target (text from previous records prepended)
- Previous records marked as disabled

**Merge Forward (with Next):**
```
[Merge with Next →]
  └─ Dropdown: [1][2][3][4][5] records
```
- Click button → Dropdown shows options 1-5
- User selects how many following records to merge
- Current record becomes the target (text from next records appended)
- Next records marked as disabled

**Split Current Record:**
```
[✂️ Split this Record]
  └─ Opens split interface:
     - Shows full text of current record
     - User clicks/drags to mark split points
     - Preview shows resulting records
     - [Cancel] [Confirm Split]
```

---

## 📊 Database Schema

### **New Columns in `knowledge_units` Table**

```sql
-- System-reserved attribute 8
attr8_value TEXT DEFAULT 'enabled',  -- 'enabled' or 'disabled'

-- Merge/split tracking
merged_into_record_id INTEGER REFERENCES book1_mybook_knowledge_units(id),
original_record_ids TEXT[],  -- Array of original IDs if merged or split

-- Indexes
INDEX idx_record_status (attr8_value),
INDEX idx_merged_into (merged_into_record_id)
```

### **Updated `attribute_keys` Table**

```sql
-- Pre-populate attribute 8
INSERT INTO book1_mybook_attribute_keys
  (attr_number, key_name, is_system_reserved, is_editable)
VALUES
  (8, 'record_status', true, false);
```

---

## 🔍 Filtering: Show Enabled/Disabled Records

### **Toggle in Verification Interface**

```
┌─────────────────────────────────────────┐
│  Show Records: [🔘 Enabled Only]       │
│                [◯ All Records]           │
│                [◯ Disabled Only]         │
└─────────────────────────────────────────┘
```

**SQL Queries:**

**Enabled Only (Default):**
```sql
SELECT * FROM book1_mybook_knowledge_units
WHERE attr8_value = 'enabled'
ORDER BY page_number, id;
```

**All Records:**
```sql
SELECT * FROM book1_mybook_knowledge_units
ORDER BY page_number, id;
```

**Disabled Only:**
```sql
SELECT * FROM book1_mybook_knowledge_units
WHERE attr8_value = 'disabled'
ORDER BY page_number, id;
```

---

## ↩️ Undo Operations

### **Unmerge (Restore Merged Records)**

**UI:**
```
Record 150: "Full merged text here..."  [enabled]
  └─ [↩️ Unmerge] button (only shown if original_record_ids exists)
```

**Action:**
- Restore original text to each record from `original_record_ids` array
- Set `attr8_value = 'enabled'` for all restored records
- Clear `merged_into_record_id` for restored records
- Clear `original_record_ids` from merged record

**SQL:**
```sql
-- Re-enable previously merged records
UPDATE book1_mybook_knowledge_units
SET
  attr8_value = 'enabled',
  merged_into_record_id = NULL,
  updated_at = NOW()
WHERE merged_into_record_id = 150;

-- Reset the merged record (requires stored original text)
-- Implementation: Keep original text in a history table
```

### **Unsplit (Recombine Split Records)**

**UI:**
```
Record 200: "First segment."  [enabled, created from split]
  └─ [↩️ Unsplit] button (only shown if this was split from original)
```

**Action:**
- Delete all records created from the split
- Restore original full text to the source record

---

## 🎨 UI Mockup Requirements

**Key Elements:**
1. **Context Panel**: Always show 5 before + current + 5 after
2. **Current Record Highlight**: Distinct border/background color
3. **Merge Buttons**: On every record in context view
4. **Split Button**: Only on current record
5. **Disabled Indicator**: Gray out disabled records, show "MERGED INTO: Record #XXX"
6. **Filter Toggle**: Radio buttons or dropdown to filter by status
7. **Undo Buttons**: Show when merge/split history exists

---

## 🔐 Business Rules

### **Default Status:**
- **All records created during OCR** → `attr8_value = 'enabled'`
- **All records created from splitting** → `attr8_value = 'enabled'`
- **All records merged into another** → `attr8_value = 'disabled'`

### **Merge Limits:**
- **Maximum backward merge**: 5 records
- **Maximum forward merge**: 5 records
- **Combined limit**: Can merge up to 11 records total (5 before + current + 5 after)

### **Split Limits:**
- **No hard limit** on number of split points
- **Minimum**: 2 resulting records (1 split point)
- **Practical**: UI should support at least 10 split points

### **Filtering:**
- **Verification interface default**: Show enabled records only
- **User can toggle** to show all or disabled only
- **Disabled records**: Cannot be merged or split (must be unmerged first)

---

## 📋 Acceptance Criteria

- ✅ Context view shows 5 records before + current + 5 records after
- ✅ User can merge current with 1-5 previous records
- ✅ User can merge current with 1-5 following records
- ✅ Merged records marked as `disabled` in Attribute 8
- ✅ Merged records store reference to target record (`merged_into_record_id`)
- ✅ Target record stores list of original IDs (`original_record_ids`)
- ✅ User can split current record into multiple records
- ✅ Split records all marked as `enabled`
- ✅ Split records reference original record ID
- ✅ Filter toggle: Enabled Only / All Records / Disabled Only
- ✅ Undo merge: Restore all merged records to enabled
- ✅ Undo split: Delete split records, restore original
- ✅ Database indexes on `attr8_value` for fast filtering
- ✅ UI clearly highlights current record
- ✅ UI shows disabled records in grayed-out style
- ✅ Attribute 8 pre-configured as system-reserved in all books

---

## 🚀 Implementation Notes

### **Frontend Considerations:**
- Use virtual scrolling if context view shows many large records
- Debounce merge/split actions to prevent accidental double-clicks
- Show confirmation dialog for bulk operations (merging 5+ records)
- Auto-scroll to keep current record centered in viewport

### **Backend Considerations:**
- Wrap merge/split operations in database transactions
- Create audit log for all merge/split operations
- Store original text in history table for undo capability
- Validate merge range (ensure all records exist and are enabled)

### **Performance:**
- Index on `attr8_value` for fast filtering
- Index on `merged_into_record_id` for undo operations
- Cache context view data (11 records) to avoid repeated queries
- Use batch updates for merging multiple records

---

## 📝 Example Use Cases

### **Use Case 1: OCR Split a Sentence**
**Problem:** "Neural networks are powerful. They" (split across 2 records)

**Solution:**
1. Navigate to first record
2. Click "Merge with Next 1"
3. Result: "Neural networks are powerful. They" (single record)

### **Use Case 2: OCR Combined Two Ideas**
**Problem:** "Backpropagation adjusts weights. Gradient descent is an optimizer." (both in 1 record)

**Solution:**
1. Navigate to record
2. Click "Split this Record"
3. Mark split point after "weights."
4. Confirm split
5. Result: 2 separate records

### **Use Case 3: Review Disabled Records**
**Problem:** User wants to see what was merged

**Solution:**
1. Change filter to "All Records"
2. Disabled records shown in gray
3. Click on disabled record → see "MERGED INTO: Record #150"
4. Click link → navigate to target record
5. Optionally unmerge if mistake

---

**End of Document**
