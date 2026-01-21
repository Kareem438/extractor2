# Database Naming Convention

**Created:** 2025-11-03
**Business Analyst Phase** - Requirements Clarification
**Status:** Confirmed by User

---

## 📋 Overview

This document defines the database table naming convention for the Knowledge Extraction System.

---

## 🏷️ Table Naming Convention

### **Format:**
```
book{N}_{sanitized_book_name}_{table_purpose}
```

### **Components:**
1. **Prefix:** `book{N}_` where N is a sequential integer (1, 2, 3, ...)
2. **Book Name:** Sanitized book name (lowercase, spaces replaced with underscores, special chars removed)
3. **Table Purpose:** Descriptive name of the table's purpose

### **Examples:**

#### Book 1: "Machine Learning Fundamentals.pdf"
- `book1_ml_fundamentals_knowledge_units` - Extracted text records with 40 attribute VALUE columns
- `book1_ml_fundamentals_images` - Extracted images with AI descriptions
- `book1_ml_fundamentals_processing_state` - Current processing status and agent states
- `book1_ml_fundamentals_settings` - Book-specific instructions and configuration
- `book1_ml_fundamentals_pages` - Page images with green rectangle markers
- `book1_ml_fundamentals_hierarchy` - Chapter/topic/sub-topic structure
- `book1_ml_fundamentals_attribute_keys` - **NEW:** Stores 40 attribute KEY NAMES (book-level configuration)

#### Book 2: "Deep Learning with Python.pdf"
- `book2_deep_learning_python_knowledge_units`
- `book2_deep_learning_python_images`
- `book2_deep_learning_python_processing_state`
- `book2_deep_learning_python_settings`
- `book2_deep_learning_python_pages`
- `book2_deep_learning_python_hierarchy`

#### Book 3: "تعلم الآلة للمبتدئين.pdf" (Arabic)
- `book3_arabic_ml_beginners_knowledge_units` - Transliterate or use generic name
- `book3_arabic_ml_beginners_images`
- `book3_arabic_ml_beginners_processing_state`
- `book3_arabic_ml_beginners_settings`
- `book3_arabic_ml_beginners_pages`
- `book3_arabic_ml_beginners_hierarchy`

---

## 📐 Naming Rules

1. **Sequential Book Numbers:**
   - Book numbers increment sequentially: 1, 2, 3, 4, ...
   - Never reuse book numbers (even if a book is deleted)
   - Book number assignment happens at upload time

2. **Book Name Sanitization:**
   - Convert to lowercase
   - Remove file extensions (.pdf, .docx, etc.)
   - Replace spaces with underscores
   - Remove special characters (except underscores)
   - Transliterate non-Latin characters to ASCII or use descriptive names
   - Limit to 50 characters maximum

3. **Table Purpose Names:**
   - Use descriptive, consistent names across all books
   - Standard table purposes:
     - `knowledge_units` - Main text extraction records (with 40 attr value columns)
     - `images` - Image records with AI descriptions
     - `processing_state` - Processing progress and agent states
     - `settings` - Book-specific instructions and config
     - `pages` - Page images with markers
     - `hierarchy` - Document structure (chapters/topics)
     - `attribute_keys` - **NEW:** Book-level attribute key names (1-40)

---

## 🔧 Database Location

- **Database Server:** Separate Windows machine on the same network
- **PostgreSQL:** Main relational database (with pgvector extension)
- **Chroma:** Vector database for similarity search
- **Connection:** Network connection from processing VM to database server

---

## 📊 Book Metadata Table

A single shared table tracks all books:

### `books_metadata`
| Column | Type | Description |
|--------|------|-------------|
| book_id | INTEGER PRIMARY KEY | Sequential book number (1, 2, 3, ...) |
| book_name | VARCHAR(255) | Original filename |
| sanitized_name | VARCHAR(100) | Sanitized name used in table names |
| table_prefix | VARCHAR(100) | Full prefix (e.g., "book1_ml_fundamentals") |
| upload_date | TIMESTAMP | When book was uploaded |
| file_type | VARCHAR(50) | Original file type (PDF, DOCX, etc.) |
| total_pages | INTEGER | Total pages in document |
| processing_status | VARCHAR(50) | Current status (uploading, processing, paused, complete) |
| language | VARCHAR(50) | Detected language(s) |

---

## 🎯 Benefits of This Convention

1. **Clear Identification:** Book number prefix makes it obvious which book data belongs to
2. **Easy Querying:** Can filter tables by book using `SHOW TABLES LIKE 'book1_%'`
3. **Isolated Data:** Each book's data is completely separate
4. **Scalable:** Works for unlimited number of books
5. **Pause/Resume:** Processing state tables are book-specific, enabling pause/resume per book
6. **Network Database:** All tables live on separate Windows database server

---

## 🚨 Important Notes

- **Never reuse book numbers** - Even if Book 3 is deleted, the next book is still Book 4
- **Table creation is atomic** - All tables for a book are created together during upload
- **Book ID assignment** - Happens when user clicks "Start Processing" on upload page
- **Sanitization consistency** - Same sanitization rules apply to all books

---

**Approved by:** User
**Date:** 2025-11-03
**Implementation:** To be detailed in Architecture phase
