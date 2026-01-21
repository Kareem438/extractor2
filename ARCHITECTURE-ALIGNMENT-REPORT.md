# Architecture Alignment Report

**Date:** 2025-11-11
**Status:** ⚠️ CRITICAL MISALIGNMENT DETECTED
**Severity:** HIGH - Implementation does not match approved architecture

---

## 🔍 Executive Summary

The current implementation (CHUNK-001 through CHUNK-045) **does not align** with the approved architecture documented in:
- `02-architecture/sequential-ocr-svg-processing.md` (Sequential OCR + Integrated SVG Processing)
- `01-requirements/ui-mockups/01-upload-page.html` (UI Requirements)
- `02-architecture/architecture-decisions-approved.md` (Decision 3, 6, 9)

**Key Issues:**
1. ✅ **FIXED:** LLM Model changed from GPT-4o to Claude Sonnet 4.5
2. ⚠️ **CRITICAL:** Upload page missing sequential OCR buttons (4-button approach)
3. ⚠️ **CRITICAL:** Missing 40-attribute configuration (only has 3 basic inputs)
4. ⚠️ **CRITICAL:** Backend uses automatic OCR fallback instead of user-controlled sequential OCR
5. ⚠️ **MEDIUM:** Missing SVG generation for images
6. ⚠️ **MEDIUM:** Missing book-specific instructions text area
7. ⚠️ **MEDIUM:** Missing processing presets (Quick Scan, Balanced, Deep Analysis)

---

## 📋 Detailed Gap Analysis

### **1. Upload Page (03-code/src/frontend/templates/upload.html)**

#### **Requirements (01-requirements/ui-mockups/01-upload-page.html):**

✅ **Step 1: Upload Document**
- Drag-and-drop file upload
- Accept ALL file types
- Display file info
- ⚠️ **MISSING:** Partial processing checkbox (process only first N pages)
- ⚠️ **MISSING:** Book-specific instructions text area

✅ **Step 2: Processing Presets**
- ⚠️ **MISSING:** Quick Scan / Balanced / Deep Analysis / Custom buttons

⚠️ **Step 3: Custom Attributes (80 attributes)**
- **Current:** Only 3 attribute input fields (attr2, attr3, attr4)
- **Required:** 40 attribute configuration fields
  - Attributes 1-8: System-reserved (locked, read-only)
    - Attribute 1: related_image
    - Attribute 2: paddleocr_text
    - Attribute 3: surya_ocr_text
    - Attribute 4: tesseract_text
    - Attribute 5: paddleocr_confidence
    - Attribute 6: surya_ocr_confidence
    - Attribute 7: tesseract_confidence
    - Attribute 8: record_status (enabled/disabled)
  - Attributes 9-40: User-defined (32 custom attributes)

✅ **Step 4: Processing Settings**
- ✅ Language detection (implemented)
- ✅ OCR mode (fixed to PaddleOCR/Surya/Tesseract)
- ✅ LLM model (fixed to Claude Sonnet 4.5)
- ⚠️ **DIFFERENT:** Currently uses dropdown for OCR mode, should use buttons in Step 5

⚠️ **Step 5: Sequential OCR Buttons** - **COMPLETELY MISSING**
- **Required:** 4 independent buttons
  - Button 1: "🚀 Start with PaddleOCR (GPU)"
  - Button 2: "🎯 Start with Surya OCR (GPU)"
  - Button 3: "🛡️ Start with Tesseract (CPU)"
  - Button 4: "✅ Evaluate, Split and Mark"
- **Current:** Simple "Upload & Start Processing" button

#### **Current Implementation Issues:**

| Feature | Required | Current | Status |
|---------|----------|---------|--------|
| File upload | ✅ | ✅ | ✅ DONE |
| Partial processing checkbox | ✅ | ❌ | ⚠️ MISSING |
| Book-specific instructions | ✅ | ❌ | ⚠️ MISSING |
| Processing presets | ✅ | ❌ | ⚠️ MISSING |
| 40-attribute configuration | ✅ | ❌ (only 3) | ⚠️ CRITICAL |
| Sequential OCR buttons (4) | ✅ | ❌ | ⚠️ CRITICAL |
| Language setting | ✅ | ✅ | ✅ DONE |
| LLM model (Claude Sonnet 4.5) | ✅ | ✅ | ✅ FIXED |
| OCR mode dropdown | ❌ (should be buttons) | ✅ | ⚠️ WRONG APPROACH |

---

### **2. Backend Processing Architecture**

#### **Requirements (sequential-ocr-svg-processing.md):**

**Sequential OCR Approach:**
```
Phase 1: OCR Processing (User-Initiated, Sequential)
├─ Button 1: "Start with PaddleOCR"
│  ├─ Load PaddleOCR into GPU (6GB VRAM)
│  ├─ FOR each page: Run OCR, store attr2_value + attr5_value
│  ├─ FOR each image: Analyze with Claude Sonnet 4.5 ONCE
│  │  ├─ Generate description + structured_json
│  │  ├─ Generate SVG from structured_json
│  │  └─ Store in book_images table (image_data, ai_description, svg_code)
│  └─ Unload PaddleOCR from GPU
│
├─ Button 2: "Start with Surya OCR" (Optional, later)
│  ├─ Load Surya into GPU (2GB+ VRAM)
│  ├─ FOR each page: Run OCR, UPDATE attr3_value + attr6_value
│  ├─ SKIP image analysis (already done)
│  └─ Unload Surya from GPU
│
├─ Button 3: "Start with Tesseract" (Optional, later)
│  ├─ Load Tesseract (CPU)
│  ├─ FOR each page: Run OCR, UPDATE attr4_value + attr7_value
│  ├─ SKIP image analysis (already done)
│  └─ Complete
│
└─ Button 4: "Evaluate, Split and Mark"
   ├─ Compare confidence scores (attr5, attr6, attr7)
   ├─ Select best OCR result per page
   ├─ Copy winning text to main `text` field
   ├─ Run Splitter Agent (semantic 3-5 line chunks)
   ├─ Run Marker Agent (green/orange rectangles)
   └─ Status: "Ready for Verification"
```

#### **Current Implementation (03-code/src/api/background_processor.py):**

**Automatic 3-Tier Fallback Approach:**
```python
async def process_book_background(book_id: int, pdf_path: str) -> bool:
    # Single "Start Processing" approach
    for page_num in range(1, total_pages + 1):
        # Automatic fallback (NOT user-controlled):
        # 1. Try PaddleOCR
        # 2. If confidence < 70%, try Surya
        # 3. If confidence < 65%, try Tesseract

        # Stores ONLY the winning result
        # Does NOT store all 3 OCR results in attributes 2-4
```

#### **Backend Implementation Issues:**

| Feature | Required | Current | Status |
|---------|----------|---------|--------|
| User-controlled sequential OCR | ✅ | ❌ | ⚠️ CRITICAL |
| Store all 3 OCR results (attr 2-4) | ✅ | ❌ | ⚠️ CRITICAL |
| Store all 3 confidence scores (attr 5-7) | ✅ | ❌ | ⚠️ CRITICAL |
| One-time image analysis (first OCR only) | ✅ | ❌ | ⚠️ CRITICAL |
| Claude Sonnet 4.5 image analysis | ✅ | ❌ | ⚠️ CRITICAL |
| SVG generation from structured_json | ✅ | ❌ | ⚠️ CRITICAL |
| GPU memory management (sequential load/unload) | ✅ | ❌ | ⚠️ MEDIUM |
| Separate OCR API endpoints (/api/ocr/paddleocr, /api/ocr/surya, /api/ocr/tesseract) | ✅ | ❌ | ⚠️ CRITICAL |
| Evaluate API endpoint (/api/evaluate-split-mark) | ✅ | ❌ | ⚠️ CRITICAL |

---

### **3. Database Schema**

#### **Requirements (sequential-ocr-svg-processing.md):**

**`book{N}_{name}_attribute_keys` Table:**
- 80 attributes total
- Attributes 1-8: System-reserved (is_system_reserved=true, is_editable=false)
- Attributes 9-40: User-defined (is_system_reserved=false, is_editable=true)

**`book{N}_{name}_knowledge_units` Table:**
- `text` field: Best OCR result (after evaluation)
- `ocr_method` field: "paddleocr" | "surya" | "tesseract"
- `confidence_score` field: Best confidence
- `attr1_value`: related_image
- `attr2_value`: paddleocr_text (FULL TEXT)
- `attr3_value`: surya_ocr_text (FULL TEXT)
- `attr4_value`: tesseract_text (FULL TEXT)
- `attr5_value`: paddleocr_confidence
- `attr6_value`: surya_ocr_confidence
- `attr7_value`: tesseract_confidence
- `attr8_value`: record_status (enabled/disabled)
- `attr9_value` through `attr40_value`: User-defined

**`book{N}_{name}_images` Table:**
- `image_data`: BYTEA (original image)
- `ai_description`: TEXT (Claude description)
- `structured_json`: JSONB (for SVG generation)
- `svg_code`: TEXT (generated SVG)
- `analyzed_during_ocr`: "paddleocr" | "surya" | "tesseract"

**`book{N}_{name}_processing_state` Table:**
- `paddleocr_complete`: BOOLEAN
- `surya_ocr_complete`: BOOLEAN
- `tesseract_complete`: BOOLEAN
- `images_processed`: BOOLEAN
- `evaluation_complete`: BOOLEAN
- `splitter_complete`: BOOLEAN
- `marker_complete`: BOOLEAN

#### **Current Implementation:**

| Feature | Required | Current | Status |
|---------|----------|---------|--------|
| 80 attributes (1-8 system, 9-80 user) | ✅ | ✅ (fully implemented) | ✅ COMPLETE |
| `ocr_method` field | ✅ | ❌ | ⚠️ CRITICAL |
| Store all 3 OCR text results (attr 2-4) | ✅ | ❌ | ⚠️ CRITICAL |
| Store all 3 confidence scores (attr 5-7) | ✅ | ❌ | ⚠️ CRITICAL |
| `svg_code` in images table | ✅ | ❌ | ⚠️ CRITICAL |
| `structured_json` in images table | ✅ | ❌ | ⚠️ CRITICAL |
| OCR completion flags in processing_state | ✅ | ❌ | ⚠️ CRITICAL |

---

### **4. API Endpoints**

#### **Requirements:**

**OCR Endpoints (Sequential):**
- `POST /api/ocr/paddleocr` - Start PaddleOCR processing
- `POST /api/ocr/surya` - Start Surya OCR processing
- `POST /api/ocr/tesseract` - Start Tesseract processing
- `POST /api/evaluate-split-mark` - Evaluate, split, and mark

**Image Analysis:**
- Uses Claude Sonnet 4.5 API during FIRST OCR run only
- Generates SVG code from structured_json

#### **Current Implementation:**

| Endpoint | Required | Current | Status |
|----------|----------|---------|--------|
| POST /api/ocr/paddleocr | ✅ | ❌ | ⚠️ MISSING |
| POST /api/ocr/surya | ✅ | ❌ | ⚠️ MISSING |
| POST /api/ocr/tesseract | ✅ | ❌ | ⚠️ MISSING |
| POST /api/evaluate-split-mark | ✅ | ❌ | ⚠️ MISSING |
| POST /api/start-processing | ❌ (wrong approach) | ✅ | ⚠️ WRONG |
| Claude Sonnet 4.5 integration | ✅ | ❌ | ⚠️ MISSING |
| SVG generation service | ✅ | ❌ | ⚠️ MISSING |

---

## 🔄 Required Changes

### **Phase 1: Frontend (Upload Page)**

**Priority:** HIGH

**Files to Update:**
- `03-code/src/frontend/templates/upload.html`

**Changes:**
1. ✅ **DONE:** Update LLM model dropdown (GPT-4o → Claude Sonnet 4.5)
2. ⚠️ **TODO:** Remove OCR mode dropdown
3. ⚠️ **TODO:** Add 4 sequential OCR buttons (Step 5)
4. ⚠️ **TODO:** Add 40-attribute configuration section (Step 3)
   - Show attributes 1-8 as locked/read-only with system-reserved labels
   - Show attributes 9-40 as editable user-defined fields
5. ⚠️ **TODO:** Add partial processing checkbox
6. ⚠️ **TODO:** Add book-specific instructions text area
7. ⚠️ **TODO:** Add processing presets buttons (Quick Scan, Balanced, Deep Analysis, Custom)

---

### **Phase 2: Backend (API Routes)**

**Priority:** HIGH

**Files to Create/Update:**
- `03-code/src/api/routes/ocr.py` (NEW)
- `03-code/src/services/ocr_sequential.py` (NEW)
- `03-code/src/services/image_analyzer.py` (NEW - Claude Sonnet 4.5)
- `03-code/src/services/svg_generator.py` (NEW)

**Changes:**
1. ⚠️ **TODO:** Create sequential OCR service
2. ⚠️ **TODO:** Create 3 OCR endpoints (PaddleOCR, Surya, Tesseract)
3. ⚠️ **TODO:** Create evaluate/split/mark endpoint
4. ⚠️ **TODO:** Integrate Claude Sonnet 4.5 API for image analysis
5. ⚠️ **TODO:** Implement SVG generation from structured_json
6. ⚠️ **TODO:** Add GPU memory management (sequential load/unload)
7. ⚠️ **TODO:** Store all 3 OCR results in attributes 2-4
8. ⚠️ **TODO:** Store all 3 confidence scores in attributes 5-7

---

### **Phase 3: Database Schema Updates**

**Priority:** HIGH

**Files to Update:**
- `03-code/src/database/models/knowledge_units.py`
- `03-code/src/database/models/images.py`
- `03-code/src/database/models/processing_state.py`
- `03-code/scripts/init_db.py`

**Changes:**
1. ⚠️ **TODO:** Add `ocr_method` field to knowledge_units
2. ⚠️ **TODO:** Expand attributes to 40 (attr1_value through attr40_value)
3. ⚠️ **TODO:** Add `svg_code` and `structured_json` to images table
4. ⚠️ **TODO:** Add OCR completion flags to processing_state
5. ⚠️ **TODO:** Create book{N}_attribute_keys table with system-reserved flags

---

### **Phase 4: Frontend JavaScript**

**Priority:** MEDIUM

**Files to Update:**
- `03-code/src/frontend/static/js/upload.js`

**Changes:**
1. ⚠️ **TODO:** Add event handlers for 4 OCR buttons
2. ⚠️ **TODO:** Add WebSocket progress monitoring per OCR engine
3. ⚠️ **TODO:** Add attribute configuration form validation
4. ⚠️ **TODO:** Add preset button functionality

---

## 📊 Impact Analysis

### **Current State:**
- **Implemented:** 16/45 chunks (CHUNK-030 through CHUNK-045)
- **Tests Passing:** 91/91 tests
- **Server:** Running on port 7777
- **Alignment with Architecture:** ⚠️ **~30% aligned** (major gaps)

### **Required Work:**
- **Frontend Redesign:** ~1-2 days (upload page complete redesign)
- **Backend Refactor:** ~2-3 days (sequential OCR, Claude integration, SVG generation)
- **Database Migration:** ~1 day (schema updates, attribute expansion)
- **Testing:** ~1-2 days (new tests for sequential OCR flow)
- **Total Estimate:** 5-8 days of development

---

## ✅ Recommendations

### **Option 1: Complete Redesign (Recommended)**

**Pros:**
- ✅ Aligns 100% with approved architecture
- ✅ User has full control over OCR engines
- ✅ Best quality results (stores all 3 OCR attempts)
- ✅ SVG generation for diagrams
- ✅ Future-proof

**Cons:**
- ⚠️ Requires significant refactoring
- ⚠️ 5-8 days of work
- ⚠️ Need to rewrite tests

**Action Plan:**
1. Start with frontend (upload page redesign)
2. Add sequential OCR API endpoints
3. Integrate Claude Sonnet 4.5
4. Implement SVG generation
5. Update database schema
6. Comprehensive testing

---

### **Option 2: Hybrid Approach (Quick Fix)**

**Pros:**
- ✅ Faster to implement (2-3 days)
- ✅ Keeps current automatic OCR fallback
- ✅ Adds Claude Sonnet 4.5 integration

**Cons:**
- ⚠️ Does not align with approved architecture
- ⚠️ Missing user control over OCR engines
- ⚠️ Missing 40-attribute configuration
- ⚠️ Missing SVG generation

**Action Plan:**
1. ✅ DONE: Fix LLM model (GPT → Claude Sonnet 4.5)
2. Add Claude API integration for image analysis
3. Add SVG generation (basic)
4. Expand attributes to 40
5. Keep automatic OCR fallback

---

## 🎯 Next Steps

**Immediate Actions:**

1. **User Decision Required:**
   - Choose between Option 1 (complete redesign) or Option 2 (hybrid)
   - Confirm prioritization and timeline

2. **If Option 1 (Recommended):**
   - Start with upload page redesign (4 OCR buttons, 80 attributes)
   - Implement sequential OCR API endpoints
   - Integrate Claude Sonnet 4.5 with SVG generation

3. **If Option 2:**
   - Focus on Claude Sonnet 4.5 integration first
   - Add basic SVG generation
   - Expand attribute configuration

---

**Report Generated:** 2025-11-11
**Status:** ⚠️ Awaiting user decision on redesign approach
