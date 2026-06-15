import pytest
import redis.asyncio as aioredis
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core import settings
from app.core.database import Base, get_db
from app.models import Paste
import app.middleware.rate_limit as rate_limit_mod
import app.services as services_mod
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///./test_pastebin.db"
TEST_REDIS_DB = 15


@pytest.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def db_session(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def test_redis():
    r = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=TEST_REDIS_DB,
        decode_responses=True,
    )
    await r.flushdb()
    yield r
    await r.flushdb()
    await r.aclose()


@pytest.fixture
async def client(db_session, test_redis):
    async def override_get_db():
        yield db_session

    original_rate_limit = rate_limit_mod.redis_client
    original_services = services_mod.redis_client
    rate_limit_mod.redis_client = test_redis
    services_mod.redis_client = test_redis

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    rate_limit_mod.redis_client = original_rate_limit
    services_mod.redis_client = original_services


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "Pastebin" in r.json()["message"]


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


async def test_get_paste(client):
    r = await client.post("/api/v1/pastes", json={"content": "x", "language": "text"})
    paste_id = r.json()["id"]

    r = await client.get(f"/api/v1/pastes/{paste_id}")
    assert r.status_code == 200
    assert r.json()["id"] == paste_id


async def test_get_paste_not_found(client):
    r = await client.get("/api/v1/pastes/nonexistent")
    assert r.status_code == 404


async def test_list_pastes(client):
    await client.post("/api/v1/pastes", json={"content": "a", "language": "python"})
    await client.post("/api/v1/pastes", json={"content": "b", "language": "javascript"})

    r = await client.get("/api/v1/pastes")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2
    assert len(data["pastes"]) >= 2


async def test_list_pastes_filter_language(client):
    await client.post("/api/v1/pastes", json={"content": "py", "language": "python"})
    await client.post("/api/v1/pastes", json={"content": "js", "language": "javascript"})

    r = await client.get("/api/v1/pastes", params={"language": "python"})
    assert r.status_code == 200
    for p in r.json()["pastes"]:
        assert p["language"] == "python"


async def test_delete_paste(client):
    r = await client.post("/api/v1/pastes", json={"content": "del", "language": "text"})
    paste_id = r.json()["id"]

    r = await client.delete(f"/api/v1/pastes/{paste_id}")
    assert r.status_code == 204

    r = await client.get(f"/api/v1/pastes/{paste_id}")
    assert r.status_code == 404


async def test_delete_paste_not_found(client):
    r = await client.delete("/api/v1/pastes/nonexistent")
    assert r.status_code == 404


async def test_languages(client):
    r = await client.get("/api/v1/languages")
    assert r.status_code == 200
    assert "python" in r.json()["languages"]


async def test_stats(client):
    await client.post("/api/v1/pastes", json={"content": "s", "language": "python"})
    r = await client.get("/api/v1/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_pastes"] >= 1
    assert data["active_pastes"] >= 1


async def test_create_paste_validation(client):
    r = await client.post("/api/v1/pastes", json={"content": ""})
    assert r.status_code == 422


async def test_cache_hit(client, test_redis):
    r = await client.post("/api/v1/pastes", json={"content": "cache", "language": "text"})
    paste_id = r.json()["id"]

    r1 = await client.get(f"/api/v1/pastes/{paste_id}")
    assert r1.status_code == 200

    cached = await test_redis.get(f"paste:{paste_id}")
    assert cached is not None

    r2 = await client.get(f"/api/v1/pastes/{paste_id}")
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


async def test_cache_invalidation_on_delete(client, test_redis):
    r = await client.post("/api/v1/pastes", json={"content": "invalidate", "language": "text"})
    paste_id = r.json()["id"]

    await client.get(f"/api/v1/pastes/{paste_id}")
    assert await test_redis.get(f"paste:{paste_id}") is not None

    await client.delete(f"/api/v1/pastes/{paste_id}")
    assert await test_redis.get(f"paste:{paste_id}") is None


async def test_rate_limit_headers(client):
    r = await client.get("/api/v1/languages")
    assert "x-ratelimit-limit" in r.headers
    assert "x-ratelimit-remaining" in r.headers


async def test_metrics(client):
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text


async def test_cleanup_removes_expired_pastes(db_session):
    from app.services import cleanup_expired_pastes
    from sqlalchemy import select

    expired = Paste(content="expired", language="text", expiration="10min",
                    expires_at=datetime.utcnow() - timedelta(minutes=5))
    db_session.add(expired)
    await db_session.commit()
    expired_id = expired.id

    live = Paste(content="alive", language="text", expiration="never")
    db_session.add(live)
    await db_session.commit()
    live_id = live.id

    count = await cleanup_expired_pastes(db=db_session)
    assert count == 1

    r = await db_session.execute(select(Paste).where(Paste.id == expired_id))
    assert r.scalar_one_or_none() is None

    r = await db_session.execute(select(Paste).where(Paste.id == live_id))
    assert r.scalar_one_or_none() is not None
