# Requirement 8: Per-Book YOLO Model Fine-Tuning

**Feature:** Book-Specific YOLO Model Training and Storage  
**Created:** January 30, 2026  
**Status:** Requirements Complete - Ready for Implementation  
**Priority:** High

---

## 1. Overview

Implement per-book YOLO model storage and selection, allowing each book to have its own fine-tuned layout detection model. This addresses the fact that different books have different layouts and require customized models for optimal detection.

**Current Problem:** The existing implementation saves trained models to a shared location (`models/layout_detection/doclayout_yolo.pt`), meaning training on one book overwrites the model used by all books.

**Solution:** Hybrid approach with global base model + book-specific fine-tuned versions, with model path stored in database.

---

## 2. Clarification Questions & Answers

### Q1: Model Storage Approach

**Question:** When you train a YOLO model on Book A's corrections, should the resulting trained model be:

| Option | Description |
|--------|-------------|
| A | Book-specific - Each book gets its own trained model file |
| B | Global with book contributions - One shared model progressively improved |
| **✅ C** | **Hybrid - Start with global base model, allow book-specific fine-tuned versions** |
| D | Other approach |

**Answer:** C - Hybrid approach. Start with a global base model, but allow creating book-specific fine-tuned versions when needed. User can choose which model to use per book.

---

### Q2: Model Selection UI Location

**Question:** Where should the user select which YOLO model to use for a book?

| Option | Description |
|--------|-------------|
| A | Book Settings page - Add dropdown for model selection |
| B | Layout Training page - Option after training completes |
| C | Auto-Slicer / Layout Review page - Prompt when running detection |
| D | Automatic - Use book-specific if exists, else global |
| **✅ E** | **Both A and B - Setting in Book Settings + prompt after training** |

**Answer:** E - Both locations:
- Book Settings page: "Layout Detection Model" dropdown
- Layout Training page: After training completes, prompt "Use this model for this book?"

---

### Q3: Cross-Book Model Sharing

**Question:** Should a book be able to use another book's trained model?

| Option | Description |
|--------|-------------|
| A | Yes - Show all books' models in dropdown |
| B | No - Only global or own model |
| **✅ C** | **Yes, but with copy - Copy another book's model as starting point** |

**Answer:** C - User can "copy" another book's model to use as this book's starting point, then optionally train further on this book's corrections. This creates an independent copy, not a reference.

---

### Q4: Model Deletion on Book Delete

**Question:** When a book is deleted, what should happen to its trained YOLO model?

| Option | Description |
|--------|-------------|
| A | Delete the model automatically |
| B | Keep the model file |
| **✅ C** | **Ask user - Checkbox in delete confirmation** |

**Answer:** C - Add checkbox in delete confirmation dialog: "☐ Also delete trained YOLO model" (default: checked). This gives user control over whether to preserve the model.

---

### Q5: Model Storage Location

**Question:** Where should book-specific YOLO models be stored on disk?

| Option | Description |
|--------|-------------|
| A | Inside models folder by book ID |
| B | Inside book's data folder |
| **✅ C+D** | **Centralized with naming + Database reference** |

**Answer:** C and D combined:
- **File location:** `models/layout_detection/book_{id}_yolo.pt` (all models in one folder)
- **Database:** Store model path in `books_metadata` table column `yolo_model_path`
- This allows easy management while maintaining flexibility

---

## 3. Feature Details

### 3.1 Model Storage Structure

```
models/
├── layout_detection/
│   ├── doclayout_yolo.pt          # Global base model
│   ├── book_1_yolo.pt             # Book 1's fine-tuned model
│   ├── book_2_yolo.pt             # Book 2's fine-tuned model
│   └── ...
├── training_data/
│   ├── book_1/                    # Training data for book 1
│   │   ├── images/
│   │   ├── labels/
│   │   └── runs/                  # Training job history
│   └── book_2/
│       └── ...
└── backups/
    └── ...                        # Model backups before training
```

### 3.2 Database Schema Changes

Add column to `books_metadata`:
```sql
ALTER TABLE books_metadata ADD COLUMN IF NOT EXISTS
    yolo_model_path TEXT DEFAULT NULL;
    -- NULL = use global model
    -- Path = use book-specific model
```

### 3.3 Model Selection Logic

When running layout detection for a book:
1. Check `books_metadata.yolo_model_path` for the book
2. If NULL or empty → use global model (`models/layout_detection/doclayout_yolo.pt`)
3. If path set → use book-specific model at that path
4. If path set but file missing → fall back to global with warning

### 3.4 Book Settings UI

Add "Layout Detection" section to Book Settings page:
- **Model dropdown:**
  - "Global Base Model" (default)
  - "This Book's Model" (if trained, shows training date)
- **Copy from another book button:**
  - Opens modal with list of books that have trained models
  - "Copy" button copies model file and sets path
- **Model info display:**
  - Training date (if book-specific)
  - Number of pages used for training
  - Model file size

### 3.5 Post-Training Prompt

After training completes on Layout Training page:
- Show success modal with training results
- Include checkbox: "☑ Use this model for this book" (default: checked)
- If checked, update `books_metadata.yolo_model_path`

### 3.6 Delete Book Integration

Update delete confirmation modal:
- Add checkbox: "☐ Also delete trained YOLO model" (default: checked)
- Only show if book has a trained model (`yolo_model_path` is set)
- If checked, delete the model file when deleting book

---

## 4. User Stories

### US-8.1: Train Book-Specific Model
**As a** user  
**I want to** train a YOLO model specifically for my book's layout  
**So that** layout detection is optimized for this book's unique format

**Acceptance Criteria:**
- [ ] Training saves model to `models/layout_detection/book_{id}_yolo.pt`
- [ ] Model path is stored in `books_metadata.yolo_model_path`
- [ ] Post-training prompt asks if user wants to use the new model

### US-8.2: Select Model in Book Settings
**As a** user  
**I want to** choose which YOLO model to use for my book  
**So that** I can switch between global and book-specific models

**Acceptance Criteria:**
- [ ] Book Settings shows "Layout Detection Model" dropdown
- [ ] Options: "Global Base Model", "This Book's Model" (if exists)
- [ ] Selection updates `books_metadata.yolo_model_path`

### US-8.3: Copy Model from Another Book
**As a** user  
**I want to** copy another book's trained model to use as my starting point  
**So that** I can leverage similar book layouts without training from scratch

**Acceptance Criteria:**
- [ ] "Copy from another book" button in Book Settings
- [ ] Modal shows list of books with trained models
- [ ] Copying creates independent file copy
- [ ] Can optionally train further on this book's corrections

### US-8.4: Delete Model with Book
**As a** user  
**I want to** choose whether to delete the trained model when deleting a book  
**So that** I can preserve useful models if needed

**Acceptance Criteria:**
- [ ] Delete confirmation shows "Also delete trained YOLO model" checkbox
- [ ] Checkbox only appears if book has trained model
- [ ] Default: checked (delete model)
- [ ] If unchecked, model file is preserved

### US-8.5: Automatic Model Loading
**As a** user  
**I want** layout detection to automatically use my book's trained model  
**So that** I don't have to manually select it each time

**Acceptance Criteria:**
- [ ] Layout detection checks `yolo_model_path` before running
- [ ] Uses book-specific model if path is set and file exists
- [ ] Falls back to global model if path is NULL or file missing
- [ ] Shows warning if configured model file is missing

---

## 5. API Changes

### 5.1 New Endpoints

#### GET /api/books/{book_id}/yolo-model
Get YOLO model info for a book.
```json
Response:
{
    "book_id": 1,
    "model_type": "book_specific",  // or "global"
    "model_path": "models/layout_detection/book_1_yolo.pt",
    "model_exists": true,
    "model_size_bytes": 45678901,
    "trained_at": "2026-01-30T10:30:00Z",
    "training_pages": 50
}
```

#### PUT /api/books/{book_id}/yolo-model
Set YOLO model for a book.
```json
Request:
{
    "model_type": "book_specific"  // or "global"
}

Response:
{
    "success": true,
    "model_path": "models/layout_detection/book_1_yolo.pt"
}
```

#### POST /api/books/{book_id}/copy-yolo-model
Copy another book's model.
```json
Request:
{
    "source_book_id": 2
}

Response:
{
    "success": true,
    "source_path": "models/layout_detection/book_2_yolo.pt",
    "target_path": "models/layout_detection/book_1_yolo.pt",
    "copied_size_bytes": 45678901
}
```

#### GET /api/books/with-yolo-models
List books that have trained models (for copy modal).
```json
Response:
{
    "books": [
        {
            "book_id": 2,
            "book_name": "Physics 101",
            "model_path": "models/layout_detection/book_2_yolo.pt",
            "trained_at": "2026-01-25T14:00:00Z"
        }
    ]
}
```

### 5.2 Modified Endpoints

#### DELETE /api/books/{book_id}
Add `delete_yolo_model` parameter:
```json
Request:
{
    "delete_chromadb": true,
    "delete_yolo_model": true,  // NEW
    "confirmation_code": "7294"
}
```

---

## 6. Implementation Tasks

### Phase 1: Database & Backend
1. Add `yolo_model_path` column to `books_metadata`
2. Modify `yolo_training_service.py` to save models per-book
3. Modify `layout_detection_service.py` to load book-specific model
4. Add new API endpoints for model management
5. Update delete API to handle YOLO model deletion

### Phase 2: Frontend - Book Settings
6. Add "Layout Detection Model" section to Book Settings
7. Implement model dropdown (Global / Book-Specific)
8. Add "Copy from another book" button and modal
9. Display model info (training date, size, etc.)

### Phase 3: Frontend - Training Integration
10. Update Layout Training page post-training flow
11. Add "Use this model" checkbox to success modal
12. Update delete confirmation to include YOLO model checkbox

### Phase 4: Testing
13. Test model training saves to correct location
14. Test model selection in Book Settings
15. Test model copy between books
16. Test model deletion with book
17. Test fallback to global model

---

## 7. Dependencies

- Existing: `yolo_training_service.py`, `layout_detection_service.py`
- Existing: `books_metadata` table
- Existing: Book Settings page, Layout Training page
- Existing: Delete book functionality (Requirement 6)

---

## 8. Notes

- Model files are typically 40-100MB each
- Training requires GPU for reasonable speed
- Global model should never be deleted
- Consider adding model versioning in future
