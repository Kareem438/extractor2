# Requirements Document

## Introduction

This feature introduces three major capabilities for the book processing system:
1. **Multi-PDF Upload** - Allow multiple PDF files to be uploaded for the same book with flexible page mapping
2. **Cross-Book Attribute Access** - Allow books to read/write custom attributes of L1/L2 titles from other books
3. **Template Reference UI** - Enhanced pipeline-config UI with autocomplete for referencing book attributes using `@` syntax

These features enable complex multi-book workflows where books can share data and reference each other's attributes in pipeline configurations.

## Glossary

- **Book**: A collection of pages from one or more PDF files with associated metadata and title hierarchy
- **PDF_Upload**: A single PDF file associated with a book, with page mapping information
- **Page_Mapping**: The relationship between PDF page numbers and book page numbers
- **L1_Title**: Level 1 title in the book hierarchy (e.g., chapters)
- **L2_Title**: Level 2 title in the book hierarchy (e.g., sections within chapters)
- **Attribute**: A named or numbered data field associated with a title (attr1-attr200 for L1, attr1-attr150 for L2)
- **Writable_Range**: The range of attributes that can be written by other books (configurable per title)
- **Template_Reference**: A syntax for referencing attributes from other books using `@BookName.Level.TitleName.attrN(Name)` format
- **Cross_Book_Access_Log**: Audit trail recording all cross-book write operations
- **Pipeline_Rule**: A configuration rule that processes book data and can read/write attributes

## Requirements

### Requirement 1: Multi-PDF Upload

**User Story:** As a user, I want to upload multiple PDF files for a single book, so that I can handle books that are split across multiple files or have different page ranges.

#### Acceptance Criteria

1. WHEN a user uploads an additional PDF to an existing book, THE System SHALL accept the file and store it with page mapping information
2. WHEN uploading a PDF, THE System SHALL allow the user to specify "PDF page to start counting from" to skip cover pages
3. WHEN uploading a PDF, THE System SHALL allow the user to specify "Book page number to assign" for the starting page
4. WHEN uploading a PDF, THE System SHALL auto-detect and suggest the starting book page based on existing pages
5. WHEN uploading a PDF, THE System SHALL allow the user to override the auto-detected starting page
6. WHEN page ranges overlap between PDFs, THE System SHALL detect the overlapping pages and prompt the user to resolve them
7. WHEN resolving overlaps, THE System SHALL allow the user to choose which PDF version to keep for each overlapping page
8. WHEN resolving overlaps, THE System SHALL provide an "Apply same choice to all duplicates" option for batch decisions
9. THE System SHALL support sequential page ranges (no gaps), ranges with gaps, and overlapping ranges
10. WHEN accessing a book page, THE System SHALL resolve which PDF contains that page and calculate the correct PDF page number

### Requirement 2: Multi-PDF Upload UI

**User Story:** As a user, I want a clear interface for managing multiple PDFs per book, so that I can easily upload, view, and manage PDF files.

#### Acceptance Criteria

1. WHEN a book has at least one PDF uploaded, THE Upload_Page SHALL display an "Upload Additional PDF" button
2. WHEN uploading an additional PDF, THE System SHALL display a page mapping form with "Skip first N pages" and "Starting book page number" inputs
3. WHEN page overlaps are detected, THE System SHALL display an overlap resolution modal
4. THE Overlap_Modal SHALL show a list of overlapping pages with radio buttons for "Keep existing" or "Use new"
5. THE Overlap_Modal SHALL include a checkbox for "Apply same choice to all"
6. THE Upload_Page SHALL display a list of all PDFs for the book with their page ranges and status

### Requirement 3: Cross-Book Attribute Access

**User Story:** As a user, I want books to be able to read and write attributes from other books, so that I can create workflows that share data across multiple books.

#### Acceptance Criteria

1. THE System SHALL allow any book to read all attributes from any other book
2. THE System SHALL allow any book to write to other books' attributes within the configured writable range
3. WHEN defining a title in Auto-Slicer, THE System SHALL allow the user to configure the external writable range
4. THE System SHALL default the writable range to attributes 151-200 for L1 titles and 101-150 for L2 titles
5. IF a book attempts to write to an attribute outside the writable range, THEN THE System SHALL reject the write with an error
6. WHEN a cross-book write occurs, THE System SHALL log the operation with source book, pipeline rule, timestamp, and old/new values
7. THE System SHALL support a "counter increment" operation that reads the current value and adds 1

### Requirement 4: Cross-Book Writable Range Configuration

**User Story:** As a user, I want to configure which attributes can be written by other books, so that I can protect important data while allowing collaboration.

#### Acceptance Criteria

1. WHEN defining a title in Auto-Slicer, THE System SHALL display "External Writable Range" inputs (start and end)
2. THE System SHALL validate that writable range values are within valid attribute numbers (1-200 for L1, 1-150 for L2)
3. THE System SHALL persist the writable range configuration with the title definition
4. THE System SHALL display help text explaining cross-book write permissions

### Requirement 5: Cross-Book Access Audit Log

**User Story:** As a user, I want to see a log of all cross-book attribute writes, so that I can track changes and troubleshoot issues.

#### Acceptance Criteria

1. THE System SHALL provide a Cross-Book Access Log page
2. THE Access_Log_Page SHALL display a table with columns: Timestamp, Source Book, Target Book, Attribute, Operation, Old→New values
3. THE Access_Log_Page SHALL allow filtering by source book, target book, and date range
4. THE Access_Log_Page SHALL provide an export to CSV option
5. WHEN displaying log entries, THE System SHALL show the pipeline rule name and number that initiated the write

### Requirement 6: Template Reference Autocomplete

**User Story:** As a user, I want autocomplete when typing template references in the pipeline configurator, so that I can easily reference attributes from other books.

#### Acceptance Criteria

1. WHEN the user types `@` in the template editor, THE System SHALL display an inline autocomplete dropdown
2. THE Autocomplete_Dropdown SHALL show filtered results as the user continues typing
3. THE Autocomplete_Dropdown SHALL display results in format: `BookName > Level > Title > attr#(Name)`
4. THE Autocomplete_Dropdown SHALL support keyboard navigation (arrow keys, Enter to select)
5. THE Autocomplete_Dropdown SHALL include a "Browse All" button to open the full reference browser modal
6. WHEN the user selects a reference, THE System SHALL insert the complete reference syntax at the cursor position

### Requirement 7: Template Reference Browser Modal

**User Story:** As a user, I want a comprehensive browser for finding and selecting attribute references, so that I can explore available attributes across all books.

#### Acceptance Criteria

1. THE Reference_Browser_Modal SHALL display a tree view structure: Books → L1/L2 Titles → Attributes
2. THE Reference_Browser_Modal SHALL allow expanding/collapsing tree nodes
3. THE Reference_Browser_Modal SHALL include a search/filter box at the top
4. WHEN the user clicks an attribute, THE System SHALL insert the reference and close the modal
5. THE Reference_Browser_Modal SHALL indicate which attributes are writable with a visual marker
6. THE Reference_Browser_Modal SHALL display the writable range for each title

### Requirement 8: Template Reference Syntax and Display

**User Story:** As a user, I want template references to be clearly displayed with syntax highlighting, so that I can easily read and understand complex references.

#### Acceptance Criteria

1. THE System SHALL use the syntax format: `@BookName.Level.TitleName.attrN(AttributeName)`
2. THE System SHALL display attribute numbers always, with names in parentheses when defined (e.g., `attr22(EnergyLevel)`)
3. THE System SHALL apply syntax highlighting with different colors for: Book name (blue), Level (purple), Title name (green), Attribute (orange)
4. WHEN an attribute has no name defined, THE System SHALL display only the attribute number (e.g., `attr22`)

### Requirement 9: Pipeline Counter Increment Operation

**User Story:** As a user, I want to increment counter values across books, so that I can track counts and sequences in multi-book workflows.

#### Acceptance Criteria

1. THE Pipeline_Rule_Editor SHALL provide an operation type dropdown with "Set Value" and "Increment Counter" options
2. WHEN "Increment Counter" is selected, THE System SHALL read the current attribute value, add 1, and write the new value
3. IF the current value is not a valid number, THEN THE System SHALL treat it as 0 and write "1"
4. WHEN an increment operation occurs, THE System SHALL log it in the audit trail with operation type "increment"
