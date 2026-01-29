/**
 * Book Settings JavaScript
 * Edit attribute names for book and manage page scanning
 */

let currentBookId = null;
let originalAttributes = {};
let currentAttributes = {};

// Page scanning elements
let scanPagesBtn = null;
let maxPagesInput = null;

// Book selector elements
let bookSelect = null;
let noBookMessage = null;
let bookContent = null;

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    currentBookId = urlParams.get('book_id');

    // Initialize elements
    scanPagesBtn = document.getElementById('scan-pages-btn');
    maxPagesInput = document.getElementById('max-pages-input');
    bookSelect = document.getElementById('book-select');
    noBookMessage = document.getElementById('no-book-message');
    bookContent = document.getElementById('book-content');

    // Load books list first
    loadBooksList();

    // Setup book selector change handler
    if (bookSelect) {
        bookSelect.addEventListener('change', onBookSelected);
    }
});

async function loadBooksList() {
    try {
        const response = await fetch('/api/books');
        const data = await response.json();

        // Handle different response structures
        const books = data.books || data || [];

        // Populate the dropdown
        bookSelect.innerHTML = '<option value="">-- Select a Book --</option>';

        books.forEach(book => {
            const option = document.createElement('option');
            option.value = book.book_id;
            option.textContent = `${book.book_name} (ID: ${book.book_id})`;
            bookSelect.appendChild(option);
        });

        // If book_id was in URL, pre-select it and load its data
        if (currentBookId) {
            bookSelect.value = currentBookId;
            showBookContent(true);
            loadBookData();
        } else {
            showBookContent(false);
        }

    } catch (error) {
        console.error('Error loading books list:', error);
        bookSelect.innerHTML = '<option value="">Error loading books</option>';
    }
}

function onBookSelected() {
    const selectedBookId = bookSelect.value;

    if (selectedBookId) {
        currentBookId = selectedBookId;

        // Update URL without reloading page
        const newUrl = `${window.location.pathname}?book_id=${selectedBookId}`;
        window.history.pushState({ book_id: selectedBookId }, '', newUrl);

        showBookContent(true);
        loadBookData();
    } else {
        currentBookId = null;
        showBookContent(false);

        // Clear URL parameter
        window.history.pushState({}, '', window.location.pathname);
    }
}

function showBookContent(show) {
    if (show) {
        noBookMessage.style.display = 'none';
        bookContent.classList.add('visible');
    } else {
        noBookMessage.style.display = 'block';
        bookContent.classList.remove('visible');

        // Reset page title and breadcrumb
        document.getElementById('page-title').textContent = '⚙️ Book Settings';
        document.getElementById('book-name').textContent = 'Book Settings';
    }
}

function loadBookData() {
    loadBookInfo();
    loadAttributes();
    loadBookSettings(); // Load prompts and configuration
    loadPrompts();      // Load Claude extraction prompts (3B.13)
    loadScanStatus();
    setupScanButton();
}

async function loadBookInfo() {
    try {
        const response = await fetch(`/api/books/${currentBookId}`);
        const book = await response.json();

        document.getElementById('page-title').textContent =
            `⚙️ Settings: ${book.book_name}`;
        document.getElementById('book-name').textContent = book.book_name;

        const uploadDate = book.upload_date
            ? new Date(book.upload_date).toLocaleDateString()
            : 'Unknown';

        document.getElementById('book-info').innerHTML = `
            <strong>Book ID:</strong> ${book.book_id} |
            <strong>Upload Date:</strong> ${uploadDate} |
            <strong>Pages:</strong> ${book.total_pages} |
            <strong>Type:</strong> ${book.file_type} |
            <strong>Status:</strong> ${book.processing_status}
        `;

        // Display PDF file path
        const pdfPathDisplay = document.getElementById('pdf-path-display');
        const pdfFilePath = document.getElementById('pdf-file-path');
        if (book.file_path) {
            pdfFilePath.textContent = book.file_path;
            pdfPathDisplay.style.display = 'block';
        } else {
            pdfPathDisplay.style.display = 'none';
        }

        // Update delete button state based on processing status
        const deleteBtn = document.getElementById('btn-delete-book');
        if (deleteBtn) {
            if (book.processing_status === 'processing') {
                deleteBtn.disabled = true;
                deleteBtn.title = 'Cannot delete - book is processing';
            } else {
                deleteBtn.disabled = false;
                deleteBtn.title = 'Delete this book';
            }
        }
    } catch (error) {
        console.error('Error loading book info:', error);
    }
}

async function loadAttributes() {
    try {
        // Try to load attribute keys from API
        const response = await fetch(`/api/books/${currentBookId}/attribute-keys`);
        const data = await response.json();

        originalAttributes = data.attributes || {};
        currentAttributes = { ...originalAttributes };

        displayAttributes();
    } catch (error) {
        // If endpoint doesn't exist, use defaults
        console.log('Using default attribute names');
        originalAttributes = generateDefaultAttributes();
        currentAttributes = { ...originalAttributes };
        displayAttributes();
    }
}

function generateDefaultAttributes() {
    const defaults = {};
    const systemReserved = [
        'related_image',
        'confidence_category',
        'text_type',
        'contains_code',
        'contains_math',
        'contains_table',
        'language_mix',
        'record_status'
    ];

    for (let i = 1; i <= 80; i++) {
        if (i <= 8) {
            defaults[`attr${i}_key`] = systemReserved[i - 1] || `System_Attr_${i}`;
        } else {
            defaults[`attr${i}_key`] = `Custom_Attribute_${i}`;
        }
    }

    return defaults;
}

function displayAttributes() {
    const container = document.getElementById('attributes-list');
    let html = '';

    // Define reserved attribute groups with their purposes
    const reservedGroups = {
        // Group 1-8: System Reserved
        1: { purpose: 'System Reserved', description: 'related_image' },
        2: { purpose: 'System Reserved', description: 'confidence_category' },
        3: { purpose: 'System Reserved', description: 'text_type' },
        4: { purpose: 'System Reserved', description: 'contains_code' },
        5: { purpose: 'System Reserved', description: 'contains_math' },
        6: { purpose: 'System Reserved', description: 'contains_table' },
        7: { purpose: 'System Reserved', description: 'language_mix' },
        8: { purpose: 'System Reserved', description: 'record_status' },
        // Group 9-10: Additional System
        9: { purpose: 'System Reserved', description: 'processing_flags' },
        10: { purpose: 'System Reserved', description: 'validation_status' },
        // Group 11-13: OCR Text Areas
        11: { purpose: 'OCR Text Areas', description: 'OCR Text Area 1' },
        12: { purpose: 'OCR Text Areas', description: 'OCR Text Area 2' },
        13: { purpose: 'OCR Text Areas', description: 'OCR Text Area 3' },
        // Group 14-16: Manual Text Areas
        14: { purpose: 'Manual Text Areas', description: 'Manual Text Area 1' },
        15: { purpose: 'Manual Text Areas', description: 'Manual Text Area 2' },
        16: { purpose: 'Manual Text Areas', description: 'Manual Text Area 3' },
        // Group 17-21: Diagram Links
        17: { purpose: 'Diagram Links', description: 'Child Diagram 1 / Parent Paragraph' },
        18: { purpose: 'Diagram Links', description: 'Child Diagram 2' },
        19: { purpose: 'Diagram Links', description: 'Child Diagram 3' },
        20: { purpose: 'Diagram Links', description: 'Child Diagram 4' },
        21: { purpose: 'Diagram Links', description: 'Child Diagram 5' }
    };

    // Track current group for section headers
    let currentGroup = '';

    for (let i = 1; i <= 80; i++) {
        const key = `attr${i}_key`;
        const isReserved = i <= 21;
        const reservedInfo = reservedGroups[i];

        // Add section header when group changes
        if (isReserved && reservedInfo && reservedInfo.purpose !== currentGroup) {
            currentGroup = reservedInfo.purpose;
            const groupRange = getGroupRange(i);
            html += `
                <div class="attr-group-header" style="background: #e3f2fd; padding: 10px 15px; margin: 20px 0 10px 0; border-radius: 4px; border-left: 4px solid #2196F3;">
                    <strong>🔒 ${currentGroup}</strong> <span style="color: #666; font-size: 12px;">(Attributes ${groupRange})</span>
                </div>
            `;
        }

        // Add section header for custom attributes
        if (i === 22) {
            html += `
                <div class="attr-group-header" style="background: #e8f5e9; padding: 10px 15px; margin: 20px 0 10px 0; border-radius: 4px; border-left: 4px solid #4CAF50;">
                    <strong>✏️ Custom Attributes</strong> <span style="color: #666; font-size: 12px;">(Attributes 22-80 - Editable)</span>
                </div>
            `;
        }

        const value = isReserved && reservedInfo
            ? reservedInfo.description
            : (currentAttributes[key] || `Custom_Attribute_${i}`);

        html += `
            <div class="attr-row" style="${isReserved ? 'background: #f5f5f5; opacity: 0.85;' : ''}">
                <div class="attr-label">
                    ${isReserved ? '🔒' : '✏️'} Attribute ${i}:
                </div>
                <input type="text"
                       class="attr-input"
                       id="${key}"
                       value="${escapeHtml(value)}"
                       ${isReserved ? 'disabled style="background: #eee; color: #666;"' : ''}
                       placeholder="Enter attribute name...">
                ${!isReserved ? `
                    <button class="edit-btn" onclick="enableEdit('${key}')">
                        ✏️ Edit
                    </button>
                ` : `<span class="locked-icon" style="color: #999; font-size: 12px;">${reservedInfo ? reservedInfo.purpose : 'Reserved'}</span>`}
            </div>
        `;
    }

    container.innerHTML = html;

    // After displaying attributes, populate the dropdowns
    populateAttributeDropdowns();
}

/**
 * Get the range string for a reserved group
 */
function getGroupRange(attrNum) {
    if (attrNum <= 8) return '1-8';
    if (attrNum <= 10) return '9-10';
    if (attrNum <= 13) return '11-13';
    if (attrNum <= 16) return '14-16';
    if (attrNum <= 21) return '17-21';
    return '';
}

// ==================== Book Settings Functions (2026-01-07) ====================

async function loadBookSettings() {
    try {
        const response = await fetch(`/api/books/${currentBookId}/settings`);
        const settings = await response.json();

        // Note: Diagram/equation/table prompts now handled via Claude Extraction Prompts section
        // which uses auto_slicer_config.extraction_prompts (see loadPrompts() function)

        // Load OCR configuration
        document.getElementById('ocr-label1').value = settings.ocr_label1 || '';
        document.getElementById('ocr-label2').value = settings.ocr_label2 || '';
        document.getElementById('ocr-label3').value = settings.ocr_label3 || '';

        // Load Manual configuration
        document.getElementById('manual-label1').value = settings.manual_label1 || '';
        document.getElementById('manual-label2').value = settings.manual_label2 || '';
        document.getElementById('manual-label3').value = settings.manual_label3 || '';

        // Set selected attributes (will populate after dropdowns are filled)
        setTimeout(() => {
            if (settings.ocr_attr1_id) document.getElementById('ocr-attr1').value = settings.ocr_attr1_id;
            if (settings.ocr_attr2_id) document.getElementById('ocr-attr2').value = settings.ocr_attr2_id;
            if (settings.ocr_attr3_id) document.getElementById('ocr-attr3').value = settings.ocr_attr3_id;
            if (settings.manual_attr1_id) document.getElementById('manual-attr1').value = settings.manual_attr1_id;
            if (settings.manual_attr2_id) document.getElementById('manual-attr2').value = settings.manual_attr2_id;
            if (settings.manual_attr3_id) document.getElementById('manual-attr3').value = settings.manual_attr3_id;
        }, 100);

    } catch (error) {
        console.error('Error loading book settings:', error);
    }
}

async function populateAttributeDropdowns() {
    try {
        // Get attributes from already loaded data
        const response = await fetch(`/api/books/${currentBookId}/attribute-keys`);
        const data = await response.json();
        const attributes = data.attributes || [];

        // Get all dropdown elements
        const dropdowns = [
            'ocr-attr1', 'ocr-attr2', 'ocr-attr3',
            'manual-attr1', 'manual-attr2', 'manual-attr3'
        ];

        // Populate each dropdown
        dropdowns.forEach(dropdownId => {
            const dropdown = document.getElementById(dropdownId);
            if (!dropdown) return;

            // Clear existing options except first
            dropdown.innerHTML = '<option value="">Select attribute...</option>';

            // Add options for each attribute
            attributes.forEach(attr => {
                const option = document.createElement('option');
                option.value = attr.attr_number;
                option.textContent = `Attr ${attr.attr_number}: ${attr.key_name || 'Unnamed'}`;

                // Disable system-reserved attributes for selection
                if (attr.is_system_reserved) {
                    option.disabled = true;
                    option.textContent += ' (System Reserved)';
                }

                dropdown.appendChild(option);
            });
        });

    } catch (error) {
        console.error('Error populating attribute dropdowns:', error);
    }
}

function enableEdit(key) {
    const input = document.getElementById(key);
    input.classList.add('editable');
    input.focus();
    input.select();

    input.addEventListener('input', () => {
        currentAttributes[key] = input.value;
    });
}

async function saveAllAttributes() {
    try {
        // 1. Save attribute names (only custom attributes 22-80, not reserved 1-21)
        const attrUpdates = [];
        for (let i = 22; i <= 80; i++) {
            const key = `attr${i}_key`;
            const input = document.getElementById(key);
            if (input && input.value) {
                attrUpdates.push({
                    attr_number: i,
                    key_name: input.value
                });
            }
        }

        if (attrUpdates.length > 0) {
            const attrResponse = await fetch(`/api/books/${currentBookId}/attribute-keys`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates: attrUpdates })
            });

            if (!attrResponse.ok) {
                console.error('Failed to save attribute names');
            }
        }

        // 2. Save book settings (OCR and manual text configuration)
        // Note: Diagram/equation/table prompts now saved via savePrompts() to auto_slicer_config
        const settingsUpdates = {
            // OCR configuration
            ocr_attr1_id: document.getElementById('ocr-attr1').value ? parseInt(document.getElementById('ocr-attr1').value) : null,
            ocr_attr2_id: document.getElementById('ocr-attr2').value ? parseInt(document.getElementById('ocr-attr2').value) : null,
            ocr_attr3_id: document.getElementById('ocr-attr3').value ? parseInt(document.getElementById('ocr-attr3').value) : null,
            ocr_label1: document.getElementById('ocr-label1').value || null,
            ocr_label2: document.getElementById('ocr-label2').value || null,
            ocr_label3: document.getElementById('ocr-label3').value || null,

            // Manual configuration
            manual_attr1_id: document.getElementById('manual-attr1').value ? parseInt(document.getElementById('manual-attr1').value) : null,
            manual_attr2_id: document.getElementById('manual-attr2').value ? parseInt(document.getElementById('manual-attr2').value) : null,
            manual_attr3_id: document.getElementById('manual-attr3').value ? parseInt(document.getElementById('manual-attr3').value) : null,
            manual_label1: document.getElementById('manual-label1').value || null,
            manual_label2: document.getElementById('manual-label2').value || null,
            manual_label3: document.getElementById('manual-label3').value || null
        };

        const settingsResponse = await fetch(`/api/books/${currentBookId}/settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settingsUpdates)
        });

        if (!settingsResponse.ok) {
            throw new Error('Failed to save settings');
        }

        alert('All changes saved successfully!');
        originalAttributes = { ...currentAttributes };
        displayAttributes();

    } catch (error) {
        console.error('Error saving:', error);
        alert('Failed to save changes. Please try again.');
    }
}

function cancelChanges() {
    if (confirm('Discard all changes?')) {
        currentAttributes = { ...originalAttributes };
        displayAttributes();
    }
}

function goBack() {
    window.location.href = '/library';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== Page Scanning Functions ====================

// Progress bar state
let progressPollingInterval = null;
let scanStartTime = null;
let initialScannedCount = 0;
let targetScanCount = 0;

function setupScanButton() {
    if (scanPagesBtn) {
        scanPagesBtn.addEventListener('click', async () => {
            await scanPages();
        });
    }
}

async function loadScanStatus() {
    try {
        const response = await fetch(`/api/check-raw-data/${currentBookId}`);
        if (!response.ok) {
            console.log('Could not load scan status');
            return null;
        }

        const data = await response.json();
        const rawPageStatus = data.raw_page_status;

        // Update status display
        document.getElementById('total-pages-stat').textContent = rawPageStatus.total_pages || 0;
        document.getElementById('scanned-pages-stat').textContent = rawPageStatus.raw_pages_saved || 0;
        document.getElementById('remaining-pages-stat').textContent = rawPageStatus.raw_pages_missing || 0;

        return rawPageStatus;

    } catch (error) {
        console.error('Error loading scan status:', error);
        return null;
    }
}

// Progress bar functions
function showProgressBar(totalToScan, alreadyScanned) {
    const container = document.getElementById('scan-progress-container');
    const progressFill = document.getElementById('scan-progress-fill');
    const progressText = document.getElementById('scan-progress-text');
    const progressStats = document.getElementById('scan-progress-stats');
    const progressCurrent = document.getElementById('scan-progress-current');
    const progressEta = document.getElementById('scan-progress-eta');

    container.classList.add('active');
    progressFill.style.width = '0%';
    progressFill.classList.remove('complete');
    progressText.textContent = '0%';
    progressStats.textContent = `0 / ${totalToScan} pages`;
    progressCurrent.textContent = 'Starting scan...';
    progressEta.textContent = '';

    // Store initial state for progress calculation
    initialScannedCount = alreadyScanned;
    targetScanCount = totalToScan;
    scanStartTime = Date.now();
}

function updateProgressBar(currentScanned, totalToScan, totalPages) {
    const progressFill = document.getElementById('scan-progress-fill');
    const progressText = document.getElementById('scan-progress-text');
    const progressStats = document.getElementById('scan-progress-stats');
    const progressCurrent = document.getElementById('scan-progress-current');
    const progressEta = document.getElementById('scan-progress-eta');

    // Calculate progress based on pages scanned since start
    const pagesScannedThisSession = currentScanned - initialScannedCount;
    const percentComplete = totalToScan > 0 ? Math.round((pagesScannedThisSession / totalToScan) * 100) : 0;

    progressFill.style.width = `${percentComplete}%`;
    progressText.textContent = `${percentComplete}%`;
    progressStats.textContent = `${pagesScannedThisSession} / ${totalToScan} pages`;

    // Calculate ETA
    if (pagesScannedThisSession > 0 && scanStartTime) {
        const elapsedMs = Date.now() - scanStartTime;
        const msPerPage = elapsedMs / pagesScannedThisSession;
        const remainingPages = totalToScan - pagesScannedThisSession;
        const remainingMs = msPerPage * remainingPages;

        if (remainingMs > 0) {
            const remainingSec = Math.ceil(remainingMs / 1000);
            if (remainingSec < 60) {
                progressEta.textContent = `~${remainingSec}s remaining`;
            } else {
                const mins = Math.floor(remainingSec / 60);
                const secs = remainingSec % 60;
                progressEta.textContent = `~${mins}m ${secs}s remaining`;
            }
        }
    }

    // Update current page info
    const remaining = totalPages - currentScanned;
    progressCurrent.textContent = `Scanned ${currentScanned} of ${totalPages} total pages (${remaining} remaining)`;

    // Check if complete
    if (pagesScannedThisSession >= totalToScan) {
        progressFill.classList.add('complete');
        progressCurrent.textContent = `Complete! All ${totalToScan} pages scanned.`;
        progressEta.textContent = '';
        return true;
    }

    return false;
}

function hideProgressBar() {
    const container = document.getElementById('scan-progress-container');
    container.classList.remove('active');

    if (progressPollingInterval) {
        clearInterval(progressPollingInterval);
        progressPollingInterval = null;
    }
}

async function pollScanProgress() {
    try {
        const status = await loadScanStatus();
        if (!status) return;

        const isComplete = updateProgressBar(
            status.raw_pages_saved,
            targetScanCount,
            status.total_pages
        );

        if (isComplete) {
            // Stop polling after a short delay to show completion
            setTimeout(() => {
                if (progressPollingInterval) {
                    clearInterval(progressPollingInterval);
                    progressPollingInterval = null;
                }
                // Re-enable button
                scanPagesBtn.disabled = false;
                scanPagesBtn.textContent = '📸 Scan Unscanned Pages';
            }, 1500);
        }

    } catch (error) {
        console.error('Error polling scan progress:', error);
    }
}

async function scanPages() {
    console.log('scanPages called');

    // Get max_pages value (this now means "scan up to N more unscanned pages")
    const maxPages = maxPagesInput && maxPagesInput.value ? parseInt(maxPagesInput.value) : null;
    console.log('Max pages:', maxPages);

    try {
        // STEP 1: Check if raw pages already exist
        console.log('Checking raw data status...');
        scanPagesBtn.disabled = true;
        scanPagesBtn.textContent = '🔍 Checking status...';

        const checkResponse = await fetch(`/api/check-raw-data/${currentBookId}`);
        if (!checkResponse.ok) {
            throw new Error(`Failed to check raw data: ${checkResponse.statusText}`);
        }

        const checkData = await checkResponse.json();
        console.log('Raw data check result:', checkData);

        // Extract status information
        const rawPageStatus = checkData.raw_page_status;
        const pagesWithoutData = rawPageStatus.pages_without_data || [];

        // Reset button
        scanPagesBtn.disabled = false;
        scanPagesBtn.textContent = '📸 Scan Unscanned Pages';

        // Check if all pages are already scanned
        if (pagesWithoutData.length === 0) {
            alert('✅ All pages are already scanned!\n\nNo new pages to scan.');
            return;
        }

        // Calculate how many pages to scan
        const pagesToScan = maxPages ? Math.min(maxPages, pagesWithoutData.length) : pagesWithoutData.length;
        const pageNumbersToScan = pagesWithoutData.slice(0, pagesToScan);

        // Build status message for user
        let statusMessage = `📊 PAGE SCANNING STATUS:\n\n`;
        statusMessage += `✅ Pages Already Scanned: ${rawPageStatus.raw_pages_saved} / ${rawPageStatus.total_pages}\n`;
        statusMessage += `📄 Pages Not Yet Scanned: ${pagesWithoutData.length}\n\n`;

        statusMessage += `🔒 SAFE MODE: Only unscanned pages will be processed.\n`;
        statusMessage += `   Already-scanned pages are protected to maintain data integrity.\n\n`;

        if (maxPages && maxPages < pagesWithoutData.length) {
            statusMessage += `📌 You requested to scan ${maxPages} pages.\n`;
        }

        statusMessage += `Ready to scan ${pagesToScan} unscanned page(s) at 600 DPI.\n`;

        // Show first few page numbers to scan
        if (pageNumbersToScan.length <= 10) {
            statusMessage += `Pages: ${pageNumbersToScan.join(', ')}\n\n`;
        } else {
            statusMessage += `Pages: ${pageNumbersToScan.slice(0, 10).join(', ')}... and ${pageNumbersToScan.length - 10} more\n\n`;
        }

        statusMessage += `Continue?`;

        console.log('Showing status to user...');

        // Show confirmation with status
        if (!confirm(statusMessage)) {
            console.log('User cancelled after seeing status');
            return;
        }

        console.log('User confirmed, starting page scan for unscanned pages only...');

        // STEP 2: Start page scanning (only unscanned pages)
        scanPagesBtn.disabled = true;
        scanPagesBtn.textContent = `⏳ Scanning...`;

        // Show progress bar
        showProgressBar(pagesToScan, rawPageStatus.raw_pages_saved);

        const requestBody = {
            book_id: parseInt(currentBookId),
            skip_existing: true  // Tell API to skip already-scanned pages
        };

        // Add max_pages if specified
        if (maxPages) {
            requestBody.max_pages = maxPages;
        }

        const response = await fetch(`/api/scan-pages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            hideProgressBar();
            throw new Error(`Failed to start page scanning: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('Scan started:', result);

        // Start polling for progress (every 1 second)
        progressPollingInterval = setInterval(pollScanProgress, 1000);

        // Also do an initial poll immediately
        await pollScanProgress();

    } catch (error) {
        console.error(`Error starting page scan:`, error);
        alert(`Error: ${error.message}`);
        hideProgressBar();
        scanPagesBtn.disabled = false;
        scanPagesBtn.textContent = '📸 Scan Unscanned Pages';
    }
}

// ==================== Auto-Slicer Functions ====================

function openAutoSlicer() {
    if (!currentBookId) {
        alert('Please select a book first');
        return;
    }
    // Navigate to Auto-slicer page with book_id parameter
    window.location.href = `/auto-slicer?book_id=${currentBookId}`;
}

// ==================== Claude Extraction Prompts Functions (3B.13) ====================

// Default prompts - must match extraction.py DEFAULT_PROMPTS
const DEFAULT_PROMPTS = {
    diagram: "Analyze this diagram and provide a detailed description of what it shows, including any labels, relationships, and key information conveyed.",
    table: "Extract all data from this table in a structured format. Include column headers, row labels, and all cell values. Preserve the table structure.",
    equation: "Identify and transcribe this mathematical equation or formula. Explain what it represents and define any variables used.",
    list_bulleted: "Extract all items from this bulleted list. Preserve the hierarchy if there are nested items.",
    list_numbered: "Extract all items from this numbered list in order. Preserve numbering and any sub-items.",
    list_lettered: "Extract all items from this lettered list (a, b, c, etc.). Preserve the lettering sequence and any sub-items.",
    question: "Analyze this question image. Extract the full question text, identify any sub-questions or parts, and note any diagrams or figures referenced.",
    answer: "Analyze this answer image. Extract the complete answer or solution, including any steps, explanations, formulas, or diagrams shown."
};

/**
 * Load extraction prompts from API
 */
async function loadPrompts() {
    if (!currentBookId) return;

    try {
        const response = await fetch(`/api/extraction/${currentBookId}/prompts`);
        if (!response.ok) {
            console.log('Could not load extraction prompts, using defaults');
            applyPromptsToUI(DEFAULT_PROMPTS);
            return;
        }

        const prompts = await response.json();
        applyPromptsToUI(prompts);

    } catch (error) {
        console.error('Error loading extraction prompts:', error);
        applyPromptsToUI(DEFAULT_PROMPTS);
    }
}

/**
 * Apply prompts object to UI textareas
 */
function applyPromptsToUI(prompts) {
    const promptTypes = ['diagram', 'table', 'equation', 'list_bulleted', 'list_numbered', 'list_lettered', 'question', 'answer'];

    promptTypes.forEach(type => {
        const textarea = document.getElementById(`prompt-${type}`);
        if (textarea) {
            textarea.value = prompts[type] || DEFAULT_PROMPTS[type] || '';
        }
    });
}

/**
 * Save extraction prompts to API
 */
async function savePrompts() {
    if (!currentBookId) {
        alert('Please select a book first');
        return;
    }

    try {
        // Gather prompts from textareas
        const prompts = {
            diagram: document.getElementById('prompt-diagram').value.trim() || null,
            table: document.getElementById('prompt-table').value.trim() || null,
            equation: document.getElementById('prompt-equation').value.trim() || null,
            list_bulleted: document.getElementById('prompt-list_bulleted').value.trim() || null,
            list_numbered: document.getElementById('prompt-list_numbered').value.trim() || null,
            list_lettered: document.getElementById('prompt-list_lettered').value.trim() || null,
            question: document.getElementById('prompt-question').value.trim() || null,
            answer: document.getElementById('prompt-answer').value.trim() || null
        };

        const response = await fetch(`/api/extraction/${currentBookId}/prompts`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(prompts)
        });

        if (!response.ok) {
            throw new Error('Failed to save prompts');
        }

        alert('Extraction prompts saved successfully!');

    } catch (error) {
        console.error('Error saving prompts:', error);
        alert('Failed to save prompts. Please try again.');
    }
}

/**
 * Reset prompts to defaults
 */
function resetPrompts() {
    if (!confirm('Reset all prompts to default values?')) {
        return;
    }

    applyPromptsToUI(DEFAULT_PROMPTS);
    alert('Prompts reset to defaults. Click "Save Prompts" to persist the changes.');
}


// ============================================================================
// Book Deletion Functions
// ============================================================================

// State for deletion
let deleteBookData = null;

/**
 * Initiate delete - fetch preview and show summary modal
 */
async function initiateDeleteBook() {
    if (!currentBookId) {
        alert('Please select a book first');
        return;
    }

    try {
        const response = await fetch(`/api/books/${currentBookId}/deletion-preview`);
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

/**
 * Show the summary modal (Step 1)
 */
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

/**
 * Show code verification modal (Step 2)
 */
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

/**
 * Validate the confirmation code
 */
function validateConfirmationCode() {
    const input = document.getElementById('confirmation-code-input').value;
    const expected = deleteBookData.confirmation_code;
    document.getElementById('btn-confirm-delete').disabled = (input !== expected);
}

/**
 * Execute the deletion
 */
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
        
        if (result.success) {
            showToast(`Book "${bookName}" deleted successfully`, 'success');
            // Redirect to Library after a short delay
            setTimeout(() => {
                window.location.href = '/library';
            }, 1500);
        } else {
            showToast(result.error || result.detail || 'Deletion failed', 'error');
        }
    } catch (error) {
        closeDeleteModals();
        showToast('Error: ' + error.message, 'error');
    }
}

/**
 * Close all delete modals
 */
function closeDeleteModals() {
    document.getElementById('delete-summary-modal').classList.remove('active');
    document.getElementById('delete-code-modal').classList.remove('active');
    document.getElementById('btn-confirm-delete').textContent = '🗑️ Delete Book';
    document.getElementById('btn-confirm-delete').disabled = true;
    deleteBookData = null;
}

/**
 * Show toast notification
 */
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
