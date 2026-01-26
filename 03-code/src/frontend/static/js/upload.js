/**
 * CHUNK-040: JavaScript - Upload Handler (UPDATED for Sequential OCR)
 *
 * Handles file upload, preset selection, and sequential OCR buttons
 */

// File input handling
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const uploadForm = document.getElementById('upload-form');
const submitBtn = document.getElementById('submit-btn');
const uploadStatus = document.getElementById('upload-status');
const partialProcessing = document.getElementById('partial-processing');
const partialPages = document.getElementById('partial-pages');

// Book selection
const proceedUploadBtn = document.getElementById('proceed-upload-btn');
const proceedExistingBtn = document.getElementById('proceed-existing-btn');
const bookSelectionSection = document.getElementById('book-selection-section');
const existingBooksList = document.getElementById('existing-books-list');
const uploadMessage = document.getElementById('upload-message');

// Sequential OCR buttons
const easyOCRBtn = document.getElementById('start-easyocr');
const suryaBtn = document.getElementById('start-surya');
const tesseractBtn = document.getElementById('start-tesseract');
const evaluateBtn = document.getElementById('evaluate-split-mark');

// Preset buttons
const presetButtons = document.querySelectorAll('.preset-btn');

// State
let selectedExistingBookId = null;

// Enable/disable partial pages input based on checkbox
partialProcessing.addEventListener('change', (e) => {
    partialPages.disabled = !e.target.checked;
    if (!e.target.checked) {
        partialPages.value = '';
    }
});

// File selection
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        fileInfo.innerHTML = `
            <div class="file-selected">
                <strong>${file.name}</strong>
                <span>${sizeMB} MB</span>
            </div>
        `;
        // Enable proceed button
        proceedUploadBtn.disabled = false;
        uploadMessage.style.display = 'none';
    }
});

// Drag and drop
const fileLabel = document.querySelector('.file-label');

fileLabel.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileLabel.classList.add('drag-over');
});

fileLabel.addEventListener('dragleave', () => {
    fileLabel.classList.remove('drag-over');
});

fileLabel.addEventListener('drop', (e) => {
    e.preventDefault();
    fileLabel.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files;
        fileInput.dispatchEvent(new Event('change'));
    }
});

// Preset button handling
presetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active class from all buttons
        presetButtons.forEach(b => {
            b.style.background = 'white';
            b.style.color = '#2196F3';
        });

        // Add active class to clicked button
        btn.style.background = '#2196F3';
        btn.style.color = 'white';

        // Apply preset settings (future enhancement)
        const preset = btn.dataset.preset;
        console.log(`Preset selected: ${preset}`);
    });
});

// Proceed with New Upload button
proceedUploadBtn.addEventListener('click', async () => {
    const file = fileInput.files[0];
    if (!file) {
        showUploadMessage('Please select a file first', 'error');
        return;
    }

    // Validate file size (500MB max)
    if (file.size > 500 * 1024 * 1024) {
        showUploadMessage('File too large (max 500MB)', 'error');
        return;
    }

    proceedUploadBtn.disabled = true;
    proceedUploadBtn.textContent = 'Uploading...';

    try {
        // Upload file
        currentBookId = await uploadFile();
        if (currentBookId) {
            // Success - show configuration section
            bookSelectionSection.style.display = 'none';
            uploadForm.style.display = 'block';
            showUploadMessage('Upload successful! Configure settings below.', 'success');
            
            // Show scanning warning banner
            if (typeof showScanningWarning === 'function') {
                showScanningWarning(currentBookId);
            }
        }
    } catch (error) {
        showUploadMessage(error.message, 'error');
        proceedUploadBtn.disabled = false;
        proceedUploadBtn.textContent = '➡️ Proceed with New Upload';
    }
});

// Proceed with Existing Book button
proceedExistingBtn.addEventListener('click', () => {
    if (!selectedExistingBookId) {
        alert('Please select a book first');
        return;
    }

    currentBookId = selectedExistingBookId;

    // Hide book selection, show configuration
    bookSelectionSection.style.display = 'none';
    uploadForm.style.display = 'block';
    showStatus(`Processing book ID ${currentBookId}`, 'success');
});

// Load existing books on page load
async function loadExistingBooks() {
    try {
        const response = await fetch('/api/books?limit=50');
        if (!response.ok) {
            throw new Error('Failed to load books');
        }

        const data = await response.json();
        const books = data.books;

        if (books.length === 0) {
            existingBooksList.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">No books uploaded yet</div>';
            return;
        }

        let html = '<div style="padding: 10px;">';
        books.forEach(book => {
            const status = book.processing_status;
            const statusColor = status === 'completed' ? '#4CAF50' :
                               status === 'processing' ? '#FF9800' : '#999';
            const fileStatus = book.file_readable ? '✅' : '❌';

            html += `
                <div onclick="selectBook(${book.book_id})"
                     id="book-${book.book_id}"
                     style="padding: 15px; margin-bottom: 10px; border: 2px solid #ddd; border-radius: 4px; cursor: pointer; transition: all 0.2s;"
                     onmouseover="this.style.borderColor='#2196F3'; this.style.background='#f5f5f5'"
                     onmouseout="this.style.borderColor='#ddd'; this.style.background='white'">
                    <div style="font-weight: bold; color: #333;">${fileStatus} ${book.book_name}</div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">
                        Status: <span style="color: ${statusColor};">${status}</span> |
                        Pages: ${book.total_pages} |
                        Size: ${(book.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                    </div>
                </div>
            `;
        });
        html += '</div>';

        existingBooksList.innerHTML = html;

    } catch (error) {
        existingBooksList.innerHTML = `<div style="padding: 20px; text-align: center; color: #f44336;">Error loading books: ${error.message}</div>`;
    }
}

// Select book function
function selectBook(bookId) {
    // Remove selection from all books
    document.querySelectorAll('[id^="book-"]').forEach(el => {
        el.style.borderColor = '#ddd';
        el.style.background = 'white';
        el.style.borderWidth = '2px';
    });

    // Highlight selected book
    const bookEl = document.getElementById(`book-${bookId}`);
    if (bookEl) {
        bookEl.style.borderColor = '#2196F3';
        bookEl.style.background = '#e3f2fd';
        bookEl.style.borderWidth = '3px';
    }

    selectedExistingBookId = bookId;
    proceedExistingBtn.disabled = false;
}

// Show upload message
function showUploadMessage(message, type) {
    uploadMessage.textContent = message;
    uploadMessage.style.display = 'block';

    if (type === 'error') {
        uploadMessage.style.background = '#ffebee';
        uploadMessage.style.color = '#c62828';
        uploadMessage.style.borderLeft = '4px solid #f44336';
    } else if (type === 'success') {
        uploadMessage.style.background = '#e8f5e9';
        uploadMessage.style.color = '#2e7d32';
        uploadMessage.style.borderLeft = '4px solid #4CAF50';
    } else {
        uploadMessage.style.background = '#e3f2fd';
        uploadMessage.style.color = '#1565c0';
        uploadMessage.style.borderLeft = '4px solid #2196F3';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadExistingBooks();
    loadStorageLocation();
});

// Sequential OCR Button Handlers

let currentBookId = null;

easyOCRBtn.addEventListener('click', async () => {
    await startOCR('easyocr');
});

suryaBtn.addEventListener('click', async () => {
    await startOCR('surya');
});

tesseractBtn.addEventListener('click', async () => {
    await startOCR('tesseract');
});

evaluateBtn.addEventListener('click', async () => {
    if (!currentBookId) {
        showStatus('Please upload a file first', 'error');
        return;
    }

    try {
        showStatus('Evaluating OCR results and processing...', 'info');
        evaluateBtn.disabled = true;

        const response = await fetch('/api/evaluate-split-mark', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ book_id: currentBookId })
        });

        if (!response.ok) {
            throw new Error('Evaluation failed');
        }

        showStatus('Evaluation complete! Redirecting to verification...', 'success');

        setTimeout(() => {
            window.location.href = `/verification?book_id=${currentBookId}`;
        }, 2000);

    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        evaluateBtn.disabled = false;
    }
});

async function startOCR(engine) {
    // First, upload file if not already uploaded
    if (!currentBookId) {
        const file = fileInput.files[0];
        if (!file) {
            showStatus('Please select a file first', 'error');
            return;
        }

        // Upload file first
        currentBookId = await uploadFile();
        if (!currentBookId) return; // Upload failed
    }

    try {
        const engineNames = {
            'easyocr': 'EasyOCR',
            'surya': 'Surya OCR',
            'tesseract': 'Tesseract'
        };

        showStatus(`Starting ${engineNames[engine]}...`, 'info');

        // Disable the button
        const button = engine === 'easyocr' ? easyOCRBtn :
                      engine === 'surya' ? suryaBtn : tesseractBtn;
        button.disabled = true;
        button.textContent = `⏳ Running ${engineNames[engine]}...`;

        const response = await fetch(`/api/ocr/${engine}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ book_id: currentBookId })
        });

        if (!response.ok) {
            throw new Error(`${engineNames[engine]} failed`);
        }

        showStatus(`${engineNames[engine]} completed successfully! You can now click "Evaluate, Split and Mark" or go directly to verification.`, 'success');
        button.textContent = `✅ ${engineNames[engine]} Complete`;

        // Add a "Go to Verification" button after OCR completes
        addVerificationButton();

    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        const button = engine === 'easyocr' ? easyOCRBtn :
                      engine === 'surya' ? suryaBtn : tesseractBtn;
        button.disabled = false;
        button.textContent = button.id.includes('easy') ? '🚀 Start with EasyOCR (GPU)' :
                            button.id.includes('surya') ? '🎯 Start with Surya OCR (GPU)' :
                            '🛡️ Start with Tesseract (CPU)';
    }
}

async function uploadFile() {
    const file = fileInput.files[0];
    if (!file) {
        throw new Error('Please select a file');
    }

    // Validate file size (500MB max)
    if (file.size > 500 * 1024 * 1024) {
        throw new Error('File too large (max 500MB)');
    }

    // Prepare form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('book_name', file.name.replace(/\.[^/.]+$/, '')); // Remove extension

    // Add default/form field values
    formData.append('language_setting', document.getElementById('language-setting')?.value || 'auto');
    formData.append('llm_model', document.getElementById('llm-model')?.value || 'claude-sonnet-4-5-20250929');
    formData.append('min_chunk_size', '100');
    formData.append('max_chunk_size', '500');
    formData.append('overlap_size', '50');
    formData.append('partial_processing_enabled', 'false');
    formData.append('partial_processing_pages', '0');
    formData.append('checkpoint_frequency', '10');

    // Collect book instructions (if form is visible)
    const bookInstructions = document.getElementById('book-instructions');
    if (bookInstructions && bookInstructions.value.trim()) {
        formData.append('book_instructions', bookInstructions.value.trim());
    }

    // Collect attribute keys (9-80) if form is visible
    const attributeKeys = {};
    for (let i = 9; i <= 80; i++) {
        const input = document.getElementById(`attr${i}`);
        if (input && input.value.trim()) {
            attributeKeys[i] = input.value.trim();
        }
    }
    formData.append('attribute_keys', JSON.stringify(attributeKeys));

    showStatus('Uploading file...', 'info');

    try {
        // Upload file
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.status === 409) {
            // Duplicate file detected
            const detail = result.detail;
            if (typeof detail === 'object' && detail.message) {
                throw new Error(`Duplicate file: ${detail.message}`);
            } else if (typeof detail === 'string') {
                throw new Error(`Duplicate file: ${detail}`);
            } else {
                throw new Error('This file has already been uploaded');
            }
        }

        if (!response.ok) {
            const errorMsg = typeof result.detail === 'string' ? result.detail :
                           typeof result.detail === 'object' && result.detail.message ? result.detail.message :
                           result.message || 'Upload failed';
            throw new Error(errorMsg);
        }

        showStatus(`Upload successful! Book ID: ${result.book_id}`, 'success');
        return result.book_id;

    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        throw error; // Re-throw so the proceed button handler can catch it
    }
}

function showStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = `status-message ${type}`;
    uploadStatus.style.display = 'block';
}

// Load storage location on page load
async function loadStorageLocation() {
    try {
        const response = await fetch('/api/storage-location');
        const data = await response.json();

        document.getElementById('storage-path').textContent = data.storage_path;

        if (data.is_temporary && data.warning) {
            const warningElement = document.getElementById('storage-warning');
            warningElement.textContent = data.warning;
            warningElement.style.display = 'block';
        }
    } catch (error) {
        document.getElementById('storage-path').textContent = 'Error loading storage location';
        console.error('Error loading storage location:', error);
    }
}

// Load uploaded files on page load
async function loadUploadedFiles() {
    try {
        const response = await fetch('/api/books?limit=10');
        const data = await response.json();

        const container = document.getElementById('uploaded-files-container');

        if (data.books.length === 0) {
            container.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">No uploaded files yet</p>';
            return;
        }

        let html = '<table style="width: 100%; border-collapse: collapse;">';
        html += '<thead><tr style="background: #f5f5f5; border-bottom: 2px solid #ddd;">';
        html += '<th style="padding: 10px; text-align: left;">Book Name</th>';
        html += '<th style="padding: 10px; text-align: left;">Type</th>';
        html += '<th style="padding: 10px; text-align: left;">Size</th>';
        html += '<th style="padding: 10px; text-align: left;">Pages</th>';
        html += '<th style="padding: 10px; text-align: left;">Status</th>';
        html += '<th style="padding: 10px; text-align: left;">File Status</th>';
        html += '<th style="padding: 10px; text-align: left;">Upload Date</th>';
        html += '<th style="padding: 10px; text-align: left;">Actions</th>';
        html += '</tr></thead><tbody>';

        data.books.forEach(book => {
            const uploadDate = book.upload_date ? new Date(book.upload_date).toLocaleString() : 'N/A';
            const sizeMB = (book.file_size_bytes / (1024 * 1024)).toFixed(2);
            const fileStatus = book.file_readable ?
                '<span style="color: #4CAF50;">✅ Available</span>' :
                '<span style="color: #FF9800;">⚠️ Missing/Corrupted</span>';

            // Add delete button for corrupted/missing files
            const deleteBtn = !book.file_readable ?
                `<button onclick="deleteBook(${book.book_id}, '${book.book_name.replace(/'/g, "\\'")}')" style="padding: 5px 10px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer;">🗑️ Delete</button>` :
                '';

            html += `<tr style="border-bottom: 1px solid #eee;">`;
            html += `<td style="padding: 10px;">${book.book_name}</td>`;
            html += `<td style="padding: 10px;">${book.file_type}</td>`;
            html += `<td style="padding: 10px;">${sizeMB} MB</td>`;
            html += `<td style="padding: 10px;">${book.total_pages}</td>`;
            html += `<td style="padding: 10px;">${book.processing_status}</td>`;
            html += `<td style="padding: 10px;">${fileStatus}</td>`;
            html += `<td style="padding: 10px;">${uploadDate}</td>`;
            html += `<td style="padding: 10px;">${deleteBtn}</td>`;
            html += `</tr>`;
        });

        html += '</tbody></table>';
        container.innerHTML = html;

    } catch (error) {
        document.getElementById('uploaded-files-container').innerHTML =
            '<p style="color: red; text-align: center; padding: 20px;">Error loading uploaded files</p>';
        console.error('Error loading uploaded files:', error);
    }
}

// Show duplicate warning modal
function showDuplicateWarning(errorDetail) {
    const modal = document.createElement('div');
    modal.id = 'duplicate-modal';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;';

    modal.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 500px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="color: #FF9800; margin-top: 0;">⚠️ Duplicate File Detected</h2>
            <p style="margin: 20px 0;">${errorDetail.message}</p>
            <p style="background: #f5f5f5; padding: 10px; border-radius: 4px;">
                <strong>Existing Book ID:</strong> #${errorDetail.existing_book_id}
            </p>
            <div style="margin-top: 30px; display: flex; gap: 10px; justify-content: flex-end;">
                <button onclick="closeDuplicateModal()" style="padding: 10px 20px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer;">
                    Cancel
                </button>
                <button onclick="viewExistingBook(${errorDetail.existing_book_id})" style="padding: 10px 20px; border: none; background: #2196F3; color: white; border-radius: 4px; cursor: pointer; font-weight: bold;">
                    View Existing Book
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

// Close duplicate modal
function closeDuplicateModal() {
    const modal = document.getElementById('duplicate-modal');
    if (modal) {
        modal.remove();
    }
}

// View existing book (navigate to library or processing page)
function viewExistingBook(bookId) {
    // TODO: Navigate to book library or verification page
    window.location.href = `/verification?book_id=${bookId}`;
}

// Delete book
// Add verification button after OCR completes
function addVerificationButton() {
    // Check if button already exists
    if (document.getElementById('goto-verification-btn')) {
        return;
    }

    // Find the OCR buttons section
    const ocrSection = document.querySelector('.ocr-buttons-section');
    if (!ocrSection) return;

    // Create a prominent "Go to Verification" button
    const buttonDiv = document.createElement('div');
    buttonDiv.id = 'verification-button-container';
    buttonDiv.style.cssText = 'margin-top: 30px; padding: 20px; background: #e8f5e9; border: 2px solid #4CAF50; border-radius: 8px;';

    buttonDiv.innerHTML = `
        <h3 style="color: #2e7d32; margin-bottom: 15px;">✅ OCR Complete!</h3>
        <p style="margin-bottom: 15px; color: #555;">
            Your document has been processed with OCR. You can now:
        </p>
        <div style="display: flex; gap: 15px;">
            <button id="goto-verification-btn" style="flex: 1; padding: 15px; background: #4CAF50; color: white; border: none; border-radius: 4px; font-size: 16px; font-weight: bold; cursor: pointer;">
                📝 Go to Verification Interface
            </button>
            <button id="run-evaluate-btn" style="flex: 1; padding: 15px; background: #FF9800; color: white; border: none; border-radius: 4px; font-size: 16px; font-weight: bold; cursor: pointer;">
                ✅ Run Evaluation First
            </button>
        </div>
    `;

    ocrSection.appendChild(buttonDiv);

    // Add click handlers
    document.getElementById('goto-verification-btn').addEventListener('click', () => {
        window.location.href = `/verification?book_id=${currentBookId}`;
    });

    document.getElementById('run-evaluate-btn').addEventListener('click', () => {
        evaluateBtn.click();
    });
}

async function deleteBook(bookId, bookName) {
    if (!confirm(`Are you sure you want to delete "${bookName}"? This will remove the book record from the database.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/books/${bookId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete book');
        }

        alert(`Book "${bookName}" deleted successfully`);
        loadUploadedFiles(); // Reload the list
    } catch (error) {
        alert(`Error deleting book: ${error.message}`);
        console.error('Error deleting book:', error);
    }
}

// Open storage management modal
function openStorageModal() {
    const modal = document.createElement('div');
    modal.id = 'storage-modal';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; overflow-y: auto;';

    modal.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 700px; max-height: 90vh; overflow-y: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="margin-top: 0;">⚙️ Storage Location Management</h2>

            <div style="margin: 20px 0;">
                <label style="display: block; font-weight: bold; margin-bottom: 5px;">New Storage Path:</label>
                <input type="text" id="new-storage-path" placeholder="/var/lib/uploads" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px;">

                <label style="display: flex; align-items: center; margin-bottom: 15px;">
                    <input type="checkbox" id="migrate-files-checkbox" checked style="margin-right: 8px;">
                    <span>Migrate existing files to new location</span>
                </label>

                <button onclick="setStorageLocation()" style="padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; margin-right: 10px;">
                    💾 Save & Migrate
                </button>
                <button onclick="closeStorageModal()" style="padding: 10px 20px; background: #ddd; border: none; border-radius: 4px; cursor: pointer;">
                    Cancel
                </button>
            </div>

            <hr style="margin: 20px 0;">

            <h3>Storage Location History</h3>
            <div id="storage-history-container" style="margin-top: 15px;">
                <p style="color: #666; text-align: center;">Loading history...</p>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    loadStorageHistory();
}

// Close storage modal
function closeStorageModal() {
    const modal = document.getElementById('storage-modal');
    if (modal) {
        modal.remove();
    }
}

// Load storage history
async function loadStorageHistory() {
    try {
        const response = await fetch('/api/storage-locations/history');
        const data = await response.json();

        const container = document.getElementById('storage-history-container');

        if (data.locations.length === 0) {
            container.innerHTML = '<p style="color: #666; text-align: center;">No history available</p>';
            return;
        }

        let html = '<table style="width: 100%; border-collapse: collapse;">';
        html += '<thead><tr style="background: #f5f5f5; border-bottom: 2px solid #ddd;">';
        html += '<th style="padding: 8px; text-align: left;">Path</th>';
        html += '<th style="padding: 8px; text-align: left;">Status</th>';
        html += '<th style="padding: 8px; text-align: left;">Created</th>';
        html += '<th style="padding: 8px; text-align: left;">Notes</th>';
        html += '</tr></thead><tbody>';

        data.locations.forEach(loc => {
            const status = loc.is_active ?
                '<span style="color: #4CAF50; font-weight: bold;">✓ Active</span>' :
                '<span style="color: #666;">Inactive</span>';
            const created = loc.created_at ? new Date(loc.created_at).toLocaleString() : 'N/A';

            html += `<tr style="border-bottom: 1px solid #eee;">`;
            html += `<td style="padding: 8px; font-family: monospace; font-size: 12px;">${loc.path}</td>`;
            html += `<td style="padding: 8px;">${status}</td>`;
            html += `<td style="padding: 8px;">${created}</td>`;
            html += `<td style="padding: 8px;">${loc.notes || '-'}</td>`;
            html += `</tr>`;
        });

        html += '</tbody></table>';
        container.innerHTML = html;

    } catch (error) {
        document.getElementById('storage-history-container').innerHTML =
            '<p style="color: red; text-align: center;">Error loading history</p>';
        console.error('Error loading storage history:', error);
    }
}

// Set storage location
async function setStorageLocation() {
    const pathInput = document.getElementById('new-storage-path');
    const migrateCheckbox = document.getElementById('migrate-files-checkbox');

    const newPath = pathInput.value.trim();
    if (!newPath) {
        alert('Please enter a storage path');
        return;
    }

    const confirmMsg = migrateCheckbox.checked ?
        `Set storage location to:\n${newPath}\n\nThis will migrate all existing files to the new location. Continue?` :
        `Set storage location to:\n${newPath}\n\nExisting files will NOT be migrated. Continue?`;

    if (!confirm(confirmMsg)) {
        return;
    }

    try {
        const response = await fetch('/api/storage-location', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                path: newPath,
                migrate_files: migrateCheckbox.checked
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to set storage location');
        }

        alert(result.message);
        closeStorageModal();
        loadStorageLocation(); // Reload storage location display
        loadUploadedFiles(); // Reload files list

    } catch (error) {
        alert(`Error: ${error.message}`);
        console.error('Error setting storage location:', error);
    }
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    loadStorageLocation();
    loadUploadedFiles();
});
