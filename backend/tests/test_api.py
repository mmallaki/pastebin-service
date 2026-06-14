import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core import settings
from app.core.database import Base, get_db
from app.models import Paste
import app.middleware.rate_limit as rate_limit_mod
import app.services as services_mod
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///./test_pastebin.db"


class MockRedis:
    def __init__(self):
        self._store = {}

    async def setex(self, key, ttl, value):
        self._store[key] = value

    async def get(self, key):
        return self._store.get(key)

    async def delete(self, key):
        self._store.pop(key, None)

    class _Pipeline:
        def __init__(self, store):
            self._store = store
            self._commands = []

        def incr(self, key):
            self._commands.append(("incr", key))

        def expire(self, key, ttl):
            self._commands.append(("expire", key, ttl))

        async def execute(self):
            return [True] * len(self._commands)

    def pipeline(self):
        return self._Pipeline(self._store)


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    mock_redis = MockRedis()
    with patch.object(rate_limit_mod, "redis_client", mock_redis), \
         patch.object(services_mod, "redis_client", mock_redis):
        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "Pastebin" in r.json()["message"]


@pytest.mark.asyncio
async def test_create_paste(client):
    r = await client.post("/api/v1/pastes", json={
        "content": "print('hello')",
        "language": "python",
        "title": "test",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "print('hello')"
    assert data["language"] == "python"
    assert data["title"] == "test"
    assert data["id"]


@pytest.mark.asyncio
async def test_get_paste(client):
    r = await client.post("/api/v1/pastes", json={"content": "x", "language": "text"})
    paste_id = r.json()["id"]

    r = await client.get(f"/api/v1/pastes/{paste_id}")
    assert r.status_code == 200
    assert r.json()["id"] == paste_id


@pytest.mark.asyncio
async def test_get_paste_not_found(client):
    r = await client.get("/api/v1/pastes/nonexistent")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_pastes(client):
    await client.post("/api/v1/pastes", json={"content": "a", "language": "python"})
    await client.post("/api/v1/pastes", json={"content": "b", "language": "javascript"})

    r = await client.get("/api/v1/pastes")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2
    assert len(data["pastes"]) >= 2


@pytest.mark.asyncio
async def test_list_pastes_filter_language(client):
    await client.post("/api/v1/pastes", json={"content": "py", "language": "python"})
    await client.post("/api/v1/pastes", json={"content": "js", "language": "javascript"})

    r = await client.get("/api/v1/pastes", params={"language": "python"})
    assert r.status_code == 200
    for p in r.json()["pastes"]:
        assert p["language"] == "python"


@pytest.mark.asyncio
async def test_delete_paste(client):
    r = await client.post("/api/v1/pastes", json={"content": "del", "language": "text"})
    paste_id = r.json()["id"]

    r = await client.delete(f"/api/v1/pastes/{paste_id}")
    assert r.status_code == 204

    r = await client.get(f"/api/v1/pastes/{paste_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_paste_not_found(client):
    r = await client.delete("/api/v1/pastes/nonexistent")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_languages(client):
    r = await client.get("/api/v1/languages")
    assert r.status_code == 200
    assert "python" in r.json()["languages"]


@pytest.mark.asyncio
async def test_stats(client):
    await client.post("/api/v1/pastes", json={"content": "s", "language": "python"})
    r = await client.get("/api/v1/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_pastes"] >= 1
    assert data["active_pastes"] >= 1


@pytest.mark.asyncio
async def test_create_paste_validation(client):
    r = await client.post("/api/v1/pastes", json={"content": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_cache_hit(client):
    r = await client.post("/api/v1/pastes", json={"content": "cache", "language": "text"})
    paste_id = r.json()["id"]

    r1 = await client.get(f"/api/v1/pastes/{paste_id}")
    r2 = await client.get(f"/api/v1/pastes/{paste_id}")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_metrics(client):
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text


@pytest.mark.asyncio
async def test_cleanup_removes_expired_pastes(client, db_session):
    from app.services import cleanup_expired_pastes

    # Create an expired paste directly in DB
    expired = Paste(content="expired", language="text", expiration="10min",
                    expires_at=datetime.utcnow() - timedelta(minutes=5))
    db_session.add(expired)
    await db_session.commit()
    expired_id = expired.id

    # Create a live paste
    live = Paste(content="alive", language="text", expiration="never")
    db_session.add(live)
    await db_session.commit()
    live_id = live.id

    count = await cleanup_expired_pastes(db=db_session)
    assert count == 1

    # Expired should be gone
    from sqlalchemy import select
    r = await db_session.execute(select(Paste).where(Paste.id == expired_id))
    assert r.scalar_one_or_none() is None

    # Live should remain
    r = await db_session.execute(select(Paste).where(Paste.id == live_id))
    assert r.scalar_one_or_none() is not None
