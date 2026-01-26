/**
 * Layout Review Page JavaScript
 *
 * Full-featured canvas editor for reviewing YOLO-detected layout regions.
 * Features:
 * - Click to select regions
 * - Draw new regions
 * - Move/resize regions (drag handles)
 * - Keyboard shortcuts
 * - Class reclassification
 * - Page navigation
 * - Dual page view (prev+current or current+next)
 * - Diagram-to-paragraph linking
 * - Ignore class for regions to skip
 */

// =============================================================================
// Global State
// =============================================================================

const state = {
    bookId: null,
    bookName: '',

    // All regions loaded from API
    allRegions: [],

    // All pages in the book (for dual view navigation)
    allBookPages: [],

    // Pages with regions (sorted)
    pages: [],
    currentPageIndex: 0,

    // Current page regions (primary canvas)
    pageRegions: [],

    // Secondary page regions (for dual view)
    secondaryPageRegions: [],
    secondaryPageNumber: null,

    // Selection - supports multi-select with Ctrl+click
    selectedRegionId: null,           // Primary selected region (for backwards compat)
    selectedRegions: [],              // Array of {id, canvasId} for multi-selection
    selectedCanvasId: 'primary',      // Canvas of primary selection

    // Canvas state
    canvas: null,
    ctx: null,
    secondaryCanvas: null,
    secondaryCtx: null,
    image: null,
    secondaryImage: null,
    zoom: 0.10, // Default 10%

    // View mode: 'single', 'dual-prev', 'dual-next'
    viewMode: 'dual-next',

    // Arabic (RTL) mode - swaps left/right page order (default: true for Arabic books)
    arabicMode: true,

    // Page confirmation status tracking
    // Key: page_number, Value: { classesConfirmed: bool, regionsConfirmed: bool }
    pageConfirmations: {},

    // Context menu state
    contextMenuRegion: null,
    contextMenuCanvas: null,

    // Interaction mode: 'select', 'draw', 'link'
    mode: 'select',

    // Drawing state
    isDrawing: false,
    isDragging: false,
    isResizing: false,
    dragStartX: 0,
    dragStartY: 0,
    dragOffsetX: 0,
    dragOffsetY: 0,
    resizeHandle: null,
    activeCanvas: null, // Which canvas is being interacted with

    // Current drawing rectangle
    drawingRect: null,

    // Linking state
    linkSourceRegion: null, // The diagram being linked
    links: [], // Array of {diagramId, paragraphId, diagramPage, paragraphPage}

    // L3 Title linking state
    isLinkingToL3: false,          // True when in "link to L3 title" mode
    regionsToLinkToL3: [],         // Regions to link when L3 title is clicked
    l3Links: [],                   // Array of {regionId, l3TitleId} for L3 title links

    // L1/L2 Title config (from Auto-Slicer)
    level1Titles: [],              // Array of {title, start_page, end_page}
    level2Titles: [],              // Array of {title, start_page, end_page}

    // Enabled classes for this book (from Auto-Slicer config)
    enabledClasses: [],            // Array of enabled class names

    // Change boundary state
    changingBoundaryRegion: null, // Region being replaced {id, class_name, page_number, canvasId}

    // Split region state
    isSplitting: false,           // True when in split mode
    splitRegion: null,            // Region being split
    splitCanvasId: null,          // Canvas where split is happening
    splitStart: null,             // Start point of split line {x, y}
    splitEnd: null,               // End point of split line {x, y}
    splitPreviewEnd: null,        // Preview end point during mouse move

    // Orphan highlight state (for validation errors)
    orphanHighlight: null,        // Set of region IDs to highlight as orphans
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
    'caption': '#99CC00',
    'question': '#9C27B0',
    'answer': '#E91E63',
    'ignore': '#444444'
};

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Get book_id from URL
    const urlParams = new URLSearchParams(window.location.search);
    state.bookId = urlParams.get('book_id');
    
    // Get optional page parameter for direct navigation
    const targetPage = urlParams.get('page') ? parseInt(urlParams.get('page')) : null;

    if (!state.bookId) {
        hideLoading();
        document.querySelector('.main-container').innerHTML = `
            <div class="no-data">
                <h2>No Book Selected</h2>
                <p>Please go back to <a href="/auto-slicer">Auto-Slicer</a> and run layout detection first.</p>
            </div>
        `;
        return;
    }

    // Set back link
    document.getElementById('back-link').href = `/auto-slicer?book_id=${state.bookId}`;

    // Set back to extraction link
    document.getElementById('back-to-extraction-link').href = `/extraction-dashboard?book_id=${state.bookId}`;

    // Initialize canvases
    state.canvas = document.getElementById('review-canvas');
    state.ctx = state.canvas.getContext('2d');
    state.secondaryCanvas = document.getElementById('secondary-canvas');
    state.secondaryCtx = state.secondaryCanvas.getContext('2d');

    // Setup event listeners
    setupCanvasEvents(state.canvas, 'primary');
    setupCanvasEvents(state.secondaryCanvas, 'secondary');
    setupKeyboardShortcuts();
    setupContextMenu();

    // Initialize RTL mode (default is checked)
    const rtlCheckbox = document.getElementById('arabic-mode-checkbox');
    rtlCheckbox.checked = state.arabicMode;
    applyArabicModeOrder();

    // Load data - use async IIFE to ensure proper order
    (async function() {
        await loadBookInfo();
        await loadTitleConfigs();  // Load L1/L2 title configurations FIRST
        await loadEnabledClasses();  // Load enabled classes for context menu filtering
        await loadRegions();  // This calls loadCurrentPage() which needs titles
        
        // Navigate to target page if specified in URL
        if (targetPage && state.pages.length > 0) {
            navigateToPage(targetPage);
        }
    })();
});

// =============================================================================
// Data Loading
// =============================================================================

async function loadBookInfo() {
    try {
        const response = await fetch(`/api/books/${state.bookId}`);
        if (response.ok) {
            const data = await response.json();
            state.bookName = data.book_name;
            state.allBookPages = Array.from({length: data.total_pages}, (_, i) => i + 1);
            document.getElementById('book-name').textContent = data.book_name;
        }
    } catch (error) {
        console.error('Error loading book info:', error);
    }
}

async function loadRegions() {
    showLoading('Loading detected regions...');

    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/detected-regions`);
        if (!response.ok) {
            throw new Error('Failed to load regions');
        }

        const data = await response.json();
        state.allRegions = data.regions || [];

        if (state.allRegions.length === 0) {
            hideLoading();
            document.querySelector('.main-container').innerHTML = `
                <div class="no-data">
                    <h2>No Regions Detected</h2>
                    <p>No layout regions found. Please run layout detection from <a href="/auto-slicer?book_id=${state.bookId}">Auto-Slicer</a> first.</p>
                </div>
            `;
            return;
        }

        // Group by page and get sorted page numbers
        const pageSet = new Set(state.allRegions.map(r => r.page_number));
        state.pages = Array.from(pageSet).sort((a, b) => a - b);
        state.currentPageIndex = 0;

        // Update page count
        document.getElementById('page-count-info').textContent = `${state.pages.length} pages with regions`;

        // Load any existing links
        await loadLinks();

        // Load existing page confirmations
        await loadPageConfirmations();

        // Load first page
        await loadCurrentPage();

        hideLoading();

    } catch (error) {
        console.error('Error loading regions:', error);
        hideLoading();
        alert('Failed to load detected regions. Please try again.');
    }
}

async function loadLinks() {
    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/region-links`);
        if (response.ok) {
            const data = await response.json();
            state.links = data.links || [];
            updateLinksCount();
            updateLinksSection();
        }
    } catch (error) {
        console.error('Error loading links:', error);
        state.links = [];
    }
}

async function loadPageConfirmations() {
    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/page-confirmations`);
        if (response.ok) {
            const data = await response.json();
            // Convert string keys back to the format we use
            const confirmations = data.confirmations || {};
            state.pageConfirmations = {};
            for (const [pageStr, conf] of Object.entries(confirmations)) {
                const pageNum = parseInt(pageStr);
                state.pageConfirmations[pageNum] = {
                    classesConfirmed: conf.classes_confirmed || false,
                    regionsConfirmed: conf.regions_confirmed || false
                };
            }
        }
    } catch (error) {
        console.error('Error loading page confirmations:', error);
        state.pageConfirmations = {};
    }
}

async function loadCurrentPage() {
    if (state.pages.length === 0) return;

    const pageNumber = state.pages[state.currentPageIndex];

    // Update page info
    document.getElementById('page-info').textContent =
        `Page ${pageNumber} (${state.currentPageIndex + 1}/${state.pages.length})`;

    // Update L1/L2 title display
    updateTitleDisplay(pageNumber);

    // Update navigation buttons
    document.getElementById('prev-page-btn').disabled = state.currentPageIndex === 0;
    document.getElementById('next-page-btn').disabled = state.currentPageIndex >= state.pages.length - 1;

    // Get regions for this page
    state.pageRegions = state.allRegions.filter(r => r.page_number === pageNumber);

    // Update regions count
    document.getElementById('regions-count').textContent = `${state.pageRegions.length} regions`;

    // Clear selection (single and multi)
    clearSelection();
    updateSelectionInfo();

    // Load page image
    await loadPageImage(pageNumber, 'primary');

    // Load secondary page if in dual view (default is dual-next)
    if (state.viewMode !== 'single') {
        await loadSecondaryPage();
    } else {
        document.getElementById('secondary-canvas-wrapper').style.display = 'none';
    }

    // Update page labels (respects Arabic RTL mode)
    updatePageLabels();

    // Update regions list
    updateRegionsList();
    
    // Update Ready for Extraction button state for primary canvas
    await updateReadyForExtractionState(pageNumber, 'primary');
    
    // Update Ready for Extraction button state for secondary canvas if in dual view
    if (state.viewMode !== 'single' && state.secondaryPageNumber) {
        await updateReadyForExtractionState(state.secondaryPageNumber, 'secondary');
    }
    
    // Update Skip Page button state for primary canvas
    await updateSkipPageState(pageNumber, 'primary');
    
    // Update Skip Page button state for secondary canvas if in dual view
    if (state.viewMode !== 'single' && state.secondaryPageNumber) {
        await updateSkipPageState(state.secondaryPageNumber, 'secondary');
    }
}

async function loadSecondaryPage() {
    const currentPage = state.pages[state.currentPageIndex];
    let secondaryPage = null;

    if (state.viewMode === 'dual-prev' && currentPage > 1) {
        secondaryPage = currentPage - 1;
    } else if (state.viewMode === 'dual-next' && currentPage < state.allBookPages.length) {
        secondaryPage = currentPage + 1;
    }

    if (secondaryPage) {
        state.secondaryPageNumber = secondaryPage;
        state.secondaryPageRegions = state.allRegions.filter(r => r.page_number === secondaryPage);
        document.getElementById('secondary-canvas-wrapper').style.display = 'flex';

        // Apply Arabic RTL order if enabled (ensures correct order when dual view is activated)
        applyArabicModeOrder();

        await loadPageImage(secondaryPage, 'secondary');
    } else {
        document.getElementById('secondary-canvas-wrapper').style.display = 'none';
        state.secondaryPageNumber = null;
        state.secondaryPageRegions = [];
    }
    // Note: updatePageLabels() is called after this in loadCurrentPage()
}

async function loadPageImage(pageNumber, canvasId) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            if (canvasId === 'primary') {
                state.image = img;
            } else {
                state.secondaryImage = img;
            }
            redrawCanvas(canvasId);
            resolve();
        };
        img.onerror = () => {
            console.error('Failed to load page image');
            reject(new Error('Failed to load page image'));
        };
        img.src = `/api/auto-slicer/${state.bookId}/page/${pageNumber}/image`;
    });
}

// =============================================================================
// Canvas Drawing
// =============================================================================

function redrawCanvas(canvasId = 'primary') {
    const canvas = canvasId === 'primary' ? state.canvas : state.secondaryCanvas;
    const ctx = canvasId === 'primary' ? state.ctx : state.secondaryCtx;
    const image = canvasId === 'primary' ? state.image : state.secondaryImage;
    const regions = canvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;

    if (!image) return;

    // Explicitly clear the canvas first (before resize which also clears)
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Reset any canvas state that might persist
    ctx.setLineDash([]);
    ctx.globalAlpha = 1.0;
    ctx.globalCompositeOperation = 'source-over';

    // Resize canvas based on zoom (this also clears, but explicit clear above ensures clean state)
    canvas.width = image.width * state.zoom;
    canvas.height = image.height * state.zoom;

    // Draw image
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

    // Draw all regions
    regions.forEach(region => {
        const isSelected = region.id === state.selectedRegionId && state.selectedCanvasId === canvasId;
        drawRegion(ctx, region, isSelected, canvasId);
    });

    // Draw current drawing rectangle on the active drawing canvas
    if (state.drawingRect && state.activeCanvas === canvasId) {
        ctx.strokeStyle = '#4fc3f7';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(
            state.drawingRect.x,
            state.drawingRect.y,
            state.drawingRect.width,
            state.drawingRect.height
        );
        ctx.setLineDash([]);
    }

    // Draw link indicators
    drawLinkIndicators(ctx, regions, canvasId);
}

function drawRegion(ctx, region, isSelected, canvasId) {
    const zoom = state.zoom;

    const x = region.x * zoom;
    const y = region.y * zoom;
    const w = region.width * zoom;
    const h = region.height * zoom;

    const color = CLASS_COLORS[region.class_name] || '#FF0000';
    const isIgnored = region.class_name === 'ignore';
    const isLinkSource = state.linkSourceRegion && state.linkSourceRegion.id === region.id;

    // Check if this region is in multi-selection
    const isMultiSelected = isRegionSelected(region.id);
    const isInMultiSelectMode = state.selectedRegions.length > 1;

    // Draw filled rectangle with transparency
    if (isLinkSource) {
        ctx.fillStyle = 'rgba(255, 152, 0, 0.3)';
    } else if (isMultiSelected && isInMultiSelectMode) {
        // Multi-select: yellow tint
        ctx.fillStyle = 'rgba(255, 215, 0, 0.2)';
    } else if (isSelected) {
        ctx.fillStyle = 'rgba(79, 195, 247, 0.2)';
    } else if (isIgnored) {
        ctx.fillStyle = 'rgba(68, 68, 68, 0.3)';
    } else {
        ctx.fillStyle = hexToRgba(color, 0.1);
    }
    ctx.fillRect(x, y, w, h);

    // Draw border
    if (isLinkSource) {
        ctx.strokeStyle = '#ff9800';
        ctx.lineWidth = 4;
    } else if (isMultiSelected && isInMultiSelectMode) {
        // Multi-select: YELLOW border (4px thick)
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 4;
    } else if (isSelected) {
        ctx.strokeStyle = '#4fc3f7';
        ctx.lineWidth = 3;
    } else {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
    }

    if (isIgnored) {
        ctx.setLineDash([4, 4]);
    }
    ctx.strokeRect(x, y, w, h);
    ctx.setLineDash([]);

    // Draw orphan highlight (red outer border) if this region is flagged as orphan
    if (state.orphanHighlight && state.orphanHighlight.has(region.id)) {
        ctx.strokeStyle = '#FF0000'; // Red for orphan warning
        ctx.lineWidth = 4;
        const outerOffset = -4;
        ctx.strokeRect(x + outerOffset, y + outerOffset, w - outerOffset * 2, h - outerOffset * 2);
    }

    // Draw double-border (inner) for regions parented to an L3 title
    if (region.l3_title_id) {
        ctx.strokeStyle = '#FFD700'; // Gold for L3 parent indicator
        ctx.lineWidth = 2;
        const innerOffset = 4;
        ctx.strokeRect(x + innerOffset, y + innerOffset, w - innerOffset * 2, h - innerOffset * 2);
    }

    // Draw label background
    const label = isIgnored ? 'IGNORE' : `${region.class_name} (${Math.round(region.confidence * 100)}%)`;
    ctx.font = 'bold 11px Arial';
    const textWidth = ctx.measureText(label).width;

    ctx.fillStyle = isLinkSource ? '#ff9800' : (isSelected ? '#4fc3f7' : color);
    ctx.fillRect(x, y - 16, textWidth + 6, 16);

    // Draw label text
    ctx.fillStyle = isIgnored || isLinkSource ? '#000' : '#fff';
    ctx.fillText(label, x + 3, y - 4);

    // Draw link badge if this region has links
    const isDiagramLinked = state.links.some(l => l.diagram_region_id === region.id);
    const diagramCount = getDiagramCountForParagraph(region.id);
    let badgeOffset = 0;  // Track badge position offset

    // Draw L3 parent badge if linked to L3 title
    if (region.l3_title_id) {
        ctx.fillStyle = '#FFD700'; // Gold
        ctx.fillRect(x + w - 22, y, 22, 14);
        ctx.fillStyle = '#000';
        ctx.font = 'bold 10px Arial';
        ctx.fillText('L3', x + w - 18, y + 10);
        badgeOffset = 24;  // Offset for next badge
    }

    if (isDiagramLinked) {
        // Diagram linked to paragraph - show "L" badge
        ctx.fillStyle = '#ff9800';
        ctx.fillRect(x + w - 20 - badgeOffset, y, 20, 14);
        ctx.fillStyle = '#000';
        ctx.font = 'bold 10px Arial';
        ctx.fillText('L', x + w - 14 - badgeOffset, y + 10);
    } else if (diagramCount > 0 && region.class_name === 'paragraph') {
        // Paragraph with linked diagrams - show count badge "D:N"
        const badgeText = `D:${diagramCount}`;
        ctx.font = 'bold 10px Arial';
        const badgeWidth = ctx.measureText(badgeText).width + 8;
        ctx.fillStyle = '#ff9800';
        ctx.fillRect(x + w - badgeWidth - badgeOffset, y, badgeWidth, 14);
        ctx.fillStyle = '#000';
        ctx.fillText(badgeText, x + w - badgeWidth + 4 - badgeOffset, y + 10);
    }

    // Draw resize handles and move icon if selected
    if (isSelected) {
        drawResizeHandles(ctx, x, y, w, h);
        drawMoveIcon(ctx, x, y);
    }
}

/**
 * Draw a move icon (4-arrow) in the top-left corner of a selected region.
 * This indicates where to click to drag/move the region.
 */
function drawMoveIcon(ctx, x, y) {
    const iconSize = 20;
    const iconX = x + 2;
    const iconY = y + 2;
    const centerX = iconX + iconSize / 2;
    const centerY = iconY + iconSize / 2;

    // Draw background circle
    ctx.fillStyle = 'rgba(79, 195, 247, 0.9)';
    ctx.beginPath();
    ctx.arc(centerX, centerY, iconSize / 2, 0, Math.PI * 2);
    ctx.fill();

    // Draw 4-arrow icon
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 1.5;
    ctx.lineCap = 'round';

    const arrowLen = 5;
    const headLen = 2;

    // Up arrow
    ctx.beginPath();
    ctx.moveTo(centerX, centerY - arrowLen);
    ctx.lineTo(centerX, centerY - 1);
    ctx.moveTo(centerX - headLen, centerY - arrowLen + headLen);
    ctx.lineTo(centerX, centerY - arrowLen);
    ctx.lineTo(centerX + headLen, centerY - arrowLen + headLen);
    ctx.stroke();

    // Down arrow
    ctx.beginPath();
    ctx.moveTo(centerX, centerY + arrowLen);
    ctx.lineTo(centerX, centerY + 1);
    ctx.moveTo(centerX - headLen, centerY + arrowLen - headLen);
    ctx.lineTo(centerX, centerY + arrowLen);
    ctx.lineTo(centerX + headLen, centerY + arrowLen - headLen);
    ctx.stroke();

    // Left arrow
    ctx.beginPath();
    ctx.moveTo(centerX - arrowLen, centerY);
    ctx.lineTo(centerX - 1, centerY);
    ctx.moveTo(centerX - arrowLen + headLen, centerY - headLen);
    ctx.lineTo(centerX - arrowLen, centerY);
    ctx.lineTo(centerX - arrowLen + headLen, centerY + headLen);
    ctx.stroke();

    // Right arrow
    ctx.beginPath();
    ctx.moveTo(centerX + arrowLen, centerY);
    ctx.lineTo(centerX + 1, centerY);
    ctx.moveTo(centerX + arrowLen - headLen, centerY - headLen);
    ctx.lineTo(centerX + arrowLen, centerY);
    ctx.lineTo(centerX + arrowLen - headLen, centerY + headLen);
    ctx.stroke();
}

function drawResizeHandles(ctx, x, y, w, h) {
    const handleSize = 8;
    ctx.fillStyle = '#4fc3f7';

    const handles = [
        { x: x - handleSize/2, y: y - handleSize/2 },
        { x: x + w/2 - handleSize/2, y: y - handleSize/2 },
        { x: x + w - handleSize/2, y: y - handleSize/2 },
        { x: x + w - handleSize/2, y: y + h/2 - handleSize/2 },
        { x: x + w - handleSize/2, y: y + h - handleSize/2 },
        { x: x + w/2 - handleSize/2, y: y + h - handleSize/2 },
        { x: x - handleSize/2, y: y + h - handleSize/2 },
        { x: x - handleSize/2, y: y + h/2 - handleSize/2 }
    ];

    handles.forEach(handle => {
        ctx.fillRect(handle.x, handle.y, handleSize, handleSize);
    });
}

function drawLinkIndicators(ctx, regions, canvasId) {
    // Draw small indicators on regions that are linked
    const pageNumber = canvasId === 'primary' ?
        state.pages[state.currentPageIndex] : state.secondaryPageNumber;

    if (!pageNumber) return;

    // Find links involving this page
    state.links.forEach(link => {
        const region = regions.find(r => r.id === link.diagram_region_id || r.id === link.paragraph_region_id);
        if (region) {
            const x = region.x * state.zoom;
            const y = region.y * state.zoom;

            // Draw link indicator
            ctx.fillStyle = '#ff9800';
            ctx.beginPath();
            ctx.arc(x + 10, y + 10, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#000';
            ctx.font = 'bold 8px Arial';
            ctx.fillText('L', x + 7, y + 13);
        }
    });
}

function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// =============================================================================
// Canvas Events
// =============================================================================

function setupCanvasEvents(canvas, canvasId) {
    canvas.addEventListener('mousedown', (e) => onMouseDown(e, canvasId));
    canvas.addEventListener('mousemove', (e) => onMouseMove(e, canvasId));
    canvas.addEventListener('mouseup', (e) => onMouseUp(e, canvasId));
    canvas.addEventListener('mouseleave', (e) => onMouseLeave(e, canvasId));
}

function onMouseDown(e, canvasId) {
    // Only handle left-clicks (button 0) - right-clicks are handled by contextmenu event
    if (e.button !== 0) return;

    const canvas = canvasId === 'primary' ? state.canvas : state.secondaryCanvas;
    const regions = canvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Convert to image coordinates
    const imgX = x / state.zoom;
    const imgY = y / state.zoom;

    state.activeCanvas = canvasId;

    // Determine if drawing is allowed on this canvas:
    // - Changing boundary: only the canvas where the original region was
    // - Normal draw mode: allowed on both canvases (primary and secondary)
    const canDrawHere = state.changingBoundaryRegion
        ? state.changingBoundaryRegion.canvasId === canvasId
        : true; // Allow drawing on any canvas

    if (state.mode === 'draw' && canDrawHere) {
        // Start drawing new region
        state.isDrawing = true;
        state.dragStartX = x;
        state.dragStartY = y;
        state.drawingRect = { x, y, width: 0, height: 0 };
        state.activeCanvas = canvasId; // Track which canvas we're drawing on
        canvas.classList.add('drawing');

    } else if (state.isLinkingToL3) {
        // Handle L3 title linking mode
        const clickedRegion = findRegionAt(imgX, imgY, regions);
        handleL3LinkClick(clickedRegion, canvasId);

    } else if (state.isSplitting) {
        // Handle split mode
        if (handleSplitClick(imgX, imgY, canvasId)) {
            return; // Split handled the click
        }

    } else if (state.mode === 'link') {
        // Handle link mode
        const clickedRegion = findRegionAt(imgX, imgY, regions);
        handleLinkClick(clickedRegion, canvasId);

    } else {
        // Select mode
        if (state.selectedRegionId && state.selectedCanvasId === canvasId) {
            const handle = getResizeHandleAt(x, y, canvasId);
            if (handle) {
                state.isResizing = true;
                state.resizeHandle = handle;
                state.dragStartX = x;
                state.dragStartY = y;
                return;
            }
        }

        const clickedRegion = findRegionAt(imgX, imgY, regions);

        if (clickedRegion) {
            const isCtrlHeld = e.ctrlKey || e.metaKey;
            const isAlreadySelected = isRegionSelected(clickedRegion.id);

            if (isCtrlHeld) {
                // Ctrl+click: Toggle selection in multi-select mode
                if (isAlreadySelected) {
                    // Remove from selection
                    removeFromSelection(clickedRegion.id);
                } else {
                    // Add to selection
                    addToSelection(clickedRegion.id, canvasId);
                }
            } else if (isAlreadySelected && state.selectedRegions.length <= 1) {
                // Single selected region clicked - try to drag from move corner
                if (isInMoveCorner(x, y, clickedRegion)) {
                    state.isDragging = true;
                    state.dragStartX = x;
                    state.dragStartY = y;
                    state.dragOffsetX = imgX - clickedRegion.x;
                    state.dragOffsetY = imgY - clickedRegion.y;
                    canvas.classList.add('moving');
                }
                // Clicking elsewhere on selected region does nothing (just keeps selection)
            } else {
                // Normal click without Ctrl: clear selection and select only this one
                selectRegion(clickedRegion.id, canvasId);
            }
        } else {
            // Clicked empty space - clear all selection
            clearSelection();
            updateSelectionInfo();
            redrawCanvas('primary');
            if (state.viewMode !== 'single') redrawCanvas('secondary');
            updateRegionsList();
        }
    }
}

function onMouseMove(e, canvasId) {
    const canvas = canvasId === 'primary' ? state.canvas : state.secondaryCanvas;
    const regions = canvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Update cursor info
    const imgX = Math.round(x / state.zoom);
    const imgY = Math.round(y / state.zoom);
    document.getElementById('cursor-info').textContent = `(${imgX}, ${imgY})`;

    // Update cursor based on hover position (only in select mode when not dragging)
    if (state.mode === 'select' && !state.isDragging && !state.isResizing && !state.isDrawing) {
        updateCursorForPosition(canvas, x, y, canvasId, regions);
    }

    // Update split preview line during mouse move
    if (state.isSplitting && state.splitStart && canvasId === state.splitCanvasId) {
        state.splitPreviewEnd = { x: imgX, y: imgY };
        redrawCanvas(canvasId);
        drawSplitPreview(canvasId);
        return;
    }

    if (state.activeCanvas !== canvasId) return;

    if (state.isDrawing) {
        state.drawingRect = {
            x: Math.min(state.dragStartX, x),
            y: Math.min(state.dragStartY, y),
            width: Math.abs(x - state.dragStartX),
            height: Math.abs(y - state.dragStartY)
        };
        redrawCanvas(state.activeCanvas || 'primary');

    } else if (state.isDragging && state.selectedRegionId) {
        const region = regions.find(r => r.id === state.selectedRegionId);
        if (region) {
            const image = canvasId === 'primary' ? state.image : state.secondaryImage;
            region.x = Math.round((x / state.zoom) - state.dragOffsetX);
            region.y = Math.round((y / state.zoom) - state.dragOffsetY);
            region.x = Math.max(0, Math.min(region.x, image.width - region.width));
            region.y = Math.max(0, Math.min(region.y, image.height - region.height));
            redrawCanvas(canvasId);
        }

    } else if (state.isResizing && state.selectedRegionId) {
        const region = regions.find(r => r.id === state.selectedRegionId);
        if (region) {
            resizeRegion(region, x, y);
            redrawCanvas(canvasId);
        }
    }
}

function onMouseUp(e, canvasId) {
    const canvas = canvasId === 'primary' ? state.canvas : state.secondaryCanvas;

    if (state.isDrawing && state.drawingRect) {
        if (state.drawingRect.width > 20 && state.drawingRect.height > 20) {
            createNewRegion(state.drawingRect);
        }
        state.drawingRect = null;
        // Note: 'drawing' class is managed by setMode(), called in createNewRegion

    } else if (state.isDragging && state.selectedRegionId) {
        saveRegionPosition(state.selectedRegionId);
        canvas.classList.remove('moving');

    } else if (state.isResizing && state.selectedRegionId) {
        saveRegionPosition(state.selectedRegionId);
    }

    state.isDrawing = false;
    state.isDragging = false;
    state.isResizing = false;
    state.resizeHandle = null;
    state.activeCanvas = null;

    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
}

function onMouseLeave(e, canvasId) {
    document.getElementById('cursor-info').textContent = '-';

    if (state.activeCanvas === canvasId && (state.isDrawing || state.isDragging || state.isResizing)) {
        onMouseUp(e, canvasId);
    }
}

// =============================================================================
// Region Interaction Helpers
// =============================================================================

function findRegionAt(imgX, imgY, regions) {
    let found = null;
    let bestScore = -Infinity;

    for (const region of regions) {
        if (imgX >= region.x && imgX <= region.x + region.width &&
            imgY >= region.y && imgY <= region.y + region.height) {
            // Score based on z_index (primary) and inverse area (secondary)
            // Higher z_index wins; among same z_index, smaller area wins
            const zIndex = region.z_index || 0;
            const area = region.width * region.height;
            // z_index * 1000000 ensures it dominates over area differences
            const score = (zIndex * 1000000) - area;

            if (score > bestScore) {
                bestScore = score;
                found = region;
            }
        }
    }

    return found;
}

/**
 * Update cursor based on hover position for visual feedback.
 * Shows resize cursor when hovering over resize handles, move cursor over move zone.
 */
function updateCursorForPosition(canvas, x, y, canvasId, regions) {
    // Check if hovering over a resize handle of selected region
    if (state.selectedRegionId && state.selectedCanvasId === canvasId) {
        const handle = getResizeHandleAt(x, y, canvasId);
        if (handle) {
            // Set resize cursor based on handle position
            const cursorMap = {
                'nw': 'nwse-resize',
                'n': 'ns-resize',
                'ne': 'nesw-resize',
                'e': 'ew-resize',
                'se': 'nwse-resize',
                's': 'ns-resize',
                'sw': 'nesw-resize',
                'w': 'ew-resize'
            };
            canvas.style.cursor = cursorMap[handle] || 'default';
            return;
        }

        // Check if hovering over move corner
        const selectedRegion = regions.find(r => r.id === state.selectedRegionId);
        if (selectedRegion && isInMoveCorner(x, y, selectedRegion)) {
            canvas.style.cursor = 'move';
            return;
        }
    }

    // Check if hovering over any region (show pointer)
    const imgX = x / state.zoom;
    const imgY = y / state.zoom;
    const hoveredRegion = findRegionAt(imgX, imgY, regions);
    if (hoveredRegion) {
        canvas.style.cursor = 'pointer';
        return;
    }

    // Default cursor
    canvas.style.cursor = 'default';
}

/**
 * Check if a point is in the move corner (top-left) of a region.
 * Move is only allowed from the top-left corner to prevent accidental moves.
 */
function isInMoveCorner(x, y, region) {
    const zoom = state.zoom;
    const regionX = region.x * zoom;
    const regionY = region.y * zoom;
    const moveZoneSize = 24; // px - size of the move corner zone

    return x >= regionX && x <= regionX + moveZoneSize &&
           y >= regionY && y <= regionY + moveZoneSize;
}

function getResizeHandleAt(x, y, canvasId) {
    if (!state.selectedRegionId || state.selectedCanvasId !== canvasId) return null;

    const regions = canvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;
    const region = regions.find(r => r.id === state.selectedRegionId);
    if (!region) return null;

    const zoom = state.zoom;
    const rx = region.x * zoom;
    const ry = region.y * zoom;
    const rw = region.width * zoom;
    const rh = region.height * zoom;

    const handleSize = 12;

    const handles = [
        { name: 'nw', x: rx, y: ry },
        { name: 'n', x: rx + rw/2, y: ry },
        { name: 'ne', x: rx + rw, y: ry },
        { name: 'e', x: rx + rw, y: ry + rh/2 },
        { name: 'se', x: rx + rw, y: ry + rh },
        { name: 's', x: rx + rw/2, y: ry + rh },
        { name: 'sw', x: rx, y: ry + rh },
        { name: 'w', x: rx, y: ry + rh/2 }
    ];

    for (const handle of handles) {
        if (Math.abs(x - handle.x) < handleSize && Math.abs(y - handle.y) < handleSize) {
            return handle.name;
        }
    }

    return null;
}

function resizeRegion(region, mouseX, mouseY) {
    const imgX = mouseX / state.zoom;
    const imgY = mouseY / state.zoom;

    const handle = state.resizeHandle;
    const minSize = 20;

    switch (handle) {
        case 'nw':
            const newW_nw = region.x + region.width - imgX;
            const newH_nw = region.y + region.height - imgY;
            if (newW_nw > minSize) { region.width = newW_nw; region.x = imgX; }
            if (newH_nw > minSize) { region.height = newH_nw; region.y = imgY; }
            break;
        case 'n':
            const newH_n = region.y + region.height - imgY;
            if (newH_n > minSize) { region.height = newH_n; region.y = imgY; }
            break;
        case 'ne':
            const newW_ne = imgX - region.x;
            const newH_ne = region.y + region.height - imgY;
            if (newW_ne > minSize) region.width = newW_ne;
            if (newH_ne > minSize) { region.height = newH_ne; region.y = imgY; }
            break;
        case 'e':
            const newW_e = imgX - region.x;
            if (newW_e > minSize) region.width = newW_e;
            break;
        case 'se':
            const newW_se = imgX - region.x;
            const newH_se = imgY - region.y;
            if (newW_se > minSize) region.width = newW_se;
            if (newH_se > minSize) region.height = newH_se;
            break;
        case 's':
            const newH_s = imgY - region.y;
            if (newH_s > minSize) region.height = newH_s;
            break;
        case 'sw':
            const newW_sw = region.x + region.width - imgX;
            const newH_sw = imgY - region.y;
            if (newW_sw > minSize) { region.width = newW_sw; region.x = imgX; }
            if (newH_sw > minSize) region.height = newH_sw;
            break;
        case 'w':
            const newW_w = region.x + region.width - imgX;
            if (newW_w > minSize) { region.width = newW_w; region.x = imgX; }
            break;
    }

    region.x = Math.round(region.x);
    region.y = Math.round(region.y);
    region.width = Math.round(region.width);
    region.height = Math.round(region.height);
}

// =============================================================================
// Region Operations - Multi-Selection Support
// =============================================================================

/**
 * Check if a region is currently selected (single or multi-select)
 */
function isRegionSelected(regionId) {
    if (state.selectedRegionId === regionId) return true;
    return state.selectedRegions.some(r => r.id === regionId);
}

/**
 * Add a region to the multi-selection
 */
function addToSelection(regionId, canvasId) {
    if (!isRegionSelected(regionId)) {
        state.selectedRegions.push({ id: regionId, canvasId });
        // Update primary selection to the first in the array
        if (state.selectedRegions.length === 1) {
            state.selectedRegionId = regionId;
            state.selectedCanvasId = canvasId;
        }
    }
    updateSelectionInfo();
    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
    updateRegionsList();
}

/**
 * Remove a region from the multi-selection
 */
function removeFromSelection(regionId) {
    state.selectedRegions = state.selectedRegions.filter(r => r.id !== regionId);
    // Update primary selection
    if (state.selectedRegionId === regionId) {
        if (state.selectedRegions.length > 0) {
            state.selectedRegionId = state.selectedRegions[0].id;
            state.selectedCanvasId = state.selectedRegions[0].canvasId;
        } else {
            state.selectedRegionId = null;
        }
    }
    updateSelectionInfo();
    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
    updateRegionsList();
}

/**
 * Clear all selections
 */
function clearSelection() {
    state.selectedRegionId = null;
    state.selectedRegions = [];
    state.selectedCanvasId = 'primary';
}

/**
 * Select a single region (clears existing selection)
 */
function selectRegion(regionId, canvasId = 'primary') {
    // Clear multi-selection and set single selection
    state.selectedRegions = [{ id: regionId, canvasId }];
    state.selectedRegionId = regionId;
    state.selectedCanvasId = canvasId;

    const regions = canvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;
    const region = regions.find(r => r.id === regionId);
    if (region) {
        document.getElementById('class-select').value = region.class_name;
    }

    updateSelectionInfo();
    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
    updateRegionsList();
}

function updateSelectionInfo() {
    const selectionCount = state.selectedRegions.length;

    if (selectionCount > 1) {
        // Multi-selection: show count
        document.getElementById('selection-info').textContent =
            `${selectionCount} regions selected (Ctrl+click to modify)`;
        document.getElementById('class-select').value = '';
    } else if (selectionCount === 1) {
        // Single selection: show details
        const regions = state.selectedCanvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;
        const region = regions.find(r => r.id === state.selectedRegionId);
        if (region) {
            document.getElementById('selection-info').textContent =
                `Selected: ${region.class_name} (${region.width}x${region.height})`;
            document.getElementById('class-select').value = region.class_name;
        } else {
            document.getElementById('selection-info').textContent = 'No selection';
            document.getElementById('class-select').value = '';
        }
    } else {
        document.getElementById('selection-info').textContent = 'No selection';
        document.getElementById('class-select').value = '';
    }
}

async function createNewRegion(drawRect) {
    // Check if we're changing a region's boundary
    const isChangingBoundary = state.changingBoundaryRegion !== null;

    // Determine which canvas the drawing was on
    const drawingCanvasId = state.activeCanvas || 'primary';

    // Use correct page number based on which canvas was drawn on
    let pageNumber;
    if (isChangingBoundary) {
        pageNumber = state.changingBoundaryRegion.page_number;
    } else if (drawingCanvasId === 'secondary' && state.secondaryPageNumber) {
        pageNumber = state.secondaryPageNumber;
    } else {
        pageNumber = state.pages[state.currentPageIndex];
    }

    const className = isChangingBoundary
        ? state.changingBoundaryRegion.class_name
        : document.getElementById('new-region-class').value;

    const region = {
        page_number: pageNumber,
        class_name: className,
        x: Math.round(drawRect.x / state.zoom),
        y: Math.round(drawRect.y / state.zoom),
        width: Math.round(drawRect.width / state.zoom),
        height: Math.round(drawRect.height / state.zoom),
        confidence: 1.0
    };

    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/add-region`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(region)
        });

        if (!response.ok) throw new Error('Failed to create region');

        const data = await response.json();
        const newRegion = { ...region, id: data.region_id };
        state.allRegions.push(newRegion);

        // Add to correct page regions array
        if (drawingCanvasId === 'secondary' && state.secondaryPageNumber === pageNumber) {
            state.secondaryPageRegions.push(newRegion);
        } else {
            state.pageRegions.push(newRegion);
        }

        selectRegion(newRegion.id, drawingCanvasId);
        document.getElementById('regions-count').textContent = `${state.pageRegions.length} regions`;

        // Clear boundary change state if applicable
        if (isChangingBoundary) {
            state.changingBoundaryRegion = null;
            document.getElementById('link-status').textContent = '';
            document.getElementById('link-status').style.color = '';
        }

        // Always return to select mode after creating a region
        setMode('select');

    } catch (error) {
        console.error('Error creating region:', error);
        alert('Failed to create region');

        // Clear boundary change state on error too
        if (isChangingBoundary) {
            state.changingBoundaryRegion = null;
            document.getElementById('link-status').textContent = '';
            document.getElementById('link-status').style.color = '';
        }
    }
}

async function saveRegionPosition(regionId) {
    // Find region in either page
    let region = state.pageRegions.find(r => r.id === regionId);
    if (!region) region = state.secondaryPageRegions.find(r => r.id === regionId);
    if (!region) return;

    try {
        await fetch(`/api/auto-slicer/${state.bookId}/detected-region/${regionId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                x: region.x,
                y: region.y,
                width: region.width,
                height: region.height
            })
        });

        const idx = state.allRegions.findIndex(r => r.id === regionId);
        if (idx !== -1) {
            state.allRegions[idx] = { ...region };
        }

    } catch (error) {
        console.error('Error saving region position:', error);
    }
}

async function applyClassChange() {
    if (!state.selectedRegionId) {
        alert('Please select a region first');
        return;
    }

    const newClass = document.getElementById('class-select').value;
    if (!newClass) return;

    // Use the unified applyClassToRegion function for consistency
    await applyClassToRegion(state.selectedRegionId, newClass, state.selectedCanvasId);
}

async function deleteSelectedRegion() {
    if (!state.selectedRegionId) {
        alert('Please select a region first');
        return;
    }

    if (!confirm('Delete this region?')) return;

    const regionIdToDelete = state.selectedRegionId;
    console.log(`deleteSelectedRegion called: regionId=${regionIdToDelete}`);
    console.log(`Before delete - pageRegions count: ${state.pageRegions.length}, allRegions count: ${state.allRegions.length}`);

    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/detected-region/${regionIdToDelete}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to delete region');
        }

        const result = await response.json();
        console.log('Delete API response:', result);

        // Remove from local arrays immediately for responsive UI
        // Use Number() to ensure type consistency in comparison
        const deleteId = Number(regionIdToDelete);
        const prevPageCount = state.pageRegions.length;
        const prevAllCount = state.allRegions.length;

        state.pageRegions = state.pageRegions.filter(r => Number(r.id) !== deleteId);
        state.secondaryPageRegions = state.secondaryPageRegions.filter(r => Number(r.id) !== deleteId);
        state.allRegions = state.allRegions.filter(r => Number(r.id) !== deleteId);

        console.log(`After filter - pageRegions: ${prevPageCount} -> ${state.pageRegions.length}, allRegions: ${prevAllCount} -> ${state.allRegions.length}`);

        // Remove any links involving this region (use Number for type safety)
        state.links = state.links.filter(l =>
            Number(l.diagram_region_id) !== deleteId &&
            Number(l.paragraph_region_id) !== deleteId
        );

        // Clear selection state
        state.selectedRegionId = null;
        state.selectedCanvasId = 'primary';
        state.selectedRegions = state.selectedRegions.filter(r => Number(r.id) !== deleteId);

        // Clear any orphan highlights that might reference this region
        if (state.orphanHighlight) {
            state.orphanHighlight.delete(deleteId);
            state.orphanHighlight.delete(regionIdToDelete);  // Also try original value
            if (state.orphanHighlight.size === 0) {
                state.orphanHighlight = null;
            }
        }

        updateSelectionInfo();
        redrawCanvas('primary');
        if (state.viewMode !== 'single') redrawCanvas('secondary');
        updateRegionsList();
        updateLinksCount();
        updateLinksSection();

        document.getElementById('regions-count').textContent = `${state.pageRegions.length} regions`;

        // Reload links from DB to ensure consistency
        await loadLinks();

        console.log(`Delete complete. Final pageRegions count: ${state.pageRegions.length}`);

    } catch (error) {
        console.error('Error deleting region:', error);
        alert('Failed to delete region: ' + error.message);
        // Reload from DB to restore correct state
        await loadRegions();
    }
}

/**
 * Delete a region directly (from context menu, no confirmation needed for single region)
 * Auto-persists to DB and reloads to ensure consistency.
 */
async function deleteRegionDirect(regionId, canvasId) {
    console.log(`deleteRegionDirect called: regionId=${regionId}, type=${typeof regionId}, canvasId=${canvasId}`);
    console.log(`Before delete - pageRegions count: ${state.pageRegions.length}, allRegions count: ${state.allRegions.length}`);

    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/detected-region/${regionId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to delete region');
        }

        const result = await response.json();
        console.log('Delete API response:', result);

        // Remove from local arrays immediately for responsive UI
        // Use Number() to ensure type consistency in comparison
        const deleteId = Number(regionId);
        const prevPageCount = state.pageRegions.length;
        const prevSecondaryCount = state.secondaryPageRegions.length;
        const prevAllCount = state.allRegions.length;

        state.pageRegions = state.pageRegions.filter(r => Number(r.id) !== deleteId);
        state.secondaryPageRegions = state.secondaryPageRegions.filter(r => Number(r.id) !== deleteId);
        state.allRegions = state.allRegions.filter(r => Number(r.id) !== deleteId);

        console.log(`After filter - pageRegions: ${prevPageCount} -> ${state.pageRegions.length}, secondaryPageRegions: ${prevSecondaryCount} -> ${state.secondaryPageRegions.length}, allRegions: ${prevAllCount} -> ${state.allRegions.length}`);

        // Remove any links involving this region (use Number for type safety)
        state.links = state.links.filter(l =>
            Number(l.diagram_region_id) !== deleteId &&
            Number(l.paragraph_region_id) !== deleteId
        );

        // Clear selection if this was the selected region
        if (state.selectedRegionId === regionId || Number(state.selectedRegionId) === deleteId) {
            state.selectedRegionId = null;
            state.selectedCanvasId = 'primary';
        }

        // Also clear from multi-select array
        state.selectedRegions = state.selectedRegions.filter(r => Number(r.id) !== deleteId);

        // Clear any orphan highlights that might reference this region
        if (state.orphanHighlight) {
            state.orphanHighlight.delete(deleteId);
            state.orphanHighlight.delete(regionId);  // Also try original value
            if (state.orphanHighlight.size === 0) {
                state.orphanHighlight = null;
            }
        }

        updateSelectionInfo();
        redrawCanvas('primary');
        if (state.viewMode !== 'single') redrawCanvas('secondary');
        updateRegionsList();
        updateLinksCount();
        updateLinksSection();

        document.getElementById('regions-count').textContent = `${state.pageRegions.length} regions`;

        // Reload links from DB to ensure consistency
        await loadLinks();

        console.log(`Delete complete. Final pageRegions count: ${state.pageRegions.length}`);

    } catch (error) {
        console.error('Error deleting region:', error);
        alert('Failed to delete region: ' + error.message);
        // Reload from DB to restore correct state
        await loadRegions();
    }
}

/**
 * Permanently ignore similar regions:
 * 1. Create an ignore rule for this class + position + size
 * 2. Delete the current region
 * 3. Delete all matching regions from other pages
 */
async function permanentlyIgnoreSimilar(region, canvasId) {
    const confirmMsg = `This will:\n` +
        `1. Create an ignore rule for "${region.class_name}" regions at this position\n` +
        `2. Delete this region\n` +
        `3. Delete ALL similar regions on other pages\n\n` +
        `Continue?`;

    if (!confirm(confirmMsg)) return;

    try {
        // Call API to create ignore rule and delete matching regions
        const response = await fetch(`/api/auto-slicer/${state.bookId}/ignore-rules`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                class_name: region.class_name,
                x: region.x,
                y: region.y,
                width: region.width,
                height: region.height,
                tolerance: 50,
                source_region_id: region.id
            })
        });

        if (!response.ok) {
            throw new Error('Failed to create ignore rule');
        }

        const data = await response.json();
        const deletedCount = data.deleted_count || 0;

        // Remove deleted regions from local state
        const deletedIds = data.deleted_region_ids || [region.id];
        deletedIds.forEach(id => {
            state.pageRegions = state.pageRegions.filter(r => r.id !== id);
            state.secondaryPageRegions = state.secondaryPageRegions.filter(r => r.id !== id);
            state.allRegions = state.allRegions.filter(r => r.id !== id);
            state.links = state.links.filter(l =>
                l.diagram_region_id !== id && l.paragraph_region_id !== id
            );
        });

        // Clear selection if deleted
        if (deletedIds.includes(state.selectedRegionId)) {
            state.selectedRegionId = null;
        }

        updateSelectionInfo();
        redrawCanvas('primary');
        if (state.viewMode !== 'single') redrawCanvas('secondary');
        updateRegionsList();
        updateLinksCount();
        updateLinksSection();
        document.getElementById('regions-count').textContent = `${state.pageRegions.length} regions`;

        // Show confirmation
        alert(`Ignore rule created.\nDeleted ${deletedCount} matching region(s).`);

    } catch (error) {
        console.error('Error creating ignore rule:', error);
        alert('Failed to create ignore rule: ' + error.message);
    }
}

// =============================================================================
// Linking Functions
// =============================================================================

function handleLinkClick(region, canvasId) {
    if (!region) {
        // Clicked empty space, cancel linking and return to select mode
        setMode('select');
        return;
    }

    // Classes that can be linked to paragraphs
    const linkableToParagraph = ['diagram', 'table', 'equation', 'list_bulleted', 'list_numbered', 'list_lettered'];
    // Classes that can be linked to questions
    const linkableToQuestion = ['answer'];
    const allLinkableClasses = [...linkableToParagraph, ...linkableToQuestion];

    if (!state.linkSourceRegion) {
        // First click - must be a linkable source type
        if (!allLinkableClasses.includes(region.class_name)) {
            document.getElementById('link-status').textContent = 'First select a diagram, table, equation, list, or answer to link';
            return;
        }

        // Check if already linked
        const existingLink = state.links.find(l => l.diagram_region_id === region.id);
        if (existingLink) {
            const targetType = region.class_name === 'answer' ? 'question' : 'paragraph';
            const confirmRelink = confirm(
                `This ${region.class_name} is already linked to a ${targetType}.\n` +
                'Do you want to remove the existing link and create a new one?'
            );
            if (!confirmRelink) {
                setMode('select');  // Return to select mode
                return;
            }
            // Remove existing link first
            removeLink(existingLink.id);
        }

        state.linkSourceRegion = region;
        const targetType = region.class_name === 'answer' ? 'QUESTION' : 'PARAGRAPH';
        document.getElementById('link-status').textContent =
            `${region.class_name} selected. Now click a ${targetType} to link (page ${region.page_number})`;
        redrawCanvas('primary');
        if (state.viewMode !== 'single') redrawCanvas('secondary');
    } else {
        // Second click - validate target type based on source type
        const sourceClass = state.linkSourceRegion.class_name;
        const expectedTarget = sourceClass === 'answer' ? 'question' : 'paragraph';

        if (region.class_name !== expectedTarget) {
            const targetType = sourceClass === 'answer' ? 'QUESTION' : 'PARAGRAPH';
            document.getElementById('link-status').textContent = `Please select a ${targetType} to link to`;
            return;
        }

        // Check if target already has maximum links (5 for paragraphs, 5 for questions)
        const targetLinkCount = getSourceCountForTarget(region.id);
        if (targetLinkCount >= 5) {
            const targetType = sourceClass === 'answer' ? 'question' : 'paragraph';
            alert(`This ${targetType} already has 5 items linked (maximum).\n` +
                  'Please remove an existing link before adding a new one.');
            setMode('select');  // Return to select mode (this also calls cancelLinkMode)
            return;
        }

        // Create the link
        createLink(state.linkSourceRegion, region);
        setMode('select');  // Return to select mode after successful link (this also calls cancelLinkMode)
    }
}

/**
 * Get the count of source regions linked to a target (paragraph or question).
 */
function getSourceCountForTarget(targetId) {
    return state.links.filter(l => l.paragraph_region_id === targetId).length;
}

// Alias for backwards compatibility
function getDiagramCountForParagraph(paragraphId) {
    return getSourceCountForTarget(paragraphId);
}

async function createLink(diagram, paragraph) {
    const diagramPage = state.pageRegions.includes(diagram) ?
        state.pages[state.currentPageIndex] : state.secondaryPageNumber;
    const paragraphPage = state.pageRegions.includes(paragraph) ?
        state.pages[state.currentPageIndex] : state.secondaryPageNumber;

    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/link-regions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                diagram_region_id: diagram.id,
                paragraph_region_id: paragraph.id
            })
        });

        if (!response.ok) throw new Error('Failed to create link');

        const data = await response.json();

        state.links.push({
            id: data.link_id,
            diagram_region_id: diagram.id,
            paragraph_region_id: paragraph.id,
            diagram_page: diagramPage,
            paragraph_page: paragraphPage
        });

        updateLinksCount();
        updateLinksSection();
        redrawCanvas('primary');
        if (state.viewMode !== 'single') redrawCanvas('secondary');
        updateRegionsList();

    } catch (error) {
        console.error('Error creating link:', error);
        alert('Failed to create link');
    }
}

async function removeLink(linkId) {
    try {
        await fetch(`/api/auto-slicer/${state.bookId}/unlink-regions/${linkId}`, {
            method: 'DELETE'
        });

        state.links = state.links.filter(l => l.id !== linkId);
        updateLinksCount();
        updateLinksSection();
        redrawCanvas('primary');
        if (state.viewMode !== 'single') redrawCanvas('secondary');
        updateRegionsList();

    } catch (error) {
        console.error('Error removing link:', error);
        alert('Failed to remove link');
    }
}

function toggleLinkMode() {
    if (state.mode === 'link') {
        setMode('select');  // This will call cancelLinkMode() internally
    } else {
        setMode('link');
    }
}

function cancelLinkMode() {
    state.linkSourceRegion = null;
    document.getElementById('link-status').textContent = '';
    // Note: Don't call setMode here - it creates circular recursion
    // setMode() already calls cancelLinkMode() when switching away from link mode
    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
}

// =============================================================================
// L3 Title Linking Functions
// =============================================================================

/**
 * Start L3 title linking mode with currently selected regions.
 */
function startL3Linking() {
    if (state.selectedRegions.length === 0) {
        alert('Please select at least one region to link to an L3 title.');
        return;
    }

    // Store the regions to link
    state.regionsToLinkToL3 = [...state.selectedRegions];
    state.isLinkingToL3 = true;

    // Update UI
    const count = state.regionsToLinkToL3.length;
    document.getElementById('link-status').textContent =
        `L3 Linking: Click a Title L3 region to link ${count} region(s)`;
    document.getElementById('link-status').style.color = '#FFCC00';

    // Set cursor mode
    state.canvas.classList.add('linking');
    state.secondaryCanvas.classList.add('linking');

    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
}

/**
 * Cancel L3 title linking mode.
 */
function cancelL3Linking() {
    state.isLinkingToL3 = false;
    state.regionsToLinkToL3 = [];

    document.getElementById('link-status').textContent = '';
    document.getElementById('link-status').style.color = '';

    state.canvas.classList.remove('linking');
    state.secondaryCanvas.classList.remove('linking');

    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
}

/**
 * Handle click in L3 linking mode - check if clicked on L3 title.
 */
function handleL3LinkClick(region, canvasId) {
    if (!region) {
        // Clicked empty space - cancel linking
        cancelL3Linking();
        return;
    }

    // Accept multiple L3 title class name variations
    const validL3Classes = ['title_level_3', 'title_l3', 'Title L3'];
    if (!validL3Classes.includes(region.class_name)) {
        document.getElementById('link-status').textContent =
            'Please click on a TITLE LEVEL 3 region (yellow label)';
        return;
    }

    // Found an L3 title - create the links
    createL3Links(region);
}

/**
 * Create L3 title links for selected regions.
 */
async function createL3Links(l3TitleRegion) {
    const regionIds = state.regionsToLinkToL3.map(r => r.id);
    const linkedRegions = [...state.regionsToLinkToL3]; // Store for visual feedback
    let successCount = 0;

    try {
        // Store L3 links via API - updates l3_title_id on each region
        for (const regId of regionIds) {
            const response = await fetch(`/api/auto-slicer/${state.bookId}/l3-link`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    region_id: regId,
                    l3_title_id: l3TitleRegion.id
                })
            });

            if (response.ok) {
                successCount++;
                // Update local region state
                const region = state.pageRegions.find(r => r.id === regId) ||
                              state.secondaryPageRegions.find(r => r.id === regId);
                if (region) {
                    region.l3_title_id = l3TitleRegion.id;
                }
            }
        }

        // Success feedback
        document.getElementById('link-status').textContent =
            `Linked ${successCount} region(s) to L3 title`;
        document.getElementById('link-status').style.color = '#4caf50';

        // Redraw to show any visual indicators
        redrawCanvas('primary');
        if (state.viewMode !== 'single') redrawCanvas('secondary');

        // Draw visual dashed lines from linked regions to L3 title
        drawL3LinkLines(linkedRegions, l3TitleRegion);

        setTimeout(() => {
            cancelL3Linking();
            // Redraw to clear the link lines
            redrawCanvas('primary');
            if (state.viewMode !== 'single') redrawCanvas('secondary');
        }, 2000);

    } catch (error) {
        console.error('Error creating L3 links:', error);
        alert('Failed to create L3 title links');
        cancelL3Linking();
    }
}

/**
 * Draw temporary dashed lines from linked regions to L3 title region.
 */
function drawL3LinkLines(linkedRegions, l3TitleRegion) {
    // Get L3 title center point (using x, y, width, height)
    const l3CenterX = l3TitleRegion.x + l3TitleRegion.width / 2;
    const l3CenterY = l3TitleRegion.y + l3TitleRegion.height / 2;

    // Draw on primary canvas
    const primaryCtx = state.canvas.getContext('2d');
    drawLinkLinesOnContext(primaryCtx, linkedRegions, l3CenterX, l3CenterY, state.pageRegions, l3TitleRegion);

    // Draw on secondary canvas if in dual view
    if (state.viewMode !== 'single') {
        const secondaryCtx = state.secondaryCanvas.getContext('2d');
        drawLinkLinesOnContext(secondaryCtx, linkedRegions, l3CenterX, l3CenterY, state.secondaryPageRegions, l3TitleRegion);
    }
}

/**
 * Draw link lines on a specific canvas context.
 */
function drawLinkLinesOnContext(ctx, linkedRegions, l3CenterX, l3CenterY, pageRegions, l3TitleRegion) {
    const scale = state.zoom;

    // Scale L3 center point
    const scaledL3X = l3CenterX * scale;
    const scaledL3Y = l3CenterY * scale;

    ctx.save();
    ctx.setLineDash([8, 4]);
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#00E676'; // Bright green
    ctx.lineCap = 'round';

    linkedRegions.forEach(linkedRegion => {
        // Check if this region is on this canvas's page
        const regionOnPage = pageRegions.find(r => r.id === linkedRegion.id);
        if (!regionOnPage) return;

        // Get region center (using x, y, width, height)
        const regCenterX = (linkedRegion.x + linkedRegion.width / 2) * scale;
        const regCenterY = (linkedRegion.y + linkedRegion.height / 2) * scale;

        // Draw dashed line
        ctx.beginPath();
        ctx.moveTo(regCenterX, regCenterY);
        ctx.lineTo(scaledL3X, scaledL3Y);
        ctx.stroke();

        // Draw small circle at region end
        ctx.beginPath();
        ctx.arc(regCenterX, regCenterY, 6, 0, Math.PI * 2);
        ctx.fillStyle = '#00E676';
        ctx.fill();
    });

    // Draw circle at L3 title end
    const l3OnPage = pageRegions.find(r => r.id === l3TitleRegion?.id);
    if (l3OnPage || linkedRegions.some(r => pageRegions.find(pr => pr.id === r.id))) {
        ctx.beginPath();
        ctx.arc(scaledL3X, scaledL3Y, 10, 0, Math.PI * 2);
        ctx.fillStyle = '#FFD700'; // Gold for L3
        ctx.fill();
        ctx.strokeStyle = '#00E676';
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
        ctx.stroke();
    }

    ctx.restore();
}

// =============================================================================
// Ready for Extraction Functions
// =============================================================================

/**
 * Toggle the "Ready for Extraction" status for a page.
 * Validates that:
 * 1. All diagrams/tables/equations/lists have parent paragraph links
 * 2. Page is covered by L1 and L2 titles
 */
async function toggleReadyForExtraction(canvasId) {
    const pageNumber = canvasId === 'primary' ?
        state.pages[state.currentPageIndex] :
        state.secondaryPageNumber;

    if (!pageNumber) return;

    const btn = document.getElementById(`${canvasId}-ready-extract`);
    const isCurrentlyReady = btn.classList.contains('ready');
    const newReadyState = !isCurrentlyReady;

    // If trying to mark as ready, validate first
    if (newReadyState) {
        // Check for orphan regions (existing validation)
        const orphanCheck = checkForOrphanRegions(canvasId);
        if (orphanCheck.hasOrphans) {
            showOrphanError(orphanCheck.orphans);
            return;
        }
        
        // Check L1/L2 title coverage (new validation)
        const titleCoverageCheck = await checkTitleCoverage(pageNumber);
        if (!titleCoverageCheck.valid) {
            showTitleCoverageError(pageNumber, titleCoverageCheck);
            return;
        }
    }

    try {
        // Set ready for extraction status
        const response = await fetch(`/api/auto-slicer/${state.bookId}/set-ready-for-extraction`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                page_number: pageNumber,
                ready: newReadyState
            })
        });

        if (!response.ok) {
            alert('Failed to update extraction status');
            return;
        }

        // Also set/unset classesConfirmed (merged from Confirm Classes button)
        if (newReadyState) {
            await fetch(`/api/auto-slicer/${state.bookId}/confirm-page-classes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ page_number: pageNumber })
            });

            // Update local state
            if (!state.pageConfirmations[pageNumber]) {
                state.pageConfirmations[pageNumber] = {};
            }
            state.pageConfirmations[pageNumber].classesConfirmed = true;
        }

        // Update button UI
        btn.classList.toggle('ready');
        btn.textContent = btn.classList.contains('ready') ? '✓ Ready' : 'Ready for Extraction';

    } catch (error) {
        console.error('Error updating extraction status:', error);
        alert('Error updating extraction status');
    }
}

/**
 * Check if a page is covered by L1 and L2 titles.
 * Returns { valid: boolean, l1_covered: boolean, l2_covered: boolean }
 */
async function checkTitleCoverage(pageNumber) {
    try {
        const response = await fetch(`/api/books/${state.bookId}/validate-title-coverage?start_page=${pageNumber}&end_page=${pageNumber}`);
        if (!response.ok) {
            console.warn('Could not validate title coverage');
            return { valid: true, l1_covered: true, l2_covered: true }; // Allow if validation fails
        }
        
        const data = await response.json();
        return {
            valid: data.valid,
            l1_covered: data.l1_valid,
            l2_covered: data.l2_valid,
            uncovered_l1_pages: data.uncovered_l1_pages || [],
            uncovered_l2_pages: data.uncovered_l2_pages || []
        };
    } catch (error) {
        console.error('Error checking title coverage:', error);
        return { valid: true, l1_covered: true, l2_covered: true }; // Allow if error
    }
}

/**
 * Show error message when page is not covered by L1/L2 titles.
 */
function showTitleCoverageError(pageNumber, coverageCheck) {
    let message = `Page ${pageNumber} cannot be marked "Ready for Extraction":\n\n`;
    
    if (!coverageCheck.l1_covered) {
        message += `❌ Not covered by any L1 title (Chapter/Unit)\n`;
    }
    if (!coverageCheck.l2_covered) {
        message += `❌ Not covered by any L2 title (Section/Topic)\n`;
    }
    
    message += `\nPlease update the L1/L2 title page ranges in the Auto-Slicer page to include page ${pageNumber}.`;
    
    alert(message);
}

/**
 * Check for orphan regions:
 * - diagrams/tables/equations/lists without parent paragraph links
 * - answers without parent question links
 * - questions without linked answers
 * Returns { hasOrphans: boolean, orphans: Array }
 */
function checkForOrphanRegions(canvasId) {
    const regions = canvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;

    console.log(`checkForOrphanRegions called for ${canvasId}, checking ${regions.length} regions`);
    console.log('Region IDs being checked:', regions.map(r => `${r.id}(type:${typeof r.id},class:${r.class_name})`).join(', '));
    console.log('Current links count:', state.links.length);

    // Classes that require a parent paragraph link
    const linkableToParagraph = ['diagram', 'table', 'equation', 'list_bulleted', 'list_numbered', 'list_lettered'];
    // Classes that require a parent question link (answer needs question)
    const linkableToQuestion = ['answer'];
    // Classes that require a child link (question needs answer)
    const requiresChildAnswer = ['question'];

    const orphans = [];

    for (const region of regions) {
        // Skip ignored regions
        if (region.class_name === 'ignore') continue;

        // Check if this region type requires a parent link (diagrams, lists, equations, answers)
        if (linkableToParagraph.includes(region.class_name) || linkableToQuestion.includes(region.class_name)) {
            // Check if it has a parent link (paragraph or question)
            const hasParentLink = state.links.some(link => link.diagram_region_id === region.id);

            if (!hasParentLink) {
                console.log(`Orphan found: region ${region.id} (${region.class_name}) has no parent link`);
                orphans.push({
                    id: region.id,
                    class_name: region.class_name,
                    x: region.x,
                    y: region.y,
                    width: region.width,
                    height: region.height,
                    needsLink: region.class_name === 'answer' ? 'question' : 'paragraph'
                });
            }
        }

        // Check if this is a question that needs a linked answer
        if (requiresChildAnswer.includes(region.class_name)) {
            // Question must have an answer linked TO it (question is the paragraph_region_id in the link)
            const hasLinkedAnswer = state.links.some(link => 
                link.paragraph_region_id === region.id && 
                regions.some(r => r.id === link.diagram_region_id && r.class_name === 'answer')
            );

            // Also check cross-page links (answer might be on different page)
            const hasLinkedAnswerCrossPage = state.links.some(link => 
                link.paragraph_region_id === region.id &&
                state.allRegions.some(r => r.id === link.diagram_region_id && r.class_name === 'answer')
            );

            if (!hasLinkedAnswer && !hasLinkedAnswerCrossPage) {
                console.log(`Orphan question found: region ${region.id} has no linked answer`);
                orphans.push({
                    id: region.id,
                    class_name: region.class_name,
                    x: region.x,
                    y: region.y,
                    width: region.width,
                    height: region.height,
                    needsLink: 'answer'
                });
            }
        }
    }

    console.log(`checkForOrphanRegions result: ${orphans.length} orphans found`);

    return {
        hasOrphans: orphans.length > 0,
        orphans: orphans
    };
}

/**
 * Show error message for orphan regions and highlight them on the canvas.
 */
function showOrphanError(orphans) {
    // Group by link type needed
    const needsParagraph = orphans.filter(o => o.needsLink === 'paragraph');
    const needsQuestion = orphans.filter(o => o.needsLink === 'question');
    const needsAnswer = orphans.filter(o => o.needsLink === 'answer');

    let message = 'Cannot mark as ready. The following regions need links:\n\n';

    if (needsParagraph.length > 0) {
        const classCounts = {};
        needsParagraph.forEach(o => {
            classCounts[o.class_name] = (classCounts[o.class_name] || 0) + 1;
        });
        message += '📄 Need PARAGRAPH links:\n';
        for (const [className, count] of Object.entries(classCounts)) {
            message += `  • ${count} ${className}${count > 1 ? 's' : ''}\n`;
        }
    }

    if (needsQuestion.length > 0) {
        const classCounts = {};
        needsQuestion.forEach(o => {
            classCounts[o.class_name] = (classCounts[o.class_name] || 0) + 1;
        });
        if (needsParagraph.length > 0) message += '\n';
        message += '❓ Need QUESTION links (answers without questions):\n';
        for (const [className, count] of Object.entries(classCounts)) {
            message += `  • ${count} ${className}${count > 1 ? 's' : ''}\n`;
        }
    }

    if (needsAnswer.length > 0) {
        const classCounts = {};
        needsAnswer.forEach(o => {
            classCounts[o.class_name] = (classCounts[o.class_name] || 0) + 1;
        });
        if (needsParagraph.length > 0 || needsQuestion.length > 0) message += '\n';
        message += '💬 Need ANSWER links (questions without answers):\n';
        for (const [className, count] of Object.entries(classCounts)) {
            message += `  • ${count} ${className}${count > 1 ? 's' : ''}\n`;
        }
    }

    message += '\nUse "Link to..." (right-click) or press L to link them.';

    alert(message);

    // Highlight orphan regions on canvas
    highlightOrphanRegions(orphans);
}

/**
 * Temporarily highlight orphan regions with a red flashing border.
 */
function highlightOrphanRegions(orphans) {
    const orphanIds = new Set(orphans.map(o => o.id));

    // Store original state
    const originalRegions = [...state.pageRegions];

    // Flash the orphan regions 3 times
    let flashCount = 0;
    const flashInterval = setInterval(() => {
        flashCount++;

        // Toggle orphan highlight
        state.orphanHighlight = flashCount % 2 === 1 ? orphanIds : null;
        redrawCanvas('primary');
        if (state.viewMode !== 'single') redrawCanvas('secondary');

        if (flashCount >= 6) {
            clearInterval(flashInterval);
            state.orphanHighlight = null;
            redrawCanvas('primary');
            if (state.viewMode !== 'single') redrawCanvas('secondary');
        }
    }, 300);
}

/**
 * Update Ready for Extraction button state when loading a page.
 */
async function updateReadyForExtractionState(pageNumber, canvasId) {
    const btn = document.getElementById(`${canvasId}-ready-extract`);
    if (!btn) return;

    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/page-status/${pageNumber}`);
        if (response.ok) {
            const data = await response.json();
            if (data.ready_for_extraction) {
                btn.classList.add('ready');
                btn.textContent = '✓ Ready';
            } else {
                btn.classList.remove('ready');
                btn.textContent = 'Ready for Extraction';
            }
        }
    } catch (error) {
        // Ignore errors, default to not ready
        btn.classList.remove('ready');
        btn.textContent = 'Ready for Extraction';
    }
}

// =============================================================================
// Skip Page Functions
// =============================================================================

/**
 * Toggle the "Skip Page" status for a page.
 * Skipped pages will not be processed for extraction.
 */
async function toggleSkipPage(canvasId) {
    const pageNumber = canvasId === 'primary' ?
        state.pages[state.currentPageIndex] :
        state.secondaryPageNumber;

    if (!pageNumber) return;

    const btn = document.getElementById(`${canvasId}-skip-page`);
    const readyBtn = document.getElementById(`${canvasId}-ready-extract`);
    const isCurrentlySkipped = btn.classList.contains('skipped');
    const newSkipState = !isCurrentlySkipped;

    try {
        // Update skip status via API
        const response = await fetch(`/api/books/${state.bookId}/page-status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                page_number: pageNumber,
                is_skipped: newSkipState
            })
        });

        if (!response.ok) {
            const error = await response.json();
            alert(error.detail || 'Failed to update skip status');
            return;
        }

        // Update button UI
        btn.classList.toggle('skipped');
        btn.textContent = btn.classList.contains('skipped') ? '⏭️ Skipped' : 'Skip Page';
        
        // If skipping, also clear ready status
        if (newSkipState && readyBtn) {
            readyBtn.classList.remove('ready');
            readyBtn.textContent = 'Ready for Extraction';
        }

    } catch (error) {
        console.error('Error updating skip status:', error);
        alert('Error updating skip status');
    }
}

/**
 * Update Skip Page button state when loading a page.
 */
async function updateSkipPageState(pageNumber, canvasId) {
    const btn = document.getElementById(`${canvasId}-skip-page`);
    if (!btn) return;

    try {
        const response = await fetch(`/api/books/${state.bookId}/page-statuses`);
        if (response.ok) {
            const data = await response.json();
            const pageStatus = data.pages.find(p => p.page_number === pageNumber);
            if (pageStatus && pageStatus.is_skipped) {
                btn.classList.add('skipped');
                btn.textContent = '⏭️ Skipped';
            } else {
                btn.classList.remove('skipped');
                btn.textContent = 'Skip Page';
            }
        }
    } catch (error) {
        // Ignore errors, default to not skipped
        btn.classList.remove('skipped');
        btn.textContent = 'Skip Page';
    }
}

// =============================================================================
// L1/L2 Title Display Functions
// =============================================================================

/**
 * Load L1/L2 title configurations from database tables.
 * Stores level1 and level2 titles separately for independent lookup by page number.
 * Falls back to JSON config if database tables don't exist.
 */
async function loadTitleConfigs() {
    try {
        // Try to load from database first (new system)
        let l1Loaded = false;
        let l2Loaded = false;
        
        // Load L1 titles from database
        try {
            const l1Response = await fetch(`/api/books/${state.bookId}/l1-titles`);
            if (l1Response.ok) {
                const l1Data = await l1Response.json();
                if (l1Data.titles && l1Data.titles.length > 0) {
                    // Convert from database format to expected format
                    state.level1Titles = l1Data.titles.map(t => ({
                        title: t.title_text,
                        start_page: t.start_page,
                        end_page: t.end_page,
                        id: t.id
                    }));
                    l1Loaded = true;
                    console.log('L1 titles loaded from database:', state.level1Titles);
                }
            }
        } catch (e) {
            console.warn('Could not load L1 titles from database:', e);
        }
        
        // Load L2 titles from database
        try {
            const l2Response = await fetch(`/api/books/${state.bookId}/l2-titles`);
            if (l2Response.ok) {
                const l2Data = await l2Response.json();
                if (l2Data.titles && l2Data.titles.length > 0) {
                    // Convert from database format to expected format
                    state.level2Titles = l2Data.titles.map(t => ({
                        title: t.title_text,
                        start_page: t.start_page,
                        end_page: t.end_page,
                        id: t.id
                    }));
                    l2Loaded = true;
                    console.log('L2 titles loaded from database:', state.level2Titles);
                }
            }
        } catch (e) {
            console.warn('Could not load L2 titles from database:', e);
        }
        
        // Fallback to JSON config if database didn't have titles
        if (!l1Loaded || !l2Loaded) {
            const response = await fetch(`/api/auto-slicer/${state.bookId}/config`);
            if (response.ok) {
                const data = await response.json();
                if (data.config && data.config.titles) {
                    const titles = data.config.titles;
                    if (!l1Loaded) {
                        state.level1Titles = (titles.level1 || []).map(t => ({
                            title: t.title,
                            start_page: t.start_page,
                            end_page: t.end_page
                        }));
                        console.log('L1 titles loaded from JSON fallback:', state.level1Titles);
                    }
                    if (!l2Loaded) {
                        state.level2Titles = (titles.level2 || []).map(t => ({
                            title: t.title,
                            start_page: t.start_page,
                            end_page: t.end_page
                        }));
                        console.log('L2 titles loaded from JSON fallback:', state.level2Titles);
                    }
                }
            }
        }
        
        // Ensure arrays are initialized
        if (!state.level1Titles) state.level1Titles = [];
        if (!state.level2Titles) state.level2Titles = [];
        
    } catch (error) {
        console.error('Error loading title configs:', error);
        state.level1Titles = [];
        state.level2Titles = [];
    }
}

/**
 * Load enabled classes from layout detection config.
 * Used to filter the context menu to only show enabled classes.
 */
async function loadEnabledClasses() {
    // Default classes that are typically enabled in auto-slicer
    // (matches auto-slicer defaults: all EXCEPT Title L1, L2, Caption, Reference)
    const DEFAULT_ENABLED_CLASSES = [
        'paragraph', 'diagram', 'equation',
        'list_bulleted', 'list_numbered', 'list_lettered', 'list_item',
        'header', 'footer', 'title_level_3',
        'question', 'answer'  // Added for Q&A support
    ];

    try {
        console.log('Loading enabled classes for book:', state.bookId);
        const response = await fetch(`/api/auto-slicer/${state.bookId}/layout-config`);
        if (!response.ok) {
            console.warn('Failed to load layout config:', response.status);
            state.enabledClasses = DEFAULT_ENABLED_CLASSES;
            return;
        }

        const config = await response.json();
        console.log('Layout config received:', config);

        if (config.enabled_classes && config.enabled_classes.length > 0) {
            state.enabledClasses = config.enabled_classes;
            console.log('Enabled classes set from config:', state.enabledClasses);
        } else {
            // Use default enabled classes when none configured
            console.log('No enabled_classes in config - using defaults:', DEFAULT_ENABLED_CLASSES);
            state.enabledClasses = DEFAULT_ENABLED_CLASSES;
        }
    } catch (error) {
        console.error('Error loading enabled classes:', error);
        state.enabledClasses = DEFAULT_ENABLED_CLASSES;
    }
}

/**
 * Filter context menu class items based on enabled classes for this book.
 * Only shows classes that are enabled in the auto-slicer configuration.
 */
function filterContextMenuClasses() {
    // Get all class items in context menu
    const classItems = document.querySelectorAll('#context-menu .context-menu-item[data-class]');

    console.log('Filtering context menu classes. Enabled:', state.enabledClasses);

    // If no enabled classes configured, show all (fallback for books without config)
    if (!state.enabledClasses || state.enabledClasses.length === 0) {
        console.log('No enabled classes configured - showing all');
        classItems.forEach(item => item.style.display = 'flex');
        return;
    }

    // Build effective enabled list including remapped classes
    // 'table' is remapped to 'diagram' during YOLO detection, so show 'table' if 'diagram' is enabled
    const effectiveEnabled = [...state.enabledClasses];
    if (effectiveEnabled.includes('diagram') && !effectiveEnabled.includes('table')) {
        effectiveEnabled.push('table');
    }

    // Filter items based on enabled classes
    classItems.forEach(item => {
        const className = item.dataset.class;
        // Always show 'ignore' option
        if (className === 'ignore') {
            item.style.display = 'flex';
            return;
        }

        // Show if class is in enabled list
        if (effectiveEnabled.includes(className)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });

    console.log('Filtered context menu to classes:', effectiveEnabled);
}

/**
 * Start linking a diagram/table/equation/list to a paragraph, or answer to question.
 * Sets the selected region as the source and enters link mode.
 */
function startLinkToParagraph(region, canvasId) {
    if (!region) {
        alert('No region selected');
        return;
    }

    // Classes that can be linked to paragraphs
    const linkableToParagraph = ['diagram', 'table', 'equation', 'list_bulleted', 'list_numbered', 'list_lettered'];
    // Classes that can be linked to questions
    const linkableToQuestion = ['answer'];
    const linkableClasses = [...linkableToParagraph, ...linkableToQuestion];

    if (!linkableClasses.includes(region.class_name)) {
        alert('Only diagrams, tables, equations, lists, and answers can be linked');
        return;
    }

    // Check if already linked
    const existingLink = state.links.find(l => l.diagram_region_id === region.id);
    if (existingLink) {
        const targetType = region.class_name === 'answer' ? 'question' : 'paragraph';
        const confirm = window.confirm(
            `This region is already linked to a ${targetType}.\n` +
            'Do you want to remove the existing link and create a new one?'
        );
        if (!confirm) return;

        // Remove existing link
        removeLink(existingLink.id);
    }

    // Set as link source and enter link mode
    state.linkSourceRegion = region;
    setMode('link');

    // Show appropriate message based on source type
    const targetType = region.class_name === 'answer' ? 'QUESTION' : 'PARAGRAPH';
    document.getElementById('link-status').textContent =
        `Click a ${targetType} to link this ${region.class_name}`;
    document.getElementById('link-status').style.color = '#ff9800';

    // Redraw to highlight the source region
    redrawCanvas(canvasId);
    if (state.viewMode !== 'single') {
        redrawCanvas(canvasId === 'primary' ? 'secondary' : 'primary');
    }
}

/**
 * Update L1/L2 title display based on current page number.
 * Searches L1 and L2 title arrays independently to find matching ranges.
 */
function updateTitleDisplay(pageNumber) {
    let l1Title = '-';
    let l2Title = '-';

    // Find L1 title for this page (search all L1 titles, later ones override)
    for (const t of state.level1Titles) {
        const startPage = t.start_page || 1;
        const endPage = t.end_page || 9999;
        if (pageNumber >= startPage && pageNumber <= endPage) {
            l1Title = t.title;
        }
    }

    // Find L2 title for this page (search all L2 titles, later ones override)
    for (const t of state.level2Titles) {
        const startPage = t.start_page || 1;
        const endPage = t.end_page || 9999;
        if (pageNumber >= startPage && pageNumber <= endPage) {
            l2Title = t.title;
        }
    }

    console.log(`Page ${pageNumber}: L1="${l1Title}", L2="${l2Title}"`);
    document.getElementById('l1-title-value').textContent = l1Title;
    document.getElementById('l2-title-value').textContent = l2Title;
}

// =============================================================================
// UI Updates
// =============================================================================

function updateRegionsList() {
    const container = document.getElementById('regions-list');
    container.innerHTML = '';

    // Combine regions from both pages if in dual view
    let allDisplayRegions = [...state.pageRegions];
    if (state.viewMode !== 'single' && state.secondaryPageRegions.length > 0) {
        allDisplayRegions = allDisplayRegions.concat(
            state.secondaryPageRegions.map(r => ({ ...r, _isSecondary: true }))
        );
    }

    if (allDisplayRegions.length === 0) {
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">No regions on this page</div>';
        return;
    }

    // Sort by page then y position
    allDisplayRegions.sort((a, b) => {
        if (a._isSecondary !== b._isSecondary) return a._isSecondary ? 1 : -1;
        return a.y - b.y;
    });

    allDisplayRegions.forEach(region => {
        const color = CLASS_COLORS[region.class_name] || '#FF0000';
        const isSelected = isRegionSelected(region.id);
        const isIgnored = region.class_name === 'ignore';
        const hasLink = state.links.some(l =>
            l.diagram_region_id === region.id || l.paragraph_region_id === region.id
        );

        const item = document.createElement('div');
        item.className = 'region-item' +
            (isSelected ? ' selected' : '') +
            (isIgnored ? ' ignored' : '') +
            (hasLink ? ' linked' : '');
        // Use yellow border for multi-selected items
        if (isSelected && state.selectedRegions.length > 1) {
            item.style.borderLeftColor = '#FFD700';
        } else {
            item.style.borderLeftColor = color;
        }

        const pageLabel = region._isSecondary ? ` (pg ${state.secondaryPageNumber})` : '';

        item.innerHTML = `
            ${hasLink ? '<span class="link-badge">L</span>' : ''}
            <div class="class-name" style="color: ${color}">${region.class_name}${pageLabel}</div>
            <div class="confidence">Confidence: ${Math.round(region.confidence * 100)}%</div>
            <div class="dimensions">${region.width} x ${region.height}</div>
        `;
        item.onclick = () => selectRegion(region.id, region._isSecondary ? 'secondary' : 'primary');
        container.appendChild(item);
    });
}

function updateLinksCount() {
    document.getElementById('links-count').textContent = `${state.links.length} links`;
}

function updateLinksSection() {
    const section = document.getElementById('links-section');
    const list = document.getElementById('links-list');

    if (state.links.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    list.innerHTML = '';

    state.links.forEach(link => {
        const item = document.createElement('div');
        item.className = 'link-item';
        item.innerHTML = `
            <span class="link-info">Diagram #${link.diagram_region_id} → Para #${link.paragraph_region_id}</span>
            <button class="unlink-btn" onclick="removeLink(${link.id})" title="Remove link">×</button>
        `;
        list.appendChild(item);
    });
}

function setMode(mode) {
    state.mode = mode;

    document.getElementById('select-mode-btn').classList.toggle('active', mode === 'select');
    document.getElementById('draw-mode-btn').classList.toggle('active', mode === 'draw');
    document.getElementById('link-mode-btn').classList.toggle('active', mode === 'link');
    document.getElementById('link-btn').classList.toggle('active', mode === 'link');

    document.getElementById('mode-display').textContent = mode.toUpperCase();

    // Determine which canvas should have drawing cursor
    // If changing boundary, only that canvas gets drawing cursor
    // Otherwise, both canvases get drawing cursor in draw mode
    const isChangingBoundary = state.changingBoundaryRegion !== null;
    const drawOnPrimary = mode === 'draw' && (!isChangingBoundary || state.changingBoundaryRegion.canvasId === 'primary');
    const drawOnSecondary = mode === 'draw' && (!isChangingBoundary || state.changingBoundaryRegion.canvasId === 'secondary');

    state.canvas.classList.toggle('drawing', drawOnPrimary);
    state.canvas.classList.toggle('linking', mode === 'link');
    state.secondaryCanvas.classList.toggle('drawing', drawOnSecondary);
    state.secondaryCanvas.classList.toggle('linking', mode === 'link');

    // Clear any inline cursor styles so CSS classes take effect
    // (inline styles from updateCursorForPosition would override CSS classes)
    if (mode === 'draw' || mode === 'link') {
        state.canvas.style.cursor = '';
        state.secondaryCanvas.style.cursor = '';
    }

    if (mode !== 'link') {
        cancelLinkMode();
    } else {
        document.getElementById('link-status').textContent = 'Click a DIAGRAM to start linking';
    }

    // Clear boundary change state if switching away from draw mode (unless we're starting boundary change)
    if (mode !== 'draw' && state.changingBoundaryRegion) {
        state.changingBoundaryRegion = null;
        document.getElementById('link-status').textContent = '';
        document.getElementById('link-status').style.color = '';
    }
}

function updateViewMode() {
    state.viewMode = document.getElementById('view-mode-select').value;

    if (state.viewMode === 'single') {
        document.getElementById('secondary-canvas-wrapper').style.display = 'none';
    } else {
        loadSecondaryPage();
    }
}

function updateZoom() {
    state.zoom = parseFloat(document.getElementById('zoom-select').value);
    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
}

/**
 * Apply Arabic RTL order to canvas wrappers based on current state.arabicMode
 * Called when toggling RTL mode and when dual view is activated
 */
function applyArabicModeOrder() {
    const primaryWrapper = document.getElementById('primary-canvas-wrapper');
    const secondaryWrapper = document.getElementById('secondary-canvas-wrapper');

    if (state.arabicMode) {
        // RTL: primary (current page) on RIGHT, secondary (next page) on LEFT
        // Higher order value = appears later (to the right in row layout)
        primaryWrapper.style.order = '2';
        secondaryWrapper.style.order = '1';
    } else {
        // LTR: primary on LEFT, secondary on RIGHT (default order)
        primaryWrapper.style.order = '1';
        secondaryWrapper.style.order = '2';
    }
}

/**
 * Toggle Arabic (RTL) mode - swaps the left/right order of pages
 * In Arabic mode: current page on right, next/prev on left
 * Uses CSS order property for explicit control over visual order
 */
function toggleArabicMode() {
    state.arabicMode = document.getElementById('arabic-mode-checkbox').checked;

    // Apply the order change
    applyArabicModeOrder();

    // Update page labels to reflect the order
    updatePageLabels();
}

/**
 * Update page labels based on Arabic mode
 * In RTL mode, labels indicate position since visual order is reversed
 */
function updatePageLabels() {
    if (!state.pages.length) return;

    const currentPage = state.pages[state.currentPageIndex];
    const primaryLabel = document.getElementById('primary-page-label');
    const secondaryLabel = document.getElementById('secondary-page-label');

    if (state.arabicMode) {
        // Arabic RTL mode: primary (current) is on RIGHT side
        // Add clear indicators since visual order is reversed
        primaryLabel.textContent = `Page ${currentPage} (Current) →`;
        if (state.secondaryPageNumber) {
            if (state.viewMode === 'dual-prev') {
                secondaryLabel.textContent = `← Page ${state.secondaryPageNumber} (Previous)`;
            } else {
                secondaryLabel.textContent = `← Page ${state.secondaryPageNumber} (Next)`;
            }
        }
    } else {
        // Normal LTR mode: primary on left, secondary on right
        primaryLabel.textContent = `Page ${currentPage}`;
        if (state.secondaryPageNumber) {
            secondaryLabel.textContent = `Page ${state.secondaryPageNumber}`;
        }
    }
}

// =============================================================================
// Page Navigation
// =============================================================================

/**
 * Navigate to a specific page number.
 * Used when opening layout review from auto-slicer with a page parameter.
 */
function navigateToPage(pageNumber) {
    // Find the index of this page in our pages array
    const pageIndex = state.pages.indexOf(pageNumber);
    
    if (pageIndex >= 0) {
        // Page has regions, navigate directly
        state.currentPageIndex = pageIndex;
        loadCurrentPage();
        console.log(`Navigated to page ${pageNumber} (index ${pageIndex})`);
    } else {
        // Page doesn't have regions, find the closest page
        // First, check if the page exists in allBookPages
        if (pageNumber >= 1 && pageNumber <= state.allBookPages.length) {
            // Find the closest page with regions
            let closestIndex = 0;
            let closestDiff = Math.abs(state.pages[0] - pageNumber);
            
            for (let i = 1; i < state.pages.length; i++) {
                const diff = Math.abs(state.pages[i] - pageNumber);
                if (diff < closestDiff) {
                    closestDiff = diff;
                    closestIndex = i;
                }
            }
            
            state.currentPageIndex = closestIndex;
            loadCurrentPage();
            console.log(`Page ${pageNumber} has no regions, navigated to closest page ${state.pages[closestIndex]}`);
        } else {
            console.warn(`Page ${pageNumber} is out of range`);
        }
    }
}

function prevPage() {
    if (state.currentPageIndex > 0) {
        state.currentPageIndex--;
        loadCurrentPage();
    }
}

function nextPage() {
    if (state.currentPageIndex < state.pages.length - 1) {
        state.currentPageIndex++;
        loadCurrentPage();
    }
}

// =============================================================================
// Confirm & Finish
// =============================================================================

async function confirmCurrentPage() {
    const pageNumber = state.pages[state.currentPageIndex];

    try {
        await fetch(`/api/auto-slicer/${state.bookId}/confirm-regions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ page_numbers: [pageNumber] })
        });

        if (state.currentPageIndex < state.pages.length - 1) {
            nextPage();
        } else {
            alert(`Page ${pageNumber} confirmed! This was the last page.`);
        }

    } catch (error) {
        console.error('Error confirming page:', error);
        alert('Failed to confirm page');
    }
}

async function confirmAllAndFinish() {
    // Check which pages have classes confirmed (regions are confirmed by default)
    const confirmedPages = state.pages.filter(page => {
        const conf = state.pageConfirmations[page];
        return conf && conf.classesConfirmed;
    });

    const unconfirmedPages = state.pages.filter(page => {
        const conf = state.pageConfirmations[page];
        return !conf || !conf.classesConfirmed;
    });

    let message = 'Confirm and save to database?\n\n';

    if (confirmedPages.length > 0) {
        message += `Pages ready to save: ${confirmedPages.join(', ')}\n`;
    }

    if (unconfirmedPages.length > 0) {
        message += `\nWARNING: ${unconfirmedPages.length} page(s) not confirmed and will NOT be saved:\n`;
        message += `Pages: ${unconfirmedPages.join(', ')}\n`;
        message += '\n(Click "Confirm Classes" on each page to confirm)';
    }

    message += '\n\nNote: Regions marked as "ignore" will not be saved.';

    if (!confirm(message)) return;

    if (confirmedPages.length === 0) {
        alert('No pages are confirmed. Please click "Confirm Classes" on at least one page.');
        return;
    }

    try {
        await fetch(`/api/auto-slicer/${state.bookId}/finalize-layout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                page_numbers: confirmedPages,
                skip_ignored: true
            })
        });

        window.location.href = `/auto-slicer?book_id=${state.bookId}`;

    } catch (error) {
        console.error('Error finalizing layout:', error);
        alert('Failed to save confirmed pages');
    }
}

// =============================================================================
// Context Menu (Right-Click)
// =============================================================================

function setupContextMenu() {
    const menu = document.getElementById('context-menu');

    // Handle context menu item clicks
    menu.querySelectorAll('.context-menu-item').forEach(item => {
        item.addEventListener('click', async () => {
            const action = item.dataset.action;
            const newClass = item.dataset.class;

            // Store references before hiding menu
            const region = state.contextMenuRegion;
            const canvasId = state.contextMenuCanvas;

            console.log('Context menu clicked:', { action, newClass, region, canvasId });

            // Hide menu first
            hideContextMenu();

            if (action === 'merge') {
                await mergeSelectedRegions();
            } else if (action === 'split') {
                startSplitRegion(region, canvasId);
            } else if (action === 'link-paragraph') {
                startLinkToParagraph(region, canvasId);
            } else if (action === 'link-l3') {
                startL3Linking();
            } else if (action === 'bring-to-front' && region) {
                await bringToFront(region, canvasId);
            } else if (action === 'send-to-back' && region) {
                await sendToBack(region, canvasId);
            } else if (action === 'change-boundary' && region) {
                await startChangeBoundary(region, canvasId);
            } else if (action === 'delete' && region) {
                await deleteRegionDirect(region.id, canvasId);
            } else if (action === 'permanent-ignore' && region) {
                await permanentlyIgnoreSimilar(region, canvasId);
            } else if (newClass && region) {
                console.log(`Calling applyClassToRegion with id=${region.id}, class=${newClass}`);
                await applyClassToRegion(region.id, newClass, canvasId);
            }
        });
    });

    // Hide menu on click outside
    document.addEventListener('click', (e) => {
        if (!menu.contains(e.target)) {
            hideContextMenu();
        }
    });

    // Hide on escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideContextMenu();
        }
    });

    // Prevent default context menu on canvases
    state.canvas.addEventListener('contextmenu', (e) => handleContextMenu(e, 'primary'));
    state.secondaryCanvas.addEventListener('contextmenu', (e) => handleContextMenu(e, 'secondary'));
}

function handleContextMenu(e, canvasId) {
    e.preventDefault();

    const canvas = canvasId === 'primary' ? state.canvas : state.secondaryCanvas;
    const regions = canvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Convert to image coordinates
    const imgX = x / state.zoom;
    const imgY = y / state.zoom;

    // Find region at click position
    const region = findRegionAt(imgX, imgY, regions);

    if (region) {
        state.contextMenuRegion = region;
        state.contextMenuCanvas = canvasId;

        // Handle selection based on Ctrl key state
        if (!isRegionSelected(region.id)) {
            if (e.ctrlKey) {
                // Ctrl+right-click: add to existing selection
                addToSelection(region.id, canvasId);
            } else {
                // Normal right-click: replace selection
                selectRegion(region.id, canvasId);
            }
        }
        // If region is already selected, keep the current selection (don't change anything)

        // Update context menu based on selection state
        updateContextMenuForSelection();

        showContextMenu(e.clientX, e.clientY);
    } else {
        hideContextMenu();
    }
}

/**
 * Update context menu items based on current selection state.
 * Shows/hides "Merge Regions" option based on multi-selection.
 */
function updateContextMenuForSelection() {
    const selectionCount = state.selectedRegions.length;
    const mergeItem = document.getElementById('merge-regions-item');
    const selectionHeader = document.getElementById('selection-count-header');
    const selectionCountText = document.getElementById('selection-count-text');

    // Update selection count header
    if (selectionCount > 1) {
        selectionHeader.style.display = 'block';
        selectionCountText.textContent = `${selectionCount} regions selected`;
    } else {
        selectionHeader.style.display = 'none';
    }

    // Show merge option only if:
    // 1. Multiple regions are selected (2+)
    // 2. All selected regions have the same class
    if (selectionCount >= 2 && canMergeSelectedRegions()) {
        mergeItem.style.display = 'flex';
    } else {
        mergeItem.style.display = 'none';
    }

    // Show "Link to Paragraph" or "Link to Question" for linkable regions
    const linkToParagraphItem = document.getElementById('link-to-paragraph-item');
    const linkToParagraphText = document.getElementById('link-to-paragraph-text');
    const linkableToParagraph = ['diagram', 'table', 'equation', 'list_bulleted', 'list_numbered', 'list_lettered'];
    const linkableToQuestion = ['answer'];
    const region = state.contextMenuRegion;

    if (region && linkableToParagraph.includes(region.class_name)) {
        linkToParagraphItem.style.display = 'flex';
        linkToParagraphText.textContent = 'Link to Paragraph';
    } else if (region && linkableToQuestion.includes(region.class_name)) {
        linkToParagraphItem.style.display = 'flex';
        linkToParagraphText.textContent = 'Link to Question';
    } else {
        linkToParagraphItem.style.display = 'none';
    }

    // Filter class items based on enabled classes for this book
    filterContextMenuClasses();
}

/**
 * Check if selected regions can be merged.
 * Returns true if all selected regions have the same class.
 */
function canMergeSelectedRegions() {
    if (state.selectedRegions.length < 2) return false;

    // Get all selected regions' classes
    const classes = new Set();
    for (const sel of state.selectedRegions) {
        // Find region in either page
        let region = state.pageRegions.find(r => r.id === sel.id);
        if (!region) region = state.secondaryPageRegions.find(r => r.id === sel.id);
        if (region) {
            classes.add(region.class_name);
        }
    }

    // All must have the same class
    return classes.size === 1;
}

/**
 * Merge all selected regions into a single region.
 * Creates a bounding box containing all selected regions.
 */
async function mergeSelectedRegions() {
    if (!canMergeSelectedRegions()) {
        alert('Cannot merge: All selected regions must have the same class.');
        return;
    }

    // Get all selected regions
    const selectedRegionObjects = [];
    let commonClass = null;
    let commonPage = null;

    for (const sel of state.selectedRegions) {
        let region = state.pageRegions.find(r => r.id === sel.id);
        if (!region) region = state.secondaryPageRegions.find(r => r.id === sel.id);
        if (region) {
            selectedRegionObjects.push(region);
            commonClass = region.class_name;
            commonPage = region.page_number;
        }
    }

    if (selectedRegionObjects.length < 2) {
        alert('Need at least 2 regions to merge.');
        return;
    }

    // Calculate bounding box
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const region of selectedRegionObjects) {
        minX = Math.min(minX, region.x);
        minY = Math.min(minY, region.y);
        maxX = Math.max(maxX, region.x + region.width);
        maxY = Math.max(maxY, region.y + region.height);
    }

    const mergedRegion = {
        page_number: commonPage,
        class_name: commonClass,
        x: Math.round(minX),
        y: Math.round(minY),
        width: Math.round(maxX - minX),
        height: Math.round(maxY - minY),
        confidence: 1.0
    };

    try {
        // Create the merged region first
        const createResponse = await fetch(`/api/auto-slicer/${state.bookId}/add-region`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(mergedRegion)
        });

        if (!createResponse.ok) throw new Error('Failed to create merged region');

        const createData = await createResponse.json();
        const newRegionId = createData.region_id;

        // Delete all original regions
        for (const region of selectedRegionObjects) {
            await fetch(`/api/auto-slicer/${state.bookId}/detected-region/${region.id}`, {
                method: 'DELETE'
            });

            // Remove from local arrays
            state.pageRegions = state.pageRegions.filter(r => r.id !== region.id);
            state.secondaryPageRegions = state.secondaryPageRegions.filter(r => r.id !== region.id);
            state.allRegions = state.allRegions.filter(r => r.id !== region.id);

            // Remove any links involving this region
            state.links = state.links.filter(l =>
                l.diagram_region_id !== region.id &&
                l.paragraph_region_id !== region.id
            );
        }

        // Add new merged region to local arrays
        const newRegion = { ...mergedRegion, id: newRegionId };
        state.allRegions.push(newRegion);

        const currentPage = state.pages[state.currentPageIndex];
        if (commonPage === currentPage) {
            state.pageRegions.push(newRegion);
        } else if (commonPage === state.secondaryPageNumber) {
            state.secondaryPageRegions.push(newRegion);
        }

        // Clear selection and select the new merged region
        clearSelection();
        selectRegion(newRegionId, commonPage === currentPage ? 'primary' : 'secondary');

        // Update UI
        updateLinksCount();
        updateLinksSection();
        document.getElementById('regions-count').textContent = `${state.pageRegions.length} regions`;

        console.log(`Merged ${selectedRegionObjects.length} regions into one`);

    } catch (error) {
        console.error('Error merging regions:', error);
        alert('Failed to merge regions: ' + error.message);
    }
}

// =============================================================================
// Z-Order Functions (Bring to Front / Send to Back)
// =============================================================================

/**
 * Bring a region to the front (highest z-index) so it's selected first when clicked.
 */
async function bringToFront(region, canvasId) {
    const regions = canvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;

    // Find max z_index on this page
    let maxZ = 0;
    for (const r of regions) {
        if (r.z_index !== undefined && r.z_index > maxZ) {
            maxZ = r.z_index;
        }
    }

    const newZIndex = maxZ + 1;

    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/detected-region/${region.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ z_index: newZIndex })
        });

        if (response.ok) {
            // Update local state
            region.z_index = newZIndex;

            // Also update in allRegions
            const allRegion = state.allRegions.find(r => r.id === region.id);
            if (allRegion) allRegion.z_index = newZIndex;

            redrawCanvas(canvasId);
            console.log(`Brought region ${region.id} to front (z_index: ${newZIndex})`);
        } else {
            alert('Failed to bring region to front');
        }
    } catch (error) {
        console.error('Error bringing to front:', error);
        alert('Error bringing region to front');
    }
}

/**
 * Send a region to the back (lowest z-index) so it's selected last when clicked.
 */
async function sendToBack(region, canvasId) {
    const regions = canvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;

    // Find min z_index on this page
    let minZ = 0;
    for (const r of regions) {
        if (r.z_index !== undefined && r.z_index < minZ) {
            minZ = r.z_index;
        }
    }

    const newZIndex = minZ - 1;

    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/detected-region/${region.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ z_index: newZIndex })
        });

        if (response.ok) {
            // Update local state
            region.z_index = newZIndex;

            // Also update in allRegions
            const allRegion = state.allRegions.find(r => r.id === region.id);
            if (allRegion) allRegion.z_index = newZIndex;

            redrawCanvas(canvasId);
            console.log(`Sent region ${region.id} to back (z_index: ${newZIndex})`);
        } else {
            alert('Failed to send region to back');
        }
    } catch (error) {
        console.error('Error sending to back:', error);
        alert('Error sending region to back');
    }
}

// =============================================================================
// Split Region Functions
// =============================================================================

/**
 * Start split mode - user will draw a line to split the region.
 */
function startSplitRegion(region, canvasId) {
    if (!region) {
        alert('No region selected to split');
        return;
    }

    state.isSplitting = true;
    state.splitRegion = region;
    state.splitCanvasId = canvasId;
    state.splitStart = null;
    state.splitEnd = null;

    // Update status
    document.getElementById('link-status').textContent =
        'Split Mode: Draw a line across the region to split it (click start and end points)';
    document.getElementById('link-status').style.color = '#4fc3f7';

    // Change cursor
    const canvas = canvasId === 'primary' ? state.canvas : state.secondaryCanvas;
    canvas.style.cursor = 'crosshair';
}

/**
 * Handle click during split mode.
 */
function handleSplitClick(imgX, imgY, canvasId) {
    if (!state.isSplitting || canvasId !== state.splitCanvasId) return false;

    const region = state.splitRegion;

    // Check if click is within the region
    const inRegion = imgX >= region.x && imgX <= region.x + region.width &&
                     imgY >= region.y && imgY <= region.y + region.height;

    if (!inRegion) {
        // Click outside - cancel split
        cancelSplit();
        return true;
    }

    if (!state.splitStart) {
        // First click - set start point
        state.splitStart = { x: imgX, y: imgY };
        document.getElementById('link-status').textContent =
            'Split Mode: Now click the end point of the split line';

        // Redraw to show start point
        redrawCanvas(canvasId);
        drawSplitPreview(canvasId);
    } else {
        // Second click - set end point and perform split
        state.splitEnd = { x: imgX, y: imgY };
        performSplit();
    }

    return true;
}

/**
 * Draw split line preview during split mode.
 */
function drawSplitPreview(canvasId) {
    if (!state.isSplitting || !state.splitStart) return;

    const canvas = canvasId === 'primary' ? state.canvas : state.secondaryCanvas;
    const ctx = canvas.getContext('2d');
    const scale = state.zoom;

    // Draw start point
    ctx.beginPath();
    ctx.arc(state.splitStart.x * scale, state.splitStart.y * scale, 8, 0, Math.PI * 2);
    ctx.fillStyle = '#4fc3f7';
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.stroke();

    // If we have an end point (during mouse move preview), draw the line
    if (state.splitPreviewEnd) {
        ctx.beginPath();
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = '#4fc3f7';
        ctx.lineWidth = 3;
        ctx.moveTo(state.splitStart.x * scale, state.splitStart.y * scale);
        ctx.lineTo(state.splitPreviewEnd.x * scale, state.splitPreviewEnd.y * scale);
        ctx.stroke();
        ctx.setLineDash([]);
    }
}

/**
 * Cancel split mode.
 */
function cancelSplit() {
    state.isSplitting = false;
    state.splitRegion = null;
    state.splitCanvasId = null;
    state.splitStart = null;
    state.splitEnd = null;
    state.splitPreviewEnd = null;

    document.getElementById('link-status').textContent = '';
    document.getElementById('link-status').style.color = '';

    state.canvas.style.cursor = '';
    state.secondaryCanvas.style.cursor = '';

    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
}

/**
 * Perform the actual split operation.
 */
async function performSplit() {
    const region = state.splitRegion;
    const start = state.splitStart;
    const end = state.splitEnd;

    // Determine split direction (horizontal or vertical) based on line angle
    const dx = Math.abs(end.x - start.x);
    const dy = Math.abs(end.y - start.y);

    let region1, region2;

    if (dx > dy) {
        // More horizontal line - split vertically (left/right)
        const splitX = (start.x + end.x) / 2;

        region1 = {
            page_number: region.page_number,
            class_name: region.class_name,
            confidence: region.confidence,
            x: region.x,
            y: region.y,
            width: Math.round(splitX - region.x),
            height: region.height
        };

        region2 = {
            page_number: region.page_number,
            class_name: region.class_name,
            confidence: region.confidence,
            x: Math.round(splitX),
            y: region.y,
            width: Math.round(region.x + region.width - splitX),
            height: region.height
        };
    } else {
        // More vertical line - split horizontally (top/bottom)
        const splitY = (start.y + end.y) / 2;

        region1 = {
            page_number: region.page_number,
            class_name: region.class_name,
            confidence: region.confidence,
            x: region.x,
            y: region.y,
            width: region.width,
            height: Math.round(splitY - region.y)
        };

        region2 = {
            page_number: region.page_number,
            class_name: region.class_name,
            confidence: region.confidence,
            x: region.x,
            y: Math.round(splitY),
            width: region.width,
            height: Math.round(region.y + region.height - splitY)
        };
    }

    // Validate regions have positive dimensions
    if (region1.width < 10 || region1.height < 10 || region2.width < 10 || region2.height < 10) {
        alert('Split line too close to edge. Please draw a line more towards the center.');
        cancelSplit();
        return;
    }

    try {
        // Create two new regions
        const response1 = await fetch(`/api/auto-slicer/${state.bookId}/add-region`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(region1)
        });

        const response2 = await fetch(`/api/auto-slicer/${state.bookId}/add-region`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(region2)
        });

        if (!response1.ok || !response2.ok) {
            throw new Error('Failed to create split regions');
        }

        const data1 = await response1.json();
        const data2 = await response2.json();

        // Delete original region
        await fetch(`/api/auto-slicer/${state.bookId}/detected-region/${region.id}`, {
            method: 'DELETE'
        });

        // Update local state
        const canvasId = state.splitCanvasId;
        const regions = canvasId === 'primary' ? state.pageRegions : state.secondaryPageRegions;

        // Remove original region
        const idx = regions.findIndex(r => r.id === region.id);
        if (idx !== -1) regions.splice(idx, 1);
        state.allRegions = state.allRegions.filter(r => r.id !== region.id);

        // Add new regions
        const newRegion1 = { ...region1, id: data1.region_id };
        const newRegion2 = { ...region2, id: data2.region_id };
        regions.push(newRegion1, newRegion2);
        state.allRegions.push(newRegion1, newRegion2);

        // Clear selection
        clearSelection();

        // Update UI
        document.getElementById('regions-count').textContent = `${state.pageRegions.length} regions`;

        console.log(`Split region ${region.id} into regions ${data1.region_id} and ${data2.region_id}`);

    } catch (error) {
        console.error('Error splitting region:', error);
        alert('Failed to split region: ' + error.message);
    }

    cancelSplit();
}

function showContextMenu(x, y) {
    const menu = document.getElementById('context-menu');

    // First make visible but off-screen to measure actual size
    menu.style.left = '-9999px';
    menu.style.top = '-9999px';
    menu.classList.add('visible');

    // Get actual menu dimensions
    const menuRect = menu.getBoundingClientRect();
    const menuWidth = menuRect.width || 200;
    const menuHeight = menuRect.height || 500;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let posX = x;
    let posY = y;

    // Adjust if menu would go off-screen horizontally
    if (x + menuWidth > viewportWidth) {
        posX = viewportWidth - menuWidth - 10;
    }

    // Adjust if menu would go off-screen vertically
    if (y + menuHeight > viewportHeight) {
        // Try positioning above the click point
        posY = y - menuHeight;
        // If still off-screen, just position at top with some margin
        if (posY < 0) {
            posY = 10;
        }
    }

    menu.style.left = posX + 'px';
    menu.style.top = posY + 'px';
}

function hideContextMenu() {
    document.getElementById('context-menu').classList.remove('visible');
    state.contextMenuRegion = null;
    state.contextMenuCanvas = null;
}

// =============================================================================
// Change Region Boundary
// =============================================================================

async function startChangeBoundary(region, canvasId) {
    // Store info about the region being replaced
    state.changingBoundaryRegion = {
        id: region.id,
        class_name: region.class_name,
        page_number: region.page_number,
        canvasId: canvasId
    };

    // Delete the old region from database
    try {
        await fetch(`/api/auto-slicer/${state.bookId}/detected-region/${region.id}`, {
            method: 'DELETE'
        });

        // Remove from local arrays
        state.pageRegions = state.pageRegions.filter(r => r.id !== region.id);
        state.secondaryPageRegions = state.secondaryPageRegions.filter(r => r.id !== region.id);
        state.allRegions = state.allRegions.filter(r => r.id !== region.id);

        // Remove any links involving this region
        state.links = state.links.filter(l =>
            l.diagram_region_id !== region.id &&
            l.paragraph_region_id !== region.id
        );

        state.selectedRegionId = null;
        updateSelectionInfo();
        updateLinksCount();
        updateLinksSection();
        document.getElementById('regions-count').textContent = `${state.pageRegions.length} regions`;

    } catch (error) {
        console.error('Error deleting region for boundary change:', error);
        state.changingBoundaryRegion = null;
        alert('Failed to start boundary change');
        return;
    }

    // Switch to draw mode
    setMode('draw');

    // Update status to inform user with prominent message
    const className = state.changingBoundaryRegion.class_name;
    document.getElementById('link-status').textContent =
        `CLICK AND DRAG to draw new boundary for: ${className}`;
    document.getElementById('link-status').style.color = '#4fc3f7';

    // Redraw canvas
    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
    updateRegionsList();

    // Add visual indicator - flash the canvas border
    const canvas = canvasId === 'primary' ? state.canvas : state.secondaryCanvas;
    canvas.style.outline = '3px solid #4fc3f7';
    canvas.style.outlineOffset = '2px';
    setTimeout(() => {
        canvas.style.outline = '';
        canvas.style.outlineOffset = '';
    }, 2000);

    // Scroll canvas into view
    canvas.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

async function applyClassToRegion(regionId, newClass, canvasId) {
    console.log(`applyClassToRegion called: regionId=${regionId}, newClass=${newClass}, canvasId=${canvasId}`);

    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/detected-region/${regionId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ class_name: newClass })
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('API error:', response.status, errorText);
            throw new Error(`Failed to update region: ${response.status}`);
        }

        const responseData = await response.json();
        console.log('API response:', responseData);

        // Update class_name in ALL arrays that might contain this region
        // Use strict numeric comparison to avoid type mismatches
        const numericId = Number(regionId);

        // Update in allRegions first (master array)
        for (const r of state.allRegions) {
            if (Number(r.id) === numericId) {
                console.log(`Updating allRegions: ${r.class_name} -> ${newClass}`);
                r.class_name = newClass;
                break;
            }
        }

        // Rebuild page region arrays from allRegions to ensure consistency
        const currentPage = state.pages[state.currentPageIndex];
        state.pageRegions = state.allRegions.filter(r => r.page_number === currentPage);

        if (state.secondaryPageNumber) {
            state.secondaryPageRegions = state.allRegions.filter(r => r.page_number === state.secondaryPageNumber);
        }

        console.log(`Updated region ${regionId} to class ${newClass}`);

        // Force complete redraw of both canvases
        redrawCanvas('primary');
        if (state.viewMode !== 'single') {
            redrawCanvas('secondary');
        }

        // Update UI elements
        updateRegionsList();
        updateSelectionInfo();

    } catch (error) {
        console.error('Error updating region class:', error);
        alert('Failed to update class: ' + error.message);
    }
}

// =============================================================================
// Page Confirmation Functions
// =============================================================================

// Note: confirmPageClasses functionality merged into toggleReadyForExtraction()
// The "Ready for Extraction" button now also sets classesConfirmed via API

// =============================================================================
// Keyboard Shortcuts
// =============================================================================

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
            return;
        }

        switch (e.key.toLowerCase()) {
            case 's':
                setMode('select');
                break;
            case 'n':
                setMode('draw');
                break;
            case 'l':
                setMode('link');
                break;
            case 'a':
                prevPage();
                break;
            case 'd':
                nextPage();
                break;
            case 'v':
                // Toggle view mode
                const viewSelect = document.getElementById('view-mode-select');
                const modes = ['single', 'dual-prev', 'dual-next'];
                const currentIdx = modes.indexOf(viewSelect.value);
                viewSelect.value = modes[(currentIdx + 1) % modes.length];
                updateViewMode();
                break;
            case 'delete':
            case 'backspace':
                if (state.selectedRegionId) {
                    e.preventDefault();
                    deleteSelectedRegion();
                }
                break;
            case 'enter':
                if (state.selectedRegionId) {
                    e.preventDefault();
                    applyClassChange();
                }
                break;
            case 'c':
                confirmCurrentPage();
                break;
            case '?':
                toggleShortcuts();
                break;
            case 'escape':
                // Cancel any active mode
                if (state.isSplitting) {
                    cancelSplit();
                } else if (state.isLinkingToL3) {
                    cancelL3Linking();
                } else if (state.mode === 'link' && state.linkSourceRegion) {
                    // Cancel linking mode
                    state.linkSourceRegion = null;
                    setMode('select');
                } else if (state.changingBoundaryRegion) {
                    // Cancel boundary change
                    state.changingBoundaryRegion = null;
                    setMode('select');
                    redrawCanvas('primary');
                    if (state.viewMode !== 'single') redrawCanvas('secondary');
                }
                break;
            case '+':
            case '=':
                zoomIn();
                break;
            case '-':
                zoomOut();
                break;
            case 'escape':
                if (state.mode === 'link') {
                    setMode('select');  // This also calls cancelLinkMode internally
                } else {
                    state.selectedRegionId = null;
                    updateSelectionInfo();
                    redrawCanvas('primary');
                    if (state.viewMode !== 'single') redrawCanvas('secondary');
                    updateRegionsList();
                }
                break;
        }
    });
}

function toggleShortcuts() {
    document.getElementById('shortcuts-panel').classList.toggle('visible');
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const icon = document.getElementById('sidebar-toggle-icon');
    sidebar.classList.toggle('collapsed');
    icon.textContent = sidebar.classList.contains('collapsed') ? '▶' : '◀';
}

function zoomIn() {
    const select = document.getElementById('zoom-select');
    if (select.selectedIndex < select.options.length - 1) {
        select.selectedIndex++;
        updateZoom();
    }
}

function zoomOut() {
    const select = document.getElementById('zoom-select');
    if (select.selectedIndex > 0) {
        select.selectedIndex--;
        updateZoom();
    }
}

// =============================================================================
// Loading Overlay
// =============================================================================

function showLoading(message) {
    document.getElementById('loading-text').textContent = message || 'Loading...';
    document.getElementById('loading-overlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

// =============================================================================
// Advanced Tools Section
// =============================================================================

function toggleAdvancedTools() {
    const header = document.querySelector('.advanced-tools-header');
    const content = document.getElementById('advanced-tools-content');
    header.classList.toggle('expanded');
    content.classList.toggle('visible');
}

function goToAutoSlicer() {
    window.location.href = `/auto-slicer?book_id=${state.bookId}`;
}

// =============================================================================
// Reset Regions Functionality
// =============================================================================

// Track which canvas triggered the reset
let resetTargetCanvas = null;
let resetTargetPage = null;

function confirmResetRegions(canvasId) {
    // Get the page number for this canvas
    const pageNumber = canvasId === 'primary' 
        ? state.pages[state.currentPageIndex] 
        : state.secondaryPageNumber;
    
    if (!pageNumber) {
        alert('No page selected');
        return;
    }
    
    resetTargetCanvas = canvasId;
    resetTargetPage = pageNumber;
    
    // Update modal text
    document.getElementById('reset-page-name').textContent = `Page ${pageNumber}`;
    
    // Show modal
    document.getElementById('reset-regions-modal').classList.remove('hidden');
}

function closeResetModal() {
    document.getElementById('reset-regions-modal').classList.add('hidden');
    resetTargetCanvas = null;
    resetTargetPage = null;
}

async function executeResetRegions() {
    if (!resetTargetPage) {
        closeResetModal();
        return;
    }
    
    const pageNumber = resetTargetPage;
    closeResetModal();
    
    showLoading(`Resetting regions on page ${pageNumber}...`);
    
    try {
        const response = await fetch(`/api/auto-slicer/${state.bookId}/reset-page-regions/${pageNumber}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to reset regions');
        }
        
        const result = await response.json();
        
        // Reload all regions to get the new detections
        await loadRegions();
        
        hideLoading();
        
        // Show success message
        alert(`Reset complete!\n\nDeleted: ${result.deleted_count} old regions\nDetected: ${result.new_regions_count} new regions`);
        
    } catch (error) {
        hideLoading();
        console.error('Error resetting regions:', error);
        alert(`Failed to reset regions: ${error.message}`);
    }
}

// =============================================================================
// L3 Title Linking UI Functions (Phase 7)
// =============================================================================

/**
 * Load L3 titles for the current page(s) and update the L3 links section.
 * Called after loading page regions.
 */
async function loadL3TitlesForPage() {
    const currentPage = state.pages[state.currentPageIndex];
    if (!currentPage) return;

    // Get L3 titles from current page regions
    const l3TitlesOnPage = state.pageRegions.filter(r => 
        ['title_level_3', 'title_l3', 'Title L3'].includes(r.class_name)
    );

    // Also get from secondary page if in dual view
    let l3TitlesOnSecondary = [];
    if (state.viewMode !== 'single' && state.secondaryPageRegions.length > 0) {
        l3TitlesOnSecondary = state.secondaryPageRegions.filter(r => 
            ['title_level_3', 'title_l3', 'Title L3'].includes(r.class_name)
        );
    }

    // Store for dropdown population
    state.currentPageL3Titles = l3TitlesOnPage;
    state.secondaryPageL3Titles = l3TitlesOnSecondary;

    // Update the L3 links section UI
    updateL3LinksSection();
}

/**
 * Update the L3 links section in the sidebar.
 * Shows all paragraphs and their L3 title links.
 */
function updateL3LinksSection() {
    const container = document.getElementById('l3-links-list');
    const warningDiv = document.getElementById('l3-validation-warning');
    const warningText = document.getElementById('l3-warning-text');

    if (!container) return;

    container.innerHTML = '';

    // Get all paragraphs from current page(s)
    let paragraphs = state.pageRegions.filter(r => r.class_name === 'paragraph');
    if (state.viewMode !== 'single' && state.secondaryPageRegions.length > 0) {
        paragraphs = paragraphs.concat(
            state.secondaryPageRegions.filter(r => r.class_name === 'paragraph')
                .map(r => ({ ...r, _isSecondary: true }))
        );
    }

    // Sort by page then y position
    paragraphs.sort((a, b) => {
        if (a._isSecondary !== b._isSecondary) return a._isSecondary ? 1 : -1;
        return a.y - b.y;
    });

    // Count unlinked paragraphs
    let unlinkedCount = 0;

    if (paragraphs.length === 0) {
        container.innerHTML = '<div style="padding: 10px; text-align: center; color: #666; font-size: 11px;">No paragraphs on this page</div>';
        warningDiv.style.display = 'none';
        return;
    }

    // Get all L3 titles for dropdown
    const allL3Titles = [
        ...(state.currentPageL3Titles || []),
        ...(state.secondaryPageL3Titles || []).map(t => ({ ...t, _isSecondary: true }))
    ];

    paragraphs.forEach(para => {
        const isLinked = para.l3_title_id !== null && para.l3_title_id !== undefined;
        if (!isLinked) unlinkedCount++;

        // Find the linked L3 title info
        let linkedL3Title = null;
        if (isLinked) {
            linkedL3Title = allL3Titles.find(t => t.id === para.l3_title_id);
            if (!linkedL3Title) {
                // L3 title might be on a different page - just show ID
                linkedL3Title = { id: para.l3_title_id, _notOnPage: true };
            }
        }

        const item = document.createElement('div');
        item.className = 'l3-link-item' + (isLinked ? '' : ' unlinked');
        
        const pageLabel = para._isSecondary ? ` (pg ${state.secondaryPageNumber})` : '';
        const l3PageLabel = linkedL3Title && linkedL3Title._isSecondary ? ` (pg ${state.secondaryPageNumber})` : '';

        // Create dropdown for L3 title selection
        const dropdownId = `l3-dropdown-${para.id}`;
        let dropdownOptions = '<option value="">-- None --</option>';
        allL3Titles.forEach(l3 => {
            const selected = para.l3_title_id === l3.id ? 'selected' : '';
            const l3Label = l3._isSecondary ? ` (pg ${state.secondaryPageNumber})` : '';
            // Truncate long titles
            const titleText = (l3.ocr_text || `L3 #${l3.id}`).substring(0, 30);
            dropdownOptions += `<option value="${l3.id}" ${selected}>${titleText}${l3Label}</option>`;
        });

        item.innerHTML = `
            <div class="l3-link-info">
                <span class="l3-link-region">Para #${para.id}${pageLabel}</span>
                <span class="l3-link-target ${isLinked ? '' : 'none'}">
                    ${isLinked ? `→ L3 #${para.l3_title_id}${l3PageLabel}` : '⚠ Not linked'}
                </span>
            </div>
            <select class="l3-link-dropdown" id="${dropdownId}" onchange="changeL3Link(${para.id}, this.value, ${para._isSecondary || false})">
                ${dropdownOptions}
            </select>
        `;

        container.appendChild(item);
    });

    // Show/hide validation warning
    if (unlinkedCount > 0) {
        warningDiv.style.display = 'flex';
        warningText.textContent = `${unlinkedCount} paragraph(s) not linked to L3 titles`;
        
        // Highlight unlinked paragraphs on canvas
        highlightUnlinkedParagraphs(paragraphs.filter(p => !p.l3_title_id));
    } else {
        warningDiv.style.display = 'none';
        clearOrphanHighlight();
    }
}

/**
 * Highlight unlinked paragraphs on the canvas.
 */
function highlightUnlinkedParagraphs(unlinkedParagraphs) {
    state.orphanHighlight = new Set(unlinkedParagraphs.map(p => p.id));
    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
}

/**
 * Clear orphan highlight.
 */
function clearOrphanHighlight() {
    state.orphanHighlight = null;
    redrawCanvas('primary');
    if (state.viewMode !== 'single') redrawCanvas('secondary');
}

/**
 * Change the L3 title link for a paragraph.
 * @param {number} paragraphId - The paragraph region ID
 * @param {string} l3TitleId - The L3 title region ID (or empty string to unlink)
 * @param {boolean} isSecondary - Whether the paragraph is on the secondary canvas
 */
async function changeL3Link(paragraphId, l3TitleId, isSecondary) {
    const l3Id = l3TitleId ? parseInt(l3TitleId) : null;

    try {
        if (l3Id) {
            // Link to L3 title using the API
            const response = await fetch(`/api/books/${state.bookId}/paragraph-l3-link`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    paragraph_region_id: paragraphId,
                    l3_title_id: l3Id
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update L3 link');
            }
        } else {
            // Unlink - set l3_title_id to null
            const response = await fetch(`/api/auto-slicer/${state.bookId}/detected-region/${paragraphId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ l3_title_id: null })
            });

            if (!response.ok) {
                throw new Error('Failed to unlink paragraph');
            }
        }

        // Update local state
        const regions = isSecondary ? state.secondaryPageRegions : state.pageRegions;
        const region = regions.find(r => r.id === paragraphId);
        if (region) {
            region.l3_title_id = l3Id;
        }

        // Also update in allRegions
        const allRegion = state.allRegions.find(r => r.id === paragraphId);
        if (allRegion) {
            allRegion.l3_title_id = l3Id;
        }

        // Refresh UI
        updateL3LinksSection();
        redrawCanvas('primary');
        if (state.viewMode !== 'single') redrawCanvas('secondary');

        console.log(`Updated paragraph ${paragraphId} L3 link to ${l3Id}`);

    } catch (error) {
        console.error('Error changing L3 link:', error);
        alert('Failed to update L3 link: ' + error.message);
        // Refresh to restore correct state
        updateL3LinksSection();
    }
}

/**
 * Auto-link all paragraphs on current page(s) to nearest L3 title above.
 * Uses the API endpoint for auto-linking.
 */
async function autoLinkParagraphsToL3() {
    const currentPage = state.pages[state.currentPageIndex];
    if (!currentPage) return;

    // Build page list
    let pageNumbers = [currentPage];
    if (state.viewMode !== 'single' && state.secondaryPageNumber) {
        pageNumbers.push(state.secondaryPageNumber);
    }

    showLoading('Auto-linking paragraphs to L3 titles...');

    try {
        const response = await fetch(`/api/books/${state.bookId}/auto-link-paragraphs?page_numbers=${pageNumbers.join(',')}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to auto-link paragraphs');
        }

        const result = await response.json();

        // Reload regions to get updated l3_title_id values
        await loadRegions();

        hideLoading();

        // Show result
        if (result.linked_count > 0) {
            alert(`Auto-linked ${result.linked_count} paragraph(s) to L3 titles`);
        } else if (result.skipped_pages > 0) {
            alert(`No paragraphs linked. ${result.skipped_pages} page(s) have no L3 titles.`);
        } else {
            alert('All paragraphs were already linked or no paragraphs found.');
        }

    } catch (error) {
        hideLoading();
        console.error('Error auto-linking paragraphs:', error);
        alert('Failed to auto-link paragraphs: ' + error.message);
    }
}

/**
 * Validate L3 links for current page(s).
 * Returns validation result with unlinked paragraphs.
 */
async function validateL3Links() {
    const currentPage = state.pages[state.currentPageIndex];
    if (!currentPage) return { valid: true };

    // Build page list
    let pageNumbers = [currentPage];
    if (state.viewMode !== 'single' && state.secondaryPageNumber) {
        pageNumbers.push(state.secondaryPageNumber);
    }

    try {
        const response = await fetch(`/api/books/${state.bookId}/validate-l3-links?page_numbers=${pageNumbers.join(',')}`);
        if (!response.ok) {
            console.error('Failed to validate L3 links');
            return { valid: true }; // Assume valid on error
        }

        return await response.json();

    } catch (error) {
        console.error('Error validating L3 links:', error);
        return { valid: true };
    }
}

// =============================================================================
// Override loadCurrentPage to include L3 title loading
// =============================================================================

// Store original loadCurrentPage function
const _originalLoadCurrentPage = loadCurrentPage;

// Override to add L3 title loading
loadCurrentPage = async function() {
    await _originalLoadCurrentPage();
    await loadL3TitlesForPage();
};
