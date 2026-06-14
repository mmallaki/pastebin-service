const API = '/api/v1';
let currentPasteId = null;

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
    showView('create');
}

function showView(name) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`view-${name}`).classList.add('active');

    if (name === 'list') loadList();
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

async function viewPaste(id) {
    currentPasteId = id;
    showView('paste');

    try {
        const res = await fetch(`${API}/pastes/${id}`);
        if (!res.ok) throw new Error('Paste not found');
        const paste = await res.json();

        document.getElementById('paste-title').textContent = paste.title || 'Untitled';
        document.getElementById('paste-lang').textContent = paste.language;
        document.getElementById('paste-date').textContent = formatDate(paste.created_at);
        document.getElementById('paste-views').textContent = `${paste.views} view${paste.views !== 1 ? 's' : ''}`;
        document.getElementById('paste-code').textContent = paste.content;
    } catch (err) {
        showToast(err.message);
        showView('list');
    }
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

async function loadList() {
    const container = document.getElementById('paste-list');
    container.innerHTML = '<div class="empty-state">Loading...</div>';

    try {
        const res = await fetch(`${API}/pastes?per_page=50`);
        const data = await res.json();

        if (data.pastes.length === 0) {
            container.innerHTML = '<div class="empty-state">No pastes yet. Create one!</div>';
            return;
        }

        container.innerHTML = data.pastes.map(p => `
            <a class="paste-item" href="#" onclick="viewPaste('${p.id}'); return false;">
                <div class="paste-item-info">
                    <span class="paste-item-title">${escapeHtml(p.title || 'Untitled')}</span>
                    <span class="paste-item-meta">${formatDate(p.created_at)} &middot; ${p.views} view${p.views !== 1 ? 's' : ''}</span>
                </div>
                <span class="paste-item-lang">${p.language}</span>
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
