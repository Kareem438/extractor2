# Image Clip Tables Documentation

## Overview
Two new tables have been added to each book's schema to store user-selected image clips from the verify-pages interface:

1. **`raw_{table_prefix}_paragraph_images`** - For paragraph selections
2. **`raw_{table_prefix}_diagram_images`** - For diagram selections

## Table Schema

Both tables share the same structure:

### Fields

#### Primary Key
- **`id`** (SERIAL PRIMARY KEY) - Auto-incrementing unique identifier

#### Foreign Key & Page Reference
- **`raw_page_id`** (INTEGER NOT NULL) - References `raw_{table_prefix}_pages(id)`
- **`page_number`** (INTEGER NOT NULL) - Page number for quick filtering
- **Foreign Key Constraint**: ON DELETE CASCADE (deleting a page deletes all its clips)

#### Selection Coordinates
Stores the original selection rectangle on the source page image:
- **`selection_x`** (INTEGER NOT NULL) - X coordinate of top-left corner
- **`selection_y`** (INTEGER NOT NULL) - Y coordinate of top-left corner
- **`selection_width`** (INTEGER NOT NULL) - Width of selection rectangle
- **`selection_height`** (INTEGER NOT NULL) - Height of selection rectangle

#### Cropped Image Data
- **`image_data`** (BYTEA NOT NULL) - Binary image data (PNG format)
- **`image_format`** (VARCHAR(20) NOT NULL DEFAULT 'png') - Image format

#### Image Dimensions
Dimensions of the cropped image itself:
- **`image_width`** (INTEGER NOT NULL) - Width in pixels
- **`image_height`** (INTEGER NOT NULL) - Height in pixels
- **`image_size_bytes`** (INTEGER NOT NULL) - File size in bytes

#### User Notes/Description
- **`user_notes`** (TEXT) - User's notes about the selection
- **`description`** (TEXT) - Description of the selected area

#### Workflow Status
- **`approval_status`** (VARCHAR(50) DEFAULT 'pending') - Status: 'pending', 'approved', or 'rejected'

#### Category/Tags
- **`category`** (VARCHAR(100)) - Additional categorization beyond paragraph/diagram
- **`tags`** (TEXT[]) - Array of tag strings for flexible tagging

#### User/Session Info
- **`created_by`** (VARCHAR(100)) - Username or session ID who created the clip

#### Timestamps
- **`created_at`** (TIMESTAMP DEFAULT NOW()) - When the clip was created
- **`updated_at`** (TIMESTAMP DEFAULT NOW()) - When the clip was last modified

### Indexes

Four indexes are created for each table for optimal query performance:

1. **Page number index**: `idx_raw_{table_prefix}_para_img_page` / `idx_raw_{table_prefix}_diag_img_page`
   - Fast lookups by page number

2. **Foreign key index**: `idx_raw_{table_prefix}_para_img_raw_page` / `idx_raw_{table_prefix}_diag_img_raw_page`
   - Optimizes FK constraint checks

3. **Status index**: `idx_raw_{table_prefix}_para_img_status` / `idx_raw_{table_prefix}_diag_img_status`
   - Filter by approval status

4. **Category index**: `idx_raw_{table_prefix}_para_img_category` / `idx_raw_{table_prefix}_diag_img_category`
   - Filter by category

## Automatic Creation

These tables are automatically created when:
- A new book is uploaded (via `create_book_tables()` function)
- The tables are created right after `raw_pages` and `raw_knowledge_units` tables

## Migration for Existing Books

For books created before this update, the tables can be added by running:

```bash
python3 migrate_add_image_tables.py
```

Note: This migration script requires access to a master books registry table.

## Usage Flow

1. User opens verify-pages for a book
2. User selects a rectangular area on the page image
3. User chooses to save as "paragraph" or "diagram"
4. Image is cropped, scaled correctly, and saved to the appropriate table
5. Selection coordinates are preserved for reference
6. User can add notes, descriptions, tags, and categories
7. Workflow status allows for review/approval process

## Implementation Files

- **Table Schema**: `/mnt/h/12-extractor/03-code/src/database/table_creator.py`
  - `create_raw_paragraph_images_table(table_prefix: str)`
  - `create_raw_diagram_images_table(table_prefix: str)`
  - Updated `create_book_tables()` function

- **Migration Script**: `/mnt/h/12-extractor/03-code/migrate_add_image_tables.py`

## Next Steps

To complete the feature, you'll need to:

1. **Add API endpoints** to save/retrieve image clips
2. **Update verify-pages UI** to add "Save as Paragraph" and "Save as Diagram" buttons
3. **Implement save logic** that:
   - Converts the canvas data URL to binary
   - Gets the raw_page_id for the current page
   - Saves to the appropriate table with metadata
4. **Add listing/management UI** to view and manage saved clips
5. **Implement approval workflow** if needed

## Example Query

To retrieve all paragraph clips for page 5:

```sql
SELECT * FROM raw_book1_example_paragraph_images
WHERE page_number = 5
ORDER BY created_at DESC;
```

To get all approved diagram clips:

```sql
SELECT * FROM raw_book1_example_diagram_images
WHERE approval_status = 'approved'
ORDER BY created_at DESC;
```
