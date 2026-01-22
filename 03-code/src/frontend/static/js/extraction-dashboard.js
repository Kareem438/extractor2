// Extraction Dashboard JavaScript
// Phase 3D Implementation

// State
const state = {
    bookId: null,
    bookName: '',
    readyPages: [],
    diagrams: [],
    filteredDiagrams: [],
    summary: [],
    currentPage: 1,
    pageSize: 25,
    totalPages: 1,
    selectedDiagramId: null,
    selectedPageNumber: null,  // Currently selected page in thumbnails
    defaultPrompts: {},
    ws: null,
    isExtracting: false
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get book_id from URL
    const urlParams = new URLSearchParams(window.location.search);
    state.bookId = urlParams.get('book_id');

    if (!state.bookId) {
        alert('No book selected. Please access this page from Auto-Slicer.');
        window.location.href = '/auto-slicer';
        return;
    }

    // Update navigation links
    document.getElementById('layout-review-link').href = `/layout-review?book_id=${state.bookId}`;
    document.getElementById('auto-slicer-link').href = `/auto-slicer?book_id=${state.bookId}`;

    // Load initial data
    loadDashboardData();

    // Connect WebSocket
    connectWebSocket();
});

// Load all dashboard data
async function loadDashboardData() {
    try {
        showLoading('Loading dashboard...');

        // Load book info, ready pages, summary, and diagrams in parallel
        const [bookInfo, dashboardData] = await Promise.all([
            fetch(`/api/books/${state.bookId}`).then(r => r.json()),
            fetch(`/api/extraction/${state.bookId}/dashboard`).then(r => r.json())
        ]);

        state.bookName = bookInfo.book_name || `Book ${state.bookId}`;
        document.getElementById('book-name').textContent = state.bookName;

        // Update state with dashboard data
        state.readyPages = dashboardData.ready_pages || [];
        state.summary = dashboardData.summary || [];
        state.diagrams = dashboardData.diagrams || [];
        state.defaultPrompts = dashboardData.prompts || {};

        // Update progress
        updateProgress(dashboardData.progress || {});

        // Render components
        renderThumbnails();
        renderSummaryTable();
        filterDiagrams();
        updateClassStats();

        hideLoading();
    } catch (error) {
        console.error('Error loading dashboard:', error);
        hideLoading();
        alert('Error loading dashboard data. Please try again.');
    }
}

// Connect WebSocket for live updates
function connectWebSocket() {
    // Don't reconnect if we already have an active connection
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        return;
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/extraction/${state.bookId}`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        console.log('WebSocket connected');
    };

    state.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };

    state.ws.onclose = () => {
        console.log('WebSocket closed');
        // Only reconnect if extraction is in progress
        if (state.isExtracting) {
            console.log('Reconnecting in 3s...');
            setTimeout(connectWebSocket, 3000);
        }
    };

    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'progress':
            updateProgress(message.data);
            break;
        case 'status_change':
            updateDiagramStatus(message.data.diagram_id, message.data.new_status);
            break;
        case 'completed':
            state.isExtracting = false;
            document.getElementById('start-btn').disabled = false;
            document.getElementById('start-btn').textContent = 'Start OCR Extraction';
            hideLoading();
            loadDashboardData(); // Refresh all data
            break;
        case 'error':
            console.error('Extraction error:', message.data.message);
            if (message.data.diagram_id) {
                updateDiagramStatus(message.data.diagram_id, 'failed');
            }
            break;
    }
}

// Update progress bars
function updateProgress(progress) {
    const ocrCompleted = progress.paragraphs_ocr?.completed || 0;
    const ocrTotal = progress.paragraphs_ocr?.total || 0;
    const decodeCompleted = progress.diagrams_decode?.completed || 0;
    const decodeTotal = progress.diagrams_decode?.total || 0;

    const ocrPercent = ocrTotal > 0 ? Math.round((ocrCompleted / ocrTotal) * 100) : 0;
    const decodePercent = decodeTotal > 0 ? Math.round((decodeCompleted / decodeTotal) * 100) : 0;

    document.getElementById('ocr-progress-bar').style.width = `${ocrPercent}%`;
    document.getElementById('ocr-progress-text').textContent = `${ocrPercent}%`;
    document.getElementById('ocr-count').textContent = `${ocrCompleted}/${ocrTotal}`;

    document.getElementById('decode-progress-bar').style.width = `${decodePercent}%`;
    document.getElementById('decode-progress-text').textContent = `${decodePercent}%`;
    document.getElementById('decode-count').textContent = `${decodeCompleted}/${decodeTotal}`;
}

// Update single diagram status
function updateDiagramStatus(diagramId, newStatus) {
    const diagram = state.diagrams.find(d => d.id === diagramId);
    if (diagram) {
        diagram.status = newStatus;
        renderDiagramsTable();
    }
}

// Render page thumbnails in sidebar
function renderThumbnails() {
    const container = document.getElementById('thumbnails-container');
    container.innerHTML = '';

    document.getElementById('page-count').textContent = `${state.readyPages.length} pages`;

    if (state.readyPages.length === 0) {
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">No pages ready for extraction</div>';
        return;
    }

    state.readyPages.forEach(page => {
        const item = document.createElement('div');
        item.className = 'thumbnail-item';
        item.dataset.pageNumber = page.page_number;
        
        // Left-click: select page and show regions in right panel
        item.onclick = (e) => {
            e.preventDefault();
            selectPage(page.page_number);
        };
        
        // Right-click: show context menu
        item.oncontextmenu = (e) => {
            e.preventDefault();
            showThumbnailContextMenu(e, page.page_number);
        };

        // Status dot
        let statusClass = 'pending';
        if (page.ocr_complete && page.decode_complete) {
            statusClass = 'complete';
        } else if (page.ocr_complete || page.decode_complete) {
            statusClass = 'partial';
        }

        item.innerHTML = `
            <div class="status-dot ${statusClass}"></div>
            <canvas id="thumb-canvas-${page.page_number}" width="160" height="120"></canvas>
            <div class="thumbnail-label">Page ${page.page_number}</div>
        `;

        container.appendChild(item);

        // Render thumbnail with region boxes (no image, just colored boxes on dark background)
        renderThumbnailRegions(page.page_number, page.regions);
    });
    
    // Select first page by default if none selected
    if (state.readyPages.length > 0 && !state.selectedPageNumber) {
        selectPage(state.readyPages[0].page_number);
    }
}

// Render thumbnail with page image and colored region boxes
async function renderThumbnailRegions(pageNumber, regions) {
    const canvas = document.getElementById(`thumb-canvas-${pageNumber}`);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    
    // Dark background initially
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    try {
        // Load page image using the review-raw endpoint (same as auto-slicer)
        const response = await fetch(`/api/review-raw/${state.bookId}/page/${pageNumber}`);
        if (!response.ok) {
            throw new Error('Failed to load page image');
        }

        const data = await response.json();
        if (!data.image_base64) {
            throw new Error('No image data');
        }

        const img = new Image();
        img.onload = () => {
            // Calculate scale to fit canvas
            const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
            const drawWidth = img.width * scale;
            const drawHeight = img.height * scale;
            const offsetX = (canvas.width - drawWidth) / 2;
            const offsetY = (canvas.height - drawHeight) / 2;

            // Clear and draw image
            ctx.fillStyle = '#1a1a2e';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);

            // Draw region boxes if available
            if (regions && regions.length > 0) {
                regions.forEach(region => {
                    const x = offsetX + region.x * scale;
                    const y = offsetY + region.y * scale;
                    const w = region.width * scale;
                    const h = region.height * scale;

                    // Border
                    ctx.strokeStyle = getClassColor(region.class_name);
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x, y, w, h);
                });
            }
        };

        img.onerror = () => {
            drawNoPreview(ctx, canvas);
        };

        img.src = `data:image/png;base64,${data.image_base64}`;

    } catch (error) {
        console.error('Error loading thumbnail:', error);
        drawNoPreview(ctx, canvas);
    }
}

// Draw "No preview" message on canvas
function drawNoPreview(ctx, canvas) {
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#666';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('No preview', canvas.width / 2, canvas.height / 2);
}

// Select a page and update the right panel
function selectPage(pageNumber) {
    state.selectedPageNumber = pageNumber;
    
    // Update thumbnail selection visual
    document.querySelectorAll('.thumbnail-item').forEach(item => {
        item.classList.remove('selected');
        if (parseInt(item.dataset.pageNumber) === pageNumber) {
            item.classList.add('selected');
        }
    });
    
    // Update right panel with page regions
    renderPageRegions(pageNumber);
}

// Render regions for selected page in right panel
function renderPageRegions(pageNumber) {
    const page = state.readyPages.find(p => p.page_number === pageNumber);
    if (!page) return;
    
    // Update header
    const header = document.querySelector('.diagrams-section h3') || document.querySelector('.content-section h3');
    if (header) {
        header.textContent = `Page ${pageNumber} Regions`;
    }
    
    // Filter diagrams to show only this page's regions
    state.filteredDiagrams = state.diagrams.filter(d => d.page_number === pageNumber);
    
    // Re-render the diagrams table
    renderDiagramsTable();
}

// Show context menu for thumbnail
function showThumbnailContextMenu(event, pageNumber) {
    // Remove existing context menu if any
    const existingMenu = document.getElementById('thumbnail-context-menu');
    if (existingMenu) existingMenu.remove();
    
    const menu = document.createElement('div');
    menu.id = 'thumbnail-context-menu';
    menu.className = 'context-menu';
    menu.style.cssText = `
        position: fixed;
        left: ${event.clientX}px;
        top: ${event.clientY}px;
        background: #2d2d44;
        border: 1px solid #444;
        border-radius: 4px;
        padding: 4px 0;
        z-index: 1000;
        min-width: 180px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    
    menu.innerHTML = `
        <div class="context-menu-item" onclick="openLayoutReview(${pageNumber}); hideThumbnailContextMenu();" 
             style="padding: 8px 16px; cursor: pointer; color: #fff;">
            🔍 Go to Layout Review
        </div>
        <div class="context-menu-item" onclick="extractSinglePage(${pageNumber}); hideThumbnailContextMenu();"
             style="padding: 8px 16px; cursor: pointer; color: #fff;">
            ⚡ Extract This Page
        </div>
    `;
    
    // Add hover effect
    menu.querySelectorAll('.context-menu-item').forEach(item => {
        item.onmouseenter = () => item.style.background = '#3d3d5c';
        item.onmouseleave = () => item.style.background = 'transparent';
    });
    
    document.body.appendChild(menu);
    
    // Close menu on click outside
    setTimeout(() => {
        document.addEventListener('click', hideThumbnailContextMenu, { once: true });
    }, 0);
}

function hideThumbnailContextMenu() {
    const menu = document.getElementById('thumbnail-context-menu');
    if (menu) menu.remove();
}

// Extract a single page
async function extractSinglePage(pageNumber) {
    if (state.isExtracting) {
        alert('Extraction already in progress');
        return;
    }
    
    const confirmed = confirm(`Start extraction for page ${pageNumber}?`);
    if (!confirmed) return;
    
    try {
        state.isExtracting = true;
        
        const response = await fetch(`/api/extraction/${state.bookId}/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ page_numbers: [pageNumber] })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Extraction failed');
        }
        
        alert(`Extraction started for page ${pageNumber}`);
        
    } catch (error) {
        console.error('Error starting extraction:', error);
        alert('Failed to start extraction: ' + error.message);
    } finally {
        state.isExtracting = false;
    }
}

// Get color for region class
function getClassColor(className) {
    const colors = {
        'paragraph': '#4CAF50',
        'diagram': '#2196F3',
        'table': '#4CAF50',
        'equation': '#9C27B0',
        'list_bulleted': '#FF9800',
        'list_numbered': '#FF9800',
        'list_lettered': '#FF9800',
        'question': '#9C27B0',
        'answer': '#E91E63',
        'title_l1': '#f44336',
        'title_l2': '#E91E63',
        'title_l3': '#FF5722'
    };
    return colors[className] || '#666';
}

// Open layout review for a page
function openLayoutReview(pageNumber) {
    window.open(`/layout-review?book_id=${state.bookId}&page=${pageNumber}`, '_blank');
}

// Render summary table
function renderSummaryTable() {
    const tbody = document.getElementById('summary-table-body');
    tbody.innerHTML = '';

    if (state.summary.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #666;">No data available</td></tr>';
        return;
    }

    // Calculate totals
    const totals = { paragraphs: 0, diagrams: 0, tables: 0, equations: 0, lists: 0, questions: 0, answers: 0 };

    state.summary.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="l3-title">${item.l3_title || '(No L3 Title)'}</td>
            <td class="count">${item.paragraphs || 0}</td>
            <td class="count">${item.diagrams || 0}</td>
            <td class="count">${item.tables || 0}</td>
            <td class="count">${item.equations || 0}</td>
            <td class="count">${item.lists || 0}</td>
            <td class="count">${item.questions || 0}</td>
            <td class="count">${item.answers || 0}</td>
        `;
        row.style.cursor = 'pointer';
        row.onclick = () => filterByL3Title(item.l3_title);
        tbody.appendChild(row);

        totals.paragraphs += item.paragraphs || 0;
        totals.diagrams += item.diagrams || 0;
        totals.tables += item.tables || 0;
        totals.equations += item.equations || 0;
        totals.lists += item.lists || 0;
        totals.questions += item.questions || 0;
        totals.answers += item.answers || 0;
    });

    // Add totals row
    const totalRow = document.createElement('tr');
    totalRow.className = 'total-row';
    totalRow.innerHTML = `
        <td>Total</td>
        <td class="count">${totals.paragraphs}</td>
        <td class="count">${totals.diagrams}</td>
        <td class="count">${totals.tables}</td>
        <td class="count">${totals.equations}</td>
        <td class="count">${totals.lists}</td>
        <td class="count">${totals.questions}</td>
        <td class="count">${totals.answers}</td>
    `;
    tbody.appendChild(totalRow);
}

// Filter diagrams by L3 title (from summary table click)
function filterByL3Title(l3Title) {
    // For now, just log - can implement L3 filtering later
    console.log('Filter by L3:', l3Title);
}

// Filter diagrams
function filterDiagrams() {
    const classFilter = document.getElementById('class-filter').value;
    const statusFilter = document.getElementById('status-filter').value;

    state.filteredDiagrams = state.diagrams.filter(d => {
        let matchClass = true;
        let matchStatus = true;

        if (classFilter !== 'all') {
            if (classFilter === 'list') {
                matchClass = d.class_name.startsWith('list');
            } else {
                matchClass = d.class_name === classFilter;
            }
        }

        if (statusFilter !== 'all') {
            matchStatus = d.status === statusFilter;
        }

        return matchClass && matchStatus;
    });

    state.currentPage = 1;
    state.totalPages = Math.ceil(state.filteredDiagrams.length / state.pageSize) || 1;
    renderDiagramsTable();
    updatePagination();
}

// Change page size
function changePageSize() {
    state.pageSize = parseInt(document.getElementById('page-size').value);
    state.currentPage = 1;
    state.totalPages = Math.ceil(state.filteredDiagrams.length / state.pageSize) || 1;
    renderDiagramsTable();
    updatePagination();
}

// Render diagrams table
function renderDiagramsTable() {
    const tbody = document.getElementById('diagrams-table-body');
    tbody.innerHTML = '';

    const startIndex = (state.currentPage - 1) * state.pageSize;
    const endIndex = startIndex + state.pageSize;
    const pageDiagrams = state.filteredDiagrams.slice(startIndex, endIndex);

    if (pageDiagrams.length === 0) {
        document.getElementById('no-diagrams-message').style.display = 'block';
        return;
    }
    document.getElementById('no-diagrams-message').style.display = 'none';

    pageDiagrams.forEach(diagram => {
        const row = document.createElement('tr');

        // Determine class badge style
        let classType = 'diagram';
        if (diagram.class_name === 'table') classType = 'table';
        else if (diagram.class_name === 'equation') classType = 'equation';
        else if (diagram.class_name.startsWith('list')) classType = 'list';
        else if (diagram.class_name === 'question') classType = 'question';
        else if (diagram.class_name === 'answer') classType = 'answer';

        row.innerHTML = `
            <td class="thumbnail-cell">
                <img src="/api/extraction/${state.bookId}/diagram-image/${diagram.id}"
                     alt="Diagram"
                     onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2260%22 height=%2245%22><rect fill=%22%230f3460%22 width=%2260%22 height=%2245%22/><text x=%2230%22 y=%2225%22 fill=%22%23666%22 text-anchor=%22middle%22 font-size=%2210%22>No image</text></svg>'"
                     onclick="openViewModal(${diagram.id})">
            </td>
            <td>${diagram.page_number}</td>
            <td class="class-cell">
                <span class="class-badge ${classType}">${formatClassName(diagram.class_name)}</span>
            </td>
            <td class="status-cell">
                <span class="status-badge ${diagram.status}">${formatStatus(diagram.status)}</span>
            </td>
            <td class="actions-cell">
                <button class="action-btn view" onclick="openViewModal(${diagram.id})">View</button>
                <button class="action-btn edit" onclick="openEditModal(${diagram.id})">Edit</button>
                <button class="action-btn redecode" onclick="openRedecodeModal(${diagram.id})">Re-decode</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Format class name for display
function formatClassName(className) {
    const names = {
        'diagram': 'Diagram',
        'table': 'Table',
        'equation': 'Equation',
        'list_bulleted': 'Bullet List',
        'list_numbered': 'Numbered List',
        'list_lettered': 'Lettered List',
        'question': 'Question',
        'answer': 'Answer'
    };
    return names[className] || className;
}

// Format status for display
function formatStatus(status) {
    const statuses = {
        'pending': 'Pending',
        'processing': 'Processing',
        'decoded': 'Decoded',
        'failed': 'Failed'
    };
    return statuses[status] || status;
}

// Update pagination controls
function updatePagination() {
    document.getElementById('page-info').textContent = `Page ${state.currentPage} of ${state.totalPages}`;
    document.getElementById('prev-btn').disabled = state.currentPage <= 1;
    document.getElementById('next-btn').disabled = state.currentPage >= state.totalPages;
}

// Pagination controls
function prevPage() {
    if (state.currentPage > 1) {
        state.currentPage--;
        renderDiagramsTable();
        updatePagination();
    }
}

function nextPage() {
    if (state.currentPage < state.totalPages) {
        state.currentPage++;
        renderDiagramsTable();
        updatePagination();
    }
}

// Start extraction
async function startExtraction() {
    if (state.isExtracting) return;

    if (state.readyPages.length === 0) {
        alert('No pages ready for extraction. Please mark pages as "Ready for Extraction" in Layout Review first.');
        return;
    }

    const confirmed = confirm(`Start OCR extraction for ${state.readyPages.length} pages using Surya OCR?`);

    if (!confirmed) return;

    try {
        state.isExtracting = true;
        document.getElementById('start-btn').disabled = true;
        document.getElementById('start-btn').textContent = 'Extracting...';
        showLoading('Starting OCR extraction...');

        const response = await fetch(`/api/extraction/${state.bookId}/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                page_numbers: state.readyPages.map(p => p.page_number)
            })
        });

        if (!response.ok) {
            throw new Error('Failed to start extraction');
        }

        // WebSocket will handle progress updates
    } catch (error) {
        console.error('Error starting extraction:', error);
        state.isExtracting = false;
        document.getElementById('start-btn').disabled = false;
        document.getElementById('start-btn').textContent = 'Start OCR Extraction';
        hideLoading();
        alert('Error starting extraction: ' + error.message);
    }
}

// View Modal
async function openViewModal(diagramId) {
    const diagram = state.diagrams.find(d => d.id === diagramId);
    if (!diagram) return;

    state.selectedDiagramId = diagramId;

    try {
        const response = await fetch(`/api/extraction/${state.bookId}/diagram/${diagramId}/view`);
        const data = await response.json();

        document.getElementById('view-image').src = `/api/extraction/${state.bookId}/diagram-image/${diagramId}`;
        document.getElementById('view-page').textContent = data.page_number;
        document.getElementById('view-class').textContent = formatClassName(data.class_name);
        document.getElementById('view-parent').textContent = data.parent_paragraph || '(No parent paragraph)';
        document.getElementById('view-text').textContent = data.extracted_text || '(Not decoded yet)';

        document.getElementById('view-modal').classList.add('active');
    } catch (error) {
        console.error('Error loading diagram details:', error);
        alert('Error loading diagram details');
    }
}

function closeViewModal() {
    document.getElementById('view-modal').classList.remove('active');
    state.selectedDiagramId = null;
}

// Edit Modal
async function openEditModal(diagramId) {
    const diagram = state.diagrams.find(d => d.id === diagramId);
    if (!diagram) return;

    state.selectedDiagramId = diagramId;

    try {
        const response = await fetch(`/api/extraction/${state.bookId}/diagram/${diagramId}/view`);
        const data = await response.json();

        document.getElementById('edit-textarea').value = data.extracted_text || '';
        document.getElementById('edit-modal').classList.add('active');
    } catch (error) {
        console.error('Error loading diagram for edit:', error);
        alert('Error loading diagram');
    }
}

function closeEditModal() {
    document.getElementById('edit-modal').classList.remove('active');
    state.selectedDiagramId = null;
}

async function saveEdit() {
    if (!state.selectedDiagramId) return;

    const newText = document.getElementById('edit-textarea').value;

    try {
        showLoading('Saving...');

        const response = await fetch(`/api/extraction/${state.bookId}/diagram/${state.selectedDiagramId}/edit`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ extracted_text: newText })
        });

        if (!response.ok) {
            throw new Error('Failed to save');
        }

        // Update local state
        const diagram = state.diagrams.find(d => d.id === state.selectedDiagramId);
        if (diagram) {
            diagram.extracted_text = newText;
            if (newText && newText.trim()) {
                diagram.status = 'decoded';
            }
        }

        hideLoading();
        closeEditModal();
        renderDiagramsTable();
    } catch (error) {
        console.error('Error saving edit:', error);
        hideLoading();
        alert('Error saving: ' + error.message);
    }
}

// Re-decode Modal
async function openRedecodeModal(diagramId) {
    const diagram = state.diagrams.find(d => d.id === diagramId);
    if (!diagram) return;

    state.selectedDiagramId = diagramId;

    try {
        const response = await fetch(`/api/extraction/${state.bookId}/diagram/${diagramId}/view`);
        const data = await response.json();

        document.getElementById('redecode-image').src = `/api/extraction/${state.bookId}/diagram-image/${diagramId}`;
        document.getElementById('redecode-parent').textContent = data.parent_paragraph || '(No parent paragraph)';

        // Get default prompt for this class
        const classPrompt = state.defaultPrompts[diagram.class_name] || state.defaultPrompts['diagram'] || '';
        document.getElementById('redecode-prompt').value = classPrompt;

        document.getElementById('redecode-result').innerHTML = '<span style="color: #666;">Click "Re-decode" to generate result</span>';
        document.getElementById('save-redecode-btn').disabled = true;

        document.getElementById('redecode-modal').classList.add('active');
    } catch (error) {
        console.error('Error loading diagram for re-decode:', error);
        alert('Error loading diagram');
    }
}

function closeRedecodeModal() {
    document.getElementById('redecode-modal').classList.remove('active');
    state.selectedDiagramId = null;
}

function resetPrompt() {
    const diagram = state.diagrams.find(d => d.id === state.selectedDiagramId);
    if (!diagram) return;

    const classPrompt = state.defaultPrompts[diagram.class_name] || state.defaultPrompts['diagram'] || '';
    document.getElementById('redecode-prompt').value = classPrompt;
}

async function executeRedecode() {
    if (!state.selectedDiagramId) return;

    const prompt = document.getElementById('redecode-prompt').value;
    if (!prompt.trim()) {
        alert('Please enter a prompt');
        return;
    }

    try {
        document.getElementById('redecode-result').innerHTML = '<div class="loading"><div class="spinner"></div> Processing...</div>';
        document.getElementById('redecode-result').classList.add('loading');

        const response = await fetch(`/api/extraction/${state.bookId}/diagram/${state.selectedDiagramId}/redecode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt })
        });

        if (!response.ok) {
            throw new Error('Re-decode failed');
        }

        const data = await response.json();

        document.getElementById('redecode-result').classList.remove('loading');
        document.getElementById('redecode-result').textContent = data.result || '(Empty response)';
        document.getElementById('save-redecode-btn').disabled = false;

        // Store result for saving
        state.redecodeResult = data.result;
    } catch (error) {
        console.error('Error re-decoding:', error);
        document.getElementById('redecode-result').classList.remove('loading');
        document.getElementById('redecode-result').innerHTML = `<span style="color: #f44336;">Error: ${error.message}</span>`;
    }
}

async function saveRedecodeResult() {
    if (!state.selectedDiagramId || !state.redecodeResult) return;

    try {
        showLoading('Saving result...');

        const response = await fetch(`/api/extraction/${state.bookId}/diagram/${state.selectedDiagramId}/edit`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ extracted_text: state.redecodeResult })
        });

        if (!response.ok) {
            throw new Error('Failed to save');
        }

        // Update local state
        const diagram = state.diagrams.find(d => d.id === state.selectedDiagramId);
        if (diagram) {
            diagram.extracted_text = state.redecodeResult;
            diagram.status = 'decoded';
        }

        hideLoading();
        closeRedecodeModal();
        renderDiagramsTable();

        // Update progress
        loadDashboardData();
    } catch (error) {
        console.error('Error saving re-decode result:', error);
        hideLoading();
        alert('Error saving: ' + error.message);
    }
}

// Loading overlay
function showLoading(text) {
    document.getElementById('loading-text').textContent = text || 'Processing...';
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}

// Update class statistics based on radio button selection
function updateClassStats() {
    const scope = document.querySelector('input[name="stats-scope"]:checked').value;
    const tbody = document.getElementById('class-stats-body');
    
    if (!tbody) return;
    
    // Calculate stats based on scope
    let stats = {};
    const classTypes = ['paragraph', 'diagram', 'table', 'equation', 'list_bulleted', 'list_numbered', 'list_lettered', 'question', 'answer'];
    
    // Initialize stats
    classTypes.forEach(cls => {
        stats[cls] = { count: 0, extracted: 0, pending: 0 };
    });
    
    if (scope === 'current' && state.selectedPageNumber) {
        // Get stats for current page only
        const page = state.readyPages.find(p => p.page_number === state.selectedPageNumber);
        if (page && page.regions) {
            page.regions.forEach(region => {
                const cls = region.class_name;
                if (stats[cls]) {
                    stats[cls].count++;
                    stats[cls].pending++;
                }
            });
        }
        
        // Check extracted diagrams for this page
        state.diagrams.filter(d => d.page_number === state.selectedPageNumber).forEach(d => {
            const cls = d.class_name;
            if (stats[cls]) {
                stats[cls].extracted++;
                stats[cls].pending = Math.max(0, stats[cls].pending - 1);
            }
        });
    } else {
        // Get stats for all ready pages
        state.readyPages.forEach(page => {
            if (page.regions) {
                page.regions.forEach(region => {
                    const cls = region.class_name;
                    if (stats[cls]) {
                        stats[cls].count++;
                        stats[cls].pending++;
                    }
                });
            }
        });
        
        // Check extracted diagrams
        state.diagrams.forEach(d => {
            const cls = d.class_name;
            if (stats[cls]) {
                stats[cls].extracted++;
                stats[cls].pending = Math.max(0, stats[cls].pending - 1);
            }
        });
    }
    
    // Render table
    tbody.innerHTML = '';
    
    const classLabels = {
        'paragraph': 'Paragraph',
        'diagram': 'Diagram',
        'table': 'Table',
        'equation': 'Equation',
        'list_bulleted': 'Bulleted List',
        'list_numbered': 'Numbered List',
        'list_lettered': 'Lettered List',
        'question': 'Question',
        'answer': 'Answer'
    };
    
    let totalCount = 0, totalExtracted = 0, totalPending = 0;
    
    classTypes.forEach(cls => {
        const s = stats[cls];
        if (s.count > 0) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${classLabels[cls]}</td>
                <td class="count">${s.count}</td>
                <td class="count" style="color: #4CAF50;">${s.extracted}</td>
                <td class="count" style="color: #FF9800;">${s.pending}</td>
            `;
            tbody.appendChild(row);
            
            totalCount += s.count;
            totalExtracted += s.extracted;
            totalPending += s.pending;
        }
    });
    
    // Add total row
    if (totalCount > 0) {
        const totalRow = document.createElement('tr');
        totalRow.className = 'total-row';
        totalRow.innerHTML = `
            <td><strong>Total</strong></td>
            <td class="count"><strong>${totalCount}</strong></td>
            <td class="count" style="color: #4CAF50;"><strong>${totalExtracted}</strong></td>
            <td class="count" style="color: #FF9800;"><strong>${totalPending}</strong></td>
        `;
        tbody.appendChild(totalRow);
    } else {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #666;">No regions detected</td></tr>';
    }
}

// Override selectPage to also update class stats
const originalSelectPage = selectPage;
selectPage = function(pageNumber) {
    originalSelectPage(pageNumber);
    updateClassStats();
    showPagePreview(pageNumber);
    loadPageExtractionResults(pageNumber);
};

// Toggle statistics section
function toggleStatsSection() {
    const section = document.getElementById('stats-section');
    const content = document.getElementById('stats-content');
    const icon = document.getElementById('stats-toggle-icon');
    
    if (section.classList.contains('collapsed')) {
        section.classList.remove('collapsed');
        content.classList.add('expanded');
        icon.textContent = '▲';
    } else {
        section.classList.add('collapsed');
        content.classList.remove('expanded');
        icon.textContent = '▼';
    }
}

// Show page preview
function showPagePreview(pageNumber) {
    const previewSection = document.getElementById('page-preview-section');
    const previewTitle = document.getElementById('preview-page-title');
    const previewImage = document.getElementById('preview-page-image');
    
    previewSection.style.display = 'block';
    previewTitle.textContent = `Page ${pageNumber} Preview`;
    
    // Load page image
    previewImage.src = `/api/review-raw/${state.bookId}/page/${pageNumber}/image`;
    previewImage.onerror = () => {
        previewImage.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="300" height="400"><rect fill="%230a0a15" width="300" height="400"/><text x="150" y="200" fill="%23666" text-anchor="middle" font-size="14">No preview available</text></svg>';
    };
}

// Load extraction results for a page from raw tables
async function loadPageExtractionResults(pageNumber) {
    const paragraphsContainer = document.getElementById('paragraphs-results');
    const diagramsContainer = document.getElementById('diagrams-results');
    
    // Show loading state
    paragraphsContainer.innerHTML = '<div class="no-results">Loading...</div>';
    diagramsContainer.innerHTML = '<div class="no-results">Loading...</div>';
    
    try {
        // Fetch extraction results for this page
        const response = await fetch(`/api/extraction/${state.bookId}/page/${pageNumber}/results`);
        
        if (!response.ok) {
            throw new Error('Failed to load results');
        }
        
        const data = await response.json();
        
        // Render paragraphs
        if (data.paragraphs && data.paragraphs.length > 0) {
            paragraphsContainer.innerHTML = data.paragraphs.map(p => `
                <div class="result-item">
                    ${p.image_url ? `<img src="${p.image_url}" alt="Paragraph" onerror="this.style.display='none'">` : ''}
                    <div class="result-text">${p.extracted_text || '(No text extracted)'}</div>
                </div>
            `).join('');
        } else {
            paragraphsContainer.innerHTML = '<div class="no-results">No paragraphs extracted yet</div>';
        }
        
        // Render other classes (diagrams, tables, equations, etc.)
        if (data.diagrams && data.diagrams.length > 0) {
            diagramsContainer.innerHTML = data.diagrams.map(d => `
                <div class="result-item">
                    <div class="result-class">${formatClassName(d.class_name)}</div>
                    ${d.image_url ? `<img src="${d.image_url}" alt="${d.class_name}" onerror="this.style.display='none'">` : ''}
                    <div class="result-text">${d.extracted_text || '(Pending Claude analysis)'}</div>
                </div>
            `).join('');
        } else {
            diagramsContainer.innerHTML = '<div class="no-results">No diagrams/tables/equations extracted yet</div>';
        }
        
    } catch (error) {
        console.error('Error loading extraction results:', error);
        paragraphsContainer.innerHTML = '<div class="no-results">Error loading results</div>';
        diagramsContainer.innerHTML = '<div class="no-results">Error loading results</div>';
    }
}

// Extract selected page
async function extractSelectedPage() {
    if (!state.selectedPageNumber) {
        alert('Please select a page first');
        return;
    }
    
    await extractSinglePage(state.selectedPageNumber);
}
