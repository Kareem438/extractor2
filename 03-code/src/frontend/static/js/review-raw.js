/**
 * Review Raw Data JavaScript
 * Displays book pages with associated paragraphs and diagrams
 */

// State
let currentBookId = null;
let currentStartPage = 1;
let totalPages = 0;
let books = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Review Raw loaded');
    loadBooks();
    setupEventListeners();
});

// Get URL parameter by name
function getUrlParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

// Setup event listeners
function setupEventListeners() {
    const bookSelect = document.getElementById('book-select');
    const pageInput = document.getElementById('page-input');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const loadBtn = document.getElementById('load-btn');

    bookSelect.addEventListener('change', (e) => {
        currentBookId = parseInt(e.target.value);
        if (currentBookId) {
            const book = books.find(b => b.book_id === currentBookId);
            if (book) {
                totalPages = book.total_pages;
                currentStartPage = 1;
                pageInput.value = 1;
                pageInput.max = totalPages;
                updatePageInfo();
                loadPages();
            }
            loadBtn.disabled = false;
            prevBtn.disabled = false;
            nextBtn.disabled = false;
        } else {
            loadBtn.disabled = true;
            prevBtn.disabled = true;
            nextBtn.disabled = true;
        }
    });

    pageInput.addEventListener('change', (e) => {
        let page = parseInt(e.target.value);
        if (page < 1) page = 1;
        if (page > totalPages) page = totalPages;
        currentStartPage = page;
        e.target.value = page;
        updatePageInfo();
    });

    prevBtn.addEventListener('click', () => {
        if (currentStartPage > 2) {
            currentStartPage -= 2;
        } else {
            currentStartPage = 1;
        }
        pageInput.value = currentStartPage;
        updatePageInfo();
        loadPages();
    });

    nextBtn.addEventListener('click', () => {
        if (currentStartPage + 2 <= totalPages) {
            currentStartPage += 2;
        }
        pageInput.value = currentStartPage;
        updatePageInfo();
        loadPages();
    });

    loadBtn.addEventListener('click', () => {
        currentStartPage = parseInt(pageInput.value);
        loadPages();
    });
}

// Load books list
async function loadBooks() {
    try {
        const response = await fetch('/api/books?limit=100');
        const data = await response.json();
        books = data.books || [];

        const select = document.getElementById('book-select');
        books.forEach(book => {
            const option = document.createElement('option');
            option.value = book.book_id;
            option.textContent = `${book.book_id}: ${book.book_name} (${book.total_pages} pages)`;
            select.appendChild(option);
        });

        // Check for book_id in URL
        const bookIdParam = getUrlParameter('book_id');
        if (bookIdParam) {
            select.value = bookIdParam;
            select.dispatchEvent(new Event('change'));
        }
    } catch (error) {
        console.error('Error loading books:', error);
    }
}

// Update page info display
function updatePageInfo() {
    const page2 = Math.min(currentStartPage + 1, totalPages);
    document.getElementById('current-pages').textContent =
        currentStartPage === page2 ? currentStartPage : `${currentStartPage}-${page2}`;
    document.getElementById('total-pages').textContent = totalPages;

    // Update button states
    document.getElementById('prev-btn').disabled = currentStartPage <= 1;
    document.getElementById('next-btn').disabled = currentStartPage + 1 >= totalPages;
}

// Load pages and their clips
async function loadPages() {
    if (!currentBookId) return;

    const pageRowsContainer = document.getElementById('page-rows-container');
    const loadingIndicator = document.getElementById('loading-indicator');

    // Show loading state
    pageRowsContainer.innerHTML = `
        <div class="loading" id="loading-indicator">
            <div class="loading-spinner"></div>
            <p>Loading pages...</p>
        </div>
    `;

    // Hide stats bar while loading
    document.getElementById('stats-bar').style.display = 'none';

    try {
        // Load two pages
        const page1 = currentStartPage;
        const page2 = Math.min(currentStartPage + 1, totalPages);

        const [data1, data2, clipsData] = await Promise.all([
            fetchPageData(page1),
            page2 !== page1 ? fetchPageData(page2) : null,
            fetchClipsForPages(page1, page2)
        ]);

        const paragraphs = clipsData.paragraphs || [];
        const diagrams = clipsData.diagrams || [];

        // Clear container
        pageRowsContainer.innerHTML = '';

        // Create page row for page 1
        if (data1) {
            const pageParas1 = paragraphs.filter(p => p.page_number === page1);
            const pageDiags1 = diagrams.filter(d => d.page_number === page1);
            pageRowsContainer.appendChild(createPageRow(data1, page1, pageParas1, pageDiags1));
        }

        // Create page row for page 2
        if (data2 && page2 !== page1) {
            const pageParas2 = paragraphs.filter(p => p.page_number === page2);
            const pageDiags2 = diagrams.filter(d => d.page_number === page2);
            pageRowsContainer.appendChild(createPageRow(data2, page2, pageParas2, pageDiags2));
        }

        // Draw overlays on page images (with a small delay to ensure images are loaded)
        setTimeout(() => {
            drawClipOverlays(page1, paragraphs, diagrams);
            if (page2 !== page1) {
                drawClipOverlays(page2, paragraphs, diagrams);
            }
        }, 100);

        // Update stats
        updateStats(page1, page2, clipsData);

    } catch (error) {
        console.error('Error loading pages:', error);
        pageRowsContainer.innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Pages</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Fetch single page data
async function fetchPageData(pageNumber) {
    const response = await fetch(`/api/review-raw/${currentBookId}/page/${pageNumber}`);
    if (!response.ok) {
        throw new Error(`Failed to load page ${pageNumber}`);
    }
    return response.json();
}

// Fetch clips for the given pages
async function fetchClipsForPages(page1, page2) {
    const response = await fetch(`/api/review-raw/${currentBookId}/clips?page_start=${page1}&page_end=${page2}`);
    if (!response.ok) {
        throw new Error('Failed to load clips');
    }
    return response.json();
}

// Store page data for overlay drawing
let pageDataCache = {};

// Create page card element
function createPageCard(data, pageNumber) {
    const card = document.createElement('div');
    card.className = 'page-card';
    card.dataset.pageNumber = pageNumber;

    // Cache the page dimensions for scaling
    pageDataCache[pageNumber] = {
        naturalWidth: data.image_width || 0,
        naturalHeight: data.image_height || 0
    };

    let imageHtml = '';
    if (data.image_base64) {
        const imageSrc = `data:image/${data.image_format || 'png'};base64,${data.image_base64}`;
        imageHtml = `
            <div class="page-image-wrapper">
                <img class="page-image" id="page-image-${pageNumber}" src="${imageSrc}" alt="Page ${pageNumber}">
                <canvas class="page-overlay-canvas" id="page-canvas-${pageNumber}"></canvas>
            </div>
        `;
    } else {
        imageHtml = `
            <div class="empty-state">
                <h3>No Image</h3>
                <p>Page image not available</p>
            </div>
        `;
    }

    card.innerHTML = `
        <div class="page-card-header">
            <span>Page ${pageNumber}</span>
            <span class="badge badge-page">${data.image_width || 0} x ${data.image_height || 0}</span>
        </div>
        <div class="page-card-body">
            <div class="page-image-container">
                ${imageHtml}
            </div>
        </div>
    `;

    return card;
}

// Create a page row with page on left and clips on right
function createPageRow(pageData, pageNumber, paragraphs, diagrams) {
    const row = document.createElement('div');
    row.className = 'page-row';

    // Left column: Page image
    const pageColumn = document.createElement('div');
    pageColumn.className = 'page-column';
    pageColumn.appendChild(createPageCard(pageData, pageNumber));

    // Right column: Clips
    const clipsColumn = document.createElement('div');
    clipsColumn.className = 'clips-column';

    // Paragraphs section
    const parasSection = document.createElement('div');
    parasSection.className = 'mini-clips-section';
    parasSection.innerHTML = `
        <div class="mini-clips-header paragraphs">
            <span>Paragraphs</span>
            <span>${paragraphs.length} items</span>
        </div>
        <div class="mini-clips-grid" id="mini-paras-${pageNumber}"></div>
    `;
    clipsColumn.appendChild(parasSection);

    // Add paragraph clips
    const parasGrid = parasSection.querySelector('.mini-clips-grid');
    if (paragraphs.length > 0) {
        paragraphs.forEach((clip, index) => {
            parasGrid.appendChild(createMiniClipCard(clip, index + 1, 'paragraph'));
        });
    } else {
        parasGrid.innerHTML = '<div class="empty-state" style="padding: 15px; text-align: center; color: #999;">No paragraphs on this page</div>';
    }

    // Diagrams section
    const diagsSection = document.createElement('div');
    diagsSection.className = 'mini-clips-section';
    diagsSection.innerHTML = `
        <div class="mini-clips-header diagrams">
            <span>Diagrams</span>
            <span>${diagrams.length} items</span>
        </div>
        <div class="mini-clips-grid" id="mini-diags-${pageNumber}"></div>
    `;
    clipsColumn.appendChild(diagsSection);

    // Add diagram clips
    const diagsGrid = diagsSection.querySelector('.mini-clips-grid');
    if (diagrams.length > 0) {
        diagrams.forEach((clip, index) => {
            diagsGrid.appendChild(createMiniClipCard(clip, index + 1, 'diagram'));
        });
    } else {
        diagsGrid.innerHTML = '<div class="empty-state" style="padding: 15px; text-align: center; color: #999;">No diagrams on this page</div>';
    }

    row.appendChild(pageColumn);
    row.appendChild(clipsColumn);

    return row;
}

// Create a mini clip card for the side-by-side layout
function createMiniClipCard(clip, number, type) {
    const card = document.createElement('div');
    card.className = `mini-clip-card ${type}`;

    let imageHtml = '';
    if (clip.image_base64) {
        const imageSrc = `data:image/${clip.image_format || 'png'};base64,${clip.image_base64}`;
        imageHtml = `<img class="mini-clip-image" src="${imageSrc}" alt="${type} ${number}">`;
    } else {
        imageHtml = `<div style="padding: 30px; color: #999; font-size: 12px;">No image</div>`;
    }

    // Prepare text preview
    let textPreview = '';
    const text = clip.extracted_text || clip.description || '';
    if (text) {
        const shortText = text.length > 150 ? text.substring(0, 150) + '...' : text;
        textPreview = `<div class="mini-clip-text">${escapeHtml(shortText)}</div>`;
    }

    // Level badge
    let levelBadge = '';
    if (clip.selected_level_number) {
        levelBadge = `<span style="background: #e0e0e0; padding: 2px 6px; border-radius: 3px; font-size: 10px;">L${clip.selected_level_number}</span>`;
    }

    const prefix = type === 'paragraph' ? 'P' : 'D';
    const typeName = type === 'paragraph' ? 'Paragraph' : 'Diagram';

    card.innerHTML = `
        <div class="mini-clip-header">
            <span>${typeName} #${number}</span>
            ${levelBadge}
        </div>
        <div class="mini-clip-image-container">
            ${imageHtml}
        </div>
        <div class="mini-clip-info">
            <div class="mini-clip-meta">
                Position: (${clip.selection_x}, ${clip.selection_y}) | Size: ${clip.selection_width}×${clip.selection_height}px
            </div>
            ${textPreview}
        </div>
        <div class="mini-clip-actions">
            <button class="btn-edit-clip" onclick="openEditModal('${type}', ${clip.id}, ${clip.page_number})">
                ✏️ Edit
            </button>
        </div>
    `;

    return card;
}

// Draw clip overlays on a page canvas
function drawClipOverlays(pageNumber, paragraphs, diagrams) {
    const img = document.getElementById(`page-image-${pageNumber}`);
    const canvas = document.getElementById(`page-canvas-${pageNumber}`);

    if (!img || !canvas) {
        console.log(`Canvas or image not found for page ${pageNumber}`);
        return;
    }

    // Wait for image to load before drawing
    const drawOverlays = () => {
        const displayedWidth = img.clientWidth;
        const displayedHeight = img.clientHeight;
        const pageData = pageDataCache[pageNumber];

        if (!pageData || !pageData.naturalWidth || !pageData.naturalHeight) {
            console.log(`No page data for page ${pageNumber}`);
            return;
        }

        // Set canvas size to match displayed image
        canvas.width = displayedWidth;
        canvas.height = displayedHeight;
        canvas.style.width = displayedWidth + 'px';
        canvas.style.height = displayedHeight + 'px';

        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Calculate scale factors
        const scaleX = displayedWidth / pageData.naturalWidth;
        const scaleY = displayedHeight / pageData.naturalHeight;

        // Colors matching the UI
        const paragraphColor = '#9C27B0'; // Purple
        const diagramColor = '#FF6F00';   // Orange

        // Filter clips for this page and draw them
        const pageParas = paragraphs.filter(p => p.page_number === pageNumber);
        const pageDiags = diagrams.filter(d => d.page_number === pageNumber);

        // Draw paragraphs
        pageParas.forEach((clip, index) => {
            drawClipBox(ctx, clip, index + 1, 'P', paragraphColor, scaleX, scaleY);
        });

        // Draw diagrams
        pageDiags.forEach((clip, index) => {
            drawClipBox(ctx, clip, index + 1, 'D', diagramColor, scaleX, scaleY);
        });
    };

    // If image already loaded, draw immediately; otherwise wait
    if (img.complete) {
        drawOverlays();
    } else {
        img.onload = drawOverlays;
    }
}

// Draw a single clip bounding box with label
function drawClipBox(ctx, clip, number, prefix, color, scaleX, scaleY) {
    const x = clip.selection_x * scaleX;
    const y = clip.selection_y * scaleY;
    const width = clip.selection_width * scaleX;
    const height = clip.selection_height * scaleY;

    // Draw bounding box
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, width, height);

    // Prepare label text
    let labelText = `${prefix}${number}`;
    if (clip.selected_level_number) {
        labelText += ` L${clip.selected_level_number}`;
    }

    // Draw label background
    ctx.font = 'bold 12px Arial';
    const textMetrics = ctx.measureText(labelText);
    const labelPadding = 4;
    const labelHeight = 16;
    const labelWidth = textMetrics.width + labelPadding * 2;

    // Position label at top-left, outside the box
    const labelX = x;
    const labelY = y - labelHeight - 2;

    // Draw label background
    ctx.fillStyle = color;
    ctx.fillRect(labelX, labelY, labelWidth, labelHeight);

    // Draw label text
    ctx.fillStyle = 'white';
    ctx.textBaseline = 'middle';
    ctx.fillText(labelText, labelX + labelPadding, labelY + labelHeight / 2);
}

// Render clips (paragraphs and diagrams)
function renderClips(clipsData) {
    const paragraphsSection = document.getElementById('paragraphs-section');
    const diagramsSection = document.getElementById('diagrams-section');
    const paragraphsGrid = document.getElementById('paragraphs-grid');
    const diagramsGrid = document.getElementById('diagrams-grid');

    // Clear existing clips
    paragraphsGrid.innerHTML = '';
    diagramsGrid.innerHTML = '';

    // Render paragraphs
    if (clipsData.paragraphs && clipsData.paragraphs.length > 0) {
        paragraphsSection.style.display = 'block';
        document.getElementById('paragraphs-count').textContent = `${clipsData.paragraphs.length} items`;

        clipsData.paragraphs.forEach(clip => {
            paragraphsGrid.appendChild(createClipCard(clip, 'paragraph'));
        });
    } else {
        paragraphsSection.style.display = 'block';
        document.getElementById('paragraphs-count').textContent = '0 items';
        paragraphsGrid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <h3>No Paragraphs</h3>
                <p>No paragraph clips found for these pages.</p>
            </div>
        `;
    }

    // Render diagrams
    if (clipsData.diagrams && clipsData.diagrams.length > 0) {
        diagramsSection.style.display = 'block';
        document.getElementById('diagrams-count').textContent = `${clipsData.diagrams.length} items`;

        clipsData.diagrams.forEach(clip => {
            diagramsGrid.appendChild(createClipCard(clip, 'diagram'));
        });
    } else {
        diagramsSection.style.display = 'block';
        document.getElementById('diagrams-count').textContent = '0 items';
        diagramsGrid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <h3>No Diagrams</h3>
                <p>No diagram clips found for these pages.</p>
            </div>
        `;
    }
}

// Create clip card element
function createClipCard(clip, type) {
    const card = document.createElement('div');
    card.className = `clip-card ${type}`;

    let imageHtml = '';
    if (clip.image_base64) {
        const imageSrc = `data:image/${clip.image_format || 'png'};base64,${clip.image_base64}`;
        imageHtml = `<img class="clip-image" src="${imageSrc}" alt="${type} ${clip.id}">`;
    } else {
        imageHtml = `<div class="empty-state" style="padding: 20px;"><p>No image</p></div>`;
    }

    // Prepare text preview
    let textPreview = '';
    if (clip.extracted_text) {
        const text = clip.extracted_text.length > 200
            ? clip.extracted_text.substring(0, 200) + '...'
            : clip.extracted_text;
        textPreview = `<div class="clip-text-preview">${escapeHtml(text)}</div>`;
    } else if (clip.description) {
        const text = clip.description.length > 200
            ? clip.description.substring(0, 200) + '...'
            : clip.description;
        textPreview = `<div class="clip-text-preview">${escapeHtml(text)}</div>`;
    }

    // Level badge
    let levelBadge = '';
    if (clip.selected_level_number) {
        levelBadge = `<span class="badge badge-level">L${clip.selected_level_number}</span>`;
    }

    card.innerHTML = `
        <div class="clip-card-header">
            <span>${type === 'paragraph' ? 'Paragraph' : 'Diagram'} #${clip.id}</span>
            <div>
                <span class="badge badge-page">Page ${clip.page_number}</span>
                ${levelBadge}
            </div>
        </div>
        <div class="clip-image-container">
            ${imageHtml}
        </div>
        <div class="clip-details">
            <div class="clip-details-row">
                <span class="clip-details-label">Position:</span>
                <span class="clip-details-value">(${clip.selection_x}, ${clip.selection_y})</span>
            </div>
            <div class="clip-details-row">
                <span class="clip-details-label">Size:</span>
                <span class="clip-details-value">${clip.selection_width} x ${clip.selection_height}</span>
            </div>
            ${clip.ocr_confidence ? `
            <div class="clip-details-row">
                <span class="clip-details-label">Confidence:</span>
                <span class="clip-details-value">${(clip.ocr_confidence * 100).toFixed(1)}%</span>
            </div>
            ` : ''}
            ${clip.selected_level_text ? `
            <div class="clip-details-row">
                <span class="clip-details-label">Level:</span>
                <span class="clip-details-value">${escapeHtml(clip.selected_level_text)}</span>
            </div>
            ` : ''}
            ${textPreview}
        </div>
    `;

    return card;
}

// Update stats bar
function updateStats(page1, page2, clipsData) {
    const statsBar = document.getElementById('stats-bar');
    statsBar.style.display = 'flex';

    const pagesShown = page1 === page2 ? 1 : 2;
    document.getElementById('stat-pages').textContent = pagesShown;
    document.getElementById('stat-paragraphs').textContent = clipsData.paragraphs ? clipsData.paragraphs.length : 0;
    document.getElementById('stat-diagrams').textContent = clipsData.diagrams ? clipsData.diagrams.length : 0;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Open edit modal with iframe
function openEditModal(type, clipId, pageNumber) {
    const modal = document.getElementById('edit-modal');
    const iframe = document.getElementById('modal-iframe');
    const title = document.getElementById('modal-title');

    // Set modal title
    const typeName = type === 'paragraph' ? 'Paragraph' : 'Diagram';
    title.textContent = `Edit ${typeName} #${clipId}`;

    // Build the URL for the edit page
    const editPage = type === 'paragraph' ? 'edit-paragraphs' : 'edit-diagrams';
    const url = `/${editPage}?book_id=${currentBookId}&page=${pageNumber}&scroll_to=${clipId}&modal=true`;

    // Set iframe source and show modal
    iframe.src = url;
    modal.classList.add('visible');

    // Prevent body scrolling while modal is open
    document.body.style.overflow = 'hidden';

    console.log(`Opening ${editPage} for clip ${clipId} on page ${pageNumber}`);
}

// Close edit modal
function closeEditModal(shouldRefresh = false) {
    const modal = document.getElementById('edit-modal');
    const iframe = document.getElementById('modal-iframe');

    // Hide modal
    modal.classList.remove('visible');

    // Clear iframe source
    iframe.src = 'about:blank';

    // Restore body scrolling
    document.body.style.overflow = '';

    // Refresh the page data if requested
    if (shouldRefresh) {
        console.log('Refreshing page data after modal close');
        loadPages();
    }
}

// Listen for messages from iframe (for close/save events)
window.addEventListener('message', function(event) {
    // Check if the message is from our iframe
    if (event.data && event.data.type === 'closeEditModal') {
        closeEditModal(event.data.refresh || false);
    }
});

// Close modal when clicking on overlay background
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('edit-modal');
    if (modal) {
        modal.addEventListener('click', function(event) {
            // Only close if clicking directly on the overlay, not the container
            if (event.target === modal) {
                closeEditModal(false);
            }
        });
    }
});

// Close modal with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('edit-modal');
        if (modal && modal.classList.contains('visible')) {
            closeEditModal(false);
        }
    }
});
