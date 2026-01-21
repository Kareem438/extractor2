/**
 * Edit Diagrams JavaScript
 * Manage and edit diagram image clips
 */

// State
let currentBookId = null;
let books = [];
let diagramClips = [];
let returnPageNumber = null; // Page number to return to in verify-pages

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Edit Diagrams page loaded');
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
    const backBtn = document.getElementById('back-to-verify-btn');

    bookSelect.addEventListener('change', (e) => {
        currentBookId = parseInt(e.target.value);
        if (currentBookId) {
            loadDiagrams();
        } else {
            showEmptyState();
        }
    });

    // Back to Verify Pages button
    backBtn.addEventListener('click', () => {
        if (currentBookId) {
            let url = `/verify-pages?book_id=${currentBookId}`;

            // If we know which page to return to, include it
            if (returnPageNumber) {
                url += `&page=${returnPageNumber}`;
            }

            window.location.href = url;
        }
    });
}

// Load books list
async function loadBooks() {
    console.log('Loading books...');
    try {
        const response = await fetch('/api/books?limit=100');
        const data = await response.json();

        books = data.books || [];
        console.log('Number of books:', books.length);

        const bookSelect = document.getElementById('book-select');

        if (books.length === 0) {
            bookSelect.innerHTML = '<option value="">No books available</option>';
            return;
        }

        bookSelect.innerHTML = '<option value="">Select a book...</option>' +
            books.map(book =>
                `<option value="${book.book_id}">${book.book_name} (${book.total_pages} pages)</option>`
            ).join('');

        // Check if book_id was passed in URL
        const bookIdParam = getUrlParameter('book_id');
        const scrollToParam = getUrlParameter('scroll_to');

        if (bookIdParam) {
            const bookId = parseInt(bookIdParam);
            const book = books.find(b => b.book_id === bookId);

            if (book) {
                bookSelect.value = bookId;
                currentBookId = bookId;
                await loadDiagrams();

                // Scroll to specific clip if scroll_to parameter is provided
                if (scrollToParam) {
                    const scrollToClipId = parseInt(scrollToParam);
                    scrollToClip(scrollToClipId);
                }
            }
        }

    } catch (error) {
        console.error('Error loading books:', error);
    }
}

// Load diagram clips for selected book
async function loadDiagrams() {
    if (!currentBookId) return;

    showLoading();

    try {
        // Fetch all diagram clips for this book (no limit, no page filter)
        const response = await fetch(`/api/all-image-clips/${currentBookId}?clip_type=diagram`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        diagramClips = data.clips || [];

        console.log('Loaded diagram clips:', diagramClips.length);

        // Determine return page number: prioritize URL page param, then scroll_to clip, then first clip
        const pageParam = getUrlParameter('page');
        if (pageParam) {
            returnPageNumber = parseInt(pageParam);
            console.log('Using page from URL parameter:', returnPageNumber);
        } else {
            const scrollToParam = getUrlParameter('scroll_to');
            if (scrollToParam) {
                const scrollToClipId = parseInt(scrollToParam);
                const scrollToClip = diagramClips.find(c => c.id === scrollToClipId);
                if (scrollToClip) {
                    returnPageNumber = scrollToClip.page_number;
                    console.log('Using page from scroll_to clip:', returnPageNumber);
                }
            }

            // If no page or scroll_to, use first clip's page
            if (!returnPageNumber && diagramClips.length > 0) {
                returnPageNumber = diagramClips[0].page_number;
                console.log('Using page from first clip:', returnPageNumber);
            }
        }

        // Show back button if we have a book selected
        const backBtn = document.getElementById('back-to-verify-btn');
        if (currentBookId && backBtn) {
            backBtn.style.display = 'inline-block';
        }

        // Display the clips
        displayDiagrams();

    } catch (error) {
        console.error('Error loading diagrams:', error);
        showError(`Failed to load diagrams: ${error.message}`);
    }
}

// Display diagrams with merge buttons
function displayDiagrams() {
    const content = document.getElementById('diagrams-content');

    if (!diagramClips || diagramClips.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <h2>📊 No Diagrams Found</h2>
                <p>This book has no diagram clips yet. Use the Verify Pages tool to create clips.</p>
            </div>
        `;
        return;
    }

    let html = '<div class="diagrams-grid">';

    diagramClips.forEach((clip, index) => {
        // Add diagram item
        html += createDiagramHtml(clip, index);

        // Add merge button between items (not after the last one)
        if (index < diagramClips.length - 1) {
            html += createMergeButtonHtml(index);
        }
    });

    html += '</div>';

    content.innerHTML = html;

    // Load parent paragraph data for diagrams with links
    loadAllParentParagraphs();
}

// Create diagram HTML
function createDiagramHtml(clip, index) {
    const imageSrc = `data:image/${clip.image_format};base64,${clip.image_data_base64}`;
    const timestamp = new Date(clip.created_at).toLocaleString();
    const statusClass = `status-${clip.approval_status || 'new'}`;

    return `
        <div class="diagram-item" id="diagram-${index}" data-clip-id="${clip.id}">
            <div class="diagram-thumbnail">
                <img src="${imageSrc}" alt="Diagram ${clip.id}" />
                <button
                    class="btn-load-titles"
                    onclick="loadTitlesToVerifyPages(${index})"
                    style="margin-top: 8px; width: 100%; padding: 8px 12px; background: #FF9800; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: bold;"
                    title="Load this diagram's level titles to verify-pages"
                >
                    📋 Load Titles
                </button>
            </div>
            <div class="diagram-info">
                <div class="diagram-meta">
                    <div class="meta-item">
                        <span class="meta-label">ID:</span>
                        <span class="meta-value">#${clip.id}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Page:</span>
                        <span class="meta-value">${clip.page_number}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Status:</span>
                        <span class="status-badge ${statusClass}">${clip.approval_status || 'new'}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Created:</span>
                        <span class="meta-value">${timestamp}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Size:</span>
                        <span class="meta-value">${clip.image_width} × ${clip.image_height} px</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Position:</span>
                        <span class="meta-value">(${clip.selection_x}, ${clip.selection_y})</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Display Order:</span>
                        <input
                            type="number"
                            class="display-order-input"
                            value="${clip.display_order}"
                            data-clip-id="${clip.id}"
                            data-index="${index}"
                            style="width: 80px; padding: 4px; border: 1px solid #ddd; border-radius: 4px;"
                        />
                        <button
                            class="btn-save-order"
                            onclick="saveDisplayOrder(${index})"
                            style="margin-left: 8px; padding: 4px 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;"
                        >
                            💾 Save
                        </button>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Enabled:</span>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <input
                                type="checkbox"
                                class="enabled-checkbox"
                                ${clip.is_enabled ? 'checked' : ''}
                                data-clip-id="${clip.id}"
                                data-index="${index}"
                                onchange="updateEnabled(${index}, this.checked)"
                                style="width: 18px; height: 18px; cursor: pointer;"
                            />
                            <span style="color: ${clip.is_enabled ? '#4CAF50' : '#f44336'}; font-weight: bold;">
                                ${clip.is_enabled ? '✓ Enabled' : '✗ Disabled'}
                            </span>
                        </div>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Level:</span>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <select
                                class="level-select"
                                data-clip-id="${clip.id}"
                                data-index="${index}"
                                style="padding: 4px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; cursor: pointer;"
                            >
                                <option value="Level 1" ${(clip.level || 'Level 1') === 'Level 1' ? 'selected' : ''}>Level 1</option>
                                <option value="Level 2" ${clip.level === 'Level 2' ? 'selected' : ''}>Level 2</option>
                                <option value="Level 3" ${clip.level === 'Level 3' ? 'selected' : ''}>Level 3</option>
                                <option value="Level 4" ${clip.level === 'Level 4' ? 'selected' : ''}>Level 4</option>
                                <option value="Level 5" ${clip.level === 'Level 5' ? 'selected' : ''}>Level 5</option>
                            </select>
                            <button
                                class="btn-save-level"
                                onclick="saveLevel(${index})"
                                style="padding: 4px 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;"
                            >
                                💾 Save
                            </button>
                        </div>
                    </div>
                    ${clip.description ? `
                    <div class="meta-item" style="grid-column: 1 / -1;">
                        <span class="meta-label">Description:</span>
                        <span class="meta-value">${escapeHtml(clip.description)}</span>
                    </div>
                    ` : ''}
                    ${clip.user_notes ? `
                    <div class="meta-item" style="grid-column: 1 / -1;">
                        <span class="meta-label">Notes:</span>
                        <span class="meta-value">${escapeHtml(clip.user_notes)}</span>
                    </div>
                    ` : ''}
                </div>
                <div class="diagram-actions">
                    <button class="btn-action btn-delete" onclick="deleteDiagram(${index})">
                        🗑️ Delete
                    </button>
                </div>

                <!-- Parent Paragraph Section -->
                <div class="parent-paragraph-section">
                    <div class="parent-paragraph-header">
                        🔗 Parent Paragraph (attr17)
                    </div>
                    <div class="parent-paragraph-content" id="parent-paragraph-${clip.id}">
                        ${clip.attr17_value ? `
                            <span style="font-size: 12px; color: #666;">Loading parent...</span>
                        ` : `
                            <span class="parent-paragraph-empty">Not linked to any paragraph</span>
                            <button class="btn-link-paragraph" onclick="openParagraphPicker(${clip.id})">
                                ➕ Link to Paragraph
                            </button>
                        `}
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Create merge button HTML
function createMergeButtonHtml(topIndex) {
    return `
        <div class="merge-button-container">
            <button class="btn-merge" onclick="mergeClips(${topIndex}, ${topIndex + 1})">
                ⬇️ Merge ⬇️
            </button>
        </div>
    `;
}

// Update clip status
async function updateStatus(index, newStatus) {
    const clip = diagramClips[index];
    if (!clip) return;

    try {
        const response = await fetch(`/api/update-clip-status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: currentBookId,
                clip_type: 'diagram',
                clip_id: clip.id,
                approval_status: newStatus
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to update status`);
        }

        console.log(`Updated clip ${clip.id} to ${newStatus}`);

        // Reload diagrams to reflect new status
        await loadDiagrams();

    } catch (error) {
        console.error('Error updating status:', error);
        alert(`❌ Failed to update status: ${error.message}`);
    }
}

// Save display order for a clip
async function saveDisplayOrder(index) {
    const clip = diagramClips[index];
    if (!clip) return;

    // Get the new display order value from the input
    const input = document.querySelector(`.display-order-input[data-index="${index}"]`);
    if (!input) return;

    const newDisplayOrder = parseInt(input.value);

    if (isNaN(newDisplayOrder)) {
        alert('❌ Please enter a valid number for display order');
        return;
    }

    try {
        const response = await fetch(`/api/update-clip-display-order`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: currentBookId,
                clip_type: 'diagram',
                clip_id: clip.id,
                display_order: newDisplayOrder
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to update display order`);
        }

        console.log(`Updated clip ${clip.id} display order to ${newDisplayOrder}`);

        // Update the clip in memory
        clip.display_order = newDisplayOrder;

        // Show visual feedback
        input.style.borderColor = '#4CAF50';
        setTimeout(() => {
            input.style.borderColor = '#ddd';
        }, 1000);

    } catch (error) {
        console.error('Error updating display order:', error);
        alert(`❌ Failed to update display order: ${error.message}`);
    }
}

// Save level for a clip
async function saveLevel(index) {
    const clip = diagramClips[index];
    if (!clip) return;

    // Get the selected level from the dropdown
    const select = document.querySelector(`.level-select[data-index="${index}"]`);
    if (!select) return;

    const newLevel = select.value;

    try {
        const response = await fetch(`/api/update-clip-level`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: currentBookId,
                clip_type: 'diagram',
                clip_id: clip.id,
                level: newLevel
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to update level`);
        }

        console.log(`Updated clip ${clip.id} level to ${newLevel}`);

        // Update the clip in memory
        clip.level = newLevel;

        // Show visual feedback
        select.style.borderColor = '#4CAF50';
        setTimeout(() => {
            select.style.borderColor = '#ddd';
        }, 1000);

    } catch (error) {
        console.error('Error updating level:', error);
        alert(`❌ Failed to update level: ${error.message}`);
    }
}

// Update enabled status for a clip
async function updateEnabled(index, isEnabled) {
    const clip = diagramClips[index];
    if (!clip) return;

    try {
        const response = await fetch(`/api/update-clip-enabled`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: currentBookId,
                clip_type: 'diagram',
                clip_id: clip.id,
                is_enabled: isEnabled
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to update enabled status`);
        }

        console.log(`Updated clip ${clip.id} enabled to ${isEnabled}`);

        // Update the clip in memory
        clip.is_enabled = isEnabled;

        // Reload to update the UI with the new color
        await loadDiagrams();

    } catch (error) {
        console.error('Error updating enabled status:', error);
        alert(`❌ Failed to update enabled status: ${error.message}`);
        // Reload to revert the checkbox
        await loadDiagrams();
    }
}

// Delete diagram
async function deleteDiagram(index) {
    const clip = diagramClips[index];
    if (!clip) return;

    if (!confirm(`Delete diagram #${clip.id}? This cannot be undone.`)) {
        return;
    }

    try {
        await deleteImageClip('diagram', clip.id);

        // Reload diagrams
        await loadDiagrams();

        console.log(`Deleted clip ${clip.id}`);

    } catch (error) {
        console.error('Error deleting diagram:', error);
        alert(`❌ Failed to delete: ${error.message}`);
    }
}

// Merge two adjacent clips
async function mergeClips(index1, index2) {
    if (!diagramClips || index1 >= diagramClips.length || index2 >= diagramClips.length) {
        alert('❌ Invalid clip indices');
        return;
    }

    const clip1 = diagramClips[index1];
    const clip2 = diagramClips[index2];

    console.log('Merging clips:', { clip1, clip2 });

    try {
        // Load both images
        const img1 = await loadImageFromBase64(`data:image/${clip1.image_format};base64,${clip1.image_data_base64}`);
        const img2 = await loadImageFromBase64(`data:image/${clip2.image_format};base64,${clip2.image_data_base64}`);

        // Create canvas to combine images vertically
        const maxWidth = Math.max(img1.width, img2.width);
        const totalHeight = img1.height + img2.height;

        const mergeCanvas = document.createElement('canvas');
        mergeCanvas.width = maxWidth;
        mergeCanvas.height = totalHeight;
        const mergeCtx = mergeCanvas.getContext('2d');

        // Fill with white background
        mergeCtx.fillStyle = 'white';
        mergeCtx.fillRect(0, 0, maxWidth, totalHeight);

        // Draw first image at top (centered if narrower)
        const x1 = (maxWidth - img1.width) / 2;
        mergeCtx.drawImage(img1, x1, 0);

        // Draw second image below first (centered if narrower)
        const x2 = (maxWidth - img2.width) / 2;
        mergeCtx.drawImage(img2, x2, img1.height);

        // Convert to base64
        const mergedImageData = mergeCanvas.toDataURL('image/png');

        // Save merged clip with the display_order of the first clip
        const requestData = {
            book_id: currentBookId,
            page_number: clip1.page_number,
            clip_type: 'diagram',
            selection_x: clip1.selection_x,
            selection_y: clip1.selection_y,
            selection_width: maxWidth,
            selection_height: totalHeight,
            image_data_base64: mergedImageData,
            image_format: 'png',
            description: `Merged from clips #${clip1.id} and #${clip2.id}`,
            display_order: clip1.display_order  // Inherit display_order from first clip
        };

        // Save merged clip to database
        const saveResponse = await fetch('/api/save-image-clip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });

        if (!saveResponse.ok) {
            throw new Error(`Failed to save merged clip`);
        }

        const saveResult = await saveResponse.json();
        console.log('Merged clip saved:', saveResult);

        // Disable the two original clips (mark as is_enabled = FALSE)
        await disableImageClip('diagram', clip1.id);
        await disableImageClip('diagram', clip2.id);

        // Reload diagrams
        await loadDiagrams();

        alert('✅ Clips merged successfully!');

    } catch (error) {
        console.error('Error merging clips:', error);
        alert(`❌ Failed to merge clips: ${error.message}`);
    }
}

// Helper function to load image from base64
function loadImageFromBase64(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
    });
}

// Disable an image clip (mark as is_enabled = FALSE)
async function disableImageClip(type, clipId) {
    const response = await fetch(`/api/disable-image-clip/${type}/${clipId}`, {
        method: 'PATCH'
    });

    if (!response.ok) {
        throw new Error(`Failed to disable clip ${clipId}`);
    }

    return await response.json();
}

// Delete an image clip (permanently remove)
async function deleteImageClip(type, clipId) {
    const response = await fetch(`/api/delete-image-clip/${type}/${clipId}`, {
        method: 'DELETE'
    });

    if (!response.ok) {
        throw new Error(`Failed to delete clip ${clipId}`);
    }

    return await response.json();
}

// Show loading state
function showLoading() {
    const content = document.getElementById('diagrams-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading diagrams...</p>
        </div>
    `;
}

// Show empty state
function showEmptyState() {
    const content = document.getElementById('diagrams-content');
    content.innerHTML = `
        <div class="empty-state">
            <h2>📖 No Book Selected</h2>
            <p>Select a book above to view and edit diagram clips.</p>
        </div>
    `;
}

// Show error state
function showError(message) {
    const content = document.getElementById('diagrams-content');
    content.innerHTML = `
        <div class="empty-state">
            <h2>⚠️ Error</h2>
            <p>${escapeHtml(message)}</p>
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

// Scroll to a specific clip and highlight it
function scrollToClip(clipId) {
    // Find the diagram element with matching clip ID
    const diagramElements = document.querySelectorAll('.diagram-item');

    for (const element of diagramElements) {
        if (parseInt(element.dataset.clipId) === clipId) {
            // Scroll to element with some offset
            setTimeout(() => {
                element.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // Highlight the element temporarily
                element.style.transition = 'all 0.3s';
                element.style.border = '3px solid #2196F3';
                element.style.boxShadow = '0 4px 12px rgba(33, 150, 243, 0.5)';

                // Remove highlight after 2 seconds
                setTimeout(() => {
                    element.style.border = '';
                    element.style.boxShadow = '';
                }, 2000);
            }, 500); // Wait for rendering to complete

            break;
        }
    }
}

// Load diagram titles to verify-pages
function loadTitlesToVerifyPages(index) {
    const clip = diagramClips[index];
    if (!clip) {
        alert('❌ Diagram not found');
        return;
    }

    // Build URL with page number and level titles
    const params = new URLSearchParams();
    params.set('book_id', currentBookId);
    params.set('page', clip.page_number);

    // Add level titles (only add if they have values)
    if (clip.level_1_title) params.set('level1', clip.level_1_title);
    if (clip.level_2_title) params.set('level2', clip.level_2_title);
    if (clip.level_3_title) params.set('level3', clip.level_3_title);
    if (clip.level_4_title) params.set('level4', clip.level_4_title);
    if (clip.level_5_title) params.set('level5', clip.level_5_title);

    // Navigate to verify-pages
    window.location.href = `/verify-pages?${params.toString()}`;
}

// ============================================================================
// Parent Paragraph Linking Functions
// ============================================================================

// State for paragraph linking
let currentDiagramIdForLinking = null;
let parentParagraphCache = {}; // Cache for parent paragraph data

/**
 * Load all parent paragraph data for displayed diagrams
 */
async function loadAllParentParagraphs() {
    for (const clip of diagramClips) {
        if (clip.attr17_value) {
            loadParentParagraph(clip.id, clip.attr17_value);
        }
    }
}

/**
 * Load parent paragraph data for a diagram
 * @param {number} diagramId - The diagram ID
 * @param {string} paragraphId - The parent paragraph ID
 */
async function loadParentParagraph(diagramId, paragraphId) {
    const containerEl = document.getElementById(`parent-paragraph-${diagramId}`);
    if (!containerEl) return;

    try {
        // Check cache first
        if (parentParagraphCache[paragraphId]) {
            renderParentParagraph(diagramId, parentParagraphCache[paragraphId]);
            return;
        }

        // Fetch paragraph data
        const response = await fetch(`/api/clips/${currentBookId}/paragraph/${paragraphId}/details`);
        if (!response.ok) {
            throw new Error('Paragraph not found');
        }

        const data = await response.json();
        const paragraph = data.clip;

        // Cache the data
        parentParagraphCache[paragraphId] = paragraph;

        // Render
        renderParentParagraph(diagramId, paragraph);

    } catch (error) {
        console.error(`Error loading parent paragraph ${paragraphId}:`, error);
        containerEl.innerHTML = `
            <span class="parent-paragraph-empty">Parent paragraph #${paragraphId} not found</span>
            <button class="btn-link-paragraph" onclick="openParagraphPicker(${diagramId})">
                🔄 Change
            </button>
        `;
    }
}

/**
 * Render parent paragraph in the UI
 * @param {number} diagramId - The diagram ID
 * @param {object} paragraph - The paragraph data
 */
function renderParentParagraph(diagramId, paragraph) {
    const containerEl = document.getElementById(`parent-paragraph-${diagramId}`);
    if (!containerEl) return;

    const imgSrc = paragraph.image_data_base64
        ? `data:image/${paragraph.image_format || 'png'};base64,${paragraph.image_data_base64}`
        : '';

    containerEl.innerHTML = `
        ${imgSrc ? `<img src="${imgSrc}" class="parent-paragraph-thumbnail" alt="Paragraph ${paragraph.id}" onclick="viewParagraph(${paragraph.id})" />` : ''}
        <div class="parent-paragraph-info">
            <strong>Paragraph #${paragraph.id}</strong><br>
            Page ${paragraph.page_number || 'N/A'}
        </div>
        <button class="btn-link-paragraph" onclick="openParagraphPicker(${diagramId})" style="margin-left: auto;">
            🔄 Change
        </button>
        <button class="btn-unlink-paragraph" onclick="unlinkFromParagraph(${diagramId}, ${paragraph.id})">
            ✕ Unlink
        </button>
    `;
}

/**
 * View a paragraph in edit-paragraphs page
 * @param {number} paragraphId - The paragraph ID
 */
function viewParagraph(paragraphId) {
    window.open(`/edit-paragraphs?book_id=${currentBookId}&scroll_to=${paragraphId}`, '_blank');
}

/**
 * Open paragraph picker modal
 * @param {number} diagramId - The diagram ID to link
 */
async function openParagraphPicker(diagramId) {
    currentDiagramIdForLinking = diagramId;

    const modal = document.getElementById('paragraph-picker-modal');
    const contentEl = document.getElementById('paragraph-picker-content');

    if (!modal || !contentEl) return;

    contentEl.innerHTML = '<div style="text-align: center; padding: 30px;">⏳ Loading paragraphs...</div>';
    modal.classList.add('visible');

    try {
        // Fetch recent paragraphs
        const response = await fetch(`/api/diagrams/${currentBookId}/recent-paragraphs?limit=15`);
        if (!response.ok) {
            throw new Error('Failed to fetch paragraphs');
        }

        const data = await response.json();
        const paragraphs = data.paragraphs || [];

        if (paragraphs.length === 0) {
            contentEl.innerHTML = '<div style="text-align: center; padding: 30px; color: #999;">No paragraphs found. Create some paragraphs first in Verify Pages.</div>';
            return;
        }

        // Render paragraph grid
        contentEl.innerHTML = '<div class="paragraph-picker-grid" id="paragraph-picker-grid"></div>';
        const gridEl = document.getElementById('paragraph-picker-grid');

        paragraphs.forEach(para => {
            const isFull = para.linked_diagrams_count >= 5;
            const itemEl = document.createElement('div');
            itemEl.className = 'paragraph-picker-item' + (isFull ? ' full' : '');

            const imgSrc = para.thumbnail_base64
                ? `data:image/png;base64,${para.thumbnail_base64}`
                : '';

            itemEl.innerHTML = `
                ${imgSrc ? `<img src="${imgSrc}" alt="Paragraph ${para.paragraph_id}" />` : '<div style="height: 80px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; color: #999;">No image</div>'}
                <div class="paragraph-picker-item-info">
                    ID: ${para.paragraph_id} | Page ${para.page_number}<br>
                    ${isFull ? '<span style="color: #f44336;">Full (5/5)</span>' : `<span style="color: #4CAF50;">Slots: ${para.linked_diagrams_count}/5</span>`}
                </div>
            `;

            if (!isFull) {
                itemEl.onclick = () => linkToParagraph(para.paragraph_id);
            }

            gridEl.appendChild(itemEl);
        });

    } catch (error) {
        console.error('Error loading paragraphs for picker:', error);
        contentEl.innerHTML = '<div style="text-align: center; padding: 30px; color: #f44336;">❌ Error loading paragraphs</div>';
    }
}

/**
 * Close paragraph picker modal
 */
function closeParagraphPicker() {
    const modal = document.getElementById('paragraph-picker-modal');
    if (modal) {
        modal.classList.remove('visible');
    }
    currentDiagramIdForLinking = null;
}

/**
 * Link diagram to a paragraph
 * @param {number} paragraphId - The paragraph ID to link to
 */
async function linkToParagraph(paragraphId) {
    if (!currentDiagramIdForLinking) return;

    try {
        const response = await fetch('/api/diagrams/link-to-paragraph', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                book_id: currentBookId,
                diagram_id: currentDiagramIdForLinking,
                paragraph_id: paragraphId
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            console.log('Diagram linked successfully:', result);
            closeParagraphPicker();
            // Reload diagrams to show updated link
            loadDiagrams();
        } else if (result.needs_confirmation) {
            // Diagram already has a parent
            const confirmReplace = confirm(
                `This diagram is already linked to paragraph #${result.existing_parent_id}.\n\n` +
                `Do you want to replace the existing link with paragraph #${paragraphId}?`
            );

            if (confirmReplace) {
                // Force link
                const forceResponse = await fetch('/api/diagrams/link-to-paragraph-force', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        book_id: currentBookId,
                        diagram_id: currentDiagramIdForLinking,
                        paragraph_id: paragraphId
                    })
                });

                if (forceResponse.ok) {
                    console.log('Diagram forcefully linked');
                    closeParagraphPicker();
                    loadDiagrams();
                } else {
                    alert('Failed to link diagram');
                }
            }
        } else {
            alert('Failed to link diagram: ' + (result.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error linking diagram:', error);
        alert('Error linking diagram: ' + error.message);
    }
}

/**
 * Unlink diagram from its parent paragraph
 * @param {number} diagramId - The diagram ID
 * @param {number} paragraphId - The parent paragraph ID
 */
async function unlinkFromParagraph(diagramId, paragraphId) {
    if (!confirm('Unlink this diagram from its parent paragraph?')) {
        return;
    }

    try {
        const response = await fetch('/api/diagrams/unlink-from-paragraph', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                book_id: currentBookId,
                diagram_id: diagramId,
                paragraph_id: paragraphId
            })
        });

        if (response.ok) {
            console.log('Diagram unlinked successfully');
            // Reload diagrams to show updated state
            loadDiagrams();
        } else {
            const error = await response.json();
            alert('Failed to unlink diagram: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error unlinking diagram:', error);
        alert('Error unlinking diagram: ' + error.message);
    }
}

// Close paragraph picker on overlay click
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('paragraph-picker-modal');
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeParagraphPicker();
            }
        });
    }
});
