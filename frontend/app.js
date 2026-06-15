const API = '/api/v1';
let currentPasteId = null;
let currentShareKey = null;

const LANGUAGES = [
    'text','python','javascript','typescript','java','c','cpp',
    'csharp','go','rust','ruby','php','swift','kotlin',
    'html','css','sql','bash','powershell','yaml','json','markdown'
];

function init() {
    const sel = document.getElementById('language');
    LANGUAGES.forEach(l => {
        const o = document.createElement('option');
        o.value = l; o.textContent = l;
        sel.appendChild(o);
    });

    document.getElementById('lookup-form').addEventListener('submit', handleLookup);

    document.querySelectorAll('textarea').forEach(ta => {
        ta.addEventListener('keydown', e => {
            if (e.key === 'Tab') {
                e.preventDefault();
                const s = ta.selectionStart, end = ta.selectionEnd;
                ta.value = ta.value.substring(0, s) + '    ' + ta.value.substring(end);
                ta.selectionStart = ta.selectionEnd = s + 4;
            }
        });
    });

    window.addEventListener('hashchange', onHash);
    onHash();
}

function onHash() {
    const hash = location.hash.replace('#', '') || 'home';
    if (hash.startsWith('paste-')) {
        const id = hash.substring(6);
        viewPaste(id);
    } else {
        show(hash);
    }
}

function go(name) {
    location.hash = name;
}

function show(name) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const el = document.getElementById('page-' + name);
    if (el) el.classList.add('active');

    if (name === 'create') setTimeout(() => document.getElementById('content')?.focus(), 100);
    if (name === 'lookup') {
        document.getElementById('lookup-key').value = '';
        document.getElementById('lookup-result').innerHTML = '';
        setTimeout(() => document.getElementById('lookup-key')?.focus(), 100);
    }
}

async function handleCreate(e) {
    e.preventDefault();
    const btn = document.getElementById('create-btn');
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
        if (!res.ok) { const err = await res.json(); throw new Error(err.detail); }
        const p = await res.json();
        document.getElementById('title').value = '';
        document.getElementById('content').value = '';
        showToast('Paste created');
        location.hash = 'paste-' + p.id;
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
        showToast('Saved');
        location.hash = 'paste-' + currentPasteId;
    } catch (err) { showToast(err.message); }
}

async function handleLookup(e) {
    e.preventDefault();
    const key = document.getElementById('lookup-key').value.trim().toLowerCase();
    if (!key) return;
    const r = document.getElementById('lookup-result');
    r.innerHTML = '<div class="empty-state">Loading...</div>';
    try {
        const res = await fetch(`${API}/view/${key}`);
        if (!res.ok) { r.innerHTML = '<div class="empty-state">Not found</div>'; return; }
        const p = await res.json();
        location.hash = 'paste-' + p.id;
    } catch { r.innerHTML = '<div class="empty-state">Error</div>'; }
}

function startEdit() {
    if (!currentPasteId) return;
    fetch(`${API}/pastes/${currentPasteId}`).then(r => r.json()).then(p => {
        document.getElementById('edit-title').value = p.title || '';
        document.getElementById('edit-content').value = p.content;
        const sel = document.getElementById('edit-language');
        sel.innerHTML = '';
        LANGUAGES.forEach(l => {
            const o = document.createElement('option');
            o.value = l; o.textContent = l;
            if (l === p.language) o.selected = true;
            sel.appendChild(o);
        });
        show('edit');
    });
}

function viewPaste(id) {
    currentPasteId = id;
    fetch(`${API}/pastes/${id}`).then(r => r.json()).then(p => {
        currentShareKey = p.share_key;
        document.getElementById('paste-title').textContent = p.title || 'Untitled';
        document.getElementById('paste-lang').textContent = p.language;
        document.getElementById('paste-date').textContent = fmtDate(p.created_at);
        document.getElementById('paste-views').textContent = p.views + ' view' + (p.views !== 1 ? 's' : '');
        document.getElementById('paste-share-key').textContent = p.share_key;
        document.getElementById('paste-share-url').value = location.origin + '/view/' + p.share_key;
        const c = document.getElementById('paste-code');
        c.textContent = p.content;
        c.className = 'language-' + p.language;
        if (window.hljs) hljs.highlightElement(c);
        show('paste');
    }).catch(() => { showToast('Not found'); go('home'); });
}

function copyToClipboard(text) {
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).catch(() => fbCopy(text));
    else fbCopy(text);
}
function fbCopy(text) {
    const t = document.createElement('textarea');
    t.value = text; t.style.position = 'fixed'; t.style.left = '-9999px';
    document.body.appendChild(t); t.select(); document.execCommand('copy');
    document.body.removeChild(t);
}
function copyKey() { if (currentShareKey) { copyToClipboard(currentShareKey); showToast('Copied'); } }
function copyLink() { const u = location.origin + '/view/' + currentShareKey; copyToClipboard(u); showToast('Link copied'); }

async function deletePaste() {
    if (!currentPasteId) return;
    if (!confirm('Delete?')) return;
    try {
        await fetch(`${API}/pastes/${currentPasteId}`, { method: 'DELETE' });
        showToast('Deleted');
        go('home');
    } catch { showToast('Error'); }
}

function fmtDate(iso) {
    const d = new Date(iso), diff = (Date.now() - d) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

document.addEventListener('DOMContentLoaded', init);
