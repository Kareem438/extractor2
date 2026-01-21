/**
 * Edit Paragraphs JavaScript
 * Manage and edit paragraph image clips
 */

// State
let currentBookId = null;
let books = [];
let paragraphClips = [];
let returnPageNumber = null; // Page number to return to in verify-pages
let cameFromAutoSlicer = false; // Track if we came from auto-slicer

// Full Details Modal - Attribute State
let collapsibleSectionStates = {}; // Tracks expanded/collapsed state for each section
let currentClipAttributes = {}; // Stores current clip's attribute values
let currentAttributeNames = {}; // Stores attribute names from settings
let originalAttributeValues = {}; // Tracks original values to detect changes

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Edit Paragraphs page loaded');
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
    const backAutoSlicerBtn = document.getElementById('back-to-autoslicer-btn');

    bookSelect.addEventListener('change', (e) => {
        currentBookId = parseInt(e.target.value);
        if (currentBookId) {
            loadParagraphs();
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

    // Back to Auto-Slicer button
    if (backAutoSlicerBtn) {
        backAutoSlicerBtn.addEventListener('click', () => {
            if (currentBookId) {
                window.location.href = `/auto-slicer?book_id=${currentBookId}`;
            }
        });

        // Show the button if coming from auto-slicer
        const fromParam = getUrlParameter('from');
        if (fromParam === 'autoslicer') {
            backAutoSlicerBtn.style.display = 'inline-block';
        }
    }
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
        const fromParam = getUrlParameter('from');

        if (bookIdParam) {
            const bookId = parseInt(bookIdParam);
            const book = books.find(b => b.book_id === bookId);

            if (book) {
                bookSelect.value = bookId;
                currentBookId = bookId;
                await loadParagraphs();

                // Scroll to specific clip if scroll_to parameter is provided
                if (scrollToParam) {
                    const scrollToClipId = parseInt(scrollToParam);
                    console.log('scroll_to param:', scrollToClipId);
                    console.log('from param:', fromParam);
                    console.log('paragraphClips count:', paragraphClips.length);

                    scrollToClip(scrollToClipId);

                    // If coming from auto-slicer, automatically open full details modal
                    if (fromParam === 'autoslicer') {
                        cameFromAutoSlicer = true;
                        const clipIndex = paragraphClips.findIndex(c => c.id === scrollToClipId);
                        console.log('Found clip at index:', clipIndex);

                        if (clipIndex !== -1) {
                            // Longer delay to ensure UI is fully ready
                            console.log('Will auto-open full details in 500ms...');
                            setTimeout(() => {
                                console.log('Auto-opening full details now');
                                openFullDetails(clipIndex);
                            }, 500);
                        } else {
                            console.log('ERROR: Clip not found in paragraphClips array');
                        }
                    }
                }
            }
        }

    } catch (error) {
        console.error('Error loading books:', error);
    }
}

// Load paragraph clips for selected book
async function loadParagraphs() {
    if (!currentBookId) return;

    showLoading();

    try {
        // Fetch all paragraph clips for this book (no limit, no page filter)
        const response = await fetch(`/api/all-image-clips/${currentBookId}?clip_type=paragraph`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        paragraphClips = data.clips || [];

        console.log('Loaded paragraph clips:', paragraphClips.length);

        // Determine return page number: prioritize URL page param, then scroll_to clip, then first clip
        const pageParam = getUrlParameter('page');
        if (pageParam) {
            returnPageNumber = parseInt(pageParam);
            console.log('Using page from URL parameter:', returnPageNumber);
        } else {
            const scrollToParam = getUrlParameter('scroll_to');
            if (scrollToParam) {
                const scrollToClipId = parseInt(scrollToParam);
                const scrollToClip = paragraphClips.find(c => c.id === scrollToClipId);
                if (scrollToClip) {
                    returnPageNumber = scrollToClip.page_number;
                    console.log('Using page from scroll_to clip:', returnPageNumber);
                }
            }

            // If no page or scroll_to, use first clip's page
            if (!returnPageNumber && paragraphClips.length > 0) {
                returnPageNumber = paragraphClips[0].page_number;
                console.log('Using page from first clip:', returnPageNumber);
            }
        }

        // Show back button if we have a book selected
        const backBtn = document.getElementById('back-to-verify-btn');
        if (currentBookId && backBtn) {
            backBtn.style.display = 'inline-block';
        }

        // Display the clips
        displayParagraphs();

    } catch (error) {
        console.error('Error loading paragraphs:', error);
        showError(`Failed to load paragraphs: ${error.message}`);
    }
}

// Display paragraphs with merge buttons
function displayParagraphs() {
    const content = document.getElementById('paragraphs-content');

    if (!paragraphClips || paragraphClips.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <h2>📝 No Paragraphs Found</h2>
                <p>This book has no paragraph clips yet. Use the Verify Pages tool to create clips.</p>
            </div>
        `;
        return;
    }

    let html = '<div class="paragraphs-grid">';

    paragraphClips.forEach((clip, index) => {
        // Add paragraph item
        html += createParagraphHtml(clip, index);

        // Add merge button between items (not after the last one)
        if (index < paragraphClips.length - 1) {
            html += createMergeButtonHtml(index);
        }
    });

    html += '</div>';

    content.innerHTML = html;
}

// Create paragraph HTML
function createParagraphHtml(clip, index) {
    const imageSrc = `data:image/${clip.image_format};base64,${clip.image_data_base64}`;
    const timestamp = new Date(clip.created_at).toLocaleString();
    const statusClass = `status-${clip.approval_status || 'new'}`;

    return `
        <div class="paragraph-item" id="paragraph-${index}" data-clip-id="${clip.id}">
            <div class="paragraph-thumbnail">
                <img src="${imageSrc}" alt="Paragraph ${clip.id}" />
                <button
                    class="btn-load-titles"
                    onclick="loadTitlesToVerifyPages(${index})"
                    style="margin-top: 8px; width: 100%; padding: 8px 12px; background: #FF9800; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: bold;"
                    title="Load this paragraph's level titles to verify-pages"
                >
                    📋 Load Titles
                </button>
            </div>
            <div class="paragraph-info">
                <div class="paragraph-meta">
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
                <div class="paragraph-actions">
                    <button class="btn-action btn-full-details" onclick="openFullDetails(${index})">
                        📋 Full Details
                    </button>
                    <button class="btn-action btn-delete" onclick="deleteParagraph(${index})">
                        🗑️ Delete
                    </button>
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
    const clip = paragraphClips[index];
    if (!clip) return;

    try {
        const response = await fetch(`/api/update-clip-status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: currentBookId,
                clip_type: 'paragraph',
                clip_id: clip.id,
                approval_status: newStatus
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to update status`);
        }

        console.log(`Updated clip ${clip.id} to ${newStatus}`);

        // Reload paragraphs to reflect new status
        await loadParagraphs();

    } catch (error) {
        console.error('Error updating status:', error);
        alert(`❌ Failed to update status: ${error.message}`);
    }
}

// Save display order for a clip
async function saveDisplayOrder(index) {
    const clip = paragraphClips[index];
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
                clip_type: 'paragraph',
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
    const clip = paragraphClips[index];
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
                clip_type: 'paragraph',
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
    const clip = paragraphClips[index];
    if (!clip) return;

    try {
        const response = await fetch(`/api/update-clip-enabled`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: currentBookId,
                clip_type: 'paragraph',
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
        await loadParagraphs();

    } catch (error) {
        console.error('Error updating enabled status:', error);
        alert(`❌ Failed to update enabled status: ${error.message}`);
        // Reload to revert the checkbox
        await loadParagraphs();
    }
}

// Delete paragraph
async function deleteParagraph(index) {
    const clip = paragraphClips[index];
    if (!clip) return;

    if (!confirm(`Delete paragraph #${clip.id}? This cannot be undone.`)) {
        return;
    }

    try {
        await deleteImageClip('paragraph', clip.id);

        // Reload paragraphs
        await loadParagraphs();

        console.log(`Deleted clip ${clip.id}`);

    } catch (error) {
        console.error('Error deleting paragraph:', error);
        alert(`❌ Failed to delete: ${error.message}`);
    }
}

// Merge two adjacent clips
async function mergeClips(index1, index2) {
    if (!paragraphClips || index1 >= paragraphClips.length || index2 >= paragraphClips.length) {
        alert('❌ Invalid clip indices');
        return;
    }

    const clip1 = paragraphClips[index1];
    const clip2 = paragraphClips[index2];

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
            clip_type: 'paragraph',
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
        await disableImageClip('paragraph', clip1.id);
        await disableImageClip('paragraph', clip2.id);

        // Reload paragraphs
        await loadParagraphs();

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
    const content = document.getElementById('paragraphs-content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading paragraphs...</p>
        </div>
    `;
}

// Show empty state
function showEmptyState() {
    const content = document.getElementById('paragraphs-content');
    content.innerHTML = `
        <div class="empty-state">
            <h2>📖 No Book Selected</h2>
            <p>Select a book above to view and edit paragraph clips.</p>
        </div>
    `;
}

// Show error state
function showError(message) {
    const content = document.getElementById('paragraphs-content');
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
    // Find the paragraph element with matching clip ID
    const paragraphElements = document.querySelectorAll('.paragraph-item');

    for (const element of paragraphElements) {
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

// Load paragraph titles to verify-pages
function loadTitlesToVerifyPages(index) {
    const clip = paragraphClips[index];
    if (!clip) {
        alert('❌ Paragraph not found');
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

// ==================== Full Details Modal Functions ====================

let currentDetailsClipIndex = null;

// Toggle collapsible section
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

/**
 * Check if a section should be expanded based on saved state
 * @param {string} sectionId - The section ID
 * @param {boolean} defaultExpanded - Default state if no saved state exists
 */
function isSectionExpanded(sectionId, defaultExpanded = false) {
    if (collapsibleSectionStates.hasOwnProperty(sectionId)) {
        return collapsibleSectionStates[sectionId];
    }
    return defaultExpanded;
}

/**
 * Fetch attribute values and names for a clip
 */
async function fetchClipAttributes(clipId) {
    if (!currentBookId) return null;

    try {
        const response = await fetch(`/api/clip-with-attributes/${currentBookId}/paragraph/${clipId}`);
        if (!response.ok) {
            console.warn(`Failed to fetch attributes for clip ${clipId}`);
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching clip attributes:', error);
        return null;
    }
}

/**
 * Save a single attribute value
 */
async function saveSingleAttribute(attrNumber, value) {
    const clip = paragraphClips[currentDetailsClipIndex];
    if (!clip || !currentBookId) return false;

    const btn = document.getElementById(`attr-save-btn-${attrNumber}`);
    const textarea = document.getElementById(`attr-textarea-${attrNumber}`);

    // Show saving state
    if (btn) {
        btn.classList.add('saving');
        btn.textContent = '⏳';
        btn.disabled = true;
    }

    try {
        const response = await fetch('/api/update-single-attribute', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: currentBookId,
                clip_id: clip.id,
                clip_type: 'paragraph',
                attr_number: attrNumber,
                attr_value: value || null
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // Show success
        if (btn) {
            btn.classList.remove('saving');
            btn.classList.add('saved');
            btn.textContent = '✓';
        }
        if (textarea) {
            textarea.classList.remove('modified');
            textarea.classList.add('saved');
        }

        // Update original value
        originalAttributeValues[attrNumber] = value;

        // Reset button after delay
        setTimeout(() => {
            if (btn) {
                btn.classList.remove('saved');
                btn.textContent = '💾';
                btn.disabled = false;
            }
            if (textarea) {
                textarea.classList.remove('saved');
            }
        }, 1500);

        return true;

    } catch (error) {
        console.error(`Error saving attribute ${attrNumber}:`, error);

        // Show error
        if (btn) {
            btn.classList.remove('saving');
            btn.textContent = '❌';
            btn.disabled = false;
        }

        setTimeout(() => {
            if (btn) {
                btn.textContent = '💾';
            }
        }, 2000);

        return false;
    }
}

/**
 * Handle attribute textarea change - mark as modified
 */
function onAttributeChange(attrNumber) {
    const textarea = document.getElementById(`attr-textarea-${attrNumber}`);
    if (!textarea) return;

    const currentValue = textarea.value;
    const originalValue = originalAttributeValues[attrNumber] || '';

    if (currentValue !== originalValue) {
        textarea.classList.add('modified');
        textarea.classList.remove('saved');
    } else {
        textarea.classList.remove('modified');
    }
}

/**
 * Generate HTML for a single attribute field
 */
function generateAttributeFieldHTML(attrNumber, value, name) {
    const displayName = name || `Attribute ${attrNumber}`;
    const escapedValue = escapeHtml(value || '');

    return `
        <div class="attr-field-container">
            <div class="attr-field-content">
                <label class="attr-field-label">
                    ${escapeHtml(displayName)} <span class="attr-number">(#${attrNumber})</span>
                </label>
                <textarea
                    id="attr-textarea-${attrNumber}"
                    class="attr-textarea"
                    data-attr="${attrNumber}"
                    oninput="onAttributeChange(${attrNumber})"
                    placeholder="Enter value..."
                >${escapedValue}</textarea>
            </div>
            <button
                id="attr-save-btn-${attrNumber}"
                class="attr-save-btn"
                onclick="saveSingleAttribute(${attrNumber}, document.getElementById('attr-textarea-${attrNumber}').value)"
                title="Save this attribute"
            >💾</button>
        </div>
    `;
}

/**
 * Generate HTML for an attribute group section (8 attributes)
 */
function generateAttributeGroupHTML(groupStart, groupEnd, attributes, attributeNames) {
    const sectionId = `section-attrs-${groupStart}-${groupEnd}`;
    const isExpanded = isSectionExpanded(sectionId, false); // All collapsed by default
    const expandedClass = isExpanded ? 'expanded' : '';

    let fieldsHTML = '';
    for (let i = groupStart; i <= groupEnd; i++) {
        const value = attributes[`attr${i}_value`] || '';
        const nameInfo = attributeNames[i];
        const name = nameInfo ? nameInfo.key_name : null;
        fieldsHTML += generateAttributeFieldHTML(i, value, name);
    }

    return `
        <div class="collapsible-section">
            <div class="collapsible-header ${expandedClass}" data-section="${sectionId}" onclick="toggleCollapsible('${sectionId}')">
                <div class="collapsible-header-title">
                    <span class="collapsible-icon">▶</span>
                    <span class="attr-group-header">📊 Attributes ${groupStart}-${groupEnd}</span>
                </div>
            </div>
            <div class="collapsible-content ${expandedClass}" id="${sectionId}">
                <div class="collapsible-inner">
                    <div class="attr-grid">
                        ${fieldsHTML}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Generate all 10 attribute group sections HTML
 */
function generateAllAttributeGroupsHTML(attributes, attributeNames) {
    let html = '';
    const groups = [
        [1, 8], [9, 16], [17, 24], [25, 32], [33, 40],
        [41, 48], [49, 56], [57, 64], [65, 72], [73, 80]
    ];

    for (const [start, end] of groups) {
        html += generateAttributeGroupHTML(start, end, attributes, attributeNames);
    }

    return html;
}

// Open the Full Details modal
async function openFullDetails(index) {
    const clip = paragraphClips[index];
    if (!clip) return;

    currentDetailsClipIndex = index;

    const modal = document.getElementById('details-modal');
    const title = document.getElementById('details-modal-title');
    const body = document.getElementById('details-modal-body');

    title.textContent = `Paragraph #${clip.id} - Full Details`;

    // Show loading state
    body.innerHTML = '<div style="text-align: center; padding: 40px;">⏳ Loading attributes...</div>';
    modal.classList.add('visible');
    document.body.style.overflow = 'hidden';

    // Fetch attributes
    const attrData = await fetchClipAttributes(clip.id);

    // Store attributes for change tracking
    currentClipAttributes = attrData?.attributes || {};
    currentAttributeNames = attrData?.attribute_names || {};
    originalAttributeValues = {};

    // Initialize original values for change tracking
    for (let i = 1; i <= 80; i++) {
        originalAttributeValues[i] = currentClipAttributes[`attr${i}_value`] || '';
    }

    const imageSrc = `data:image/${clip.image_format};base64,${clip.image_data_base64}`;
    const createdAt = clip.created_at ? new Date(clip.created_at).toLocaleString() : 'N/A';
    const updatedAt = clip.updated_at ? new Date(clip.updated_at).toLocaleString() : 'N/A';

    // Check section states (with defaults for the original sections)
    const imageExpanded = isSectionExpanded('section-image', true);
    const titlesExpanded = isSectionExpanded('section-titles', true);
    const editableExpanded = isSectionExpanded('section-editable', true);
    const systemExpanded = isSectionExpanded('section-system', false);
    const coordsExpanded = isSectionExpanded('section-coordinates', false);
    const imagePropsExpanded = isSectionExpanded('section-image-props', false);

    // Generate attribute groups HTML
    const attributeGroupsHTML = generateAllAttributeGroupsHTML(currentClipAttributes, currentAttributeNames);

    body.innerHTML = `
        <!-- Image Preview -->
        <div class="collapsible-section">
            <div class="collapsible-header ${imageExpanded ? 'expanded' : ''}" data-section="section-image" onclick="toggleCollapsible('section-image')">
                <div class="collapsible-header-title">
                    <span class="collapsible-icon">▶</span>
                    <span>🖼️ Image Preview</span>
                </div>
            </div>
            <div class="collapsible-content ${imageExpanded ? 'expanded' : ''}" id="section-image">
                <div class="collapsible-inner">
                    <img src="${imageSrc}" class="details-image-preview" alt="Paragraph ${clip.id}" />
                </div>
            </div>
        </div>

        <!-- Level Titles -->
        <div class="collapsible-section">
            <div class="collapsible-header ${titlesExpanded ? 'expanded' : ''}" data-section="section-titles" onclick="toggleCollapsible('section-titles')">
                <div class="collapsible-header-title">
                    <span class="collapsible-icon">▶</span>
                    <span>📑 Level Titles</span>
                </div>
            </div>
            <div class="collapsible-content ${titlesExpanded ? 'expanded' : ''}" id="section-titles">
                <div class="collapsible-inner">
                    <div class="details-section">
                        <div class="details-section-title">Level Titles</div>
            <div class="details-grid">
                <div class="details-field full-width">
                    <label>Level 1 Title</label>
                    <input type="text" id="detail-level-1-title" value="${escapeHtml(clip.level_1_title || '')}" placeholder="Chapter or main section title" />
                </div>
                <div class="details-field full-width">
                    <label>Level 2 Title</label>
                    <input type="text" id="detail-level-2-title" value="${escapeHtml(clip.level_2_title || '')}" placeholder="Section title" />
                </div>
                <div class="details-field full-width">
                    <label>Level 3 Title</label>
                    <input type="text" id="detail-level-3-title" value="${escapeHtml(clip.level_3_title || '')}" placeholder="Subsection title" />
                </div>
                <div class="details-field full-width">
                    <label>Level 4 Title</label>
                    <input type="text" id="detail-level-4-title" value="${escapeHtml(clip.level_4_title || '')}" placeholder="Sub-subsection title" />
                </div>
            </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Editable Fields -->
        <div class="collapsible-section">
            <div class="collapsible-header ${editableExpanded ? 'expanded' : ''}" data-section="section-editable" onclick="toggleCollapsible('section-editable')">
                <div class="collapsible-header-title">
                    <span class="collapsible-icon">▶</span>
                    <span>✏️ Editable Fields</span>
                </div>
            </div>
            <div class="collapsible-content ${editableExpanded ? 'expanded' : ''}" id="section-editable">
                <div class="collapsible-inner">
                    <div class="details-section">
                        <div class="details-section-title">Editable Fields</div>
            <div class="details-grid">
                <div class="details-field">
                    <label>Approval Status</label>
                    <select id="detail-approval-status">
                        <option value="pending" ${clip.approval_status === 'pending' ? 'selected' : ''}>Pending</option>
                        <option value="approved" ${clip.approval_status === 'approved' ? 'selected' : ''}>Approved</option>
                        <option value="rejected" ${clip.approval_status === 'rejected' ? 'selected' : ''}>Rejected</option>
                        <option value="reviewed" ${clip.approval_status === 'reviewed' ? 'selected' : ''}>Reviewed</option>
                    </select>
                </div>
                <div class="details-field">
                    <label>Display Order</label>
                    <input type="number" id="detail-display-order" value="${clip.display_order || 0}" />
                </div>
                <div class="details-field">
                    <label>Enabled</label>
                    <select id="detail-is-enabled">
                        <option value="true" ${clip.is_enabled ? 'selected' : ''}>Yes</option>
                        <option value="false" ${!clip.is_enabled ? 'selected' : ''}>No</option>
                    </select>
                </div>
                <div class="details-field">
                    <label>Level</label>
                    <select id="detail-level">
                        <option value="" ${!clip.level ? 'selected' : ''}>None</option>
                        <option value="Level 1" ${clip.level === 'Level 1' ? 'selected' : ''}>Level 1</option>
                        <option value="Level 2" ${clip.level === 'Level 2' ? 'selected' : ''}>Level 2</option>
                        <option value="Level 3" ${clip.level === 'Level 3' ? 'selected' : ''}>Level 3</option>
                        <option value="Level 4" ${clip.level === 'Level 4' ? 'selected' : ''}>Level 4</option>
                        <option value="Level 5" ${clip.level === 'Level 5' ? 'selected' : ''}>Level 5</option>
                    </select>
                </div>
                <div class="details-field">
                    <label>Category</label>
                    <input type="text" id="detail-category" value="${escapeHtml(clip.category || '')}" placeholder="e.g., introduction, summary" />
                </div>
                <div class="details-field">
                    <label>Created By</label>
                    <input type="text" id="detail-created-by" value="${escapeHtml(clip.created_by || '')}" placeholder="Username or source" />
                </div>
                <div class="details-field">
                    <label>Selected Level Number</label>
                    <select id="detail-selected-level-number">
                        <option value="" ${!clip.selected_level_number ? 'selected' : ''}>None</option>
                        <option value="1" ${clip.selected_level_number === 1 ? 'selected' : ''}>1</option>
                        <option value="2" ${clip.selected_level_number === 2 ? 'selected' : ''}>2</option>
                        <option value="3" ${clip.selected_level_number === 3 ? 'selected' : ''}>3</option>
                        <option value="4" ${clip.selected_level_number === 4 ? 'selected' : ''}>4</option>
                        <option value="5" ${clip.selected_level_number === 5 ? 'selected' : ''}>5</option>
                    </select>
                </div>
                <div class="details-field">
                    <label>Selected Level Text</label>
                    <input type="text" id="detail-selected-level-text" value="${escapeHtml(clip.selected_level_text || '')}" placeholder="Level title text" />
                </div>
                <div class="details-field full-width">
                    <label>Description</label>
                    <textarea id="detail-description" placeholder="Description of this paragraph clip">${escapeHtml(clip.description || '')}</textarea>
                </div>
                <div class="details-field full-width">
                    <label>User Notes</label>
                    <textarea id="detail-user-notes" placeholder="Your notes about this clip">${escapeHtml(clip.user_notes || '')}</textarea>
                </div>
                <div class="details-field full-width">
                    <label>Extracted Text (OCR)</label>
                    <textarea id="detail-extracted-text" placeholder="OCR extracted text" style="min-height: 120px;">${escapeHtml(clip.extracted_text || '')}</textarea>
                </div>
                <div class="details-field">
                    <label>OCR Confidence</label>
                    <input type="number" id="detail-ocr-confidence" value="${clip.ocr_confidence || ''}" min="0" max="100" step="0.01" placeholder="0-100" />
                </div>
                <div class="details-field full-width">
                    <label>Tags (comma-separated)</label>
                    <input type="text" id="detail-tags" value="${Array.isArray(clip.tags) ? clip.tags.join(', ') : ''}" placeholder="tag1, tag2, tag3" />
                </div>
            </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- System Information (Read-Only) -->
        <div class="collapsible-section">
            <div class="collapsible-header ${systemExpanded ? 'expanded' : ''}" data-section="section-system" onclick="toggleCollapsible('section-system')">
                <div class="collapsible-header-title">
                    <span class="collapsible-icon">▶</span>
                    <span>ℹ️ System Information (Read-Only)</span>
                </div>
            </div>
            <div class="collapsible-content ${systemExpanded ? 'expanded' : ''}" id="section-system">
                <div class="collapsible-inner">
                    <div class="details-section">
                        <div class="details-section-title">System Information (Read-Only)</div>
            <div class="details-grid">
                <div class="details-field">
                    <label>ID</label>
                    <div class="readonly-value">${clip.id}</div>
                </div>
                <div class="details-field">
                    <label>Raw Page ID</label>
                    <div class="readonly-value">${clip.raw_page_id || 'N/A'}</div>
                </div>
                <div class="details-field">
                    <label>Page Number</label>
                    <div class="readonly-value">${clip.page_number}</div>
                </div>
                <div class="details-field">
                    <label>Created At</label>
                    <div class="readonly-value">${createdAt}</div>
                </div>
                <div class="details-field">
                    <label>Updated At</label>
                    <div class="readonly-value">${updatedAt}</div>
                </div>
                <div class="details-field">
                    <label>Linked KU ID</label>
                    <div class="readonly-value">${clip.linked_knowledge_unit_id || 'Not linked'}</div>
                </div>
            </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Selection Coordinates (Read-Only) -->
        <div class="collapsible-section">
            <div class="collapsible-header ${coordsExpanded ? 'expanded' : ''}" data-section="section-coordinates" onclick="toggleCollapsible('section-coordinates')">
                <div class="collapsible-header-title">
                    <span class="collapsible-icon">▶</span>
                    <span>📍 Selection Coordinates (Read-Only)</span>
                </div>
            </div>
            <div class="collapsible-content ${coordsExpanded ? 'expanded' : ''}" id="section-coordinates">
                <div class="collapsible-inner">
                    <div class="details-section">
                        <div class="details-section-title">Selection Coordinates (Read-Only)</div>
            <div class="details-grid">
                <div class="details-field">
                    <label>X Position</label>
                    <div class="readonly-value">${clip.selection_x} px</div>
                </div>
                <div class="details-field">
                    <label>Y Position</label>
                    <div class="readonly-value">${clip.selection_y} px</div>
                </div>
                <div class="details-field">
                    <label>Selection Width</label>
                    <div class="readonly-value">${clip.selection_width} px</div>
                </div>
                <div class="details-field">
                    <label>Selection Height</label>
                    <div class="readonly-value">${clip.selection_height} px</div>
                </div>
            </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Image Properties (Read-Only) -->
        <div class="collapsible-section">
            <div class="collapsible-header ${imagePropsExpanded ? 'expanded' : ''}" data-section="section-image-props" onclick="toggleCollapsible('section-image-props')">
                <div class="collapsible-header-title">
                    <span class="collapsible-icon">▶</span>
                    <span>🖼️ Image Properties (Read-Only)</span>
                </div>
            </div>
            <div class="collapsible-content ${imagePropsExpanded ? 'expanded' : ''}" id="section-image-props">
                <div class="collapsible-inner">
                    <div class="details-section">
                        <div class="details-section-title">Image Properties (Read-Only)</div>
            <div class="details-grid">
                <div class="details-field">
                    <label>Image Format</label>
                    <div class="readonly-value">${clip.image_format || 'png'}</div>
                </div>
                <div class="details-field">
                    <label>Image Size</label>
                    <div class="readonly-value">${clip.image_width} × ${clip.image_height} px</div>
                </div>
                <div class="details-field">
                    <label>File Size</label>
                    <div class="readonly-value">${formatBytes(clip.image_size_bytes)}</div>
                </div>
            </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Linked Diagrams -->
        <div class="collapsible-section">
            <div class="collapsible-header expanded" data-section="section-linked-diagrams" onclick="toggleCollapsible('section-linked-diagrams')">
                <div class="collapsible-header-title">
                    <span class="collapsible-icon">▶</span>
                    <span>🔗 Linked Diagrams (attr17-21)</span>
                </div>
            </div>
            <div class="collapsible-content expanded" id="section-linked-diagrams">
                <div class="collapsible-inner">
                    <div class="linked-diagrams-grid" id="linked-diagrams-grid">
                        <!-- Will be populated by loadLinkedDiagrams() -->
                        <div style="text-align: center; padding: 20px; grid-column: 1/-1;">⏳ Loading linked diagrams...</div>
                    </div>
                    <div style="text-align: center;">
                        <button class="btn-link-new-diagram" id="btn-link-new-diagram" onclick="openDiagramPicker()">
                            ➕ Link a Diagram
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Attribute Groups (1-80) -->
        ${attributeGroupsHTML}
    `;

    // Load linked diagrams after modal content is set
    loadLinkedDiagrams(clip.id);

    // Update navigation button states
    updateNavigationButtons();
}

// Update navigation button states based on current position
function updateNavigationButtons() {
    const prevBtn = document.getElementById('btn-prev-paragraph');
    const nextBtn = document.getElementById('btn-next-paragraph');
    const backToAutoSlicerBtn = document.getElementById('btn-back-to-autoslicer-modal');

    if (!prevBtn || !nextBtn || currentDetailsClipIndex === null) return;

    // Show/hide Back to Auto-Slicer button
    if (backToAutoSlicerBtn) {
        backToAutoSlicerBtn.style.display = cameFromAutoSlicer ? 'inline-block' : 'none';
    }

    // Disable Previous button if at first paragraph
    if (currentDetailsClipIndex <= 0) {
        prevBtn.disabled = true;
    } else {
        prevBtn.disabled = false;
    }

    // Disable Next button if at last paragraph
    if (currentDetailsClipIndex >= paragraphClips.length - 1) {
        nextBtn.disabled = true;
    } else {
        nextBtn.disabled = false;
    }
}

// Navigate to previous paragraph
function navigateToPreviousParagraph() {
    if (currentDetailsClipIndex === null || currentDetailsClipIndex <= 0) return;

    const newIndex = currentDetailsClipIndex - 1;
    openFullDetails(newIndex);
}

// Navigate to next paragraph
function navigateToNextParagraph() {
    if (currentDetailsClipIndex === null || currentDetailsClipIndex >= paragraphClips.length - 1) return;

    const newIndex = currentDetailsClipIndex + 1;
    openFullDetails(newIndex);
}

// Go back to Auto-Slicer page
function goBackToAutoSlicer() {
    if (currentBookId) {
        // Include the current clip ID to scroll to that thumbnail
        const clip = paragraphClips[currentDetailsClipIndex];
        const clipId = clip ? clip.id : null;
        let url = `/auto-slicer?book_id=${currentBookId}`;
        if (clipId) {
            url += `&scroll_to=${clipId}`;
        }
        window.location.href = url;
    }
}

// Close the Full Details modal
function closeDetailsModal() {
    const modal = document.getElementById('details-modal');
    modal.classList.remove('visible');
    document.body.style.overflow = '';
    currentDetailsClipIndex = null;
}

// Save the Full Details changes
async function saveFullDetails() {
    if (currentDetailsClipIndex === null) return;

    const clip = paragraphClips[currentDetailsClipIndex];
    if (!clip) return;

    // Gather all editable values
    const updates = {
        book_id: currentBookId,
        clip_id: clip.id,
        clip_type: 'paragraph',
        approval_status: document.getElementById('detail-approval-status').value,
        display_order: parseInt(document.getElementById('detail-display-order').value) || 0,
        is_enabled: document.getElementById('detail-is-enabled').value === 'true',
        level: document.getElementById('detail-level').value || null,
        category: document.getElementById('detail-category').value || null,
        created_by: document.getElementById('detail-created-by').value || null,
        selected_level_number: document.getElementById('detail-selected-level-number').value ? parseInt(document.getElementById('detail-selected-level-number').value) : null,
        selected_level_text: document.getElementById('detail-selected-level-text').value || null,
        description: document.getElementById('detail-description').value || null,
        user_notes: document.getElementById('detail-user-notes').value || null,
        extracted_text: document.getElementById('detail-extracted-text').value || null,
        ocr_confidence: document.getElementById('detail-ocr-confidence').value ? parseFloat(document.getElementById('detail-ocr-confidence').value) : null,
        tags: document.getElementById('detail-tags').value.trim() || null,
        level_1_title: document.getElementById('detail-level-1-title').value || null,
        level_2_title: document.getElementById('detail-level-2-title').value || null,
        level_3_title: document.getElementById('detail-level-3-title').value || null,
        level_4_title: document.getElementById('detail-level-4-title').value || null
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

        console.log('Clip details updated successfully');

        // Close modal and reload paragraphs
        closeDetailsModal();
        await loadParagraphs();

        alert('✅ Details saved successfully!');

    } catch (error) {
        console.error('Error saving details:', error);
        alert(`❌ Failed to save details: ${error.message}`);
    }
}

// Format bytes to human readable
function formatBytes(bytes) {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

// Close modal on Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('details-modal');
        if (modal && modal.classList.contains('visible')) {
            closeDetailsModal();
        }
    }
});

// Close modal when clicking overlay background
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('details-modal');
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeDetailsModal();
            }
        });
    }

    // Also close diagram picker on overlay click
    const diagramPicker = document.getElementById('diagram-picker-modal');
    if (diagramPicker) {
        diagramPicker.addEventListener('click', function(event) {
            if (event.target === diagramPicker) {
                closeDiagramPicker();
            }
        });
    }
});

// ============================================================================
// Linked Diagrams Functions
// ============================================================================

// State for linked diagrams
let linkedDiagramsData = [null, null, null, null, null]; // 5 slots for attr17-21
let currentParagraphIdForLinking = null;

/**
 * Load linked diagrams for a paragraph
 * @param {number} paragraphId - The paragraph ID
 */
async function loadLinkedDiagrams(paragraphId) {
    currentParagraphIdForLinking = paragraphId;
    const gridEl = document.getElementById('linked-diagrams-grid');
    const linkBtn = document.getElementById('btn-link-new-diagram');

    if (!gridEl) return;

    gridEl.innerHTML = '<div style="text-align: center; padding: 20px; grid-column: 1/-1;">⏳ Loading linked diagrams...</div>';

    try {
        // Fetch paragraph attributes to get linked diagram IDs (attr17-21)
        const attrResponse = await fetch(`/api/clips/${currentBookId}/paragraph/${paragraphId}/attributes`);
        if (!attrResponse.ok) {
            throw new Error('Failed to fetch attributes');
        }
        const attrData = await attrResponse.json();
        const attrs = attrData.attributes || {};

        // Get diagram IDs from attr17-21
        const diagramIds = [];
        for (let i = 17; i <= 21; i++) {
            const val = attrs[`attr${i}_value`];
            diagramIds.push(val ? parseInt(val) : null);
        }

        // Fetch diagram details for each linked ID
        linkedDiagramsData = [null, null, null, null, null];
        const fetchPromises = diagramIds.map(async (diagramId, index) => {
            if (diagramId) {
                try {
                    const response = await fetch(`/api/diagrams/${currentBookId}/${diagramId}`);
                    if (response.ok) {
                        const data = await response.json();
                        linkedDiagramsData[index] = data.diagram;
                    }
                } catch (e) {
                    console.warn(`Failed to fetch diagram ${diagramId}:`, e);
                }
            }
        });

        await Promise.all(fetchPromises);

        // Render the slots
        renderLinkedDiagramSlots();

        // Update link button state
        const filledCount = linkedDiagramsData.filter(d => d !== null).length;
        if (linkBtn) {
            linkBtn.disabled = filledCount >= 5;
            linkBtn.textContent = filledCount >= 5 ? '✓ All 5 Slots Filled' : '➕ Link a Diagram';
        }

    } catch (error) {
        console.error('Error loading linked diagrams:', error);
        gridEl.innerHTML = '<div style="text-align: center; padding: 20px; color: #f44336; grid-column: 1/-1;">❌ Error loading linked diagrams</div>';
    }
}

/**
 * Render the 5 linked diagram slots
 */
function renderLinkedDiagramSlots() {
    const gridEl = document.getElementById('linked-diagrams-grid');
    if (!gridEl) return;

    gridEl.innerHTML = '';

    for (let i = 0; i < 5; i++) {
        const diagram = linkedDiagramsData[i];
        const slotNumber = i + 1;
        const attrNumber = 17 + i;

        const slotEl = document.createElement('div');
        slotEl.className = 'linked-diagram-slot' + (diagram ? ' filled' : '');

        if (diagram) {
            const imgSrc = diagram.image_data_base64
                ? `data:image/${diagram.image_format || 'png'};base64,${diagram.image_data_base64}`
                : '';

            slotEl.innerHTML = `
                <button class="btn-unlink-diagram" onclick="unlinkDiagram(${slotNumber}, ${diagram.id})" title="Unlink diagram">×</button>
                <span class="linked-diagram-slot-label">Slot ${slotNumber} (attr${attrNumber})</span>
                ${imgSrc ? `<img src="${imgSrc}" class="linked-diagram-thumbnail" alt="Diagram ${diagram.id}" onclick="viewDiagram(${diagram.id})" />` : '<div class="linked-diagram-empty">No image</div>'}
                <div class="linked-diagram-info">
                    ID: ${diagram.id}<br>
                    Page ${diagram.page_number || 'N/A'}
                </div>
            `;
        } else {
            slotEl.innerHTML = `
                <span class="linked-diagram-slot-label">Slot ${slotNumber} (attr${attrNumber})</span>
                <div class="linked-diagram-empty">Empty</div>
            `;
        }

        gridEl.appendChild(slotEl);
    }
}

/**
 * Unlink a diagram from a paragraph
 * @param {number} slotNumber - The slot number (1-5)
 * @param {number} diagramId - The diagram ID
 */
async function unlinkDiagram(slotNumber, diagramId) {
    if (!confirm(`Unlink diagram #${diagramId} from this paragraph?`)) {
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
                paragraph_id: currentParagraphIdForLinking
            })
        });

        if (response.ok) {
            console.log('Diagram unlinked successfully');
            // Reload linked diagrams
            loadLinkedDiagrams(currentParagraphIdForLinking);
        } else {
            const error = await response.json();
            alert('Failed to unlink diagram: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error unlinking diagram:', error);
        alert('Error unlinking diagram: ' + error.message);
    }
}

/**
 * View a diagram (placeholder - could open diagram details)
 * @param {number} diagramId - The diagram ID
 */
function viewDiagram(diagramId) {
    // Navigate to edit-diagrams page with this diagram
    window.open(`/edit-diagrams?book_id=${currentBookId}&scroll_to=${diagramId}`, '_blank');
}

/**
 * Open the diagram picker modal
 */
async function openDiagramPicker() {
    const modal = document.getElementById('diagram-picker-modal');
    const contentEl = document.getElementById('diagram-picker-content');

    if (!modal || !contentEl) return;

    contentEl.innerHTML = '<div style="text-align: center; padding: 30px;">⏳ Loading diagrams...</div>';
    modal.classList.add('visible');

    try {
        // Fetch recent diagrams
        const response = await fetch(`/api/paragraphs/${currentBookId}/recent-diagrams?limit=15`);
        if (!response.ok) {
            throw new Error('Failed to fetch diagrams');
        }

        const data = await response.json();
        const diagrams = data.diagrams || [];

        if (diagrams.length === 0) {
            contentEl.innerHTML = '<div style="text-align: center; padding: 30px; color: #999;">No diagrams found. Create some diagrams first in Verify Pages.</div>';
            return;
        }

        // Get IDs of already linked diagrams
        const linkedIds = linkedDiagramsData.filter(d => d !== null).map(d => d.id);

        // Render diagram grid
        contentEl.innerHTML = '<div class="diagram-picker-grid" id="diagram-picker-grid"></div>';
        const gridEl = document.getElementById('diagram-picker-grid');

        diagrams.forEach(diagram => {
            const isLinked = linkedIds.includes(diagram.diagram_id);
            const itemEl = document.createElement('div');
            itemEl.className = 'diagram-picker-item' + (isLinked ? ' already-linked' : '');

            const imgSrc = diagram.thumbnail_base64
                ? `data:image/png;base64,${diagram.thumbnail_base64}`
                : '';

            itemEl.innerHTML = `
                ${imgSrc ? `<img src="${imgSrc}" alt="Diagram ${diagram.diagram_id}" />` : '<div style="height: 80px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; color: #999;">No image</div>'}
                <div class="diagram-picker-item-info">
                    ID: ${diagram.diagram_id} | Page ${diagram.page_number}<br>
                    ${isLinked ? '<span style="color: #FF9800;">Already linked</span>' : (diagram.parent_paragraph_id ? '<span style="color: #999;">Has parent</span>' : '<span style="color: #4CAF50;">Available</span>')}
                </div>
            `;

            if (!isLinked) {
                itemEl.onclick = () => linkDiagramToParagraph(diagram.diagram_id);
            }

            gridEl.appendChild(itemEl);
        });

    } catch (error) {
        console.error('Error loading diagrams for picker:', error);
        contentEl.innerHTML = '<div style="text-align: center; padding: 30px; color: #f44336;">❌ Error loading diagrams</div>';
    }
}

/**
 * Close the diagram picker modal
 */
function closeDiagramPicker() {
    const modal = document.getElementById('diagram-picker-modal');
    if (modal) {
        modal.classList.remove('visible');
    }
}

/**
 * Link a diagram to the current paragraph
 * @param {number} diagramId - The diagram ID to link
 */
async function linkDiagramToParagraph(diagramId) {
    try {
        const response = await fetch('/api/diagrams/link-to-paragraph', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                book_id: currentBookId,
                diagram_id: diagramId,
                paragraph_id: currentParagraphIdForLinking
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            console.log('Diagram linked successfully:', result);
            closeDiagramPicker();
            loadLinkedDiagrams(currentParagraphIdForLinking);
        } else if (result.needs_confirmation) {
            // Diagram already has a parent
            const confirmReplace = confirm(
                `This diagram is already linked to paragraph #${result.existing_parent_id}.\n\n` +
                `Do you want to replace the existing link?`
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
                        diagram_id: diagramId,
                        paragraph_id: currentParagraphIdForLinking
                    })
                });

                if (forceResponse.ok) {
                    console.log('Diagram forcefully linked');
                    closeDiagramPicker();
                    loadLinkedDiagrams(currentParagraphIdForLinking);
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
