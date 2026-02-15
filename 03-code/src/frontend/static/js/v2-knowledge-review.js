/**
 * V2 Knowledge Review Page
 * 
 * Three-view display: queryable parameters, formatted JSON, formatted XML
 * Navigation, verification, and notes functionality.
 */

let bookId = null;
let knowledgePages = [];
let currentKPIndex = -1;
let currentPage = 1;
let totalPages = 1;
const perPage = 50;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    bookId = parseInt(params.get('book_id'));
    if (!bookId) {
        document.getElementById('book-name').textContent = 'No book selected';
        return;
    }
    loadBookInfo();
    loadKnowledgePages();
    loadStats();
});

async function loadBookInfo() {
    try {
        const resp = await fetch(`/api/books/${bookId}`);
        const book = await resp.json();
        document.getElementById('book-name').textContent = book.book_name;
    } catch (e) { console.error('Failed to load book info:', e); }
}

async function loadKnowledgePages() {
    try {
        const resp = await fetch(`/api/v2/books/${bookId}/knowledge-pages?page=${currentPage}&per_page=${perPage}`);
        const data = await resp.json();
        knowledgePages = data.knowledge_pages;
        totalPages = data.total_pages || 1;

        document.getElementById('kp-count-info').textContent = `${data.total} knowledge pages`;
        document.getElementById('page-info').textContent = `${currentPage} / ${totalPages}`;

        renderKPList();
        if (knowledgePages.length > 0 && currentKPIndex < 0) {
            selectKP(0);
        }
    } catch (e) { console.error('Failed to load KPs:', e); }
}

async function loadStats() {
    try {
        const resp = await fetch(`/api/v2/books/${bookId}/extraction/status`);
        const data = await resp.json();
        const stats = data.stats;
        document.getElementById('stat-total').textContent = stats.knowledge_pages || 0;
        document.getElementById('stat-cost').textContent = '$' + (stats.total_cost || 0).toFixed(4);

        // Count verified from loaded pages (approximate)
        const verified = knowledgePages.filter(kp => kp.verified).length;
        document.getElementById('stat-verified').textContent = verified;
        document.getElementById('stat-unverified').textContent = knowledgePages.length - verified;
    } catch (e) { console.error('Failed to load stats:', e); }
}

function renderKPList() {
    const container = document.getElementById('kp-list');
    if (knowledgePages.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">No knowledge pages found</div>';
        return;
    }

    container.innerHTML = knowledgePages.map((kp, idx) => `
        <div class="kp-card ${idx === currentKPIndex ? 'active' : ''}" onclick="selectKP(${idx})">
            <div class="kp-title">${kp.l3_title_text || 'Untitled'}</div>
            <div class="kp-meta">
                Pages ${kp.start_page}-${kp.end_page} | ${kp.concept_type || 'N/A'}
            </div>
            <div>
                <span class="kp-badge ${kp.verified ? 'kp-badge-verified' : 'kp-badge-unverified'}">${kp.verified ? '✅ Verified' : '❌ Unverified'}</span>
                ${kp.difficulty_score ? `<span class="kp-badge" style="background: #1a3a5c; color: #90caf9;">D:${kp.difficulty_score}</span>` : ''}
                ${kp.physics_domain ? `<span class="kp-badge" style="background: #1a3a2e; color: #a5d6a7;">${kp.physics_domain}</span>` : ''}
            </div>
        </div>
    `).join('');
}

function selectKP(index) {
    currentKPIndex = index;
    renderKPList();
    renderCurrentKP();
}

function renderCurrentKP() {
    if (currentKPIndex < 0 || currentKPIndex >= knowledgePages.length) return;
    const kp = knowledgePages[currentKPIndex];

    // Update verify button
    const verifyBtn = document.getElementById('verify-btn');
    verifyBtn.textContent = kp.verified ? '✅ Verified' : '☐ Mark Verified';
    verifyBtn.className = kp.verified ? 'btn-verify verified' : 'btn-verify';

    // Update notes
    document.getElementById('notes-area').value = kp.notes || '';

    // Render all three views
    renderParamsView(kp);
    renderJSONView(kp);
    renderXMLView(kp);
}

function renderParamsView(kp) {
    const params = [
        { label: 'L3 Title', value: kp.l3_title_text || 'N/A', full: true },
        { label: 'Page Range', value: `${kp.start_page} - ${kp.end_page}` },
        { label: 'Difficulty', value: kp.difficulty_score || 'N/A' },
        { label: 'Concept Type', value: kp.concept_type || 'N/A' },
        { label: 'Physics Domain', value: kp.physics_domain || 'N/A' },
        { label: 'Bloom Level', value: kp.bloom_taxonomy_level || 'N/A' },
        { label: 'Exam Relevance', value: kp.exam_relevance || 'N/A' },
        { label: 'Confidence', value: kp.extraction_confidence || 'N/A' },
        { label: 'Worked Example', value: kp.has_worked_example ? 'Yes' : 'No' },
        { label: 'Problem Set', value: kp.has_problem_set ? 'Yes' : 'No' },
        { label: 'Element Count', value: kp.element_count || 0 },
        { label: 'LLM Provider', value: kp.llm_provider || 'N/A' },
        { label: 'Model', value: kp.model_name || 'N/A' },
        { label: 'Status', value: kp.record_status || 'enabled' },
        { label: 'Summary', value: kp.summary || 'N/A', full: true },
    ];

    document.getElementById('params-content').innerHTML = params.map(p => `
        <div class="param-card ${p.full ? 'param-card-full' : ''}">
            <div class="param-label">${p.label}</div>
            <div class="param-value">${p.value}</div>
        </div>
    `).join('');
}

function renderJSONView(kp) {
    let jsonData;
    try {
        jsonData = typeof kp.parsed_json === 'string' ? JSON.parse(kp.parsed_json) : kp.parsed_json;
    } catch (e) {
        jsonData = { error: 'Failed to parse JSON', raw: kp.parsed_json };
    }

    const formatted = JSON.stringify(jsonData, null, 2);
    document.getElementById('json-content').innerHTML = syntaxHighlightJSON(formatted);
}

function renderXMLView(kp) {
    const xml = kp.raw_xml || '<no_data/>';
    document.getElementById('xml-content').innerHTML = syntaxHighlightXML(xml);
}

function syntaxHighlightJSON(json) {
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
        let cls = 'json-number';
        if (/^"/.test(match)) {
            cls = /:$/.test(match) ? 'json-key' : 'json-string';
        } else if (/true|false/.test(match)) {
            cls = 'json-bool';
        }
        return `<span class="${cls}">${match}</span>`;
    });
}

function syntaxHighlightXML(xml) {
    return xml
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/(&lt;\/?)([\w_-]+)/g, '$1<span class="xml-tag">$2</span>')
        .replace(/([\w_-]+)=(".*?")/g, '<span class="xml-attr">$1</span>=<span class="xml-value">$2</span>');
}


// =========================================================================
// View Switching
// =========================================================================

function switchView(viewName) {
    // Update tabs
    document.querySelectorAll('.view-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));

    // Activate selected
    const tabs = document.querySelectorAll('.view-tab');
    const panels = { params: 'view-params', json: 'view-json', xml: 'view-xml' };

    if (viewName === 'params') tabs[0].classList.add('active');
    else if (viewName === 'json') tabs[1].classList.add('active');
    else if (viewName === 'xml') tabs[2].classList.add('active');

    document.getElementById(panels[viewName]).classList.add('active');
}

// =========================================================================
// KP Navigation
// =========================================================================

function prevKP() {
    if (currentKPIndex > 0) {
        selectKP(currentKPIndex - 1);
        scrollKPIntoView();
    }
}

function nextKP() {
    if (currentKPIndex < knowledgePages.length - 1) {
        selectKP(currentKPIndex + 1);
        scrollKPIntoView();
    }
}

function scrollKPIntoView() {
    const cards = document.querySelectorAll('.kp-card');
    if (cards[currentKPIndex]) {
        cards[currentKPIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// =========================================================================
// Pagination
// =========================================================================

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        currentKPIndex = -1;
        loadKnowledgePages();
    }
}

function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        currentKPIndex = -1;
        loadKnowledgePages();
    }
}

// =========================================================================
// Verification Toggle
// =========================================================================

async function toggleVerify() {
    if (currentKPIndex < 0 || currentKPIndex >= knowledgePages.length) return;
    const kp = knowledgePages[currentKPIndex];
    const newVerified = !kp.verified;

    try {
        const resp = await fetch(`/api/v2/books/${bookId}/knowledge-pages/${kp.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ verified: newVerified })
        });
        if (resp.ok) {
            kp.verified = newVerified;
            renderCurrentKP();
            renderKPList();
            loadStats();
        } else {
            console.error('Failed to toggle verify:', await resp.text());
        }
    } catch (e) { console.error('Failed to toggle verify:', e); }
}

// =========================================================================
// Notes
// =========================================================================

function toggleNotes() {
    const area = document.getElementById('notes-area');
    area.style.display = area.style.display === 'none' ? 'block' : 'none';
}

async function saveNotes() {
    if (currentKPIndex < 0 || currentKPIndex >= knowledgePages.length) return;
    const kp = knowledgePages[currentKPIndex];
    const notes = document.getElementById('notes-area').value;

    try {
        const resp = await fetch(`/api/v2/books/${bookId}/knowledge-pages/${kp.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notes })
        });
        if (resp.ok) {
            kp.notes = notes;
        } else {
            console.error('Failed to save notes:', await resp.text());
        }
    } catch (e) { console.error('Failed to save notes:', e); }
}

// =========================================================================
// Keyboard Navigation
// =========================================================================

document.addEventListener('keydown', (e) => {
    // Don't intercept when typing in notes
    if (e.target.tagName === 'TEXTAREA') return;

    if (e.key === 'ArrowUp' || e.key === 'k') { e.preventDefault(); prevKP(); }
    else if (e.key === 'ArrowDown' || e.key === 'j') { e.preventDefault(); nextKP(); }
    else if (e.key === 'v') { toggleVerify(); }
    else if (e.key === '1') { switchView('params'); }
    else if (e.key === '2') { switchView('json'); }
    else if (e.key === '3') { switchView('xml'); }
});
