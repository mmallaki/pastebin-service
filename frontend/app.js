const API = '/api/v1';
let currentPasteId = null;
let currentShareKey = null;
let searchTimer = null;

const LANGUAGES = [
    'text', 'python', 'javascript', 'typescript', 'java', 'c', 'cpp',
    'csharp', 'go', 'rust', 'ruby', 'php', 'swift', 'kotlin',
    'html', 'css', 'sql', 'bash', 'powershell', 'yaml', 'json', 'markdown'
];

function init() {
    const langSelect = document.getElementById('language');
    LANGUAGES.forEach(lang => {
        const opt = document.createElement('option');
        opt.value = lang;
        opt.textContent = lang;
        langSelect.appendChild(opt);
    });

    document.getElementById('create-form').addEventListener('submit', handleCreate);
    document.getElementById('edit-form').addEventListener('submit', handleUpdate);
    document.getElementById('lookup-form').addEventListener('submit', handleLookup);

    setupTabSupport('content');
    setupTabSupport('edit-content');

    showView('create');
}

function setupTabSupport(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = el.selectionStart;
            const end = el.selectionEnd;
            el.value = el.value.substring(0, start) + '    ' + el.value.substring(end);
            el.selectionStart = el.selectionEnd = start + 4;
        }
    });
}

function showView(name) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`view-${name}`).classList.add('active');

    if (name === 'list') loadList();
    if (name === 'lookup') document.getElementById('lookup-key').focus();
}

async function handleCreate(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    btn.disabled = true;
    btn.textContent = 'Creating...';

    try {
        const res = await fetch(`${API}/pastes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: document.getElementById('title').value || null,
                content: document.getElementById('content').value,
                language: document.getElementById('language').value,
                expiration: document.getElementById('expiration').value,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to create paste');
        }

        const paste = await res.json();
        document.getElementById('title').value = '';
        document.getElementById('content').value = '';
        showToast('Paste created');
        viewPaste(paste.id);
    } catch (err) {
        showToast(err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Paste';
    }
}

async function handleUpdate(e) {
    e.preventDefault();
    if (!currentPasteId) return;
    const btn = e.target.querySelector('button');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
        const res = await fetch(`${API}/pastes/${currentPasteId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: document.getElementById('edit-title').value || null,
                content: document.getElementById('edit-content').value,
                language: document.getElementById('edit-language').value,
            }),
        });

        if (!res.ok) throw new Error('Failed to update');
        showToast('Paste updated');
        showView('paste');
        viewPaste(currentPasteId);
    } catch (err) {
        showToast(err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save';
    }
}

async function handleLookup(e) {
    e.preventDefault();
    const key = document.getElementById('lookup-key').value.trim().toLowerCase();
    if (!key) return;

    const result = document.getElementById('lookup-result');
    result.innerHTML = '<div class="empty-state">Loading...</div>';

    try {
        const res = await fetch(`${API}/view/${key}`);
        if (!res.ok) {
            result.innerHTML = '<div class="empty-state">Paste not found. Check the key and try again.</div>';
            return;
        }
        const paste = await res.json();
        currentPasteId = paste.id;
        currentShareKey = paste.share_key;
        showView('paste');
        renderPaste(paste);
    } catch (err) {
        result.innerHTML = '<div class="empty-state">Failed to look up paste.</div>';
    }
}

function startEdit() {
    if (!currentPasteId) return;
    fetch(`${API}/pastes/${currentPasteId}`)
        .then(r => r.json())
        .then(paste => {
            document.getElementById('edit-title').value = paste.title || '';
            document.getElementById('edit-content').value = paste.content;

            const langSelect = document.getElementById('edit-language');
            langSelect.innerHTML = '';
            LANGUAGES.forEach(lang => {
                const opt = document.createElement('option');
                opt.value = lang;
                opt.textContent = lang;
                if (lang === paste.language) opt.selected = true;
                langSelect.appendChild(opt);
            });

            showView('edit');
        });
}

async function viewPaste(id) {
    currentPasteId = id;
    showView('paste');

    try {
        const res = await fetch(`${API}/pastes/${id}`);
        if (!res.ok) throw new Error('Paste not found');
        const paste = await res.json();
        renderPaste(paste);
    } catch (err) {
        showToast(err.message);
        showView('list');
    }
}

function renderPaste(paste) {
    currentPasteId = paste.id;
    currentShareKey = paste.share_key;

    document.getElementById('paste-title').textContent = paste.title || 'Untitled';
    document.getElementById('paste-lang').textContent = paste.language;
    document.getElementById('paste-date').textContent = formatDate(paste.created_at);
    document.getElementById('paste-views').textContent = `${paste.views} view${paste.views !== 1 ? 's' : ''}`;
    document.getElementById('paste-share-key').textContent = paste.share_key;
    document.getElementById('paste-share-url').value = getShareUrl();

    const codeEl = document.getElementById('paste-code');
    codeEl.textContent = paste.content;
    codeEl.className = `language-${paste.language}`;

    if (window.hljs) {
        hljs.highlightElement(codeEl);
    }
}

function getShareUrl() {
    if (!currentShareKey) return '';
    return `${window.location.origin}/view/${currentShareKey}`;
}

function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
}

function copyShareKey() {
    if (!currentShareKey) return;
    copyToClipboard(currentShareKey);
    showToast('Share key copied');
}

function copyShareLink() {
    const url = getShareUrl();
    if (!url) return;
    copyToClipboard(url);
    showToast('Share link copied');
}

async function deletePaste() {
    if (!currentPasteId) return;
    if (!confirm('Delete this paste?')) return;

    try {
        const res = await fetch(`${API}/pastes/${currentPasteId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete');
        showToast('Paste deleted');
        showView('list');
    } catch (err) {
        showToast(err.message);
    }
}

function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadList, 300);
}

async function loadList() {
    const container = document.getElementById('paste-list');
    const query = document.getElementById('search-input')?.value?.trim() || '';
    container.innerHTML = '<div class="empty-state">Loading...</div>';

    try {
        let url = `${API}/pastes?per_page=50`;
        if (query) url += `&search=${encodeURIComponent(query)}`;

        const res = await fetch(url);
        const data = await res.json();

        if (data.pastes.length === 0) {
            container.innerHTML = `<div class="empty-state">${query ? 'No pastes found' : 'No pastes yet. Create one!'}</div>`;
            return;
        }

        container.innerHTML = data.pastes.map(p => `
            <a class="paste-item" href="#" onclick="viewPaste('${p.id}'); return false;">
                <div class="paste-item-info">
                    <span class="paste-item-title">${escapeHtml(p.title || 'Untitled')}</span>
                    <span class="paste-item-meta">${formatDate(p.created_at)} &middot; ${p.views} view${p.views !== 1 ? 's' : ''}</span>
                </div>
                <span class="paste-item-lang">${p.share_key}</span>
            </a>
        `).join('');
    } catch (err) {
        container.innerHTML = '<div class="empty-state">Failed to load pastes</div>';
    }
}

function formatDate(iso) {
    const d = new Date(iso);
    const now = new Date();
    const diff = (now - d) / 1000;

    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
}

document.addEventListener('DOMContentLoaded', init);
