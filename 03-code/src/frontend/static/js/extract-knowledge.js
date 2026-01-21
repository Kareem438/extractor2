/**
 * Extract Knowledge Units - Frontend JavaScript
 *
 * Handles:
 * - Page selection for extraction
 * - Extraction process and progress
 * - Summary table display
 * - Claude decoding (batch and direct)
 * - Diagram preview and prompt testing
 */

// =============================================================================
// Global State
// =============================================================================

let currentBookId = null;
let bookInfo = null;
let readyPages = [];
let selectedPages = new Set();
let extractionInProgress = false;
let websocket = null;

// Preview state
let previewDiagrams = [];
let previewCurrentIndex = 0;
let defaultPrompts = {};

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Get book_id from URL params
    const urlParams = new URLSearchParams(window.location.search);
    const bookId = urlParams.get('book_id');

    if (bookId) {
        currentBookId = parseInt(bookId);
        loadBookInfo();
        loadReadyPages();
        loadDefaultPrompts();
    } else {
        // Show no book message
        document.getElementById('no-book-message').style.display = 'block';
        document.getElementById('book-content').classList.remove('visible');
    }
});

// =============================================================================
// Data Loading
// =============================================================================

/**
 * Load book information
 */
async function loadBookInfo() {
    try {
        const response = await fetch(`/api/books/${currentBookId}`);
        if (!response.ok) throw new Error('Failed to load book info');

        bookInfo = await response.json();

        // Update breadcrumb
        document.getElementById('breadcrumb-book').textContent = `Extract - ${bookInfo.title}`;
        document.getElementById('breadcrumb-auto-slicer').href = `/auto-slicer?book_id=${currentBookId}`;

        // Show book content
        document.getElementById('no-book-message').style.display = 'none';
        document.getElementById('book-content').classList.add('visible');

    } catch (error) {
        console.error('Error loading book info:', error);
        alert('Failed to load book information');
    }
}

/**
 * Load pages that are ready for extraction
 */
async function loadReadyPages() {
    try {
        const response = await fetch(`/api/extraction/${currentBookId}/ready-pages`);
        if (!response.ok) throw new Error('Failed to load ready pages');

        const data = await response.json();
        readyPages = data.pages || [];

        renderPagesTable();

        // Load saved selection if any
        loadPageSelection();

        // Check if we should show summary
        checkForExistingExtractions();

    } catch (error) {
        console.error('Error loading ready pages:', error);
        document.getElementById('pages-table').style.display = 'none';
        document.getElementById('no-pages-message').style.display = 'block';
    }
}

/**
 * Load default prompts for each class type
 */
async function loadDefaultPrompts() {
    try {
        const response = await fetch(`/api/extraction/${currentBookId}/prompts`);
        if (!response.ok) throw new Error('Failed to load prompts');

        defaultPrompts = await response.json();
    } catch (error) {
        console.error('Error loading prompts:', error);
        // Use system defaults
        defaultPrompts = {
            diagram: "Analyze this diagram and provide a detailed description of what it shows, including any labels, relationships, and key information conveyed.",
            table: "Extract all data from this table in a structured format. Include column headers, row labels, and all cell values. Preserve the table structure.",
            equation: "Identify and transcribe this mathematical equation or formula. Explain what it represents and define any variables used.",
            list_bulleted: "Extract all items from this bulleted list. Preserve the hierarchy if there are nested items.",
            list_numbered: "Extract all items from this numbered list in order. Preserve numbering and any sub-items.",
            list_lettered: "Extract all items from this lettered list (a, b, c, etc.). Preserve the lettering sequence and any sub-items."
        };
    }
}

/**
 * Load saved page selection
 */
async function loadPageSelection() {
    try {
        const response = await fetch(`/api/extraction/${currentBookId}/page-selection`);
        if (!response.ok) return;

        const data = await response.json();
        if (data.selected_pages) {
            selectedPages = new Set(data.selected_pages);
            updateCheckboxes();
        }
    } catch (error) {
        console.error('Error loading page selection:', error);
    }
}

/**
 * Check for existing extractions and show summary if any
 */
async function checkForExistingExtractions() {
    try {
        const response = await fetch(`/api/extraction/${currentBookId}/summary`);
        if (!response.ok) return;

        const data = await response.json();
        if (data.summary && data.summary.length > 0) {
            renderSummaryTable(data.summary);
            document.getElementById('summary-section').style.display = 'block';
            document.getElementById('decode-section').style.display = 'block';
        }
    } catch (error) {
        console.error('Error checking for existing extractions:', error);
    }
}

// =============================================================================
// Page Selection Table
// =============================================================================

/**
 * Render the pages table
 */
function renderPagesTable() {
    const tbody = document.getElementById('pages-table-body');

    if (readyPages.length === 0) {
        document.getElementById('pages-table').style.display = 'none';
        document.getElementById('no-pages-message').style.display = 'block';
        return;
    }

    document.getElementById('pages-table').style.display = 'table';
    document.getElementById('no-pages-message').style.display = 'none';

    tbody.innerHTML = readyPages.map(page => {
        const isExtracted = page.status === 'extracted';
        const isSelected = selectedPages.has(page.page_number);
        const statusClass = isExtracted ? 'status-extracted' : 'status-ready';
        const statusText = isExtracted ? 'Extracted' : 'Ready';

        return `
            <tr>
                <td>
                    <input type="checkbox"
                           data-page="${page.page_number}"
                           ${isSelected && !isExtracted ? 'checked' : ''}
                           ${isExtracted ? 'disabled' : ''}
                           onchange="togglePageSelection(${page.page_number})">
                </td>
                <td>${page.page_number}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>${page.paragraph_count || 0}</td>
                <td>${page.diagram_count || 0}</td>
                <td>${page.table_count || 0}</td>
                <td>${page.equation_count || 0}</td>
                <td>${page.list_count || 0}</td>
            </tr>
        `;
    }).join('');
}

/**
 * Update checkbox states based on selectedPages
 */
function updateCheckboxes() {
    const checkboxes = document.querySelectorAll('#pages-table-body input[type="checkbox"]');
    checkboxes.forEach(cb => {
        const pageNum = parseInt(cb.dataset.page);
        cb.checked = selectedPages.has(pageNum) && !cb.disabled;
    });
}

/**
 * Toggle page selection
 */
function togglePageSelection(pageNumber) {
    if (selectedPages.has(pageNumber)) {
        selectedPages.delete(pageNumber);
    } else {
        selectedPages.add(pageNumber);
    }
    savePageSelection();
}

/**
 * Select all available pages
 */
function selectAllPages() {
    readyPages.forEach(page => {
        if (page.status !== 'extracted') {
            selectedPages.add(page.page_number);
        }
    });
    updateCheckboxes();
    savePageSelection();
}

/**
 * Deselect all pages
 */
function deselectAllPages() {
    selectedPages.clear();
    updateCheckboxes();
    savePageSelection();
}

/**
 * Save page selection to server
 */
async function savePageSelection() {
    try {
        await fetch(`/api/extraction/${currentBookId}/page-selection`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ selected_pages: Array.from(selectedPages) })
        });
    } catch (error) {
        console.error('Error saving page selection:', error);
    }
}

// =============================================================================
// Extraction Process
// =============================================================================

/**
 * Show extraction confirmation modal
 */
function showExtractionConfirmation() {
    if (selectedPages.size === 0) {
        alert('Please select at least one page to extract.');
        return;
    }

    // Calculate totals
    let totalParagraphs = 0;
    let totalDiagrams = 0;
    let totalTables = 0;
    let totalEquations = 0;
    let totalLists = 0;

    readyPages.forEach(page => {
        if (selectedPages.has(page.page_number)) {
            totalParagraphs += page.paragraph_count || 0;
            totalDiagrams += page.diagram_count || 0;
            totalTables += page.table_count || 0;
            totalEquations += page.equation_count || 0;
            totalLists += page.list_count || 0;
        }
    });

    // Update modal
    document.getElementById('modal-pages-count').textContent = selectedPages.size;
    document.getElementById('modal-paragraphs-count').textContent = `~${totalParagraphs}`;
    document.getElementById('modal-diagrams-count').textContent = `~${totalDiagrams}`;
    document.getElementById('modal-tables-count').textContent = `~${totalTables}`;
    document.getElementById('modal-equations-count').textContent = `~${totalEquations}`;
    document.getElementById('modal-lists-count').textContent = `~${totalLists}`;

    document.getElementById('extraction-modal').classList.add('active');
}

/**
 * Close extraction confirmation modal
 */
function closeExtractionModal() {
    document.getElementById('extraction-modal').classList.remove('active');
}

/**
 * Start the extraction process
 */
async function startExtraction() {
    closeExtractionModal();

    // Show progress section
    document.getElementById('progress-section').classList.add('active');
    document.getElementById('extract-btn').disabled = true;
    extractionInProgress = true;

    // Connect WebSocket for progress updates
    connectExtractionWebSocket();

    try {
        const response = await fetch(`/api/extraction/${currentBookId}/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ page_numbers: Array.from(selectedPages) })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Extraction failed');
        }

    } catch (error) {
        console.error('Error starting extraction:', error);
        alert('Failed to start extraction: ' + error.message);
        document.getElementById('progress-section').classList.remove('active');
        document.getElementById('extract-btn').disabled = false;
        extractionInProgress = false;
    }
}

/**
 * Connect WebSocket for extraction progress
 */
function connectExtractionWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    websocket = new WebSocket(`${protocol}//${window.location.host}/ws/extraction/${currentBookId}`);

    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleExtractionProgress(data);
    };

    websocket.onerror = function(error) {
        console.error('WebSocket error:', error);
    };

    websocket.onclose = function() {
        console.log('WebSocket closed');
    };
}

/**
 * Handle extraction progress updates
 */
function handleExtractionProgress(data) {
    if (data.type === 'progress') {
        const percent = Math.round((data.current / data.total) * 100);
        document.getElementById('progress-bar').style.width = `${percent}%`;
        document.getElementById('progress-bar').textContent = `${percent}%`;
        document.getElementById('progress-current').textContent =
            `Processing page ${data.current_page} (${data.current} of ${data.total})`;
        document.getElementById('progress-counts').textContent =
            `Paragraphs: ${data.paragraphs_extracted || 0} | Images: ${data.images_extracted || 0}`;
    } else if (data.type === 'complete') {
        extractionComplete(data);
    } else if (data.type === 'error') {
        extractionError(data.message);
    }
}

/**
 * Handle extraction completion
 */
function extractionComplete(data) {
    extractionInProgress = false;
    document.getElementById('extract-btn').disabled = false;

    // Update progress to 100%
    document.getElementById('progress-bar').style.width = '100%';
    document.getElementById('progress-bar').textContent = '100%';
    document.getElementById('progress-current').textContent = 'Extraction complete!';

    // Clear selection for extracted pages
    selectedPages.clear();

    // Reload pages and show summary
    setTimeout(() => {
        loadReadyPages();
        document.getElementById('progress-section').classList.remove('active');
        document.getElementById('summary-section').style.display = 'block';
        document.getElementById('decode-section').style.display = 'block';

        // Load summary
        checkForExistingExtractions();
    }, 1500);

    if (websocket) {
        websocket.close();
    }
}

/**
 * Handle extraction error
 */
function extractionError(message) {
    extractionInProgress = false;
    document.getElementById('extract-btn').disabled = false;
    document.getElementById('progress-section').classList.remove('active');

    alert('Extraction error: ' + message);

    if (websocket) {
        websocket.close();
    }
}

// =============================================================================
// Summary Table
// =============================================================================

/**
 * Render the summary table
 */
function renderSummaryTable(summary) {
    const tbody = document.getElementById('summary-table-body');

    tbody.innerHTML = summary.map(row => {
        const diagramsCell = formatDecodedCount(row.diagrams_decoded, row.diagrams_total);
        const tablesCell = formatDecodedCount(row.tables_decoded, row.tables_total);
        const equationsCell = formatDecodedCount(row.equations_decoded, row.equations_total);
        const listsCell = formatDecodedCount(row.lists_decoded, row.lists_total);

        return `
            <tr data-l3-title="${row.l3_title}">
                <td>${row.l3_title || '(No L3 Title)'}</td>
                <td>${row.page_range || '-'}</td>
                <td class="count-cell">${row.paragraphs || 0}</td>
                <td class="count-cell">${diagramsCell}</td>
                <td class="count-cell">${tablesCell}</td>
                <td class="count-cell">${equationsCell}</td>
                <td class="count-cell">${listsCell}</td>
            </tr>
        `;
    }).join('');
}

/**
 * Format decoded/total count display
 */
function formatDecodedCount(decoded, total) {
    if (total === 0) return '0';
    if (decoded === total) {
        return `<span class="decoded-count">${decoded}/${total}</span>`;
    }
    return `<span class="pending-count">${decoded}/${total}</span>`;
}

/**
 * Filter summary table by type
 */
function filterSummary(type) {
    // Update active tab
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // TODO: Implement actual filtering logic
    console.log('Filter by:', type);
}

// =============================================================================
// Claude Decoding
// =============================================================================

/**
 * Start decoding all unprocessed diagrams
 */
async function startDecoding() {
    const mode = document.querySelector('input[name="decode-mode"]:checked').value;

    if (!confirm(`Start ${mode === 'batch' ? 'batch' : 'direct'} decoding for all unprocessed diagrams?`)) {
        return;
    }

    const endpoint = mode === 'batch' ? 'decode-batch' : 'decode-direct';

    try {
        const response = await fetch(`/api/extraction/${currentBookId}/${endpoint}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Decoding failed');
        }

        const data = await response.json();

        if (mode === 'batch') {
            // Show batch status
            document.getElementById('batch-status').style.display = 'block';
            document.getElementById('batch-status-text').textContent =
                `Batch submitted: ${data.batch_id}. Processing...`;

            // Start polling for status
            pollBatchStatus(data.batch_id);
        } else {
            alert('Direct decoding started. Results will appear shortly.');
            // Refresh summary after a delay
            setTimeout(checkForExistingExtractions, 3000);
        }

    } catch (error) {
        console.error('Error starting decoding:', error);
        alert('Failed to start decoding: ' + error.message);
    }
}

/**
 * Poll for batch status
 */
async function pollBatchStatus(batchId) {
    try {
        const response = await fetch(`/api/extraction/${currentBookId}/batch-status?batch_id=${batchId}`);
        if (!response.ok) throw new Error('Failed to get batch status');

        const data = await response.json();

        document.getElementById('batch-status-text').textContent =
            `Status: ${data.status} | Progress: ${data.completed || 0}/${data.total || 0}`;

        if (data.status === 'completed') {
            document.getElementById('batch-status-text').textContent = 'Batch completed!';
            checkForExistingExtractions();
        } else if (data.status === 'failed') {
            document.getElementById('batch-status-text').textContent = 'Batch failed: ' + (data.error || 'Unknown error');
        } else {
            // Continue polling
            setTimeout(() => pollBatchStatus(batchId), 5000);
        }

    } catch (error) {
        console.error('Error polling batch status:', error);
    }
}

// =============================================================================
// Preview Modal
// =============================================================================

/**
 * Open preview modal
 */
async function openPreviewModal() {
    document.getElementById('preview-modal').classList.add('active');
    await loadPreviewDiagrams();
}

/**
 * Close preview modal
 */
function closePreviewModal() {
    document.getElementById('preview-modal').classList.remove('active');
}

/**
 * Load diagrams for preview
 */
async function loadPreviewDiagrams() {
    const typeFilter = document.getElementById('preview-type-filter').value;

    try {
        let url = `/api/extraction/${currentBookId}/diagrams-for-preview`;
        if (typeFilter !== 'all') {
            url += `?type=${typeFilter}`;
        }

        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load diagrams');

        const data = await response.json();
        previewDiagrams = data.diagrams || [];
        previewCurrentIndex = 0;

        showPreviewDiagram();

    } catch (error) {
        console.error('Error loading preview diagrams:', error);
        previewDiagrams = [];
        showPreviewDiagram();
    }
}

/**
 * Load preview diagram (alias)
 */
function loadPreviewDiagram() {
    loadPreviewDiagrams();
}

/**
 * Show current preview diagram
 */
function showPreviewDiagram() {
    const imageEl = document.getElementById('preview-image');
    const noImageEl = document.getElementById('preview-no-image');
    const infoEl = document.getElementById('preview-info');
    const navInfoEl = document.getElementById('preview-nav-info');
    const promptEl = document.getElementById('preview-prompt');
    const responseEl = document.getElementById('preview-response');

    if (previewDiagrams.length === 0) {
        imageEl.style.display = 'none';
        noImageEl.style.display = 'block';
        infoEl.textContent = 'Page: - | Type: - | L3: -';
        navInfoEl.textContent = '0 of 0';
        promptEl.value = '';
        responseEl.innerHTML = '<span style="color: #999;">No diagrams available</span>';
        return;
    }

    const diagram = previewDiagrams[previewCurrentIndex];

    // Load image
    imageEl.src = `/api/extraction/${currentBookId}/diagram-image/${diagram.id}`;
    imageEl.style.display = 'block';
    noImageEl.style.display = 'none';

    // Update info
    infoEl.textContent = `Page: ${diagram.page_number} | Type: ${diagram.diagram_type} | L3: ${diagram.l3_title || '-'}`;
    navInfoEl.textContent = `${previewCurrentIndex + 1} of ${previewDiagrams.length}`;

    // Load prompt for this type
    const promptType = diagram.diagram_type.startsWith('list_') ? diagram.diagram_type : diagram.diagram_type;
    promptEl.value = defaultPrompts[promptType] || defaultPrompts['diagram'] || '';

    // Clear response
    responseEl.innerHTML = '<span style="color: #999;">Click "Test Prompt" to see Claude\'s response</span>';
}

/**
 * Previous preview diagram
 */
function prevPreviewDiagram() {
    if (previewCurrentIndex > 0) {
        previewCurrentIndex--;
        showPreviewDiagram();
    }
}

/**
 * Next preview diagram
 */
function nextPreviewDiagram() {
    if (previewCurrentIndex < previewDiagrams.length - 1) {
        previewCurrentIndex++;
        showPreviewDiagram();
    }
}

/**
 * Test prompt on current diagram
 */
async function testPrompt() {
    if (previewDiagrams.length === 0) return;

    const diagram = previewDiagrams[previewCurrentIndex];
    const prompt = document.getElementById('preview-prompt').value;
    const responseEl = document.getElementById('preview-response');

    responseEl.innerHTML = '<span style="color: #999;">Testing prompt...</span>';

    try {
        const response = await fetch(`/api/extraction/${currentBookId}/preview-decode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                diagram_id: diagram.id,
                prompt: prompt
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Test failed');
        }

        const data = await response.json();
        responseEl.innerHTML = `<pre style="white-space: pre-wrap; margin: 0;">${escapeHtml(data.response)}</pre>`;

    } catch (error) {
        console.error('Error testing prompt:', error);
        responseEl.innerHTML = `<span style="color: #f44336;">Error: ${escapeHtml(error.message)}</span>`;
    }
}

/**
 * Save current prompt as default for this type
 */
async function saveAsDefaultPrompt() {
    if (previewDiagrams.length === 0) return;

    const diagram = previewDiagrams[previewCurrentIndex];
    const prompt = document.getElementById('preview-prompt').value;
    const promptType = diagram.diagram_type;

    try {
        const response = await fetch(`/api/extraction/${currentBookId}/prompts`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                [promptType]: prompt
            })
        });

        if (!response.ok) throw new Error('Failed to save prompt');

        // Update local cache
        defaultPrompts[promptType] = prompt;

        alert(`Default prompt for "${promptType}" saved successfully.`);

    } catch (error) {
        console.error('Error saving prompt:', error);
        alert('Failed to save prompt: ' + error.message);
    }
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
