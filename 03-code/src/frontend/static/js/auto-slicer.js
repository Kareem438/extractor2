/**
 * Auto-Slicer Frontend JavaScript
 *
 * Handles:
 * - Book selection and loading
 * - Configuration management
 * - Dynamic row management for titles/batches
 * - Canvas drawing for OCR boundaries
 * - WebSocket progress updates
 * - Button state management
 */

// =============================================================================
// Global State
// =============================================================================

let currentBookId = null;
let currentConfig = null;
let websocket = null;
let isRunning = false;
let isPaused = false;
let startTime = null;

// Preview state
let previewParagraphs = [];
let previewCurrentPage = 1;
const PREVIEW_PER_PAGE = 20;
let currentDetailsClipIndex = null;
let collapsibleSectionStates = {};

// Canvas state for rectangle drawing
let canvasState = {
    image: null,
    zoom: 0.1,
    rectangles: [],
    isDrawing: false,
    startX: 0,
    startY: 0,
    currentRect: null
};

// Boundary being edited
let editingBoundary = null;
let boundaryIndex = -1;

// =============================================================================
// Initialization
// =============================================================================

// Store scroll_to parameter for later use
let scrollToClipId = null;

document.addEventListener('DOMContentLoaded', function() {
    loadBooks();
    setupCanvasEvents();
    setupModalEvents();
    setupYoloClassCheckboxListeners();  // Setup listeners for YOLO class checkboxes

    // Check for book_id in URL params, then localStorage
    const urlParams = new URLSearchParams(window.location.search);
    let bookId = urlParams.get('book_id');
    scrollToClipId = urlParams.get('scroll_to') ? parseInt(urlParams.get('scroll_to')) : null;

    // If no URL param, try localStorage
    if (!bookId) {
        bookId = localStorage.getItem('autoSlicerLastBookId');
    }

    if (bookId) {
        setTimeout(() => {
            const select = document.getElementById('book-select');
            if (select.querySelector(`option[value="${bookId}"]`)) {
                select.value = bookId;
                onBookSelect();
            }
        }, 500);
    }
});

// Setup modal event listeners
function setupModalEvents() {
    const modal = document.getElementById('details-modal');
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeDetailsModal();
            }
        });
    }

    // Close modal on Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            if (modal && modal.classList.contains('visible')) {
                closeDetailsModal();
            }
        }
    });
}

// =============================================================================
// Book Loading
// =============================================================================

async function loadBooks() {
    try {
        const response = await fetch('/api/books?limit=100');
        const data = await response.json();

        const select = document.getElementById('book-select');
        select.innerHTML = '<option value="">-- Select a Book --</option>';

        data.books.forEach(book => {
            const option = document.createElement('option');
            option.value = book.book_id;
            option.textContent = `${book.book_name} (${book.total_pages} pages)`;
            select.appendChild(option);
        });

        select.addEventListener('change', onBookSelect);
    } catch (error) {
        console.error('Failed to load books:', error);
    }
}

async function onBookSelect() {
    const select = document.getElementById('book-select');
    const bookId = select.value;

    if (!bookId) {
        document.getElementById('no-book-message').style.display = 'block';
        document.getElementById('book-content').classList.remove('visible');
        currentBookId = null;
        hidePreviewSection();
        return;
    }

    currentBookId = parseInt(bookId);

    // Save to localStorage for next visit
    localStorage.setItem('autoSlicerLastBookId', bookId);

    document.getElementById('no-book-message').style.display = 'none';
    document.getElementById('book-content').classList.add('visible');

    // Load book config
    await loadConfig();

    // Update breadcrumb
    const bookName = select.options[select.selectedIndex].text;
    document.getElementById('breadcrumb-book').textContent = bookName;

    // Update dashboard link
    const dashboardLink = document.getElementById('dashboard-link');
    if (dashboardLink) {
        dashboardLink.href = `/extraction-dashboard?book_id=${currentBookId}`;
        dashboardLink.style.display = 'inline-block';
    }

    // Check status
    await checkStatus();

    // Initialize page viewer
    const option = select.options[select.selectedIndex];
    const match = option.textContent.match(/\((\d+) pages\)/);
    if (match) {
        viewerState.totalPages = parseInt(match[1]);
    }
    viewerState.currentPage = 1;
    initViewerCanvas();
    loadViewerPage();

    // Load existing paragraphs for preview
    await loadPreviewParagraphs();

    // Check if there are existing layout detection regions
    await checkExistingLayoutRegions();
    
    // Check scanning status and show warning if needed
    await checkScanningStatus(currentBookId);
}

// Check if book has been scanned
async function checkScanningStatus(bookId) {
    try {
        const response = await fetch(`/api/books/${bookId}`);
        if (response.ok) {
            const book = await response.json();
            const warningEl = document.getElementById('scanning-status-warning');
            if (warningEl) {
                if (book.progress && book.progress.pages_scanned === 0) {
                    warningEl.style.display = 'block';
                } else {
                    warningEl.style.display = 'none';
                }
            }
        }
    } catch (e) {
        console.error('Error checking scanning status:', e);
    }
}

// =============================================================================
// Configuration Management
// =============================================================================

async function loadConfig() {
    if (!currentBookId) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/config`);
        const data = await response.json();

        currentConfig = data.config || {};

        // Update book info
        document.getElementById('book-pages-info').textContent = `Total: ${data.total_pages} pages`;
        document.getElementById('end-page').value = data.total_pages;
        document.getElementById('end-page').max = data.total_pages;
        document.getElementById('boundary-end').value = data.total_pages;

        // Load page range
        if (currentConfig.page_range) {
            document.getElementById('start-page').value = currentConfig.page_range.start || 1;
            document.getElementById('end-page').value = currentConfig.page_range.end || data.total_pages;
        }

        // Load titles
        loadTitles();

        // Load batches
        loadBatches();

        // Load boundaries
        loadBoundaries();

        // Load layout detection config (enabled classes)
        await loadLayoutDetectionConfig();

    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

/**
 * Load layout detection config and apply enabled classes to checkboxes.
 * This restores the checkbox state from the last detection run.
 */
async function loadLayoutDetectionConfig() {
    if (!currentBookId) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/layout-config`);
        if (!response.ok) {
            console.log('No layout config found, using defaults');
            return;
        }

        const config = await response.json();
        console.log('Layout detection config loaded:', config);

        if (config.enabled_classes && config.enabled_classes.length > 0) {
            applyEnabledClassesToCheckboxes(config.enabled_classes);
        }
    } catch (error) {
        console.error('Failed to load layout detection config:', error);
    }
}

/**
 * Apply enabled classes to YOLO detection checkboxes.
 * Maps class names back to checkbox IDs and sets their checked state.
 */
function applyEnabledClassesToCheckboxes(enabledClasses) {
    // Reverse mapping from class names to checkbox IDs
    const classToCheckbox = {
        'paragraph': 'yolo-class-paragraph',
        'diagram': 'yolo-class-diagram',
        'equation': 'yolo-class-equation',
        'list_bulleted': 'yolo-class-list',
        'list_numbered': 'yolo-class-list',
        'list_lettered': 'yolo-class-list',
        'list_item': 'yolo-class-list',
        'header': 'yolo-class-header',
        'footer': 'yolo-class-footer',
        'title_level_1': 'yolo-class-title-l1',
        'title_level_2': 'yolo-class-title-l2',
        'title_level_3': 'yolo-class-title-l3',
        'caption': 'yolo-class-caption',
        'reference': 'yolo-class-reference',
        'question': 'yolo-class-question',
        'answer': 'yolo-class-answer'
    };

    // First, uncheck all checkboxes
    const allCheckboxIds = [
        'yolo-class-paragraph', 'yolo-class-diagram', 'yolo-class-equation',
        'yolo-class-list', 'yolo-class-header', 'yolo-class-footer',
        'yolo-class-title-l1', 'yolo-class-title-l2', 'yolo-class-title-l3',
        'yolo-class-caption', 'yolo-class-reference',
        'yolo-class-question', 'yolo-class-answer'
    ];

    allCheckboxIds.forEach(id => {
        const checkbox = document.getElementById(id);
        if (checkbox) checkbox.checked = false;
    });

    // Then check the ones that are enabled
    const checkedIds = new Set();
    enabledClasses.forEach(className => {
        const checkboxId = classToCheckbox[className];
        if (checkboxId && !checkedIds.has(checkboxId)) {
            const checkbox = document.getElementById(checkboxId);
            if (checkbox) {
                checkbox.checked = true;
                checkedIds.add(checkboxId);
            }
        }
    });

    console.log('Applied enabled classes to checkboxes:', enabledClasses);
}

async function loadTitles() {
    // Load L1 and L2 titles from database, L3 from JSON config
    
    // Load L1 titles from database
    try {
        const l1Response = await fetch(`/api/books/${currentBookId}/l1-titles`);
        const l1Data = await l1Response.json();
        
        const l1Container = document.getElementById('level1-titles');
        if (l1Container) {
            l1Container.innerHTML = '';
            (l1Data.titles || []).forEach(t => {
                addTitleRow('level1', t.title_text, t.start_page, t.end_page, t.id, t.external_writable_start, t.external_writable_end);
            });
        }
    } catch (error) {
        console.warn('Could not load L1 titles from database, falling back to JSON:', error);
        // Fallback to JSON config
        const l1Container = document.getElementById('level1-titles');
        if (l1Container) {
            l1Container.innerHTML = '';
            const titles = currentConfig.titles?.level1 || [];
            titles.forEach(t => addTitleRow('level1', t.title, t.start_page, t.end_page, null, t.writable_start, t.writable_end));
        }
    }
    
    // Load L2 titles from database
    try {
        const l2Response = await fetch(`/api/books/${currentBookId}/l2-titles`);
        const l2Data = await l2Response.json();
        
        const l2Container = document.getElementById('level2-titles');
        if (l2Container) {
            l2Container.innerHTML = '';
            (l2Data.titles || []).forEach(t => {
                addTitleRow('level2', t.title_text, t.start_page, t.end_page, t.id, t.external_writable_start, t.external_writable_end);
            });
        }
    } catch (error) {
        console.warn('Could not load L2 titles from database, falling back to JSON:', error);
        // Fallback to JSON config
        const l2Container = document.getElementById('level2-titles');
        if (l2Container) {
            l2Container.innerHTML = '';
            const titles = currentConfig.titles?.level2 || [];
            titles.forEach(t => addTitleRow('level2', t.title, t.start_page, t.end_page, null, t.writable_start, t.writable_end));
        }
    }
    
    // Load L3 titles from JSON config (these are detected by YOLO, not stored in DB)
    const l3Container = document.getElementById('level3-titles');
    if (l3Container) {
        l3Container.innerHTML = '';
        const titles = currentConfig.titles?.level3 || [];
        titles.forEach(t => addTitleRow('level3', t.title, t.start_page, t.end_page, null));
    }
}

function loadBatches() {
    const container = document.getElementById('batches');
    container.innerHTML = '';

    const batches = currentConfig.batches || [];
    batches.forEach(b => addBatchRow(b.start_page, b.end_page));
}

function loadBoundaries() {
    const container = document.getElementById('boundary-list');
    container.innerHTML = '';

    const boundaries = currentConfig.ocr_boundaries || [];
    boundaries.forEach((b, i) => {
        const rectCount = b.rectangles?.length || 0;
        const div = document.createElement('div');
        div.className = 'boundary-item';
        div.innerHTML = `
            <div class="boundary-info">
                <strong>Pages ${b.start_page} - ${b.end_page}</strong>
                <span>${rectCount} rectangle(s)</span>
            </div>
            <button type="button" class="btn btn-secondary" onclick="editBoundary(${i})">Edit</button>
            <button type="button" class="btn btn-delete" onclick="deleteBoundary(${i})">Delete</button>
        `;
        container.appendChild(div);
    });
}

async function saveConfig() {
    if (!currentBookId) return;

    // Gather configuration
    const config = {
        page_range: {
            start: parseInt(document.getElementById('start-page').value) || 1,
            end: parseInt(document.getElementById('end-page').value) || 1
        },
        titles: gatherTitles(),
        batches: gatherBatches(),
        ocr_boundaries: currentConfig.ocr_boundaries || []
    };

    try {
        // Save to JSON config
        const response = await fetch(`/api/auto-slicer/${currentBookId}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();
        if (result.success) {
            // Also sync L1/L2 titles to database
            await syncTitlesToDatabase(config.titles);
            
            showMessage('Configuration saved successfully', 'success');
            currentConfig = config;
        } else {
            showMessage('Failed to save configuration', 'error');
        }
    } catch (error) {
        console.error('Failed to save config:', error);
        showMessage('Failed to save configuration', 'error');
    }
}

async function syncTitlesToDatabase(titles) {
    /**
     * Sync L1/L2 titles from JSON config to database tables.
     * This keeps the database in sync with the JSON config.
     */
    try {
        const response = await fetch(`/api/books/${currentBookId}/sync-titles-to-db`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ titles: titles })
        });
        
        const result = await response.json();
        if (result.success) {
            console.log(`Synced titles to DB: ${result.l1_synced} L1, ${result.l2_synced} L2`);
        } else {
            console.warn('Failed to sync titles to database:', result);
        }
    } catch (error) {
        console.error('Error syncing titles to database:', error);
        // Don't show error to user - JSON save succeeded, DB sync is secondary
    }
}

function gatherTitles() {
    const titles = { level1: [], level2: [], level3: [] };

    ['level1', 'level2', 'level3'].forEach(level => {
        const rows = document.querySelectorAll(`#${level}-titles .dynamic-row`);
        rows.forEach(row => {
            const title = row.querySelector('.title-input').value.trim();
            const startPage = parseInt(row.querySelector('.start-page').value) || 0;
            const endPage = parseInt(row.querySelector('.end-page').value) || 0;
            
            // Get writable range for L1/L2 titles
            const writableStartEl = row.querySelector('.writable-start');
            const writableEndEl = row.querySelector('.writable-end');
            const writableStart = writableStartEl ? parseInt(writableStartEl.value) : null;
            const writableEnd = writableEndEl ? parseInt(writableEndEl.value) : null;

            if (title && startPage && endPage) {
                const titleData = { title, start_page: startPage, end_page: endPage };
                if (writableStart !== null) titleData.writable_start = writableStart;
                if (writableEnd !== null) titleData.writable_end = writableEnd;
                titles[level].push(titleData);
            }
        });
    });

    return titles;
}

function gatherBatches() {
    const batches = [];
    const rows = document.querySelectorAll('#batches .dynamic-row');

    rows.forEach(row => {
        const startPage = parseInt(row.querySelector('.start-page').value) || 0;
        const endPage = parseInt(row.querySelector('.end-page').value) || 0;

        if (startPage && endPage) {
            batches.push({ start_page: startPage, end_page: endPage });
        }
    });

    return batches;
}

// =============================================================================
// Dynamic Row Management
// =============================================================================

function addTitleRow(level, title = '', startPage = '', endPage = '', titleId = null, writableStart = null, writableEnd = null) {
    const container = document.getElementById(`${level}-titles`);
    const row = document.createElement('div');
    row.className = 'dynamic-row';
    
    // Only show Attributes button for L1 and L2 titles (not L3)
    const showAttributesBtn = (level === 'level1' || level === 'level2') && titleId;
    const attrBtnHtml = showAttributesBtn 
        ? `<button type="button" class="btn btn-secondary btn-sm" onclick="openAttributeEditor('${level}', ${titleId})" title="Edit Attributes">Attrs</button>`
        : '';
    
    // Writable range fields for L1 and L2 (for cross-book access)
    const defaultWritableStart = level === 'level1' ? 151 : (level === 'level2' ? 101 : null);
    const defaultWritableEnd = level === 'level1' ? 200 : (level === 'level2' ? 150 : null);
    const showWritableRange = (level === 'level1' || level === 'level2');
    const writableRangeHtml = showWritableRange 
        ? `<span class="writable-range-label" title="External writable range for cross-book access">Writable:</span>
           <input type="number" class="page-input writable-start" placeholder="Start" min="1" value="${writableStart || defaultWritableStart}" title="First attribute writable by other books">
           <span>-</span>
           <input type="number" class="page-input writable-end" placeholder="End" min="1" value="${writableEnd || defaultWritableEnd}" title="Last attribute writable by other books">`
        : '';
    
    row.innerHTML = `
        <input type="text" class="title-input" placeholder="Title text" value="${title}" data-title-id="${titleId || ''}">
        <input type="number" class="page-input start-page" placeholder="Start" min="1" value="${startPage}">
        <input type="number" class="page-input end-page" placeholder="End" min="1" value="${endPage}">
        ${writableRangeHtml}
        ${attrBtnHtml}
        <button type="button" class="btn btn-delete" onclick="this.parentElement.remove()">Delete</button>
    `;
    container.appendChild(row);
}

function openAttributeEditor(level, titleId) {
    /**
     * Open the attribute editor page for an L1 or L2 title.
     */
    const levelNum = level === 'level1' ? 'l1' : 'l2';
    window.open(`/book/${currentBookId}/${levelNum}-title/${titleId}/attributes`, '_blank');
}

function addBatchRow(startPage = '', endPage = '') {
    const container = document.getElementById('batches');
    const row = document.createElement('div');
    row.className = 'dynamic-row';
    row.innerHTML = `
        <span style="color: #666;">Batch:</span>
        <input type="number" class="page-input start-page" placeholder="Start" min="1" value="${startPage}">
        <span>to</span>
        <input type="number" class="page-input end-page" placeholder="End" min="1" value="${endPage}">
        <button type="button" class="btn btn-delete" onclick="this.parentElement.remove()">Delete</button>
    `;
    container.appendChild(row);
}

// =============================================================================
// OCR Boundary Management
// =============================================================================

function openBoundaryModal() {
    editingBoundary = null;
    boundaryIndex = -1;
    canvasState.rectangles = [];

    document.getElementById('boundary-start').value = document.getElementById('start-page').value || 1;
    document.getElementById('boundary-end').value = document.getElementById('end-page').value || 1;
    document.getElementById('preview-page').value = document.getElementById('start-page').value || 1;

    document.getElementById('boundary-modal').classList.add('active');
    updateRectangleList();
}

function closeBoundaryModal() {
    document.getElementById('boundary-modal').classList.remove('active');
    editingBoundary = null;
    boundaryIndex = -1;
}

function editBoundary(index) {
    const boundaries = currentConfig.ocr_boundaries || [];
    if (index < 0 || index >= boundaries.length) return;

    editingBoundary = boundaries[index];
    boundaryIndex = index;

    document.getElementById('boundary-start').value = editingBoundary.start_page;
    document.getElementById('boundary-end').value = editingBoundary.end_page;
    document.getElementById('preview-page').value = editingBoundary.start_page;

    // Load rectangles
    canvasState.rectangles = (editingBoundary.rectangles || []).map(r => ({
        label: r.label,
        x: r.x,
        y: r.y,
        width: r.width,
        height: r.height,
        target: r.target
    }));

    document.getElementById('boundary-modal').classList.add('active');
    loadPreview();
    updateRectangleList();
}

function deleteBoundary(index) {
    if (!confirm('Delete this OCR boundary?')) return;

    currentConfig.ocr_boundaries = currentConfig.ocr_boundaries || [];
    currentConfig.ocr_boundaries.splice(index, 1);
    loadBoundaries();
}

async function loadPreview() {
    const pageNum = parseInt(document.getElementById('preview-page').value) || 1;
    const canvas = document.getElementById('preview-canvas');
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#666';
    ctx.font = '16px Arial';
    ctx.fillText('Loading page preview...', 20, 50);

    try {
        // Get page image from auto-slicer endpoint (uses raw_pages table)
        const response = await fetch(`/api/auto-slicer/${currentBookId}/page/${pageNum}/image`);
        if (!response.ok) throw new Error('Failed to load page');

        const blob = await response.blob();
        const img = new Image();
        img.onload = () => {
            canvasState.image = img;
            redrawCanvas();
        };
        img.src = URL.createObjectURL(blob);

    } catch (error) {
        console.error('Failed to load preview:', error);
        ctx.fillStyle = '#f44336';
        ctx.fillText('Failed to load page preview', 20, 50);
    }
}

function updateZoom() {
    canvasState.zoom = parseFloat(document.getElementById('preview-zoom').value);
    redrawCanvas();
}

function redrawCanvas() {
    const canvas = document.getElementById('preview-canvas');
    const ctx = canvas.getContext('2d');

    if (!canvasState.image) return;

    // Resize canvas
    canvas.width = canvasState.image.width * canvasState.zoom;
    canvas.height = canvasState.image.height * canvasState.zoom;

    // Draw image
    ctx.drawImage(canvasState.image, 0, 0, canvas.width, canvas.height);

    // Draw existing rectangles
    canvasState.rectangles.forEach((rect, i) => {
        const x = rect.x * canvasState.zoom;
        const y = rect.y * canvasState.zoom;
        const w = rect.width * canvasState.zoom;
        const h = rect.height * canvasState.zoom;

        ctx.strokeStyle = i === 0 ? '#f44336' : '#2196F3';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);

        // Label
        ctx.fillStyle = i === 0 ? '#f44336' : '#2196F3';
        ctx.font = '12px Arial';
        ctx.fillText(rect.label || `Rectangle ${i + 1}`, x + 4, y + 14);
    });

    // Draw current rectangle being drawn
    if (canvasState.currentRect) {
        ctx.strokeStyle = '#4CAF50';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(
            canvasState.currentRect.x,
            canvasState.currentRect.y,
            canvasState.currentRect.width,
            canvasState.currentRect.height
        );
        ctx.setLineDash([]);
    }
}

function setupCanvasEvents() {
    const canvas = document.getElementById('preview-canvas');

    canvas.addEventListener('mousedown', (e) => {
        if (!canvasState.image) return;

        const rect = canvas.getBoundingClientRect();
        canvasState.isDrawing = true;
        canvasState.startX = e.clientX - rect.left;
        canvasState.startY = e.clientY - rect.top;
    });

    canvas.addEventListener('mousemove', (e) => {
        if (!canvasState.isDrawing) return;

        const rect = canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;

        canvasState.currentRect = {
            x: Math.min(canvasState.startX, currentX),
            y: Math.min(canvasState.startY, currentY),
            width: Math.abs(currentX - canvasState.startX),
            height: Math.abs(currentY - canvasState.startY)
        };

        redrawCanvas();
    });

    canvas.addEventListener('mouseup', () => {
        if (!canvasState.isDrawing || !canvasState.currentRect) return;

        canvasState.isDrawing = false;

        // Only add if rectangle is large enough
        if (canvasState.currentRect.width > 10 && canvasState.currentRect.height > 10) {
            // Convert to image coordinates
            const newRect = {
                label: canvasState.rectangles.length === 0 ? 'Main Text' : `Region ${canvasState.rectangles.length + 1}`,
                x: Math.round(canvasState.currentRect.x / canvasState.zoom),
                y: Math.round(canvasState.currentRect.y / canvasState.zoom),
                width: Math.round(canvasState.currentRect.width / canvasState.zoom),
                height: Math.round(canvasState.currentRect.height / canvasState.zoom),
                target: canvasState.rectangles.length === 0 ? 'text_content' : 'attr31'
            };

            canvasState.rectangles.push(newRect);
            updateRectangleList();
        }

        canvasState.currentRect = null;
        redrawCanvas();
    });
}

function updateRectangleList() {
    const container = document.getElementById('rectangle-list');
    container.innerHTML = '';

    if (canvasState.rectangles.length === 0) {
        container.innerHTML = '<p style="color: #666;">Draw rectangles on the preview above.</p>';
        return;
    }

    canvasState.rectangles.forEach((rect, i) => {
        const div = document.createElement('div');
        div.className = 'rectangle-item';
        div.innerHTML = `
            <span style="color: ${i === 0 ? '#f44336' : '#2196F3'}; font-weight: bold;">#${i + 1}</span>
            <input type="text" value="${rect.label}" onchange="updateRectLabel(${i}, this.value)" placeholder="Label">
            <select onchange="updateRectTarget(${i}, this.value)" ${i === 0 ? 'disabled' : ''}>
                ${i === 0 ? '<option value="text_content">text_content</option>' : getAttributeOptions(rect.target)}
            </select>
            <span style="color: #999; font-size: 12px;">${rect.width}x${rect.height}</span>
            <button type="button" class="btn btn-delete" onclick="deleteRectangle(${i})">Delete</button>
        `;
        container.appendChild(div);
    });
}

function getAttributeOptions(selected) {
    let html = '';
    for (let i = 31; i <= 80; i++) {
        const value = `attr${i}`;
        html += `<option value="${value}" ${selected === value ? 'selected' : ''}>attr${i}</option>`;
    }
    return html;
}

function updateRectLabel(index, label) {
    if (index < canvasState.rectangles.length) {
        canvasState.rectangles[index].label = label;
        redrawCanvas();
    }
}

function updateRectTarget(index, target) {
    if (index < canvasState.rectangles.length) {
        canvasState.rectangles[index].target = target;
    }
}

function deleteRectangle(index) {
    canvasState.rectangles.splice(index, 1);
    updateRectangleList();
    redrawCanvas();
}

function saveBoundary() {
    const boundary = {
        start_page: parseInt(document.getElementById('boundary-start').value) || 1,
        end_page: parseInt(document.getElementById('boundary-end').value) || 1,
        rectangles: canvasState.rectangles.map(r => ({
            label: r.label,
            x: r.x,
            y: r.y,
            width: r.width,
            height: r.height,
            target: r.target
        }))
    };

    currentConfig.ocr_boundaries = currentConfig.ocr_boundaries || [];

    if (boundaryIndex >= 0) {
        currentConfig.ocr_boundaries[boundaryIndex] = boundary;
    } else {
        currentConfig.ocr_boundaries.push(boundary);
    }

    loadBoundaries();
    closeBoundaryModal();
}

// =============================================================================
// Execution Management
// =============================================================================

async function runAutoSlicer() {
    if (!currentBookId) return;

    // Save config first
    await saveConfig();

    // Validate
    const titles = gatherTitles();
    const hasTitle = titles.level1.length > 0 || titles.level2.length > 0 || titles.level3.length > 0;

    if (!hasTitle) {
        showMessage('Please configure at least one title', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/run`, {
            method: 'POST'
        });

        const result = await response.json();

        if (response.ok && result.success) {
            isRunning = true;
            isPaused = false;
            startTime = Date.now();

            updateStatus('running');
            showProgressSection(true);
            connectWebSocket();
        } else {
            showMessage(result.detail || 'Failed to start Auto-slicer', 'error');
        }
    } catch (error) {
        console.error('Failed to start Auto-slicer:', error);
        showMessage('Failed to start Auto-slicer', 'error');
    }
}

async function pauseAutoSlicer() {
    if (!currentBookId || !isRunning) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/pause`, {
            method: 'POST'
        });

        const result = await response.json();
        if (result.success) {
            isPaused = true;
            updateStatus('paused');
            document.getElementById('pause-btn').textContent = 'Resume';
            document.getElementById('pause-btn').onclick = resumeAutoSlicer;
        }
    } catch (error) {
        console.error('Failed to pause:', error);
    }
}

async function resumeAutoSlicer() {
    if (!currentBookId || !isPaused) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/resume`, {
            method: 'POST'
        });

        const result = await response.json();
        if (result.success) {
            isPaused = false;
            isRunning = true;
            updateStatus('running');
            document.getElementById('pause-btn').textContent = 'Pause';
            document.getElementById('pause-btn').onclick = pauseAutoSlicer;
        }
    } catch (error) {
        console.error('Failed to resume:', error);
    }
}

async function cancelAutoSlicer() {
    if (!currentBookId) return;

    if (!confirm('Are you sure you want to cancel? Completed work will be kept.')) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/cancel`, {
            method: 'POST'
        });

        const result = await response.json();
        if (result.success) {
            isRunning = false;
            isPaused = false;
            updateStatus('cancelled');
            disconnectWebSocket();
        }
    } catch (error) {
        console.error('Failed to cancel:', error);
    }
}

async function retryFailedPages() {
    if (!currentBookId) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/retry`, {
            method: 'POST'
        });

        const result = await response.json();

        if (response.ok && result.success) {
            isRunning = true;
            startTime = Date.now();
            updateStatus('running');
            showProgressSection(true);
            connectWebSocket();
        } else {
            showMessage(result.detail || 'Failed to retry', 'error');
        }
    } catch (error) {
        console.error('Failed to retry:', error);
    }
}

async function checkStatus() {
    if (!currentBookId) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/status`);
        const status = await response.json();

        updateStatus(status.status);

        if (status.status === 'running') {
            isRunning = true;
            showProgressSection(true);
            connectWebSocket();
        } else if (status.status === 'paused') {
            isPaused = true;
            isRunning = true;
            showProgressSection(true);
            document.getElementById('pause-btn').textContent = 'Resume';
            document.getElementById('pause-btn').onclick = resumeAutoSlicer;
        }

        // Show results if there's a last run
        if (status.last_run) {
            showResults(status.last_run);
        }
    } catch (error) {
        console.error('Failed to check status:', error);
    }
}

// =============================================================================
// WebSocket Connection
// =============================================================================

function connectWebSocket() {
    if (websocket) {
        websocket.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/auto-slicer/${currentBookId}`;

    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
        console.log('WebSocket connected');
    };

    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    websocket.onclose = () => {
        console.log('WebSocket closed');
    };

    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function disconnectWebSocket() {
    if (websocket) {
        websocket.close();
        websocket = null;
    }
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'progress':
            updateProgress(data.current_page, data.total_pages, data.percent);
            break;

        case 'page_complete':
            // Reload paragraphs to show new ones
            loadPreviewParagraphs();
            break;

        case 'paragraph_created':
            // Add new paragraph to preview in real-time
            if (data.paragraph) {
                addParagraphToPreview(data.paragraph);
            }
            break;

        case 'status_change':
            updateStatus(data.status);
            if (data.status === 'paused') {
                isPaused = true;
                document.getElementById('pause-btn').textContent = 'Resume';
                document.getElementById('pause-btn').onclick = resumeAutoSlicer;
            }
            break;

        case 'complete':
            isRunning = false;
            isPaused = false;
            updateStatus(data.status);
            showResults({
                pages_processed: data.pages_processed,
                pages_failed: data.pages_failed,
                failed_pages: data.failed_pages
            });
            disconnectWebSocket();
            // Final reload of paragraphs
            loadPreviewParagraphs();
            break;

        case 'heartbeat':
            // Keep alive
            break;
    }
}

// =============================================================================
// UI Updates
// =============================================================================

function updateStatus(status) {
    const indicator = document.getElementById('status-indicator');
    indicator.className = `status-indicator status-${status}`;
    indicator.textContent = status.charAt(0).toUpperCase() + status.slice(1);

    // Update button states
    const runBtn = document.getElementById('run-btn');
    runBtn.disabled = (status === 'running' || status === 'paused');
}

function showProgressSection(show) {
    const section = document.getElementById('progress-section');
    section.classList.toggle('active', show);
}

function updateProgress(current, total, percent) {
    const bar = document.getElementById('progress-bar');
    bar.style.width = `${percent}%`;
    bar.textContent = `${Math.round(percent)}%`;

    document.getElementById('progress-current').textContent = `Processing page ${current} of ${total}`;

    if (startTime) {
        const elapsed = Math.round((Date.now() - startTime) / 1000);
        document.getElementById('progress-time').textContent = `Elapsed: ${formatTime(elapsed)}`;
    }
}

function showResults(results) {
    const section = document.getElementById('results-section');
    section.classList.add('active');

    if (results.pages_failed > 0) {
        section.classList.add('has-failures');
    } else {
        section.classList.remove('has-failures');
    }

    document.getElementById('result-processed').textContent = results.pages_processed;
    document.getElementById('result-failed').textContent = results.pages_failed;

    // Show retry button if there are failures
    const retryBtn = document.getElementById('retry-btn');
    retryBtn.style.display = results.pages_failed > 0 ? 'inline-block' : 'none';

    // Show failed pages list
    const list = document.getElementById('failed-pages-list');
    list.innerHTML = '';

    if (results.failed_pages && results.failed_pages.length > 0) {
        results.failed_pages.forEach(page => {
            const div = document.createElement('div');
            div.className = 'failed-page-item';
            div.innerHTML = `<span>Page ${page}</span>`;
            list.appendChild(div);
        });
    }
}

function showMessage(message, type = 'info') {
    // Simple alert for now - could be replaced with toast notification
    alert(message);
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
}

// =============================================================================
// Page Viewer for Title Extraction
// =============================================================================

let viewerState = {
    currentPage: 1,
    totalPages: 1,
    zoom: 0.1,
    image: null,
    isDrawing: false,
    startX: 0,
    startY: 0,
    selectionRect: null
};

function initViewerCanvas() {
    const canvas = document.getElementById('viewer-canvas');
    if (!canvas) return;

    canvas.addEventListener('mousedown', onViewerMouseDown);
    canvas.addEventListener('mousemove', onViewerMouseMove);
    canvas.addEventListener('mouseup', onViewerMouseUp);
}

// Initialize viewer when book is selected
async function loadViewerPage() {
    if (!currentBookId) return;

    const pageNum = viewerState.currentPage;
    const canvas = document.getElementById('viewer-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Show loading
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#666';
    ctx.font = '16px Arial';
    ctx.fillText('Loading page...', 20, 50);

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/page/${pageNum}/image`);
        if (!response.ok) throw new Error('Failed to load page');

        const blob = await response.blob();
        const img = new Image();
        img.onload = () => {
            viewerState.image = img;
            redrawViewerCanvas();
        };
        img.src = URL.createObjectURL(blob);

        // Update UI
        document.getElementById('viewer-page-input').value = pageNum;
        document.getElementById('viewer-page-info').textContent = `Page ${pageNum} of ${viewerState.totalPages}`;

        // Update button states
        document.getElementById('viewer-prev-btn').disabled = pageNum <= 1;
        document.getElementById('viewer-next-btn').disabled = pageNum >= viewerState.totalPages;

    } catch (error) {
        console.error('Failed to load viewer page:', error);
        ctx.fillStyle = '#f44336';
        ctx.fillText('Failed to load page', 20, 50);
    }
}

function redrawViewerCanvas() {
    const canvas = document.getElementById('viewer-canvas');
    const ctx = canvas.getContext('2d');

    if (!viewerState.image) return;

    // Resize canvas based on zoom
    canvas.width = viewerState.image.width * viewerState.zoom;
    canvas.height = viewerState.image.height * viewerState.zoom;

    // Draw image
    ctx.drawImage(viewerState.image, 0, 0, canvas.width, canvas.height);

    // Draw selection rectangle if exists
    if (viewerState.selectionRect) {
        const r = viewerState.selectionRect;
        ctx.strokeStyle = '#f44336';
        ctx.lineWidth = 2;
        ctx.strokeRect(r.x, r.y, r.width, r.height);

        // Semi-transparent fill
        ctx.fillStyle = 'rgba(244, 67, 54, 0.1)';
        ctx.fillRect(r.x, r.y, r.width, r.height);
    }
}

function onViewerMouseDown(e) {
    if (!viewerState.image) return;

    const canvas = document.getElementById('viewer-canvas');
    const rect = canvas.getBoundingClientRect();

    viewerState.isDrawing = true;
    viewerState.startX = e.clientX - rect.left;
    viewerState.startY = e.clientY - rect.top;
    viewerState.selectionRect = null;
}

function onViewerMouseMove(e) {
    if (!viewerState.isDrawing) return;

    const canvas = document.getElementById('viewer-canvas');
    const rect = canvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    viewerState.selectionRect = {
        x: Math.min(viewerState.startX, currentX),
        y: Math.min(viewerState.startY, currentY),
        width: Math.abs(currentX - viewerState.startX),
        height: Math.abs(currentY - viewerState.startY)
    };

    redrawViewerCanvas();
}

async function onViewerMouseUp(e) {
    if (!viewerState.isDrawing) return;
    viewerState.isDrawing = false;

    // Only process if rectangle is large enough
    if (viewerState.selectionRect &&
        viewerState.selectionRect.width > 20 &&
        viewerState.selectionRect.height > 10) {

        // Convert to image coordinates
        const imageRect = {
            x: Math.round(viewerState.selectionRect.x / viewerState.zoom),
            y: Math.round(viewerState.selectionRect.y / viewerState.zoom),
            width: Math.round(viewerState.selectionRect.width / viewerState.zoom),
            height: Math.round(viewerState.selectionRect.height / viewerState.zoom)
        };

        // Extract text from selection
        await extractTextFromSelection(imageRect);
    }
}

async function extractTextFromSelection(rect) {
    const textarea = document.getElementById('viewer-extracted-text');
    textarea.value = `Extracting text from region (${rect.x}, ${rect.y}) ${rect.width}x${rect.height}px...`;

    console.log('OCR request:', {
        book_id: currentBookId,
        page_number: viewerState.currentPage,
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
        zoom: viewerState.zoom,
        imageSize: viewerState.image ? `${viewerState.image.width}x${viewerState.image.height}` : 'unknown'
    });

    try {
        // Call OCR API for the selection
        const response = await fetch('/api/ocr/extract-region', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: currentBookId,
                page_number: viewerState.currentPage,
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height
            })
        });

        if (!response.ok) {
            throw new Error('OCR extraction failed');
        }

        const data = await response.json();
        console.log('OCR result:', data);

        if (data.text && data.text.trim()) {
            textarea.value = data.text;
        } else {
            textarea.value = `(No text detected in selection)\nRegion: ${rect.width}x${rect.height}px at (${rect.x}, ${rect.y})\nConfidence: ${(data.confidence * 100).toFixed(1)}%\n\nTry selecting a different area with visible text.`;
        }

    } catch (error) {
        console.error('Failed to extract text:', error);
        textarea.value = '(Error extracting text - try selecting a larger area)';
    }
}

function prevViewerPage() {
    if (viewerState.currentPage > 1) {
        viewerState.currentPage--;
        viewerState.selectionRect = null;
        document.getElementById('viewer-extracted-text').value = '';
        loadViewerPage();
    }
}

function nextViewerPage() {
    if (viewerState.currentPage < viewerState.totalPages) {
        viewerState.currentPage++;
        viewerState.selectionRect = null;
        document.getElementById('viewer-extracted-text').value = '';
        loadViewerPage();
    }
}

function goToViewerPage() {
    const input = document.getElementById('viewer-page-input');
    let page = parseInt(input.value) || 1;

    // Clamp to valid range
    page = Math.max(1, Math.min(page, viewerState.totalPages));
    input.value = page;

    viewerState.currentPage = page;
    viewerState.selectionRect = null;
    document.getElementById('viewer-extracted-text').value = '';
    loadViewerPage();
}

function updateViewerZoom() {
    viewerState.zoom = parseFloat(document.getElementById('viewer-zoom').value);
    redrawViewerCanvas();
}

function addExtractedAsTitle() {
    const text = document.getElementById('viewer-extracted-text').value.trim();
    if (!text || text.startsWith('(')) {
        alert('Please extract text first by drawing a rectangle on the page.');
        return;
    }

    const level = document.getElementById('viewer-title-level').value;
    const currentPage = viewerState.currentPage;

    // Add to title configuration
    addTitleRow(level, text, currentPage, currentPage);

    // Clear extracted text
    document.getElementById('viewer-extracted-text').value = '';
    viewerState.selectionRect = null;
    redrawViewerCanvas();

    // Show confirmation
    alert(`Added "${text}" as ${level.replace('level', 'Level ')} title starting at page ${currentPage}`);
}

// =============================================================================
// Paragraph Preview Functions
// =============================================================================

async function loadPreviewParagraphs() {
    if (!currentBookId) return;

    try {
        const response = await fetch(`/api/all-image-clips/${currentBookId}?clip_type=paragraph`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        previewParagraphs = data.clips || [];
        previewCurrentPage = 1;

        // Show preview section if we have paragraphs
        if (previewParagraphs.length > 0) {
            // If we have a scroll_to parameter, navigate to the correct page
            if (scrollToClipId) {
                const clipIndex = previewParagraphs.findIndex(p => p.id === scrollToClipId);
                if (clipIndex !== -1) {
                    // Calculate which page this clip is on
                    previewCurrentPage = Math.floor(clipIndex / PREVIEW_PER_PAGE) + 1;
                }
            }

            showPreviewSection();
            renderPreviewGrid();

            // Scroll to the specific thumbnail after rendering
            if (scrollToClipId) {
                setTimeout(() => {
                    scrollToPreviewThumbnail(scrollToClipId);
                    scrollToClipId = null; // Clear after use
                }, 300);
            }
        } else {
            hidePreviewSection();
        }
    } catch (error) {
        console.error('Failed to load preview paragraphs:', error);
    }
}

// Scroll to a specific thumbnail in the preview grid and highlight it
function scrollToPreviewThumbnail(clipId) {
    const thumbnails = document.querySelectorAll('.preview-item');
    for (const thumb of thumbnails) {
        // Find the thumbnail with matching clip ID (from the onclick handler)
        const infoText = thumb.querySelector('.preview-info strong');
        if (infoText && infoText.textContent === `#${clipId}`) {
            // Scroll into view
            thumb.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Highlight briefly
            thumb.style.boxShadow = '0 0 0 4px #9C27B0';
            thumb.style.transform = 'scale(1.05)';
            setTimeout(() => {
                thumb.style.boxShadow = '';
                thumb.style.transform = '';
            }, 2000);
            break;
        }
    }
}

function addParagraphToPreview(paragraph) {
    // Add to beginning of array
    previewParagraphs.unshift(paragraph);
    previewCurrentPage = 1; // Go to first page to see new paragraph

    showPreviewSection();
    renderPreviewGrid();

    // Highlight the new item briefly
    setTimeout(() => {
        const firstItem = document.querySelector('.preview-item');
        if (firstItem) {
            firstItem.classList.add('new');
            setTimeout(() => firstItem.classList.remove('new'), 500);
        }
    }, 100);
}

function showPreviewSection() {
    const section = document.getElementById('preview-section');
    if (section) {
        section.classList.add('active');
    }
}

function hidePreviewSection() {
    const section = document.getElementById('preview-section');
    if (section) {
        section.classList.remove('active');
    }
}

function renderPreviewGrid() {
    const grid = document.getElementById('preview-grid');
    const countEl = document.getElementById('preview-count');
    const paginationEl = document.getElementById('preview-pagination');

    if (!grid) return;

    // Update count
    const totalParagraphs = previewParagraphs.length;
    if (countEl) {
        countEl.textContent = `${totalParagraphs} paragraph${totalParagraphs !== 1 ? 's' : ''}`;
    }

    // Calculate pagination
    const totalPages = Math.ceil(totalParagraphs / PREVIEW_PER_PAGE);
    const startIdx = (previewCurrentPage - 1) * PREVIEW_PER_PAGE;
    const endIdx = Math.min(startIdx + PREVIEW_PER_PAGE, totalParagraphs);
    const currentItems = previewParagraphs.slice(startIdx, endIdx);

    // Render grid
    grid.innerHTML = '';

    if (currentItems.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #666;">No paragraphs yet. Run Auto-Slicer to extract paragraphs.</div>';
        if (paginationEl) paginationEl.style.display = 'none';
        return;
    }

    currentItems.forEach((clip, localIndex) => {
        const globalIndex = startIdx + localIndex;
        const div = document.createElement('div');
        div.className = 'preview-item';

        const imageSrc = clip.image_data_base64
            ? `data:image/${clip.image_format || 'png'};base64,${clip.image_data_base64}`
            : '';

        div.innerHTML = `
            <button class="preview-delete-btn" onclick="event.stopPropagation(); deleteParagraphPreview(${clip.id})" title="Delete paragraph">&times;</button>
            <button class="preview-layout-btn" onclick="event.stopPropagation(); openInLayoutReview(${clip.page_number})" title="View in Layout Review">&#128269;</button>
            ${imageSrc ? `<img src="${imageSrc}" class="preview-thumb" alt="Paragraph ${clip.id}" />` : '<div class="preview-thumb" style="display: flex; align-items: center; justify-content: center; color: #999;">No image</div>'}
            <div class="preview-info">
                <strong>#${clip.id}</strong> | Page ${clip.page_number}<br>
                ${clip.level_1_title ? `<span style="color: #1976D2;">${escapeHtml(clip.level_1_title.substring(0, 30))}${clip.level_1_title.length > 30 ? '...' : ''}</span>` : ''}
            </div>
        `;

        // Add click handler for opening details (not on delete or layout buttons)
        div.onclick = (e) => {
            if (!e.target.classList.contains('preview-delete-btn') && !e.target.classList.contains('preview-layout-btn')) {
                openFullDetails(globalIndex);
            }
        };

        grid.appendChild(div);
    });

    // Update pagination
    if (totalPages > 1 && paginationEl) {
        paginationEl.style.display = 'flex';
        document.getElementById('preview-page-info').textContent = `Page ${previewCurrentPage} of ${totalPages}`;
        document.getElementById('preview-prev-btn').disabled = previewCurrentPage <= 1;
        document.getElementById('preview-next-btn').disabled = previewCurrentPage >= totalPages;
    } else if (paginationEl) {
        paginationEl.style.display = 'none';
    }
}

function prevPreviewPage() {
    if (previewCurrentPage > 1) {
        previewCurrentPage--;
        renderPreviewGrid();
    }
}

function nextPreviewPage() {
    const totalPages = Math.ceil(previewParagraphs.length / PREVIEW_PER_PAGE);
    if (previewCurrentPage < totalPages) {
        previewCurrentPage++;
        renderPreviewGrid();
    }
}

// =============================================================================
// Full Details Modal Functions
// =============================================================================

function toggleCollapsible(sectionId) {
    const header = document.querySelector(`[data-section="${sectionId}"]`);
    const content = document.getElementById(sectionId);

    if (!header || !content) return;

    const isExpanded = content.classList.contains('expanded');

    if (isExpanded) {
        content.classList.remove('expanded');
        header.classList.remove('expanded');
        collapsibleSectionStates[sectionId] = false;
    } else {
        content.classList.add('expanded');
        header.classList.add('expanded');
        collapsibleSectionStates[sectionId] = true;
    }
}

function isSectionExpanded(sectionId, defaultExpanded = false) {
    if (collapsibleSectionStates.hasOwnProperty(sectionId)) {
        return collapsibleSectionStates[sectionId];
    }
    return defaultExpanded;
}

/**
 * Open the Layout Review page for a specific page number.
 * Navigates to the layout review with the book_id and page parameters.
 */
function openInLayoutReview(pageNumber) {
    if (!currentBookId) {
        alert('No book selected');
        return;
    }
    // Navigate to layout review with page parameter
    window.location.href = `/layout-review?book_id=${currentBookId}&page=${pageNumber}`;
}

function openFullDetails(index) {
    const clip = previewParagraphs[index];
    if (!clip) return;

    // Redirect to edit-paragraphs page for full details
    // This ensures all 80 attributes, linked diagrams, and full editing capabilities are available
    // Any changes made there will automatically be reflected when returning to auto-slicer
    const url = `/edit-paragraphs?book_id=${currentBookId}&scroll_to=${clip.id}&from=autoslicer`;
    window.location.href = url;
}

function closeDetailsModal() {
    const modal = document.getElementById('details-modal');
    modal.classList.remove('visible');
    document.body.style.overflow = '';
    currentDetailsClipIndex = null;
}

function updateNavigationButtons() {
    const prevBtn = document.getElementById('btn-prev-paragraph');
    const nextBtn = document.getElementById('btn-next-paragraph');

    if (!prevBtn || !nextBtn || currentDetailsClipIndex === null) return;

    prevBtn.disabled = currentDetailsClipIndex <= 0;
    nextBtn.disabled = currentDetailsClipIndex >= previewParagraphs.length - 1;
}

function navigateToPreviousParagraph() {
    if (currentDetailsClipIndex === null || currentDetailsClipIndex <= 0) return;
    openFullDetails(currentDetailsClipIndex - 1);
}

function navigateToNextParagraph() {
    if (currentDetailsClipIndex === null || currentDetailsClipIndex >= previewParagraphs.length - 1) return;
    openFullDetails(currentDetailsClipIndex + 1);
}

async function saveFullDetails() {
    if (currentDetailsClipIndex === null) return;

    const clip = previewParagraphs[currentDetailsClipIndex];
    if (!clip) return;

    const updates = {
        book_id: currentBookId,
        clip_id: clip.id,
        clip_type: 'paragraph',
        approval_status: document.getElementById('detail-approval-status').value,
        display_order: parseInt(document.getElementById('detail-display-order').value) || 0,
        is_enabled: document.getElementById('detail-is-enabled').value === 'true',
        description: document.getElementById('detail-description').value || null,
        extracted_text: document.getElementById('detail-extracted-text').value || null,
        level_1_title: document.getElementById('detail-level-1-title').value || null,
        level_2_title: document.getElementById('detail-level-2-title').value || null,
        level_3_title: document.getElementById('detail-level-3-title').value || null
    };

    try {
        const response = await fetch('/api/update-clip-details', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update clip details');
        }

        // Update local data
        Object.assign(clip, {
            approval_status: updates.approval_status,
            display_order: updates.display_order,
            is_enabled: updates.is_enabled,
            description: updates.description,
            extracted_text: updates.extracted_text,
            level_1_title: updates.level_1_title,
            level_2_title: updates.level_2_title,
            level_3_title: updates.level_3_title
        });

        closeDetailsModal();
        renderPreviewGrid();
        alert('Details saved successfully!');

    } catch (error) {
        console.error('Error saving details:', error);
        alert('Failed to save details: ' + error.message);
    }
}

// =============================================================================
// Delete Functions
// =============================================================================

async function deleteParagraphPreview(clipId) {
    if (!confirm(`Delete paragraph #${clipId}? This cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/delete-image-clip/paragraph/${clipId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Failed to delete paragraph ${clipId}`);
        }

        // Remove from local array
        const index = previewParagraphs.findIndex(p => p.id === clipId);
        if (index !== -1) {
            previewParagraphs.splice(index, 1);
        }

        // Re-render the grid
        renderPreviewGrid();

        // If modal is open and showing this clip, close it
        if (currentDetailsClipIndex !== null) {
            const currentClip = previewParagraphs[currentDetailsClipIndex];
            if (!currentClip || currentClip.id === clipId) {
                closeDetailsModal();
            }
        }

        console.log(`Deleted paragraph ${clipId}`);

    } catch (error) {
        console.error('Error deleting paragraph:', error);
        alert(`Failed to delete: ${error.message}`);
    }
}

// =============================================================================
// Helper Functions
// =============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =============================================================================
// Layout Detection (YOLO)
// =============================================================================

// Layout detection state
let layoutDetectionState = {
    isRunning: false,
    websocket: null,
    currentPage: 0,
    totalPages: 0,
    regionsDetected: 0,
    detectedRegions: [],
    reviewPageIndex: 0,
    reviewPages: [],
    selectedRegionId: null,
    isDrawingNewRegion: false,
    canvasScale: 1
};

// Class colors for visualization
const CLASS_COLORS = {
    'title_level_1': '#FF0000',
    'title_level_2': '#FF6600',
    'title_level_3': '#FFCC00',
    'paragraph': '#00FF00',
    'diagram': '#0066FF',
    'table': '#9900FF',
    'equation': '#FF00FF',
    'list_bulleted': '#00FFFF',
    'list_numbered': '#00CCCC',
    'list_lettered': '#009999',
    'list_item': '#006666',
    'header': '#999999',
    'footer': '#666666',
    'reference': '#CC9900',
    'caption': '#99CC00'
};

/**
 * Get selected YOLO classes from checkboxes
 */
function getSelectedYoloClasses() {
    const classMap = {
        'yolo-class-paragraph': 'paragraph',
        'yolo-class-diagram': 'diagram',
        'yolo-class-equation': 'equation',
        'yolo-class-list': ['list_bulleted', 'list_numbered', 'list_lettered', 'list_item'],
        'yolo-class-header': 'header',
        'yolo-class-footer': 'footer',
        'yolo-class-title-l1': 'title_level_1',
        'yolo-class-title-l2': 'title_level_2',
        'yolo-class-title-l3': 'title_level_3',
        'yolo-class-caption': 'caption',
        'yolo-class-reference': 'reference',
        'yolo-class-question': 'question',
        'yolo-class-answer': 'answer'
    };

    const enabledClasses = [];
    for (const [checkboxId, className] of Object.entries(classMap)) {
        const checkbox = document.getElementById(checkboxId);
        if (checkbox && checkbox.checked) {
            if (Array.isArray(className)) {
                enabledClasses.push(...className);
            } else {
                enabledClasses.push(className);
            }
        }
    }
    return enabledClasses;
}

/**
 * Toggle all YOLO class checkboxes
 */
function toggleAllYoloClasses(enable) {
    const checkboxIds = [
        'yolo-class-paragraph', 'yolo-class-diagram', 'yolo-class-equation',
        'yolo-class-list', 'yolo-class-header', 'yolo-class-footer',
        'yolo-class-title-l1', 'yolo-class-title-l2', 'yolo-class-title-l3',
        'yolo-class-caption', 'yolo-class-reference',
        'yolo-class-question', 'yolo-class-answer'
    ];
    checkboxIds.forEach(id => {
        const checkbox = document.getElementById(id);
        if (checkbox) checkbox.checked = enable;
    });
    
    // Show unsaved warning
    const statusEl = document.getElementById('save-classes-status');
    if (statusEl) {
        statusEl.textContent = '⚠️ Unsaved changes - click "Save Classes" to apply';
        statusEl.style.color = '#ff9800';
    }
}

/**
 * Save enabled classes to the server when checkboxes change.
 * This allows the layout-review page to show the correct classes in the context menu.
 */
async function saveEnabledClasses() {
    if (!currentBookId) return;

    const enabledClasses = getSelectedYoloClasses();
    
    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/layout-config/enabled-classes`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled_classes: enabledClasses })
        });

        if (!response.ok) {
            console.error('Failed to save enabled classes:', response.status);
            return;
        }

        console.log('Enabled classes saved:', enabledClasses);
        return true;  // Return success
    } catch (error) {
        console.error('Error saving enabled classes:', error);
        return false;  // Return failure
    }
}

/**
 * Save enabled classes with user feedback (for the Save button).
 */
async function saveEnabledClassesWithFeedback() {
    if (!currentBookId) {
        alert('Please select a book first');
        return;
    }

    const statusEl = document.getElementById('save-classes-status');
    const btnEl = document.getElementById('save-classes-btn');
    
    // Show saving state
    btnEl.disabled = true;
    btnEl.textContent = '⏳ Saving...';
    statusEl.textContent = '';
    statusEl.style.color = '#666';

    const success = await saveEnabledClasses();

    if (success) {
        btnEl.textContent = '✅ Saved!';
        statusEl.textContent = 'Classes saved. Layout Review will now show these classes in the context menu.';
        statusEl.style.color = '#4CAF50';
        
        // Reset button after 2 seconds
        setTimeout(() => {
            btnEl.textContent = '💾 Save Classes';
            btnEl.disabled = false;
        }, 2000);
    } else {
        btnEl.textContent = '❌ Failed';
        statusEl.textContent = 'Failed to save classes. Please try again.';
        statusEl.style.color = '#f44336';
        
        // Reset button after 2 seconds
        setTimeout(() => {
            btnEl.textContent = '💾 Save Classes';
            btnEl.disabled = false;
        }, 2000);
    }
}

/**
 * Setup event listeners for YOLO class checkboxes to save on change.
 */
function setupYoloClassCheckboxListeners() {
    const checkboxIds = [
        'yolo-class-paragraph', 'yolo-class-diagram', 'yolo-class-equation',
        'yolo-class-list', 'yolo-class-header', 'yolo-class-footer',
        'yolo-class-title-l1', 'yolo-class-title-l2', 'yolo-class-title-l3',
        'yolo-class-caption', 'yolo-class-reference',
        'yolo-class-question', 'yolo-class-answer'
    ];
    
    checkboxIds.forEach(id => {
        const checkbox = document.getElementById(id);
        if (checkbox) {
            // Mark as unsaved when checkbox changes
            checkbox.addEventListener('change', () => {
                const statusEl = document.getElementById('save-classes-status');
                if (statusEl) {
                    statusEl.textContent = '⚠️ Unsaved changes - click "Save Classes" to apply';
                    statusEl.style.color = '#ff9800';
                }
            });
        }
    });
}

/**
 * Start layout detection with YOLO
 */
async function detectLayout() {
    if (!currentBookId) {
        alert('Please select a book first');
        return;
    }

    const startPage = parseInt(document.getElementById('start-page').value) || 1;
    const endPage = parseInt(document.getElementById('end-page').value) || 1;

    if (startPage > endPage) {
        alert('Start page must be less than or equal to end page');
        return;
    }

    // Validate title coverage before detection
    const validationPassed = await checkTitleValidationBeforeDetection();
    if (!validationPassed) {
        alert('Please configure L1 and L2 titles to cover all pages in the selected range before running Layout Detection.');
        return;
    }

    // Show layout detection section
    document.getElementById('layout-detection-section').style.display = 'block';
    document.getElementById('layout-review-section').style.display = 'none';
    document.getElementById('detect-layout-btn').disabled = true;

    layoutDetectionState.isRunning = true;
    layoutDetectionState.currentPage = 0;
    layoutDetectionState.totalPages = endPage - startPage + 1;
    layoutDetectionState.regionsDetected = 0;

    try {
        // Connect to WebSocket for progress and wait for it to open
        await connectLayoutWebSocket();

        // Get selected classes
        const enabledClasses = getSelectedYoloClasses();
        if (enabledClasses.length === 0) {
            alert('Please select at least one class to detect');
            layoutDetectionState.isRunning = false;
            document.getElementById('detect-layout-btn').disabled = false;
            document.getElementById('layout-detection-section').style.display = 'none';
            return;
        }

        // Start detection (WebSocket is now ready to receive progress)
        const response = await fetch(`/api/auto-slicer/${currentBookId}/detect-layout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_page: startPage,
                end_page: endPage,
                confidence_threshold: 0.25,
                enabled_classes: enabledClasses
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start detection');
        }

        console.log('Layout detection started');

    } catch (error) {
        console.error('Error starting layout detection:', error);
        alert(`Failed to start detection: ${error.message}`);
        layoutDetectionState.isRunning = false;
        document.getElementById('detect-layout-btn').disabled = false;
    }
}

/**
 * Connect to layout detection WebSocket
 * Returns a Promise that resolves when connection is open
 */
function connectLayoutWebSocket() {
    return new Promise((resolve, reject) => {
        if (layoutDetectionState.websocket) {
            layoutDetectionState.websocket.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/layout-detection/${currentBookId}`;

        layoutDetectionState.websocket = new WebSocket(wsUrl);

        layoutDetectionState.websocket.onopen = function() {
            console.log('Layout WebSocket connected');
            resolve();
        };

        layoutDetectionState.websocket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleLayoutProgress(data);
        };

        layoutDetectionState.websocket.onerror = function(error) {
            console.error('Layout WebSocket error:', error);
            reject(error);
        };

        layoutDetectionState.websocket.onclose = function() {
            console.log('Layout WebSocket closed');
        };
    });
}

/**
 * Handle layout detection progress updates
 */
function handleLayoutProgress(data) {
    if (data.type === 'detection_progress') {
        layoutDetectionState.currentPage = data.current_page;
        layoutDetectionState.regionsDetected = data.regions_detected;

        const progress = (data.pages_processed / layoutDetectionState.totalPages) * 100;
        document.getElementById('layout-progress-bar').style.width = `${progress}%`;
        document.getElementById('layout-progress-bar').textContent = `${Math.round(progress)}%`;
        document.getElementById('layout-progress-current').textContent =
            `Detecting layouts on page ${data.current_page} of ${layoutDetectionState.totalPages}`;
        document.getElementById('layout-regions-count').textContent =
            `Regions: ${data.regions_detected}`;

    } else if (data.type === 'detection_complete') {
        layoutDetectionState.isRunning = false;
        document.getElementById('detect-layout-btn').disabled = false;

        // Hide detection section
        document.getElementById('layout-detection-section').style.display = 'none';

        // Show review button
        document.getElementById('review-layout-btn').style.display = 'inline-block';

        // Show extract knowledge button
        document.getElementById('extract-knowledge-btn').style.display = 'inline-block';

        // Automatically open the layout review page
        openLayoutReview();
    }
}

/**
 * Cancel layout detection
 */
async function cancelLayoutDetection() {
    try {
        await fetch(`/api/auto-slicer/${currentBookId}/cancel-detection`, {
            method: 'POST'
        });

        layoutDetectionState.isRunning = false;
        document.getElementById('layout-detection-section').style.display = 'none';
        document.getElementById('detect-layout-btn').disabled = false;

        if (layoutDetectionState.websocket) {
            layoutDetectionState.websocket.close();
        }

    } catch (error) {
        console.error('Error cancelling detection:', error);
    }
}

/**
 * Load detected regions for review
 */
async function loadDetectedRegionsForReview() {
    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/detected-regions`);
        if (!response.ok) throw new Error('Failed to load regions');

        const data = await response.json();
        layoutDetectionState.detectedRegions = data.regions;

        // Group by page
        const pageMap = {};
        data.regions.forEach(region => {
            if (!pageMap[region.page_number]) {
                pageMap[region.page_number] = [];
            }
            pageMap[region.page_number].push(region);
        });

        layoutDetectionState.reviewPages = Object.keys(pageMap).map(Number).sort((a, b) => a - b);
        layoutDetectionState.reviewPageIndex = 0;

        if (layoutDetectionState.reviewPages.length > 0) {
            document.getElementById('layout-review-section').style.display = 'block';
            loadReviewPage(layoutDetectionState.reviewPages[0]);
        } else {
            alert('No regions detected');
        }

    } catch (error) {
        console.error('Error loading regions:', error);
        alert('Failed to load detected regions');
    }
}

/**
 * Load a specific page for review
 */
async function loadReviewPage(pageNumber) {
    const canvas = document.getElementById('layout-review-canvas');
    const ctx = canvas.getContext('2d');

    // Update page info
    const pageIdx = layoutDetectionState.reviewPages.indexOf(pageNumber);
    document.getElementById('layout-page-info').textContent =
        `Page ${pageNumber} (${pageIdx + 1} of ${layoutDetectionState.reviewPages.length})`;

    // Update navigation buttons
    document.getElementById('layout-prev-btn').disabled = pageIdx === 0;
    document.getElementById('layout-next-btn').disabled = pageIdx === layoutDetectionState.reviewPages.length - 1;

    try {
        // Load page image
        const img = new Image();
        img.onload = function() {
            // Scale to fit
            const maxWidth = 800;
            const scale = Math.min(1, maxWidth / img.width);
            layoutDetectionState.canvasScale = scale;

            canvas.width = img.width * scale;
            canvas.height = img.height * scale;

            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            // Draw detected regions
            const pageRegions = layoutDetectionState.detectedRegions.filter(
                r => r.page_number === pageNumber
            );
            drawRegionsOnCanvas(ctx, pageRegions, scale);

            // Update regions list
            updateRegionsList(pageRegions);
        };
        img.src = `/api/auto-slicer/${currentBookId}/page/${pageNumber}/image`;

    } catch (error) {
        console.error('Error loading page:', error);
    }
}

/**
 * Draw regions on canvas
 */
function drawRegionsOnCanvas(ctx, regions, scale) {
    regions.forEach(region => {
        const color = CLASS_COLORS[region.class_name] || '#FF0000';
        const isSelected = region.id === layoutDetectionState.selectedRegionId;

        ctx.strokeStyle = color;
        ctx.lineWidth = isSelected ? 3 : 2;
        ctx.strokeRect(
            region.x * scale,
            region.y * scale,
            region.width * scale,
            region.height * scale
        );

        // Draw label
        ctx.fillStyle = color;
        ctx.font = 'bold 12px Arial';
        const label = `${region.class_name} (${Math.round(region.confidence * 100)}%)`;
        ctx.fillText(label, region.x * scale, region.y * scale - 5);
    });
}

/**
 * Update the regions list sidebar
 */
function updateRegionsList(regions) {
    const container = document.getElementById('layout-regions-list-items');
    container.innerHTML = '';

    regions.forEach(region => {
        const color = CLASS_COLORS[region.class_name] || '#FF0000';
        const isSelected = region.id === layoutDetectionState.selectedRegionId;

        const item = document.createElement('div');
        item.className = 'region-list-item';
        item.style.cssText = `
            padding: 8px;
            margin-bottom: 8px;
            border-radius: 4px;
            cursor: pointer;
            border-left: 4px solid ${color};
            background: ${isSelected ? '#e3f2fd' : '#f5f5f5'};
        `;
        item.innerHTML = `
            <div style="font-weight: bold; font-size: 12px;">${region.class_name}</div>
            <div style="font-size: 11px; color: #666;">
                Confidence: ${Math.round(region.confidence * 100)}%
            </div>
            <div style="font-size: 10px; color: #999;">
                ${region.width}×${region.height} at (${region.x}, ${region.y})
            </div>
        `;
        item.onclick = () => selectRegion(region.id);
        container.appendChild(item);
    });
}

/**
 * Select a region
 */
function selectRegion(regionId) {
    layoutDetectionState.selectedRegionId = regionId;

    // Find the region and set the class selector
    const region = layoutDetectionState.detectedRegions.find(r => r.id === regionId);
    if (region) {
        document.getElementById('layout-class-select').value = region.class_name;
    }

    // Redraw canvas
    const pageNumber = layoutDetectionState.reviewPages[layoutDetectionState.reviewPageIndex];
    loadReviewPage(pageNumber);
}

/**
 * Reclassify selected region
 */
async function reclassifySelectedRegion() {
    if (!layoutDetectionState.selectedRegionId) {
        alert('Please select a region first');
        return;
    }

    const newClass = document.getElementById('layout-class-select').value;

    try {
        await fetch(`/api/auto-slicer/${currentBookId}/detected-region/${layoutDetectionState.selectedRegionId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ class_name: newClass })
        });

        // Update local state
        const region = layoutDetectionState.detectedRegions.find(
            r => r.id === layoutDetectionState.selectedRegionId
        );
        if (region) region.class_name = newClass;

        // Redraw
        const pageNumber = layoutDetectionState.reviewPages[layoutDetectionState.reviewPageIndex];
        loadReviewPage(pageNumber);

    } catch (error) {
        console.error('Error reclassifying region:', error);
        alert('Failed to reclassify region');
    }
}

/**
 * Delete selected region
 */
async function deleteSelectedRegion() {
    if (!layoutDetectionState.selectedRegionId) {
        alert('Please select a region first');
        return;
    }

    if (!confirm('Delete this region?')) return;

    try {
        await fetch(`/api/auto-slicer/${currentBookId}/detected-region/${layoutDetectionState.selectedRegionId}`, {
            method: 'DELETE'
        });

        // Remove from local state
        layoutDetectionState.detectedRegions = layoutDetectionState.detectedRegions.filter(
            r => r.id !== layoutDetectionState.selectedRegionId
        );
        layoutDetectionState.selectedRegionId = null;

        // Redraw
        const pageNumber = layoutDetectionState.reviewPages[layoutDetectionState.reviewPageIndex];
        loadReviewPage(pageNumber);

    } catch (error) {
        console.error('Error deleting region:', error);
        alert('Failed to delete region');
    }
}

/**
 * Start drawing a new region
 */
function startDrawingRegion() {
    layoutDetectionState.isDrawingNewRegion = true;
    document.getElementById('layout-review-canvas').style.cursor = 'crosshair';
    alert('Click and drag on the canvas to draw a new region');
}

/**
 * Confirm current page regions
 */
async function confirmCurrentPage() {
    const pageNumber = layoutDetectionState.reviewPages[layoutDetectionState.reviewPageIndex];

    try {
        await fetch(`/api/auto-slicer/${currentBookId}/confirm-regions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ page_numbers: [pageNumber] })
        });

        alert(`Page ${pageNumber} confirmed`);

        // Move to next page
        if (layoutDetectionState.reviewPageIndex < layoutDetectionState.reviewPages.length - 1) {
            nextLayoutPage();
        }

    } catch (error) {
        console.error('Error confirming page:', error);
        alert('Failed to confirm page');
    }
}

/**
 * Navigate to previous page
 */
function prevLayoutPage() {
    if (layoutDetectionState.reviewPageIndex > 0) {
        layoutDetectionState.reviewPageIndex--;
        layoutDetectionState.selectedRegionId = null;
        loadReviewPage(layoutDetectionState.reviewPages[layoutDetectionState.reviewPageIndex]);
    }
}

/**
 * Navigate to next page
 */
function nextLayoutPage() {
    if (layoutDetectionState.reviewPageIndex < layoutDetectionState.reviewPages.length - 1) {
        layoutDetectionState.reviewPageIndex++;
        layoutDetectionState.selectedRegionId = null;
        loadReviewPage(layoutDetectionState.reviewPages[layoutDetectionState.reviewPageIndex]);
    }
}

/**
 * Confirm all pages and run OCR
 */
async function confirmAllAndRunOCR() {
    if (!confirm('Confirm all pages and run OCR on detected regions?')) return;

    try {
        // Confirm all remaining pages
        await fetch(`/api/auto-slicer/${currentBookId}/confirm-regions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ page_numbers: layoutDetectionState.reviewPages })
        });

        // Hide review section
        document.getElementById('layout-review-section').style.display = 'none';

        // Now run Auto-Slicer OCR
        runAutoSlicer();

    } catch (error) {
        console.error('Error confirming all:', error);
        alert('Failed to confirm pages');
    }
}

/**
 * Open the Layout Review page in a new tab/window
 */
function openLayoutReview() {
    if (!currentBookId) {
        alert('Please select a book first');
        return;
    }

    // Open the dedicated layout review page
    window.location.href = `/layout-review?book_id=${currentBookId}`;
}

/**
 * Open the Extraction Dashboard page
 */
function openExtractKnowledge() {
    if (!currentBookId) {
        alert('Please select a book first');
        return;
    }

    // Open the extraction dashboard page
    window.location.href = `/extraction-dashboard?book_id=${currentBookId}`;
}

/**
 * Check if there are existing detected regions for the current book
 * and show/hide the review button accordingly
 */
async function checkExistingLayoutRegions() {
    if (!currentBookId) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/detected-regions`);
        if (!response.ok) return;

        const data = await response.json();
        const hasRegions = data.regions && data.regions.length > 0;

        // Show or hide the review button based on whether regions exist
        const reviewBtn = document.getElementById('review-layout-btn');
        if (reviewBtn) {
            reviewBtn.style.display = hasRegions ? 'inline-block' : 'none';
        }

        // Show or hide the extract knowledge button based on whether regions exist
        const extractBtn = document.getElementById('extract-knowledge-btn');
        if (extractBtn) {
            extractBtn.style.display = hasRegions ? 'inline-block' : 'none';
        }

        // Load layout thumbnails if regions exist
        if (hasRegions) {
            loadLayoutThumbnails(data.regions);
        } else {
            document.getElementById('layout-thumbnails-section').style.display = 'none';
        }

        // Load ignore rules
        loadIgnoreRules();

    } catch (error) {
        console.error('Error checking for existing layout regions:', error);
    }
}

// =============================================================================
// Layout Thumbnails Management
// =============================================================================

let layoutThumbnailsState = {
    pages: [],
    currentPage: 1,
    perPage: 12,
    regionsByPage: {}
};

const CLASS_COLORS_THUMBNAILS = {
    'title_level_1': '#FF0000',
    'title_level_2': '#FF6600',
    'title_level_3': '#FFCC00',
    'paragraph': '#00FF00',
    'diagram': '#0066FF',
    'table': '#9900FF',
    'equation': '#FF00FF',
    'list_bulleted': '#00FFFF',
    'list_numbered': '#00CCCC',
    'list_lettered': '#009999',
    'list_item': '#006666',
    'header': '#999999',
    'footer': '#666666',
    'reference': '#CC9900',
    'caption': '#99CC00',
    'ignore': '#444444'
};

/**
 * Load and display layout detection thumbnails
 */
function loadLayoutThumbnails(regions) {
    // Group regions by page
    layoutThumbnailsState.regionsByPage = {};
    regions.forEach(r => {
        if (!layoutThumbnailsState.regionsByPage[r.page_number]) {
            layoutThumbnailsState.regionsByPage[r.page_number] = [];
        }
        layoutThumbnailsState.regionsByPage[r.page_number].push(r);
    });

    // Get sorted list of pages with regions
    layoutThumbnailsState.pages = Object.keys(layoutThumbnailsState.regionsByPage)
        .map(Number)
        .sort((a, b) => a - b);

    layoutThumbnailsState.currentPage = 1;

    if (layoutThumbnailsState.pages.length > 0) {
        document.getElementById('layout-thumbnails-section').style.display = 'block';
        document.getElementById('ignore-rules-section').style.display = 'block';
        renderLayoutThumbnails();
    } else {
        document.getElementById('layout-thumbnails-section').style.display = 'none';
    }
}

/**
 * Render the current page of thumbnails
 */
function renderLayoutThumbnails() {
    const grid = document.getElementById('layout-thumbnails-grid');
    const { pages, currentPage, perPage, regionsByPage } = layoutThumbnailsState;

    const startIdx = (currentPage - 1) * perPage;
    const endIdx = Math.min(startIdx + perPage, pages.length);
    const visiblePages = pages.slice(startIdx, endIdx);

    grid.innerHTML = '';

    visiblePages.forEach(pageNum => {
        const regions = regionsByPage[pageNum] || [];
        const thumbnail = createLayoutThumbnail(pageNum, regions);
        grid.appendChild(thumbnail);
    });

    // Update pagination
    const totalPages = Math.ceil(pages.length / perPage);
    const paginationEl = document.getElementById('layout-thumbnails-pagination');

    if (totalPages > 1) {
        paginationEl.style.display = 'flex';
        document.getElementById('layout-thumbnails-page-info').textContent =
            `Page ${currentPage} of ${totalPages}`;
        document.getElementById('layout-thumb-prev-btn').disabled = currentPage <= 1;
        document.getElementById('layout-thumb-next-btn').disabled = currentPage >= totalPages;
    } else {
        paginationEl.style.display = 'none';
    }

    document.getElementById('layout-thumbnails-count').textContent =
        `${pages.length} pages with detections`;
}

/**
 * Create a single thumbnail element
 */
function createLayoutThumbnail(pageNumber, regions) {
    const item = document.createElement('div');
    item.className = 'layout-thumbnail-item';
    item.onclick = () => openLayoutReviewForPage(pageNumber);

    // Create canvas for thumbnail with detection boxes
    const canvas = document.createElement('canvas');
    canvas.className = 'thumbnail-image';
    canvas.width = 200;
    canvas.height = 280;

    // Load page image and draw detection boxes
    loadThumbnailImage(canvas, pageNumber, regions);

    // Delete button
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'thumbnail-delete';
    deleteBtn.innerHTML = '×';
    deleteBtn.title = 'Delete all detections for this page';
    deleteBtn.onclick = (e) => {
        e.stopPropagation();
        deletePageDetections(pageNumber);
    };

    // Info section
    const info = document.createElement('div');
    info.className = 'thumbnail-info';
    info.innerHTML = `
        <div class="thumbnail-page">Page ${pageNumber}</div>
        <div class="thumbnail-count">${regions.length} region${regions.length !== 1 ? 's' : ''}</div>
    `;

    item.appendChild(deleteBtn);
    item.appendChild(canvas);
    item.appendChild(info);

    return item;
}

/**
 * Load page image and draw detection boxes on canvas
 */
async function loadThumbnailImage(canvas, pageNumber, regions) {
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#333';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    try {
        // Use the review-raw endpoint which returns base64 image
        const response = await fetch(`/api/review-raw/${currentBookId}/page/${pageNumber}`);
        if (!response.ok) {
            console.error(`Failed to load page ${pageNumber}: ${response.status}`);
            return;
        }

        const data = await response.json();
        if (!data.image_base64) {
            console.error(`No image data for page ${pageNumber}`);
            return;
        }

        const img = new Image();
        img.onload = () => {
            // Calculate scale to fit canvas
            const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
            const drawWidth = img.width * scale;
            const drawHeight = img.height * scale;
            const offsetX = (canvas.width - drawWidth) / 2;
            const offsetY = (canvas.height - drawHeight) / 2;

            // Draw image
            ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);

            // Draw detection boxes
            regions.forEach(region => {
                const color = CLASS_COLORS_THUMBNAILS[region.class_name] || '#FF0000';
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.strokeRect(
                    offsetX + region.x * scale,
                    offsetY + region.y * scale,
                    region.width * scale,
                    region.height * scale
                );
            });
        };
        img.onerror = () => {
            console.error(`Failed to load image for page ${pageNumber}`);
        };
        img.src = `data:image/${data.image_format || 'jpeg'};base64,${data.image_base64}`;
    } catch (error) {
        console.error(`Error loading thumbnail for page ${pageNumber}:`, error);
    }
}

/**
 * Open Layout Review for a specific page
 */
function openLayoutReviewForPage(pageNumber) {
    window.location.href = `/layout-review?book_id=${currentBookId}&page=${pageNumber}`;
}

/**
 * Delete all detections for a page
 */
async function deletePageDetections(pageNumber) {
    if (!confirm(`Delete all layout detections for page ${pageNumber}?`)) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/page-detections/${pageNumber}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Remove from local state
            delete layoutThumbnailsState.regionsByPage[pageNumber];
            layoutThumbnailsState.pages = layoutThumbnailsState.pages.filter(p => p !== pageNumber);

            // Adjust current page if needed
            const totalPages = Math.ceil(layoutThumbnailsState.pages.length / layoutThumbnailsState.perPage);
            if (layoutThumbnailsState.currentPage > totalPages) {
                layoutThumbnailsState.currentPage = Math.max(1, totalPages);
            }

            if (layoutThumbnailsState.pages.length > 0) {
                renderLayoutThumbnails();
            } else {
                document.getElementById('layout-thumbnails-section').style.display = 'none';
                document.getElementById('review-layout-btn').style.display = 'none';
                document.getElementById('extract-knowledge-btn').style.display = 'none';
            }
        } else {
            alert('Failed to delete page detections');
        }
    } catch (error) {
        console.error('Error deleting page detections:', error);
        alert('Error deleting page detections');
    }
}

function prevLayoutThumbnailsPage() {
    if (layoutThumbnailsState.currentPage > 1) {
        layoutThumbnailsState.currentPage--;
        renderLayoutThumbnails();
    }
}

function nextLayoutThumbnailsPage() {
    const totalPages = Math.ceil(layoutThumbnailsState.pages.length / layoutThumbnailsState.perPage);
    if (layoutThumbnailsState.currentPage < totalPages) {
        layoutThumbnailsState.currentPage++;
        renderLayoutThumbnails();
    }
}

// =============================================================================
// Ignore Rules Management
// =============================================================================

let ignoreRulesState = {
    rules: []
};

/**
 * Load ignore rules for the current book
 */
async function loadIgnoreRules() {
    if (!currentBookId) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/ignore-rules`);
        if (!response.ok) return;

        const data = await response.json();
        ignoreRulesState.rules = data.rules || [];

        renderIgnoreRules();

        // Show section if there are rules
        const section = document.getElementById('ignore-rules-section');
        if (ignoreRulesState.rules.length > 0 || layoutThumbnailsState.pages.length > 0) {
            section.style.display = 'block';
        }

        // Update count badge
        document.getElementById('ignore-rules-count').textContent = ignoreRulesState.rules.length;

    } catch (error) {
        console.error('Error loading ignore rules:', error);
    }
}

/**
 * Render the ignore rules list
 */
function renderIgnoreRules() {
    const list = document.getElementById('ignore-rules-list');

    if (ignoreRulesState.rules.length === 0) {
        list.innerHTML = `
            <div class="no-rules-message" style="color: #999; text-align: center; padding: 20px;">
                No ignore rules defined. Right-click a region in Layout Review and select "Permanently Ignore Similar" to create rules.
            </div>
        `;
        return;
    }

    list.innerHTML = ignoreRulesState.rules.map(rule => `
        <div class="ignore-rule-item" data-rule-id="${rule.id}">
            <div class="rule-info">
                <div class="rule-class">${formatClassName(rule.class_name)}</div>
                <div class="rule-position">
                    Position: (${rule.x}, ${rule.y}) | Size: ${rule.width}×${rule.height} | Tolerance: ±${rule.tolerance}px
                </div>
            </div>
            <button class="rule-delete" onclick="deleteIgnoreRule(${rule.id})">Delete</button>
        </div>
    `).join('');
}

/**
 * Format class name for display
 */
function formatClassName(className) {
    return className
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Delete an ignore rule
 */
async function deleteIgnoreRule(ruleId) {
    if (!confirm('Delete this ignore rule?')) return;

    try {
        const response = await fetch(`/api/auto-slicer/${currentBookId}/ignore-rules/${ruleId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            ignoreRulesState.rules = ignoreRulesState.rules.filter(r => r.id !== ruleId);
            renderIgnoreRules();
            document.getElementById('ignore-rules-count').textContent = ignoreRulesState.rules.length;
        } else {
            alert('Failed to delete ignore rule');
        }
    } catch (error) {
        console.error('Error deleting ignore rule:', error);
        alert('Error deleting ignore rule');
    }
}

// =============================================================================
// Collapsible Section Toggle
// =============================================================================

/**
 * Toggle a collapsible section
 */
function toggleSection(sectionId) {
    const header = document.querySelector(`#${sectionId}-section .collapsible-header`);
    const content = document.getElementById(`${sectionId}-content`);

    if (header && content) {
        const isExpanded = header.classList.toggle('expanded');
        content.classList.toggle('expanded', isExpanded);
        collapsibleSectionStates[sectionId] = isExpanded;
    }
}

// =============================================================================
// GPU Model Management
// =============================================================================

/**
 * Load GPU status and update UI on page load
 */
async function loadGpuStatus() {
    try {
        const response = await fetch('/api/gpu/status');
        if (!response.ok) return;

        const data = await response.json();

        // Update VRAM display
        if (data.gpu_available) {
            const usedMB = Math.round(data.vram_used_mb);
            const totalMB = Math.round(data.vram_total_mb);
            document.getElementById('gpu-vram-display').textContent =
                `GPU VRAM: ${usedMB} / ${totalMB} MB`;
        } else {
            document.getElementById('gpu-vram-display').textContent = 'No GPU Available';
        }

        // Update model status badges
        updateModelStatus('surya', data.loaded_models?.includes('surya'));
        updateModelStatus('easyocr', data.loaded_models?.includes('easyocr'));
        updateModelStatus('yolo', data.loaded_models?.includes('yolo') || data.loaded_models?.includes('DocLayout-YOLO'));

    } catch (error) {
        console.error('Error loading GPU status:', error);
        document.getElementById('gpu-vram-display').textContent = 'GPU Status: Error';
    }
}

/**
 * Update model status display
 */
function updateModelStatus(model, isLoaded) {
    const statusEl = document.getElementById(`${model}-status`);
    const btnEl = document.getElementById(`${model}-load-btn`);

    if (statusEl) {
        if (isLoaded) {
            statusEl.textContent = 'Loaded ✓';
            statusEl.style.color = '#4caf50';
        } else {
            statusEl.textContent = 'Not Loaded';
            statusEl.style.color = '#666';
        }
    }

    if (btnEl) {
        btnEl.textContent = isLoaded ? 'Unload' : 'Load';
        btnEl.className = isLoaded ? 'btn btn-sm btn-danger' : 'btn btn-sm';
    }
}

/**
 * Toggle model load/unload
 */
async function toggleModelLoad(model) {
    const statusEl = document.getElementById(`${model}-status`);
    const btnEl = document.getElementById(`${model}-load-btn`);
    const isCurrentlyLoaded = statusEl?.textContent.includes('✓');

    btnEl.disabled = true;
    statusEl.textContent = isCurrentlyLoaded ? 'Unloading...' : 'Loading...';

    try {
        const endpoint = isCurrentlyLoaded ? 'unload' : 'load';
        const response = await fetch(`/api/gpu/${endpoint}/${model}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const data = await response.json();
            alert(data.detail || `Failed to ${endpoint} ${model}`);
        }

        // Refresh status
        await loadGpuStatus();

    } catch (error) {
        console.error(`Error toggling ${model}:`, error);
        alert(`Error ${isCurrentlyLoaded ? 'unloading' : 'loading'} ${model}`);
    } finally {
        btnEl.disabled = false;
    }
}

// Load GPU status on page load (if section exists)
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('gpu-management-section')) {
        loadGpuStatus();
        // Refresh every 30 seconds
        setInterval(loadGpuStatus, 30000);
    }
});


// =============================================================================
// Title Hierarchy Management (L1/L2 Titles with Attributes)
// =============================================================================

let titleHierarchyState = {
    l1Titles: [],
    l2Titles: [],
    validationPassed: false
};

/**
 * Load L1 and L2 titles for the current book
 */
async function loadTitleHierarchy() {
    if (!currentBookId) return;

    try {
        // Load L1 titles
        const l1Response = await fetch(`/api/books/${currentBookId}/l1-titles`);
        if (l1Response.ok) {
            const l1Data = await l1Response.json();
            titleHierarchyState.l1Titles = l1Data.titles || [];
        }

        // Load L2 titles
        const l2Response = await fetch(`/api/books/${currentBookId}/l2-titles`);
        if (l2Response.ok) {
            const l2Data = await l2Response.json();
            titleHierarchyState.l2Titles = l2Data.titles || [];
        }

        renderL1Titles();
        renderL2Titles();

    } catch (error) {
        console.error('Error loading title hierarchy:', error);
    }
}

/**
 * Render L1 titles list
 */
function renderL1Titles() {
    const container = document.getElementById('l1-titles-list');
    if (!container) return;

    if (titleHierarchyState.l1Titles.length === 0) {
        container.innerHTML = `
            <div class="no-titles-message" style="color: #999; text-align: center; padding: 20px; background: #f9f9f9; border-radius: 4px;">
                No L1 titles configured. Click "Add L1 Title" to create one.
            </div>
        `;
        return;
    }

    container.innerHTML = titleHierarchyState.l1Titles.map(title => `
        <div class="title-hierarchy-row" data-title-id="${title.id}">
            <input type="text" value="${escapeHtml(title.title_text)}" placeholder="Title text" 
                   onchange="updateL1TitleField(${title.id}, 'title_text', this.value)">
            <label style="font-size: 12px; color: #666;">Start:</label>
            <input type="number" value="${title.start_page}" min="1" 
                   onchange="updateL1TitleField(${title.id}, 'start_page', parseInt(this.value))">
            <label style="font-size: 12px; color: #666;">End:</label>
            <input type="number" value="${title.end_page}" min="1" 
                   onchange="updateL1TitleField(${title.id}, 'end_page', parseInt(this.value))">
            <button class="btn-attrs" onclick="openL1AttributeEditor(${title.id})" title="Edit 200 custom attributes">
                📝 Attributes
            </button>
            <button class="btn-delete-title" onclick="deleteL1Title(${title.id})" title="Delete this L1 title">
                ×
            </button>
        </div>
    `).join('');
}

/**
 * Render L2 titles list
 */
function renderL2Titles() {
    const container = document.getElementById('l2-titles-list');
    if (!container) return;

    if (titleHierarchyState.l2Titles.length === 0) {
        container.innerHTML = `
            <div class="no-titles-message" style="color: #999; text-align: center; padding: 20px; background: #f9f9f9; border-radius: 4px;">
                No L2 titles configured. Click "Add L2 Title" to create one.
            </div>
        `;
        return;
    }

    // Build L1 options for parent selection
    const l1Options = titleHierarchyState.l1Titles.map(l1 => 
        `<option value="${l1.id}">${escapeHtml(l1.title_text)} (pp. ${l1.start_page}-${l1.end_page})</option>`
    ).join('');

    container.innerHTML = titleHierarchyState.l2Titles.map(title => `
        <div class="title-hierarchy-row" data-title-id="${title.id}">
            <input type="text" value="${escapeHtml(title.title_text)}" placeholder="Title text" 
                   onchange="updateL2TitleField(${title.id}, 'title_text', this.value)">
            <label style="font-size: 12px; color: #666;">Start:</label>
            <input type="number" value="${title.start_page}" min="1" 
                   onchange="updateL2TitleField(${title.id}, 'start_page', parseInt(this.value))">
            <label style="font-size: 12px; color: #666;">End:</label>
            <input type="number" value="${title.end_page}" min="1" 
                   onchange="updateL2TitleField(${title.id}, 'end_page', parseInt(this.value))">
            <button class="btn-attrs" onclick="openL2AttributeEditor(${title.id})" title="Edit 150 custom attributes">
                📝 Attributes
            </button>
            <button class="btn-delete-title" onclick="deleteL2Title(${title.id})" title="Delete this L2 title">
                ×
            </button>
        </div>
    `).join('');
}

/**
 * Add a new L1 title
 */
async function addL1Title() {
    if (!currentBookId) return;

    const startPage = parseInt(document.getElementById('start-page')?.value) || 1;
    const endPage = parseInt(document.getElementById('end-page')?.value) || startPage;

    try {
        const response = await fetch(`/api/books/${currentBookId}/l1-titles`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title_text: 'New Chapter',
                start_page: startPage,
                end_page: endPage,
                display_order: titleHierarchyState.l1Titles.length
            })
        });

        if (response.ok) {
            await loadTitleHierarchy();
            clearValidationStatus();
        } else {
            const data = await response.json();
            alert(data.detail || 'Failed to create L1 title');
        }
    } catch (error) {
        console.error('Error creating L1 title:', error);
        alert('Error creating L1 title');
    }
}

/**
 * Add a new L2 title
 */
async function addL2Title() {
    if (!currentBookId) return;

    const startPage = parseInt(document.getElementById('start-page')?.value) || 1;
    const endPage = parseInt(document.getElementById('end-page')?.value) || startPage;

    // Find parent L1 based on page range
    let parentL1Id = null;
    for (const l1 of titleHierarchyState.l1Titles) {
        if (startPage >= l1.start_page && endPage <= l1.end_page) {
            parentL1Id = l1.id;
            break;
        }
    }

    try {
        const response = await fetch(`/api/books/${currentBookId}/l2-titles`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title_text: 'New Section',
                start_page: startPage,
                end_page: endPage,
                parent_l1_id: parentL1Id,
                display_order: titleHierarchyState.l2Titles.length
            })
        });

        if (response.ok) {
            await loadTitleHierarchy();
            clearValidationStatus();
        } else {
            const data = await response.json();
            alert(data.detail || 'Failed to create L2 title');
        }
    } catch (error) {
        console.error('Error creating L2 title:', error);
        alert('Error creating L2 title');
    }
}

/**
 * Update an L1 title field
 */
async function updateL1TitleField(titleId, field, value) {
    if (!currentBookId) return;

    try {
        const updateData = {};
        updateData[field] = value;

        const response = await fetch(`/api/books/${currentBookId}/l1-titles/${titleId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });

        if (response.ok) {
            // Update local state
            const title = titleHierarchyState.l1Titles.find(t => t.id === titleId);
            if (title) title[field] = value;
            clearValidationStatus();
        } else {
            const data = await response.json();
            alert(data.detail || 'Failed to update L1 title');
            await loadTitleHierarchy(); // Reload to reset
        }
    } catch (error) {
        console.error('Error updating L1 title:', error);
    }
}

/**
 * Update an L2 title field
 */
async function updateL2TitleField(titleId, field, value) {
    if (!currentBookId) return;

    try {
        const updateData = {};
        updateData[field] = value;

        const response = await fetch(`/api/books/${currentBookId}/l2-titles/${titleId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });

        if (response.ok) {
            // Update local state
            const title = titleHierarchyState.l2Titles.find(t => t.id === titleId);
            if (title) title[field] = value;
            clearValidationStatus();
        } else {
            const data = await response.json();
            alert(data.detail || 'Failed to update L2 title');
            await loadTitleHierarchy(); // Reload to reset
        }
    } catch (error) {
        console.error('Error updating L2 title:', error);
    }
}

/**
 * Delete an L1 title
 */
async function deleteL1Title(titleId) {
    if (!confirm('Delete this L1 title? This cannot be undone.')) return;

    try {
        const response = await fetch(`/api/books/${currentBookId}/l1-titles/${titleId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadTitleHierarchy();
            clearValidationStatus();
        } else {
            const data = await response.json();
            alert(data.detail || 'Failed to delete L1 title');
        }
    } catch (error) {
        console.error('Error deleting L1 title:', error);
        alert('Error deleting L1 title');
    }
}

/**
 * Delete an L2 title
 */
async function deleteL2Title(titleId) {
    if (!confirm('Delete this L2 title? This cannot be undone.')) return;

    try {
        const response = await fetch(`/api/books/${currentBookId}/l2-titles/${titleId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadTitleHierarchy();
            clearValidationStatus();
        } else {
            const data = await response.json();
            alert(data.detail || 'Failed to delete L2 title');
        }
    } catch (error) {
        console.error('Error deleting L2 title:', error);
        alert('Error deleting L2 title');
    }
}

/**
 * Validate title coverage for the selected page range
 */
async function validateTitleCoverage() {
    if (!currentBookId) return;

    const startPage = parseInt(document.getElementById('start-page')?.value) || 1;
    const endPage = parseInt(document.getElementById('end-page')?.value) || startPage;

    try {
        const response = await fetch(
            `/api/books/${currentBookId}/validate-title-coverage?start_page=${startPage}&end_page=${endPage}`
        );

        if (!response.ok) {
            throw new Error('Validation request failed');
        }

        const data = await response.json();
        displayValidationResult(data, startPage, endPage);
        titleHierarchyState.validationPassed = data.valid;

    } catch (error) {
        console.error('Error validating title coverage:', error);
        alert('Error validating title coverage');
    }
}

/**
 * Display validation result
 */
function displayValidationResult(data, startPage, endPage) {
    const statusEl = document.getElementById('title-validation-status');
    if (!statusEl) return;

    statusEl.style.display = 'block';

    if (data.valid) {
        statusEl.className = 'validation-success';
        statusEl.innerHTML = `
            <strong>✅ Validation Passed!</strong><br>
            All pages (${startPage}-${endPage}) are covered by both L1 and L2 titles.
            <br><br>
            <em>You can now run Layout Detection.</em>
        `;
    } else {
        statusEl.className = 'validation-error';
        let message = `<strong>❌ Validation Failed</strong><br>`;
        
        if (!data.l1_valid && data.uncovered_l1_pages?.length > 0) {
            message += `<br><strong>L1 Coverage Missing:</strong> Pages ${data.uncovered_l1_pages.join(', ')}`;
        }
        
        if (!data.l2_valid && data.uncovered_l2_pages?.length > 0) {
            message += `<br><strong>L2 Coverage Missing:</strong> Pages ${data.uncovered_l2_pages.join(', ')}`;
        }
        
        message += `<br><br><em>Please configure titles to cover all pages before running Layout Detection.</em>`;
        statusEl.innerHTML = message;
    }
}

/**
 * Clear validation status
 */
function clearValidationStatus() {
    const statusEl = document.getElementById('title-validation-status');
    if (statusEl) {
        statusEl.style.display = 'none';
        statusEl.className = '';
        statusEl.innerHTML = '';
    }
    titleHierarchyState.validationPassed = false;
}

/**
 * Open L1 attribute editor in a new tab/window
 */
function openL1AttributeEditor(titleId) {
    window.open(`/l1-title-attributes?book_id=${currentBookId}&title_id=${titleId}`, '_blank');
}

/**
 * Open L2 attribute editor in a new tab/window
 */
function openL2AttributeEditor(titleId) {
    window.open(`/l2-title-attributes?book_id=${currentBookId}&title_id=${titleId}`, '_blank');
}

/**
 * Check title validation before Layout Detection
 * Returns true if validation passes, false otherwise
 */
async function checkTitleValidationBeforeDetection() {
    const startPage = parseInt(document.getElementById('start-page')?.value) || 1;
    const endPage = parseInt(document.getElementById('end-page')?.value) || startPage;

    try {
        const response = await fetch(
            `/api/books/${currentBookId}/validate-title-coverage?start_page=${startPage}&end_page=${endPage}`
        );

        if (!response.ok) {
            return true; // Allow detection if validation endpoint fails
        }

        const data = await response.json();
        
        if (!data.valid) {
            displayValidationResult(data, startPage, endPage);
            
            // Scroll to validation section
            const section = document.getElementById('title-hierarchy-section');
            if (section) {
                section.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            
            return false;
        }
        
        return true;

    } catch (error) {
        console.error('Error checking title validation:', error);
        return true; // Allow detection if validation fails
    }
}

// Hook into book selection to load title hierarchy
const originalOnBookSelect = onBookSelect;
onBookSelect = async function() {
    await originalOnBookSelect.apply(this, arguments);
    await loadTitleHierarchy();
};
