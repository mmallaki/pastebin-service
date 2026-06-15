import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core import settings
from app.core.database import engine, Base
from app.api.v1.routes import router as api_router
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.services import cleanup_expired_pastes


async def _cleanup_loop():
    while True:
        try:
            await cleanup_expired_pastes()
        except Exception:
            pass
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()
    await engine.dispose()


app = FastAPI(
    title="Pastebin Service API",
    description="A comprehensive pastebin service with syntax highlighting and expiration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from starlette.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    return {"message": "Pastebin Service API", "docs": "/docs"}


@app.get("/view/{share_key}")
async def view_share(share_key: str):
    from starlette.responses import HTMLResponse
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#080c10">
<title>Paste - {share_key}</title>
<link rel="stylesheet" href="/static/style.css?v=3">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
</head>
<body>
<main style="max-width:640px;margin:0 auto;padding:0 16px;padding-top:24px">
<div id="loading" class="empty-state">Loading paste...</div>
<div id="paste-view" style="display:none">
<a class="back" href="/static/index.html">&larr; Home</a>
<h2 id="paste-title"></h2>
<div class="meta">
<span id="paste-lang" class="badge"></span>
<span id="paste-date"></span>
<span id="paste-views"></span>
</div>
<div class="share-row">
<code id="paste-share-key"></code>
<button class="sm" onclick="copyKey()">Copy Key</button>
<button class="sm" onclick="copyLink()">Copy Link</button>
</div>
<input type="text" id="paste-share-url" readonly onclick="this.select();copyLink()" style="font-family:var(--mono);font-size:12px;color:var(--accent);cursor:pointer;margin-bottom:12px">
<div class="sunken">
<pre><code id="paste-code"></code></pre>
</div>
</div>
<div id="not-found" style="display:none;text-align:center;padding:40px 16px">
<div style="font-size:48px;margin-bottom:16px">?</div>
<h2 style="color:var(--text);margin-bottom:8px">Paste not found</h2>
<p style="color:var(--dim);font-size:14px;margin-bottom:24px">This paste may have been deleted or expired.</p>
<a href="/static/index.html" style="display:inline-block;background:var(--accent);color:#fff;border:none;padding:10px 24px;border-radius:6px;font-size:14px;text-decoration:none">Create New Paste</a>
</div>
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script>
const SHARE_KEY = '{share_key}';
function copyToClipboard(text) {{
  if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).catch(() => fbCopy(text));
  else fbCopy(text);
}}
function fbCopy(text) {{
  const t = document.createElement('textarea');
  t.value = text; t.style.position = 'fixed'; t.style.left = '-9999px';
  document.body.appendChild(t); t.select(); document.execCommand('copy');
  document.body.removeChild(t);
}}
function copyKey() {{ copyToClipboard(SHARE_KEY); showToast('Copied'); }}
function copyLink() {{ copyToClipboard(location.href); showToast('Link copied'); }}
function showToast(msg) {{
  let t = document.getElementById('toast');
  if (!t) {{ t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; document.body.appendChild(t); }}
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}}
fetch('/api/v1/view/' + SHARE_KEY)
  .then(r => {{ if (!r.ok) throw new Error(); return r.json(); }})
  .then(p => {{
    document.getElementById('loading').style.display = 'none';
    document.getElementById('paste-view').style.display = 'block';
    document.getElementById('paste-title').textContent = p.title || 'Untitled';
    document.getElementById('paste-lang').textContent = p.language;
    document.getElementById('paste-date').textContent = new Date(p.created_at).toLocaleString();
    document.getElementById('paste-views').textContent = p.views + ' views';
    document.getElementById('paste-share-key').textContent = p.share_key;
    document.getElementById('paste-share-url').value = location.href;
    const code = document.getElementById('paste-code');
    code.textContent = p.content;
    code.className = 'language-' + p.language;
    if (window.hljs) hljs.highlightElement(code);
    document.title = (p.title || 'Untitled') + ' - Pastebin';
  }})
  .catch(() => {{
    document.getElementById('loading').style.display = 'none';
    document.getElementById('not-found').style.display = 'block';
  }});
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
