# Duplicate File Upload Prevention - Test Plan

**Date:** 2025-11-11
**Test Engineer:** Claude Code
**Status:** Ready for Implementation

---

## Test Summary

| Category | Test Count | Priority |
|----------|------------|----------|
| Unit Tests | 12 | High |
| Integration Tests | 8 | High |
| UI Tests | 6 | Medium |
| **Total** | **26** | - |

---

## Unit Tests

### **Test Suite 1: DuplicateCheckService**

**File:** `04-tests/unit/test_duplicate_check_service.py`

#### **Test 1.1: check_duplicate - No Duplicate Exists**
```python
def test_check_duplicate_no_match():
    """Test duplicate check when no matching file exists"""
    service = DuplicateCheckService()
    result = service.check_duplicate("newfile.pdf", 1048576)

    assert result.is_duplicate == False
    assert result.action == 'allow'
    assert result.existing_book_id is None
```

#### **Test 1.2: check_duplicate - Duplicate Exists, File Readable**
```python
def test_check_duplicate_exists_readable():
    """Test duplicate check when file exists and is readable"""
    # Setup: Create book with readable file
    book_id = create_test_book("test.pdf", 1048576, "/valid/path/test.pdf")

    service = DuplicateCheckService()
    result = service.check_duplicate("test.pdf", 1048576)

    assert result.is_duplicate == True
    assert result.action == 'reject'
    assert result.existing_book_id == book_id
    assert "already been uploaded" in result.message
```

#### **Test 1.3: check_duplicate - Duplicate Exists, File Not Readable**
```python
def test_check_duplicate_exists_corrupted():
    """Test duplicate check when file exists but is corrupted"""
    # Setup: Create book with invalid file path
    book_id = create_test_book("test.pdf", 1048576, "/invalid/path/test.pdf")

    service = DuplicateCheckService()
    result = service.check_duplicate("test.pdf", 1048576)

    assert result.is_duplicate == True
    assert result.action == 'overwrite'
    assert result.existing_book_id == book_id
    assert "corrupted" in result.message.lower()
```

#### **Test 1.4: is_file_readable - File Exists**
```python
def test_is_file_readable_valid_file(tmp_path):
    """Test file readability check with valid file"""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"PDF content here")

    service = DuplicateCheckService()
    assert service.is_file_readable(str(test_file)) == True
```

#### **Test 1.5: is_file_readable - File Does Not Exist**
```python
def test_is_file_readable_missing_file():
    """Test file readability check with missing file"""
    service = DuplicateCheckService()
    assert service.is_file_readable("/nonexistent/file.pdf") == False
```

#### **Test 1.6: is_file_readable - File Not Readable (Permissions)**
```python
def test_is_file_readable_no_permissions(tmp_path):
    """Test file readability check with permission denied"""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"PDF content")
    test_file.chmod(0o000)  # Remove all permissions

    service = DuplicateCheckService()
    assert service.is_file_readable(str(test_file)) == False
```

#### **Test 1.7: get_uploaded_books - Returns List**
```python
def test_get_uploaded_books():
    """Test retrieval of uploaded books list"""
    # Setup: Create 3 test books
    create_test_book("book1.pdf", 1000, "/path/book1.pdf")
    create_test_book("book2.pdf", 2000, "/path/book2.pdf")
    create_test_book("book3.pdf", 3000, "/path/book3.pdf")

    service = DuplicateCheckService()
    books = service.get_uploaded_books(limit=10, offset=0)

    assert len(books) == 3
    assert books[0].book_name == "book3.pdf"  # Most recent first
```

#### **Test 1.8: get_uploaded_books - Pagination**
```python
def test_get_uploaded_books_pagination():
    """Test pagination of uploaded books"""
    # Setup: Create 15 test books
    for i in range(15):
        create_test_book(f"book{i}.pdf", 1000 + i, f"/path/book{i}.pdf")

    service = DuplicateCheckService()

    # First page
    page1 = service.get_uploaded_books(limit=10, offset=0)
    assert len(page1) == 10

    # Second page
    page2 = service.get_uploaded_books(limit=10, offset=10)
    assert len(page2) == 5
```

---

### **Test Suite 2: File Storage Management**

**File:** `04-tests/unit/test_file_storage.py`

#### **Test 2.1: File Path Sanitization**
```python
def test_sanitize_file_path():
    """Test path traversal protection"""
    from src.services.duplicate_check_service import sanitize_file_path

    # Should reject path traversal attempts
    with pytest.raises(ValueError):
        sanitize_file_path("../../../etc/passwd")

    # Should accept valid filename
    result = sanitize_file_path("valid_file.pdf")
    assert result == "valid_file.pdf"
```

#### **Test 2.2: Storage Directory Creation**
```python
def test_create_storage_directory(tmp_path):
    """Test automatic storage directory creation"""
    from src.services.duplicate_check_service import ensure_storage_dir

    storage_path = tmp_path / "uploads"
    ensure_storage_dir(str(storage_path))

    assert storage_path.exists()
    assert storage_path.is_dir()
```

#### **Test 2.3: File Permission Setting**
```python
def test_set_file_permissions(tmp_path):
    """Test file permissions are set correctly"""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"content")

    from src.services.duplicate_check_service import set_secure_permissions
    set_secure_permissions(str(test_file))

    # Check permissions are 0o600 (rw-------)
    import stat
    mode = test_file.stat().st_mode
    assert stat.S_IMODE(mode) == 0o600
```

#### **Test 2.4: Calculate File Hash**
```python
def test_calculate_file_hash(tmp_path):
    """Test SHA-256 hash calculation"""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"Test content for hashing")

    from src.services.duplicate_check_service import calculate_file_hash
    hash_value = calculate_file_hash(str(test_file))

    assert len(hash_value) == 64  # SHA-256 is 64 hex characters
    assert hash_value.isalnum()
```

---

## Integration Tests

### **Test Suite 3: Upload API with Duplicate Check**

**File:** `04-tests/integration/test_upload_duplicate_check.py`

#### **Test 3.1: Upload New File (No Duplicate)**
```python
@pytest.mark.asyncio
async def test_upload_new_file_success(test_client):
    """Test successful upload of new file"""
    with open("test_files/sample.pdf", "rb") as f:
        response = test_client.post(
            "/api/upload",
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"book_name": "Sample Book"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] > 0
    assert data["message"] == "Upload successful"
```

#### **Test 3.2: Upload Duplicate File (Readable)**
```python
@pytest.mark.asyncio
async def test_upload_duplicate_readable_rejected(test_client):
    """Test duplicate upload is rejected when file is readable"""
    # First upload
    with open("test_files/sample.pdf", "rb") as f:
        response1 = test_client.post(
            "/api/upload",
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"book_name": "Sample Book"}
        )
    assert response1.status_code == 200

    # Second upload (duplicate)
    with open("test_files/sample.pdf", "rb") as f:
        response2 = test_client.post(
            "/api/upload",
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"book_name": "Sample Book"}
        )

    assert response2.status_code == 409  # Conflict
    data = response2.json()
    assert data["detail"]["error"] == "duplicate_file"
    assert "already been uploaded" in data["detail"]["message"]
```

#### **Test 3.3: Upload Duplicate File (Corrupted - Allow Overwrite)**
```python
@pytest.mark.asyncio
async def test_upload_duplicate_corrupted_overwrite(test_client, monkeypatch):
    """Test duplicate upload allowed when original is corrupted"""
    # First upload
    with open("test_files/sample.pdf", "rb") as f:
        response1 = test_client.post(
            "/api/upload",
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"book_name": "Sample Book"}
        )
    book_id = response1.json()["book_id"]

    # Simulate file corruption (delete the file)
    db_delete_file_path(book_id)

    # Second upload (should overwrite)
    with open("test_files/sample.pdf", "rb") as f:
        response2 = test_client.post(
            "/api/upload",
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"book_name": "Sample Book"}
        )

    assert response2.status_code == 200
    data = response2.json()
    assert data["book_id"] == book_id  # Same book ID
    assert "overwrite" in data["message"].lower()
```

#### **Test 3.4: Upload Similar Name, Different Size**
```python
@pytest.mark.asyncio
async def test_upload_same_name_different_size(test_client):
    """Test that same filename with different size is NOT duplicate"""
    # Upload small file
    small_content = b"Small PDF content"
    response1 = test_client.post(
        "/api/upload",
        files={"file": ("sample.pdf", small_content, "application/pdf")},
        data={"book_name": "Sample Book"}
    )
    assert response1.status_code == 200

    # Upload larger file with same name
    large_content = b"Large PDF content" * 1000
    response2 = test_client.post(
        "/api/upload",
        files={"file": ("sample.pdf", large_content, "application/pdf")},
        data={"book_name": "Sample Book Large"}
    )

    assert response2.status_code == 200  # Should succeed (not duplicate)
```

---

### **Test Suite 4: List Books API**

**File:** `04-tests/integration/test_list_books_api.py`

#### **Test 4.1: List Books - Empty Database**
```python
@pytest.mark.asyncio
async def test_list_books_empty(test_client):
    """Test list books when no books uploaded"""
    response = test_client.get("/api/books/list")

    assert response.status_code == 200
    data = response.json()
    assert data["books"] == []
    assert data["total"] == 0
```

#### **Test 4.2: List Books - Multiple Books**
```python
@pytest.mark.asyncio
async def test_list_books_multiple(test_client):
    """Test list books returns all uploaded books"""
    # Upload 3 books
    for i in range(3):
        with open(f"test_files/book{i}.pdf", "rb") as f:
            test_client.post(
                "/api/upload",
                files={"file": (f"book{i}.pdf", f, "application/pdf")},
                data={"book_name": f"Book {i}"}
            )

    response = test_client.get("/api/books/list")

    assert response.status_code == 200
    data = response.json()
    assert len(data["books"]) == 3
    assert data["total"] == 3
```

#### **Test 4.3: List Books - Pagination**
```python
@pytest.mark.asyncio
async def test_list_books_pagination(test_client):
    """Test list books pagination"""
    # Upload 15 books
    for i in range(15):
        upload_test_book(test_client, f"book{i}.pdf")

    # Get first page
    response1 = test_client.get("/api/books/list?limit=10&offset=0")
    data1 = response1.json()
    assert len(data1["books"]) == 10
    assert data1["total"] == 15

    # Get second page
    response2 = test_client.get("/api/books/list?limit=10&offset=10")
    data2 = response2.json()
    assert len(data2["books"]) == 5
```

#### **Test 4.4: List Books - File Readability Status**
```python
@pytest.mark.asyncio
async def test_list_books_readability_status(test_client):
    """Test that list includes file readability status"""
    # Upload book
    with open("test_files/sample.pdf", "rb") as f:
        response = test_client.post(
            "/api/upload",
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"book_name": "Sample Book"}
        )

    # List books
    response = test_client.get("/api/books/list")
    data = response.json()

    assert len(data["books"]) == 1
    book = data["books"][0]
    assert "file_readable" in book
    assert book["file_readable"] == True
```

---

## UI/Frontend Tests

### **Test Suite 5: Upload Page UI**

**File:** `04-tests/ui/test_upload_page_duplicate.py`

#### **Test 5.1: Display Uploaded Files Section**
```python
def test_uploaded_files_section_visible(selenium):
    """Test that uploaded files section is visible on page"""
    selenium.get("http://localhost:7777/upload")

    section = selenium.find_element_by_class("uploaded-files-section")
    assert section.is_displayed()
```

#### **Test 5.2: Load and Display Uploaded Files**
```python
def test_load_uploaded_files(selenium, setup_test_books):
    """Test that uploaded files are loaded and displayed"""
    selenium.get("http://localhost:7777/upload")

    # Wait for files to load
    wait = WebDriverWait(selenium, 10)
    files_container = wait.until(
        EC.presence_of_element_located((By.ID, "uploaded-files-container"))
    )

    # Check that books are displayed
    book_cards = files_container.find_elements_by_class("book-card")
    assert len(book_cards) > 0
```

#### **Test 5.3: Show Duplicate Warning Modal**
```python
def test_duplicate_warning_modal(selenium, setup_duplicate_book):
    """Test that duplicate warning modal appears"""
    selenium.get("http://localhost:7777/upload")

    # Try to upload duplicate file
    upload_file_input = selenium.find_element_by_id("file-input")
    upload_file_input.send_keys("/path/to/duplicate.pdf")

    upload_button = selenium.find_element_by_id("upload-button")
    upload_button.click()

    # Wait for modal
    wait = WebDriverWait(selenium, 10)
    modal = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "duplicate-warning"))
    )

    assert modal.is_displayed()
    assert "already been uploaded" in modal.text
```

#### **Test 5.4: Duplicate Modal - Cancel Action**
```python
def test_duplicate_modal_cancel(selenium):
    """Test canceling duplicate upload"""
    # ... trigger duplicate modal ...

    cancel_button = selenium.find_element_by_xpath("//button[text()='Cancel']")
    cancel_button.click()

    # Modal should close
    wait = WebDriverWait(selenium, 5)
    wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "duplicate-warning")))
```

#### **Test 5.5: Duplicate Modal - View Existing Book**
```python
def test_duplicate_modal_view_existing(selenium):
    """Test viewing existing book from duplicate modal"""
    # ... trigger duplicate modal with book_id=1 ...

    view_button = selenium.find_element_by_xpath("//button[contains(text(), 'View Existing')]")
    view_button.click()

    # Should redirect to book page
    wait = WebDriverWait(selenium, 10)
    wait.until(EC.url_contains("/books/1"))
```

#### **Test 5.6: Upload Success Message**
```python
def test_upload_success_message(selenium):
    """Test success message after upload"""
    selenium.get("http://localhost:7777/upload")

    # Upload new file
    upload_file("/path/to/new_file.pdf")

    # Check for success message
    wait = WebDriverWait(selenium, 10)
    success_msg = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
    )

    assert "successfully" in success_msg.text.lower()
```

---

## Performance Tests

### **Test Suite 6: Performance Benchmarks**

**File:** `04-tests/performance/test_duplicate_check_performance.py`

#### **Test 6.1: Duplicate Check Performance**
```python
def test_duplicate_check_performance():
    """Test that duplicate check completes in < 100ms"""
    import time

    service = DuplicateCheckService()

    start = time.time()
    result = service.check_duplicate("test.pdf", 1048576)
    end = time.time()

    elapsed_ms = (end - start) * 1000
    assert elapsed_ms < 100, f"Duplicate check took {elapsed_ms}ms (target: <100ms)"
```

#### **Test 6.2: File Readability Check Performance**
```python
def test_readability_check_performance(tmp_path):
    """Test that readability check completes in < 500ms"""
    # Create large file (10MB)
    test_file = tmp_path / "large.pdf"
    test_file.write_bytes(b"x" * 10_000_000)

    import time
    service = DuplicateCheckService()

    start = time.time()
    result = service.is_file_readable(str(test_file))
    end = time.time()

    elapsed_ms = (end - start) * 1000
    assert elapsed_ms < 500, f"Readability check took {elapsed_ms}ms (target: <500ms)"
```

---

## Test Execution Plan

### **Phase 1: Unit Tests (Day 1)**
```bash
pytest 04-tests/unit/test_duplicate_check_service.py -v
pytest 04-tests/unit/test_file_storage.py -v
```

### **Phase 2: Integration Tests (Day 2)**
```bash
pytest 04-tests/integration/test_upload_duplicate_check.py -v
pytest 04-tests/integration/test_list_books_api.py -v
```

### **Phase 3: UI Tests (Day 3)**
```bash
pytest 04-tests/ui/test_upload_page_duplicate.py -v
```

### **Phase 4: Performance Tests (Day 3)**
```bash
pytest 04-tests/performance/test_duplicate_check_performance.py -v
```

---

## Test Coverage Goals

- **Unit Tests:** > 90% code coverage
- **Integration Tests:** > 80% API coverage
- **UI Tests:** All critical user flows covered
- **Performance:** All benchmarks met

---

## Bug Tracking Template

```markdown
**Bug ID:** BUG-DUP-001
**Title:** [Brief description]
**Severity:** Critical | High | Medium | Low
**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Expected:** [What should happen]
**Actual:** [What actually happens]
**Environment:** Development | Staging | Production
**Test:** [Which test caught this]
```

---

**Test Plan Status:** ✅ COMPLETE
**Total Test Cases:** 26
**Next Phase:** Implementation
