# Claude Code Reference for Pipeline Page

**Purpose:** This file contains code snippets from extraction-dashboard that need to be moved/adapted for the Pipeline page's "Execute Diagram Analysis" button.

---

## 1. API Mode Selector (HTML)

```html
<div class="api-mode-toggle">
    <label>API Mode:</label>
    <select id="api-mode">
        <option value="batch">Batch (50% cost)</option>
        <option value="direct">Direct (immediate)</option>
    </select>
</div>
```

**CSS:**
```css
.api-mode-toggle {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #0f3460;
    padding: 6px 12px;
    border-radius: 4px;
}
.api-mode-toggle label { font-size: 13px; color: #aaa; }
.api-mode-toggle select {
    background: #1a4a7a;
    color: white;
    border: 1px solid #2a5a8a;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
}
```

---

## 2. Execute Diagram Analysis Function (JavaScript)

This function should be added to Pipeline page to call Claude batch/direct API:

```javascript
// Execute Diagram Analysis - sends diagrams to Claude
async function executeDiagramAnalysis() {
    if (!currentBookId) {
        showAlert('Please select a book first', 'error');
        return;
    }

    const apiMode = document.getElementById('api-mode').value;
    const confirmed = confirm(`Start Claude analysis using ${apiMode === 'batch' ? 'Batch API (50% cost)' : 'Direct API (immediate)'}?`);

    if (!confirmed) return;

    const btn = document.getElementById('btnExecuteAnalysis');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Processing...';

    try {
        const endpoint = apiMode === 'batch' 
            ? `/api/extraction/${currentBookId}/decode-batch`
            : `/api/extraction/${currentBookId}/decode-direct`;

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})  // Process all unprocessed diagrams
        });

        const data = await response.json();

        if (response.ok) {
            if (apiMode === 'batch') {
                showAlert(`Batch submitted! Batch ID: ${data.batch_id}. Results will be available in ~24 hours.`, 'success');
            } else {
                showAlert(`Direct analysis complete! Processed ${data.processed_count || 0} diagrams.`, 'success');
            }
            await loadPageStatus();
        } else {
            showAlert(data.detail || 'Failed to execute diagram analysis', 'error');
        }

    } catch (error) {
        console.error('Error executing diagram analysis:', error);
        showAlert('Error executing diagram analysis', 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}
```

---

## 3. API Endpoints for Claude Analysis

**Batch Mode (50% cost, ~24 hour delay):**
- `POST /api/extraction/{book_id}/decode-batch`
- Returns: `{ batch_id, status, message }`

**Direct Mode (immediate, full cost):**
- `POST /api/extraction/{book_id}/decode-direct`
- Returns: `{ processed_count, errors }`

**Check Batch Status:**
- `GET /api/extraction/{book_id}/batch-status?batch_id=xxx`

**Retrieve Batch Results:**
- `POST /api/extraction/{book_id}/batch-results?batch_id=xxx`

---

## 4. Re-decode Single Diagram (for testing prompts)

```javascript
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
```

---

## 5. Pipeline Page Button HTML

Add this button next to "Create Knowledge Units":

```html
<button class="btn btn-success" id="btnExecuteAnalysis" onclick="executeDiagramAnalysis()">
    Execute Diagram Analysis
</button>
```

---

## Notes

- The Extraction page should ONLY run Surya OCR (no Claude)
- The Pipeline page should have BOTH buttons:
  1. "Create Knowledge Units" - creates KU records from raw tables
  2. "Execute Diagram Analysis" - sends diagrams to Claude
- API mode selector should be on Pipeline page, not Extraction page
