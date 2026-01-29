/**
 * Book Library JavaScript
 * Displays all books with filtering, search, and statistics
 */

// State
let allBooks = [];
let filteredBooks = [];
let currentStatusFilter = 'all';
let currentTypeFilter = 'all';
let searchQuery = '';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadBooks();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Search input
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase();
        applyFilters();
    });

    // Filter chips
    document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            // Remove active from all chips
            document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');

            // Apply filter
            currentTypeFilter = chip.dataset.type || 'all';
            applyFilters();
        });
    });
}

// Load books from API
async function loadBooks() {
    try {
        const response = await fetch('/api/books?limit=100');
        const data = await response.json();

        allBooks = data.books || [];
        filteredBooks = [...allBooks];

        // Update statistics
        updateStatistics();

        // Update counts
        updateFilterCounts();

        // Display books
        displayBooks();

    } catch (error) {
        console.error('Error loading books:', error);
        showError('Failed to load books');
    }
}

// Update header statistics
function updateStatistics() {
    const totalBooks = allBooks.length;
    let totalUnits = 0;
    let totalImages = 0;
    let totalVerified = 0;
    let totalUnitsCount = 0;

    allBooks.forEach(book => {
        // These would come from book stats API in real implementation
        // For now, placeholder values
        const units = 0; // book.knowledge_units_count || 0;
        const images = 0; // book.images_count || 0;
        const verified = 0; // book.verified_count || 0;

        totalUnits += units;
        totalImages += images;
        totalVerified += verified;
        totalUnitsCount += units;
    });

    const verifiedPercentage = totalUnitsCount > 0
        ? Math.round((totalVerified / totalUnitsCount) * 100)
        : 0;

    document.getElementById('total-books').textContent = totalBooks;
    document.getElementById('total-units').textContent = totalUnits.toLocaleString();
    document.getElementById('total-images').textContent = totalImages.toLocaleString();
    document.getElementById('total-verified').textContent =
        `${totalVerified.toLocaleString()} (${verifiedPercentage}%)`;
}

// Update filter counts
function updateFilterCounts() {
    const pdfCount = allBooks.filter(b => b.file_type === 'PDF').length;

    document.getElementById('count-all').textContent = allBooks.length;
    document.getElementById('count-pdf').textContent = pdfCount;
}

// Apply filters
function applyFilters() {
    filteredBooks = allBooks.filter(book => {
        // Status filter
        if (currentStatusFilter !== 'all') {
            if (book.processing_status !== currentStatusFilter) {
                return false;
            }
        }

        // Type filter
        if (currentTypeFilter !== 'all' && currentTypeFilter !== 'recently') {
            if (book.file_type !== currentTypeFilter) {
                return false;
            }
        }

        // Search filter
        if (searchQuery) {
            if (!book.book_name.toLowerCase().includes(searchQuery)) {
                return false;
            }
        }

        return true;
    });

    // Sort by recently added if that filter is active
    if (currentTypeFilter === 'recently') {
        filteredBooks.sort((a, b) => {
            const dateA = new Date(a.upload_date || 0);
            const dateB = new Date(b.upload_date || 0);
            return dateB - dateA;
        });
    }

    displayBooks();
}

// Display books in table
function displayBooks() {
    const tbody = document.getElementById('books-table-body');

    if (filteredBooks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" style="text-align: center; padding: 40px; color: #666;">
                    <h2 style="color: #999;">📚 No books found</h2>
                    <p>Try adjusting your filters or search query.</p>
                    <button class="btn-upload" onclick="goToUpload()" style="margin-top: 20px;">
                        📤 Upload Your First Book
                    </button>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filteredBooks.map(book => createBookRow(book)).join('');
}

// Create book table row HTML
function createBookRow(book) {
    const statusClass = `status-${book.processing_status || 'pending'}`;
    const statusText = getStatusText(book.processing_status);

    const uploadDate = book.upload_date
        ? new Date(book.upload_date).toLocaleDateString()
        : 'Unknown';

    // Calculate file size
    const fileSize = book.file_size_bytes
        ? (book.file_size_bytes / (1024 * 1024)).toFixed(1) + ' MB'
        : 'N/A';

    // Get progress data
    const progress = book.progress || {
        pages_scanned: 0,
        easyocr_pages_processed: 0,
        surya_pages_processed: 0,
        tesseract_pages_processed: 0,
        pages_split_verified: 0
    };

    const totalPages = book.total_pages || 0;

    // Calculate percentages
    const pageScanPercent = totalPages > 0 ? Math.round((progress.pages_scanned / totalPages) * 100) : 0;
    const easyocrPercent = totalPages > 0 ? Math.round((progress.easyocr_pages_processed / totalPages) * 100) : 0;
    const suryaPercent = totalPages > 0 ? Math.round((progress.surya_pages_processed / totalPages) * 100) : 0;
    const tesseractPercent = totalPages > 0 ? Math.round((progress.tesseract_pages_processed / totalPages) * 100) : 0;
    const verificationPercent = totalPages > 0 ? Math.round((progress.pages_split_verified / totalPages) * 100) : 0;

    return `
        <tr>
            <td>${book.book_id}</td>
            <td>
                <div class="book-name">${escapeHtml(book.book_name)}</div>
                <div class="book-meta-text">Added: ${uploadDate} | ${book.file_type || 'PDF'}</div>
            </td>
            <td>${totalPages}</td>
            <td>${fileSize}</td>

            <!-- Page Scan Progress -->
            <td class="progress-cell">
                <div class="progress-percentage">${pageScanPercent}%</div>
                <div class="progress-bar-mini">
                    <div class="progress-fill-mini page-scan" style="width: ${pageScanPercent}%"></div>
                </div>
                <div class="progress-count">${progress.pages_scanned}/${totalPages}</div>
            </td>

            <!-- EasyOCR Progress -->
            <td class="progress-cell">
                <div class="progress-percentage">${easyocrPercent}%</div>
                <div class="progress-bar-mini">
                    <div class="progress-fill-mini easyocr" style="width: ${easyocrPercent}%"></div>
                </div>
                <div class="progress-count">${progress.easyocr_pages_processed}/${totalPages}</div>
            </td>

            <!-- Surya OCR Progress -->
            <td class="progress-cell">
                <div class="progress-percentage">${suryaPercent}%</div>
                <div class="progress-bar-mini">
                    <div class="progress-fill-mini surya" style="width: ${suryaPercent}%"></div>
                </div>
                <div class="progress-count">${progress.surya_pages_processed}/${totalPages}</div>
            </td>

            <!-- Tesseract Progress -->
            <td class="progress-cell">
                <div class="progress-percentage">${tesseractPercent}%</div>
                <div class="progress-bar-mini">
                    <div class="progress-fill-mini tesseract" style="width: ${tesseractPercent}%"></div>
                </div>
                <div class="progress-count">${progress.tesseract_pages_processed}/${totalPages}</div>
            </td>

            <!-- Verification Progress -->
            <td class="progress-cell">
                <div class="progress-percentage">${verificationPercent}%</div>
                <div class="progress-bar-mini">
                    <div class="progress-fill-mini verification" style="width: ${verificationPercent}%"></div>
                </div>
                <div class="progress-count">${progress.pages_split_verified}/${totalPages}</div>
            </td>

            <td>
                <span class="status-badge ${statusClass}">${statusText}</span>
            </td>
            <td>
                <div class="table-actions">
                    <button class="btn-action btn-scan-pages" onclick="scanPages(${book.book_id}, ${totalPages})" title="Scan pages at 600 DPI">
                        📸 Scan Pages
                    </button>
                    <button class="btn-action btn-run-ocr" onclick="runOCR(${book.book_id})" title="Run OCR engines">
                        🔍 Run OCR
                    </button>
                    <button class="btn-action btn-verify-images" onclick="verifyImages(${book.book_id})" title="Verify raw page images">
                        🖼️ Verify Page
                    </button>
                    <button class="btn-action btn-review-raw" onclick="reviewRaw(${book.book_id})" title="Review raw paragraphs and diagrams">
                        📋 Review Raw
                    </button>
                    <button class="btn-action btn-delete" onclick="initiateDeleteBook(${book.book_id})" 
                            title="${book.processing_status === 'processing' ? 'Cannot delete - book is processing' : 'Delete this book'}"
                            ${book.processing_status === 'processing' ? 'disabled' : ''}>
                        🗑️ Delete
                    </button>
                </div>
            </td>
        </tr>
    `;
}

// Get status text
function getStatusText(status) {
    const statusMap = {
        'pending': 'Pending',
        'processing': 'Processing',
        'completed': 'Completed',
        'paused': 'Paused',
        'error': 'Error'
    };
    return statusMap[status] || 'Unknown';
}

// Navigation functions
function goToUpload() {
    window.location.href = '/upload';
}

function goToUploadExisting(bookId) {
    window.location.href = `/upload?book_id=${bookId}`;
}

function goToVerification(bookId) {
    window.location.href = `/verification?book_id=${bookId}`;
}

function goToProcessing(bookId) {
    window.location.href = `/processing?book_id=${bookId}`;
}

function goToSettings(bookId) {
    window.location.href = `/book-settings?book_id=${bookId}`;
}

// Action 1: Scan Pages at 600 DPI
async function scanPages(bookId, totalPages) {
    // Prompt user for number of pages to scan
    const maxPages = prompt(`Enter number of pages to scan (1-${totalPages}), or leave empty for all pages:`);

    if (maxPages === null) {
        return; // User cancelled
    }

    const pagesToScan = maxPages.trim() === '' ? null : parseInt(maxPages);

    // Validate input
    if (pagesToScan !== null && (isNaN(pagesToScan) || pagesToScan < 1 || pagesToScan > totalPages)) {
        alert(`Invalid input! Please enter a number between 1 and ${totalPages}.`);
        return;
    }

    try {
        // Check raw data status first
        const checkResponse = await fetch(`/api/check-raw-data/${bookId}`);
        const checkData = await checkResponse.json();

        const pagesSaved = checkData.raw_page_status.raw_pages_saved;

        let statusMessage = `📊 Page Scan Status:\n\n`;
        statusMessage += `Pages already scanned: ${pagesSaved}/${totalPages}\n\n`;

        if (pagesSaved > 0) {
            statusMessage += `⚠️ WARNING: ${pagesSaved} pages already scanned.\nScanning will re-render and overwrite existing images.\n\n`;
        }

        const scanCount = pagesToScan || totalPages;
        statusMessage += `Ready to scan ${scanCount} page(s) at 600 DPI.\n\nContinue?`;

        if (!confirm(statusMessage)) {
            return;
        }

        // Start scanning
        const requestBody = { book_id: bookId };
        if (pagesToScan) {
            requestBody.max_pages = pagesToScan;
        }

        const response = await fetch('/api/scan-pages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error('Failed to start page scanning');
        }

        const msg = pagesToScan
            ? `Page scanning started for ${pagesToScan} pages!`
            : `Page scanning started for all ${totalPages} pages!`;

        alert(msg);

        // Reload books to show updated progress
        setTimeout(() => loadBooks(), 1000);

    } catch (error) {
        console.error('Error scanning pages:', error);
        alert(`Error: ${error.message}`);
    }
}

// Action 2: Run OCR - Opens OCR/Processing page
function runOCR(bookId) {
    window.location.href = `/processing?book_id=${bookId}`;
}

// Action 3: Verify Images - Opens verify-pages for raw images
function verifyImages(bookId) {
    window.location.href = `/verify-pages?book_id=${bookId}`;
}

// Review raw paragraphs and diagrams
function reviewRaw(bookId) {
    window.location.href = `/review-raw?book_id=${bookId}`;
}

// Delete book
async function deleteBook(bookId, bookName) {
    if (!confirm(`Are you sure you want to delete "${bookName}"?\n\nThis will permanently delete:\n- All knowledge units\n- All extracted images\n- All verification data\n- Processing history\n\nThis action cannot be undone!`)) {
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

        // Reload books
        await loadBooks();

    } catch (error) {
        console.error('Error deleting book:', error);
        alert(`Failed to delete book: ${error.message}`);
    }
}

// Show error
function showError(message) {
    const grid = document.getElementById('book-grid');
    grid.innerHTML = `
        <div class="empty-state">
            <h2>⚠️ Error</h2>
            <p>${escapeHtml(message)}</p>
            <button class="btn-upload" onclick="loadBooks()" style="margin-top: 20px;">
                🔄 Retry
            </button>
        </div>
    `;
}

// Escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// Combined OCR GPU Management (Surya + EasyOCR)
// ============================================================================

// Load All OCR engines (Surya + EasyOCR + YOLO)
async function loadAllOCR() {
    const statusContainer = document.getElementById('ocr-status-container');
    const messageText = document.getElementById('ocr-message-text');
    const statusHeader = document.getElementById('ocr-status-header');
    const progressContainer = document.getElementById('progress-bar-container');
    const progressFill = document.getElementById('progress-bar-fill');
    const dotSurya = document.getElementById('dot-surya');
    const dotEasyocr = document.getElementById('dot-easyocr');
    const dotYolo = document.getElementById('dot-yolo');
    const btnLoad = document.getElementById('btn-load-all-ocr');

    // Show status container and loading message
    statusContainer.classList.add('visible');
    statusHeader.className = 'ocr-status-header loading';
    messageText.textContent = '⏳ Loading all models on GPU... (this may take ~2 minutes)';
    progressContainer.style.display = 'block';

    // Set dots to loading
    dotSurya.className = 'model-dot loading';
    dotEasyocr.className = 'model-dot loading';
    dotYolo.className = 'model-dot loading';

    // Disable load button
    btnLoad.disabled = true;

    // Simulate progress bar (120 seconds)
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 0.8; // Increment to reach 100% in ~120 seconds
        if (progress > 95) progress = 95; // Stop at 95% until actual completion
        progressFill.style.width = progress + '%';
    }, 1000);

    try {
        const response = await fetch('/api/ocr/load-all');
        const data = await response.json();

        // Clear progress interval
        clearInterval(progressInterval);
        progressFill.style.width = '100%';

        // Update engine dots
        dotSurya.className = 'model-dot ' + (data.engines.surya.loaded ? 'loaded' : 'error');
        dotEasyocr.className = 'model-dot ' + (data.engines.easyocr.loaded ? 'loaded' : 'error');
        dotYolo.className = 'model-dot ' + (data.engines.yolo?.loaded ? 'loaded' : 'error');

        if (data.all_loaded) {
            // All loaded
            statusHeader.className = 'ocr-status-header success';
            messageText.textContent = '✅ All models loaded on GPU';
            btnLoad.classList.add('loaded');
        } else {
            // Partial or error
            statusHeader.className = 'ocr-status-header error';
            const msgs = [];
            if (!data.engines.surya.loaded) msgs.push('Surya: ' + data.engines.surya.message);
            if (!data.engines.easyocr.loaded) msgs.push('EasyOCR: ' + data.engines.easyocr.message);
            if (!data.engines.yolo?.loaded) msgs.push('YOLO: ' + (data.engines.yolo?.message || 'Failed'));
            messageText.textContent = '⚠️ Some models failed: ' + msgs.join('; ');
        }

        // Hide progress bar after 2 seconds
        setTimeout(() => {
            progressContainer.style.display = 'none';
            progressFill.style.width = '0%';
        }, 2000);

        btnLoad.disabled = false;

        console.log('Load all models result:', data);
    } catch (error) {
        // Network error
        clearInterval(progressInterval);
        statusHeader.className = 'ocr-status-header error';
        messageText.textContent = '❌ Error loading models: ' + error.message;
        progressContainer.style.display = 'none';
        btnLoad.disabled = false;
        dotSurya.className = 'model-dot error';
        dotEasyocr.className = 'model-dot error';
        dotYolo.className = 'model-dot error';

        console.error('Error loading all models:', error);
    }
}

// Unload All OCR engines (Surya + EasyOCR + YOLO)
async function unloadAllOCR() {
    const statusContainer = document.getElementById('ocr-status-container');
    const messageText = document.getElementById('ocr-message-text');
    const statusHeader = document.getElementById('ocr-status-header');
    const dotSurya = document.getElementById('dot-surya');
    const dotEasyocr = document.getElementById('dot-easyocr');
    const dotYolo = document.getElementById('dot-yolo');
    const btnLoad = document.getElementById('btn-load-all-ocr');
    const btnUnload = document.getElementById('btn-unload-all-ocr');

    // Show loading message
    statusContainer.classList.add('visible');
    statusHeader.className = 'ocr-status-header loading';
    messageText.textContent = '⏳ Unloading all models from GPU...';

    // Disable unload button
    btnUnload.disabled = true;

    try {
        const response = await fetch('/api/ocr/unload-all');
        const data = await response.json();

        if (data.all_unloaded) {
            // Success
            statusHeader.className = 'ocr-status-header success';
            messageText.textContent = '✅ All models unloaded from GPU';
            dotSurya.className = 'model-dot';
            dotEasyocr.className = 'model-dot';
            dotYolo.className = 'model-dot';
            btnLoad.classList.remove('loaded');
        } else {
            // Partial
            statusHeader.className = 'ocr-status-header error';
            messageText.textContent = '⚠️ Some models failed to unload';
        }

        btnUnload.disabled = false;

        console.log('Unload all models result:', data);
    } catch (error) {
        // Network error
        statusHeader.className = 'ocr-status-header error';
        messageText.textContent = '❌ Error unloading models: ' + error.message;
        btnUnload.disabled = false;

        console.error('Error unloading all models:', error);
    }
}

// Close OCR status message
function closeOCRStatus() {
    const statusContainer = document.getElementById('ocr-status-container');
    statusContainer.classList.remove('visible');
}

// Check All OCR status
async function checkAllOCRStatus() {
    const statusContainer = document.getElementById('ocr-status-container');
    const messageText = document.getElementById('ocr-message-text');
    const statusHeader = document.getElementById('ocr-status-header');
    const dotSurya = document.getElementById('dot-surya');
    const dotEasyocr = document.getElementById('dot-easyocr');
    const dotYolo = document.getElementById('dot-yolo');
    const btnLoad = document.getElementById('btn-load-all-ocr');

    // Show checking message
    statusContainer.classList.add('visible');
    statusHeader.className = 'ocr-status-header loading';
    messageText.textContent = '🔍 Checking model status...';

    try {
        const response = await fetch('/api/ocr/check-all-status');
        const data = await response.json();

        // Update dots
        dotSurya.className = 'model-dot ' + (data.engines.surya.loaded ? 'loaded' : '');
        dotEasyocr.className = 'model-dot ' + (data.engines.easyocr.loaded ? 'loaded' : '');
        dotYolo.className = 'model-dot ' + (data.engines.yolo?.loaded ? 'loaded' : '');

        if (data.all_loaded) {
            statusHeader.className = 'ocr-status-header success';
            messageText.textContent = '✅ All models loaded on GPU';
            btnLoad.classList.add('loaded');
        } else if (data.any_loaded) {
            statusHeader.className = 'ocr-status-header';
            statusHeader.style.color = '#FF9800';
            const loaded = [];
            if (data.engines.surya.loaded) loaded.push('Surya');
            if (data.engines.easyocr.loaded) loaded.push('EasyOCR');
            if (data.engines.yolo?.loaded) loaded.push('YOLO');
            messageText.textContent = '⚠️ Partially loaded: ' + loaded.join(', ');
            btnLoad.classList.remove('loaded');
        } else {
            statusHeader.className = 'ocr-status-header';
            statusHeader.style.color = '#2196F3';
            messageText.textContent = 'ℹ️ No models loaded';
            btnLoad.classList.remove('loaded');
        }

        console.log('Model status:', data);
    } catch (error) {
        // Network error
        statusHeader.className = 'ocr-status-header error';
        messageText.textContent = '❌ Error checking status: ' + error.message;

        console.error('Error checking model status:', error);
    }
}

// ============================================================================
// Individual Model Load/Unload Functions
// ============================================================================

// Load Surya OCR model
async function loadSuryaModel() {
    const dotSurya = document.getElementById('dot-surya');
    const btnLoad = document.getElementById('btn-load-surya');

    dotSurya.className = 'model-dot loading';
    btnLoad.disabled = true;
    showStatusMessage('⏳ Loading Surya OCR...', 'loading');

    try {
        const response = await fetch('/api/ocr/load-surya');
        const data = await response.json();

        if (data.status === 'success') {
            dotSurya.className = 'model-dot loaded';
            showStatusMessage('✅ Surya OCR loaded', 'success');
        } else {
            dotSurya.className = 'model-dot error';
            showStatusMessage('❌ Failed to load Surya: ' + data.message, 'error');
        }
    } catch (error) {
        dotSurya.className = 'model-dot error';
        showStatusMessage('❌ Error: ' + error.message, 'error');
    }

    btnLoad.disabled = false;
}

// Unload Surya OCR model
async function unloadSuryaModel() {
    const dotSurya = document.getElementById('dot-surya');
    const btnUnload = document.getElementById('btn-unload-surya');

    btnUnload.disabled = true;
    showStatusMessage('⏳ Unloading Surya OCR...', 'loading');

    try {
        const response = await fetch('/api/ocr/unload-surya');
        const data = await response.json();

        if (data.status === 'success') {
            dotSurya.className = 'model-dot';
            showStatusMessage('✅ Surya OCR unloaded', 'success');
        } else {
            showStatusMessage('❌ Failed to unload Surya: ' + data.message, 'error');
        }
    } catch (error) {
        showStatusMessage('❌ Error: ' + error.message, 'error');
    }

    btnUnload.disabled = false;
}

// Load EasyOCR model
async function loadEasyOCRModel() {
    const dotEasyocr = document.getElementById('dot-easyocr');
    const btnLoad = document.getElementById('btn-load-easyocr');

    dotEasyocr.className = 'model-dot loading';
    btnLoad.disabled = true;
    showStatusMessage('⏳ Loading EasyOCR...', 'loading');

    try {
        const response = await fetch('/api/ocr/load-easyocr');
        const data = await response.json();

        if (data.status === 'success') {
            dotEasyocr.className = 'model-dot loaded';
            showStatusMessage('✅ EasyOCR loaded', 'success');
        } else {
            dotEasyocr.className = 'model-dot error';
            showStatusMessage('❌ Failed to load EasyOCR: ' + data.message, 'error');
        }
    } catch (error) {
        dotEasyocr.className = 'model-dot error';
        showStatusMessage('❌ Error: ' + error.message, 'error');
    }

    btnLoad.disabled = false;
}

// Unload EasyOCR model
async function unloadEasyOCRModel() {
    const dotEasyocr = document.getElementById('dot-easyocr');
    const btnUnload = document.getElementById('btn-unload-easyocr');

    btnUnload.disabled = true;
    showStatusMessage('⏳ Unloading EasyOCR...', 'loading');

    try {
        const response = await fetch('/api/ocr/unload-easyocr');
        const data = await response.json();

        if (data.status === 'success') {
            dotEasyocr.className = 'model-dot';
            showStatusMessage('✅ EasyOCR unloaded', 'success');
        } else {
            showStatusMessage('❌ Failed to unload EasyOCR: ' + data.message, 'error');
        }
    } catch (error) {
        showStatusMessage('❌ Error: ' + error.message, 'error');
    }

    btnUnload.disabled = false;
}

// Load YOLO model
async function loadYOLOModel() {
    const dotYolo = document.getElementById('dot-yolo');
    const btnLoad = document.getElementById('btn-load-yolo');

    dotYolo.className = 'model-dot loading';
    btnLoad.disabled = true;
    showStatusMessage('⏳ Loading YOLO Layout Detection...', 'loading');

    try {
        const response = await fetch('/api/ocr/load-yolo');
        const data = await response.json();

        if (data.loaded) {
            dotYolo.className = 'model-dot loaded';
            showStatusMessage('✅ YOLO loaded', 'success');
        } else {
            dotYolo.className = 'model-dot error';
            showStatusMessage('❌ Failed to load YOLO: ' + data.message, 'error');
        }
    } catch (error) {
        dotYolo.className = 'model-dot error';
        showStatusMessage('❌ Error: ' + error.message, 'error');
    }

    btnLoad.disabled = false;
}

// Unload YOLO model
async function unloadYOLOModel() {
    const dotYolo = document.getElementById('dot-yolo');
    const btnUnload = document.getElementById('btn-unload-yolo');

    btnUnload.disabled = true;
    showStatusMessage('⏳ Unloading YOLO...', 'loading');

    try {
        const response = await fetch('/api/ocr/unload-yolo');
        const data = await response.json();

        if (data.unloaded) {
            dotYolo.className = 'model-dot';
            showStatusMessage('✅ YOLO unloaded', 'success');
        } else {
            showStatusMessage('❌ Failed to unload YOLO: ' + data.message, 'error');
        }
    } catch (error) {
        showStatusMessage('❌ Error: ' + error.message, 'error');
    }

    btnUnload.disabled = false;
}

// Helper function to show status message
function showStatusMessage(message, type) {
    const statusContainer = document.getElementById('ocr-status-container');
    const messageText = document.getElementById('ocr-message-text');
    const statusHeader = document.getElementById('ocr-status-header');

    statusContainer.classList.add('visible');
    messageText.textContent = message;

    statusHeader.className = 'ocr-status-header';
    if (type === 'loading') statusHeader.classList.add('loading');
    else if (type === 'success') statusHeader.classList.add('success');
    else if (type === 'error') statusHeader.classList.add('error');
}

// Legacy functions for backwards compatibility
function loadSuryaOCR() { loadAllOCR(); }
function unloadSuryaOCR() { unloadAllOCR(); }
function closeSuryaStatus() { closeOCRStatus(); }
function checkSuryaStatus() { checkAllOCRStatus(); }

// ============================================================================
// Book Deletion Functions
// ============================================================================

// State for deletion
let deleteBookData = null;

// Initiate delete - fetch preview and show summary modal
async function initiateDeleteBook(bookId) {
    try {
        const response = await fetch(`/api/books/${bookId}/deletion-preview`);
        const data = await response.json();
        
        if (!response.ok) {
            showToast(data.detail || 'Failed to get deletion preview', 'error');
            return;
        }
        
        if (!data.can_delete) {
            showToast(`Cannot delete: ${data.blocking_reason}`, 'error');
            return;
        }
        
        deleteBookData = data;
        showDeleteSummaryModal(data);
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

// Show the summary modal (Step 1)
function showDeleteSummaryModal(data) {
    document.getElementById('delete-book-name').textContent = data.book_name;
    document.getElementById('delete-pages-count').textContent = data.counts.pages.toLocaleString();
    document.getElementById('delete-ku-count').textContent = data.counts.knowledge_units.toLocaleString();
    document.getElementById('delete-images-count').textContent = data.counts.images.toLocaleString();
    document.getElementById('delete-para-count').textContent = data.counts.paragraph_clips.toLocaleString();
    document.getElementById('delete-diag-count').textContent = data.counts.diagram_clips.toLocaleString();
    document.getElementById('delete-embeddings-count').textContent = data.counts.chromadb_embeddings.toLocaleString();
    
    // Reset checkbox to checked
    document.getElementById('delete-chromadb-checkbox').checked = true;
    
    document.getElementById('delete-summary-modal').classList.add('active');
}

// Show code verification modal (Step 2)
function showCodeVerification() {
    document.getElementById('delete-summary-modal').classList.remove('active');
    document.getElementById('confirmation-code-display').textContent = deleteBookData.confirmation_code;
    document.getElementById('confirmation-code-input').value = '';
    document.getElementById('btn-confirm-delete').disabled = true;
    document.getElementById('delete-code-modal').classList.add('active');
    
    // Focus the input
    setTimeout(() => {
        document.getElementById('confirmation-code-input').focus();
    }, 100);
}

// Validate the confirmation code
function validateConfirmationCode() {
    const input = document.getElementById('confirmation-code-input').value;
    const expected = deleteBookData.confirmation_code;
    document.getElementById('btn-confirm-delete').disabled = (input !== expected);
}

// Execute the deletion
async function executeDelete() {
    const deleteChromadb = document.getElementById('delete-chromadb-checkbox').checked;
    const code = document.getElementById('confirmation-code-input').value;
    const bookName = deleteBookData.book_name;
    
    // Disable button to prevent double-click
    document.getElementById('btn-confirm-delete').disabled = true;
    document.getElementById('btn-confirm-delete').textContent = '⏳ Deleting...';
    
    try {
        const response = await fetch(`/api/books/${deleteBookData.book_id}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                delete_chromadb: deleteChromadb,
                confirmation_code: code
            })
        });
        
        const result = await response.json();
        
        closeDeleteModals();
        
        if (response.ok && result.success) {
            showToast(`Book "${bookName}" deleted successfully`, 'success');
            // Refresh the book list
            loadBooks();
        } else {
            // Show detailed error message
            const errorMsg = result.detail || result.error || result.message || 'Deletion failed';
            showToast(`Error: ${errorMsg}`, 'error');
            console.error('Delete failed:', result);
        }
    } catch (error) {
        closeDeleteModals();
        showToast('Error: ' + error.message, 'error');
        console.error('Delete error:', error);
    }
}

// Close all delete modals
function closeDeleteModals() {
    document.getElementById('delete-summary-modal').classList.remove('active');
    document.getElementById('delete-code-modal').classList.remove('active');
    document.getElementById('btn-confirm-delete').textContent = '🗑️ Delete Book';
    document.getElementById('btn-confirm-delete').disabled = true;
    deleteBookData = null;
}

// Show toast notification
function showToast(message, type) {
    // Remove any existing toasts
    document.querySelectorAll('.toast').forEach(t => t.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}
