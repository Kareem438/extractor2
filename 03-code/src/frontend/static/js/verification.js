/**
 * Verification Interface JavaScript
 * Handles knowledge unit verification, editing, and navigation
 */

// State
let currentBookId = null;
let currentRecordIndex = 0;
let knowledgeUnits = [];
let totalUnits = 0;
let zoomLevel = 100;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadBooks();

    // Check if book_id is in URL
    const urlParams = new URLSearchParams(window.location.search);
    const bookId = urlParams.get('book_id');
    if (bookId) {
        // Wait for books to load, then select this book
        setTimeout(() => {
            const selector = document.getElementById('book-selector');
            selector.value = bookId;
            selectBook(bookId);
        }, 500);
    }
});

// Load available books
async function loadBooks() {
    try {
        const response = await fetch('/api/books?limit=100');
        const data = await response.json();

        const selector = document.getElementById('book-selector');
        selector.innerHTML = '<option value="">-- Select a Book --</option>';

        data.books.forEach(book => {
            const option = document.createElement('option');
            option.value = book.book_id;
            option.textContent = `${book.book_name} (${book.processing_status})`;
            selector.appendChild(option);
        });

        selector.addEventListener('change', (e) => {
            if (e.target.value) {
                selectBook(parseInt(e.target.value));
            }
        });

        // Auto-select first book if no book_id in URL and books are available
        const urlParams = new URLSearchParams(window.location.search);
        const bookId = urlParams.get('book_id');

        if (!bookId && data.books.length > 0) {
            // Auto-select first book
            const firstBookId = data.books[0].book_id;
            selector.value = firstBookId;
            selectBook(firstBookId);
        }

    } catch (error) {
        console.error('Error loading books:', error);
        alert('Failed to load books');
    }
}

// Select a book and load its knowledge units
async function selectBook(bookId) {
    currentBookId = bookId;
    currentRecordIndex = 0;

    try {
        // Load book details
        const bookResponse = await fetch(`/api/books/${bookId}`);
        const book = await bookResponse.json();

        document.getElementById('page-title').textContent = `📚 ${book.book_name} - Verification`;

        // Load knowledge units
        await loadKnowledgeUnits();

    } catch (error) {
        console.error('Error selecting book:', error);
        alert('Failed to load book details');
    }
}

// Load knowledge units for current book
async function loadKnowledgeUnits() {
    if (!currentBookId) return;

    showLoading();

    try {
        const response = await fetch(`/api/books/${currentBookId}/knowledge-units?limit=1000`);
        const data = await response.json();

        knowledgeUnits = data.units || [];
        totalUnits = data.total || 0;

        if (knowledgeUnits.length === 0) {
            showNoRecords();
            return;
        }

        // Load first record
        loadRecord(0);

    } catch (error) {
        console.error('Error loading knowledge units:', error);
        alert('Failed to load knowledge units');
    }
}

// Load a specific record
async function loadRecord(index) {
    if (index < 0 || index >= knowledgeUnits.length) return;

    currentRecordIndex = index;
    const unit = knowledgeUnits[index];

    // Update progress
    updateProgress();

    // Load page image
    loadPageImage(unit.page_number);

    // Display record details
    displayRecordDetails(unit);

    // Load merge context
    loadMergeContext(index);

    // Update navigation buttons
    updateNavigationButtons();
}

// Display record details in right panel
function displayRecordDetails(unit) {
    const panel = document.getElementById('right-panel');

    // Determine status
    let statusClass = 'status-unverified';
    let statusText = 'Unverified';
    if (unit.verified) {
        statusClass = 'status-verified';
        statusText = 'Verified ✓';
    } else if (unit.confidence_score < 70) {
        statusClass = 'status-low-confidence';
        statusText = 'Low Confidence!';
    }

    // Build attributes section
    let attributesHTML = '';
    for (let i = 1; i <= 80; i++) {
        const attrValue = unit[`attr${i}_value`] || '';
        const attrKey = `Attribute ${i}`; // TODO: Load from attribute_keys table

        if (i <= 8 || attrValue) { // Show system attributes (1-8) and used custom attributes
            attributesHTML += `
                <div class="attribute-item">
                    <div class="attribute-key">${attrKey}</div>
                    <input type="text" class="attribute-value"
                           data-attr="${i}"
                           value="${escapeHtml(attrValue)}"
                           placeholder="Enter value...">
                </div>
            `;
        }
    }

    panel.innerHTML = `
        <div class="record-header">
            <div class="record-id">Unit ID: ${unit.unit_id}</div>
            <span class="verification-status ${statusClass}">${statusText}</span>
        </div>

        ${unit.confidence_score < 70 ? `
            <div class="low-confidence-warning">
                ⚠️ <strong>Low Confidence Warning!</strong><br>
                OCR confidence is ${unit.confidence_score}%. Please review carefully.
            </div>
        ` : ''}

        <h3 style="color: #2196F3;">Extracted Text:</h3>
        <div class="text-content">${escapeHtml(unit.text_content)}</div>

        <h3 style="color: #2196F3;">Metadata:</h3>
        <div class="metadata-grid">
            <div class="meta-item">
                <div class="meta-label">OCR Method</div>
                <div class="meta-value">${unit.ocr_method || 'N/A'}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Confidence Score</div>
                <div class="meta-value">${unit.confidence_score || 'N/A'}%</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Page Number</div>
                <div class="meta-value">${unit.page_number}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Language</div>
                <div class="meta-value">${unit.language || 'Auto-detected'}</div>
            </div>
        </div>

        <div class="hierarchy-section">
            <h3 style="color: #1976D2; margin: 0 0 15px 0;">📑 Hierarchy</h3>
            <div class="hierarchy-item">
                <div class="hierarchy-label">Chapter:</div>
                <input type="text" class="hierarchy-value" id="chapter-input"
                       value="${escapeHtml(unit.chapter || '')}"
                       placeholder="Enter chapter...">
                <button class="edit-btn" onclick="saveHierarchy('chapter')">💾 Save</button>
            </div>
            <div class="hierarchy-item">
                <div class="hierarchy-label">Topic:</div>
                <input type="text" class="hierarchy-value" id="topic-input"
                       value="${escapeHtml(unit.topic || '')}"
                       placeholder="Enter topic...">
                <button class="edit-btn" onclick="saveHierarchy('topic')">💾 Save</button>
            </div>
            <div class="hierarchy-item">
                <div class="hierarchy-label">Sub-topic:</div>
                <input type="text" class="hierarchy-value" id="subtopic-input"
                       value="${escapeHtml(unit.sub_topic || '')}"
                       placeholder="Enter sub-topic...">
                <button class="edit-btn" onclick="saveHierarchy('sub_topic')">💾 Save</button>
            </div>
        </div>

        <div class="level-extraction-section">
            <div class="level-extraction-title">🎯 Level Extraction</div>
            <div class="level-row">
                <div class="level-label">Level 1:</div>
                <button class="btn-extract-level" onclick="extractLevel(1)">🔍 Extract Level</button>
                <input type="text" class="level-text-input" id="level-1-input" placeholder="Extracted text will appear here...">
            </div>
            <div class="level-row">
                <div class="level-label">Level 2:</div>
                <button class="btn-extract-level" onclick="extractLevel(2)">🔍 Extract Level</button>
                <input type="text" class="level-text-input" id="level-2-input" placeholder="Extracted text will appear here...">
            </div>
            <div class="level-row">
                <div class="level-label">Level 3:</div>
                <button class="btn-extract-level" onclick="extractLevel(3)">🔍 Extract Level</button>
                <input type="text" class="level-text-input" id="level-3-input" placeholder="Extracted text will appear here...">
            </div>
            <div class="level-row">
                <div class="level-label">Level 4:</div>
                <button class="btn-extract-level" onclick="extractLevel(4)">🔍 Extract Level</button>
                <input type="text" class="level-text-input" id="level-4-input" placeholder="Extracted text will appear here...">
            </div>
            <div class="level-row">
                <div class="level-label">Level 5:</div>
                <button class="btn-extract-level" onclick="extractLevel(5)">🔍 Extract Level</button>
                <input type="text" class="level-text-input" id="level-5-input" placeholder="Extracted text will appear here...">
            </div>
        </div>

        <div class="attributes-section">
            <h3>🏷️ Custom Attributes</h3>
            ${attributesHTML}
            <button class="edit-btn" onclick="saveAllAttributes()" style="margin-top: 15px;">💾 Save All Attributes</button>
        </div>

        <h3 style="color: #2196F3; margin-top: 30px;">📝 Notes:</h3>
        <textarea id="notes-textarea" placeholder="Add verification notes...">${escapeHtml(unit.notes || '')}</textarea>
        <button class="edit-btn" onclick="saveNotes()" style="margin-top: 10px;">💾 Save Notes</button>
    `;

    // Update verify checkbox
    document.getElementById('verify-checkbox').checked = unit.verified || false;
}

// Load page image
async function loadPageImage(pageNumber) {
    if (!currentBookId || !pageNumber) return;

    const container = document.getElementById('image-container');
    container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading page image...</p></div>';

    try {
        // Try to fetch page image
        const response = await fetch(`/api/books/${currentBookId}/pages/${pageNumber}/image`);

        if (response.ok) {
            const blob = await response.blob();
            const imageUrl = URL.createObjectURL(blob);

            container.innerHTML = `
                <img src="${imageUrl}"
                     class="page-image"
                     id="page-image"
                     alt="Page ${pageNumber}"
                     style="transform: scale(${zoomLevel / 100});">
            `;
        } else {
            // Fallback: show placeholder
            container.innerHTML = `
                <div style="padding: 50px; text-align: center; color: #666;">
                    <p style="font-size: 48px;">📄</p>
                    <p>Page ${pageNumber}</p>
                    <p style="font-size: 12px; color: #999;">Image not available</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading page image:', error);
        container.innerHTML = `
            <div style="padding: 50px; text-align: center; color: #999;">
                <p>Page ${pageNumber} - Image not available</p>
            </div>
        `;
    }
}

// Load merge context (surrounding records)
function loadMergeContext(index) {
    const contextContainer = document.getElementById('context-records');
    const mergeSection = document.getElementById('merge-context');

    if (knowledgeUnits.length < 3) {
        mergeSection.style.display = 'none';
        return;
    }

    mergeSection.style.display = 'block';
    contextContainer.innerHTML = '';

    // Show 2 before, current, 2 after
    const start = Math.max(0, index - 2);
    const end = Math.min(knowledgeUnits.length, index + 3);

    for (let i = start; i < end; i++) {
        const unit = knowledgeUnits[i];
        const isCurrent = i === index;
        const position = i < index ? `${index - i} before` :
                        i > index ? `${i - index} after` : 'CURRENT';

        const recordDiv = document.createElement('div');
        recordDiv.className = `context-record ${isCurrent ? 'current' : ''}`;
        recordDiv.innerHTML = `
            <div class="context-record-label">
                ${isCurrent ? '▶️' : i < index ? '⬆️' : '⬇️'}
                RECORD ${unit.unit_id} (${position}) | Page ${unit.page_number}
            </div>
            <div>${escapeHtml(unit.text_content.substring(0, 150))}${unit.text_content.length > 150 ? '...' : ''}</div>
            ${!isCurrent ? `<button class="merge-btn" onclick="mergeRecords(${i}, ${index})">Merge ${i < index ? '↓' : '↑'}</button>` : ''}
        `;
        contextContainer.appendChild(recordDiv);
    }
}

// Update progress display
function updateProgress() {
    const verified = knowledgeUnits.filter(u => u.verified).length;
    const remaining = knowledgeUnits.length - verified;

    document.getElementById('progress-mini').textContent =
        `Record ${currentRecordIndex + 1} of ${knowledgeUnits.length} | Verified: ${verified} | Remaining: ${remaining}`;

    document.getElementById('nav-record-info').textContent =
        `Record ${currentRecordIndex + 1} / ${knowledgeUnits.length}`;
}

// Update navigation button states
function updateNavigationButtons() {
    document.getElementById('btn-prev').disabled = currentRecordIndex === 0;
    document.getElementById('btn-next').disabled = currentRecordIndex >= knowledgeUnits.length - 1;
    document.getElementById('btn-approve').disabled = currentRecordIndex >= knowledgeUnits.length - 1;
}

// Navigation functions
function previousRecord() {
    if (currentRecordIndex > 0) {
        loadRecord(currentRecordIndex - 1);
    }
}

function nextRecord() {
    if (currentRecordIndex < knowledgeUnits.length - 1) {
        loadRecord(currentRecordIndex + 1);
    }
}

async function approveAndNext() {
    // Mark as verified
    await toggleVerification(true);

    // Move to next
    if (currentRecordIndex < knowledgeUnits.length - 1) {
        loadRecord(currentRecordIndex + 1);
    } else {
        alert('All records verified! 🎉');
    }
}

// Toggle verification status
async function toggleVerification(forceValue = null) {
    const unit = knowledgeUnits[currentRecordIndex];
    const newValue = forceValue !== null ? forceValue : document.getElementById('verify-checkbox').checked;

    try {
        const response = await fetch(`/api/books/${currentBookId}/knowledge-units/${unit.unit_id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ verified: newValue })
        });

        if (!response.ok) throw new Error('Failed to update verification status');

        // Update local state
        unit.verified = newValue;
        updateProgress();

        // Refresh display
        displayRecordDetails(unit);

    } catch (error) {
        console.error('Error updating verification:', error);
        alert('Failed to update verification status');
    }
}

// Listen to verify checkbox changes
document.addEventListener('change', (e) => {
    if (e.target.id === 'verify-checkbox') {
        toggleVerification();
    }
});

// Save hierarchy field
async function saveHierarchy(field) {
    const unit = knowledgeUnits[currentRecordIndex];
    let value;

    if (field === 'chapter') value = document.getElementById('chapter-input').value;
    else if (field === 'topic') value = document.getElementById('topic-input').value;
    else if (field === 'sub_topic') value = document.getElementById('subtopic-input').value;

    try {
        const response = await fetch(`/api/books/${currentBookId}/knowledge-units/${unit.unit_id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [field]: value })
        });

        if (!response.ok) throw new Error('Failed to save');

        unit[field] = value;
        alert(`${field} saved successfully!`);

    } catch (error) {
        console.error('Error saving hierarchy:', error);
        alert(`Failed to save ${field}`);
    }
}

// Save all attributes
async function saveAllAttributes() {
    const unit = knowledgeUnits[currentRecordIndex];
    const updates = {};

    // Collect all attribute values
    document.querySelectorAll('.attribute-value').forEach(input => {
        const attrNum = input.dataset.attr;
        updates[`attr${attrNum}_value`] = input.value;
    });

    try {
        const response = await fetch(`/api/books/${currentBookId}/knowledge-units/${unit.unit_id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });

        if (!response.ok) throw new Error('Failed to save');

        // Update local state
        Object.assign(unit, updates);
        alert('All attributes saved successfully!');

    } catch (error) {
        console.error('Error saving attributes:', error);
        alert('Failed to save attributes');
    }
}

// Save notes
async function saveNotes() {
    const unit = knowledgeUnits[currentRecordIndex];
    const notes = document.getElementById('notes-textarea').value;

    try {
        const response = await fetch(`/api/books/${currentBookId}/knowledge-units/${unit.unit_id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notes })
        });

        if (!response.ok) throw new Error('Failed to save');

        unit.notes = notes;
        alert('Notes saved successfully!');

    } catch (error) {
        console.error('Error saving notes:', error);
        alert('Failed to save notes');
    }
}

// Merge records
async function mergeRecords(sourceIndex, targetIndex) {
    const source = knowledgeUnits[sourceIndex];
    const target = knowledgeUnits[targetIndex];

    if (!confirm(`Merge record ${source.unit_id} into record ${target.unit_id}?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/books/${currentBookId}/knowledge-units/merge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_id: source.unit_id,
                target_id: target.unit_id
            })
        });

        if (!response.ok) throw new Error('Failed to merge');

        alert('Records merged successfully!');

        // Reload knowledge units
        await loadKnowledgeUnits();

    } catch (error) {
        console.error('Error merging records:', error);
        alert('Failed to merge records');
    }
}

// Extract level function
function extractLevel(levelNumber) {
    const unit = knowledgeUnits[currentRecordIndex];
    const inputElement = document.getElementById(`level-${levelNumber}-input`);

    if (!inputElement) {
        console.error(`Level ${levelNumber} input not found`);
        return;
    }

    // Show the input field
    inputElement.classList.add('visible');

    // Extract text based on level (for now, using the text_content)
    // This can be customized based on your specific requirements
    let extractedText = '';

    if (unit.text_content) {
        // Simple extraction: split text by lines and extract based on level
        const lines = unit.text_content.split('\n').filter(line => line.trim());

        if (lines.length > 0) {
            // For demonstration, we'll extract different portions based on level
            if (levelNumber === 1 && lines.length > 0) {
                extractedText = lines[0]; // First line
            } else if (levelNumber === 2 && lines.length > 1) {
                extractedText = lines[1]; // Second line
            } else if (levelNumber === 3 && lines.length > 2) {
                extractedText = lines[2]; // Third line
            } else if (levelNumber === 4 && lines.length > 3) {
                extractedText = lines[3]; // Fourth line
            } else if (levelNumber === 5 && lines.length > 4) {
                extractedText = lines[4]; // Fifth line
            } else {
                extractedText = unit.text_content; // Fallback to full text
            }
        }
    }

    // Set the extracted text in the input
    inputElement.value = extractedText;

    // Focus on the input for editing
    inputElement.focus();
}

// Zoom controls
function zoomIn() {
    zoomLevel = Math.min(zoomLevel + 25, 200);
    updateZoom();
}

function zoomOut() {
    zoomLevel = Math.max(zoomLevel - 25, 50);
    updateZoom();
}

function resetZoom() {
    zoomLevel = 100;
    updateZoom();
}

function updateZoom() {
    const img = document.getElementById('page-image');
    if (img) {
        img.style.transform = `scale(${zoomLevel / 100})`;
    }
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoading() {
    document.getElementById('right-panel').innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading...</p></div>';
}

function showNoRecords() {
    document.getElementById('right-panel').innerHTML = '<div class="loading"><p>No knowledge units found for this book.</p><p>Please run OCR processing first.</p></div>';
}
