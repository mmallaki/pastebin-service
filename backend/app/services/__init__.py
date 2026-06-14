from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import json

from app.models import Paste
from app.schemas import PasteCreate, PasteUpdate
from app.core.database import redis_client


class PasteService:
    EXPIRATION_MAP = {
        "10min": timedelta(minutes=10),
        "1hr": timedelta(hours=1),
        "1day": timedelta(days=1),
        "1week": timedelta(weeks=1),
        "never": None,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_paste(self, paste_data: PasteCreate, ip_address: str = None) -> Paste:
        paste = Paste(
            title=paste_data.title,
            content=paste_data.content,
            language=paste_data.language,
            expiration=paste_data.expiration.value,
            is_private=paste_data.is_private,
        )

        if paste_data.expiration != "never":
            paste.expires_at = datetime.utcnow() + self.EXPIRATION_MAP[paste_data.expiration.value]

        self.db.add(paste)
        await self.db.commit()
        await self.db.refresh(paste)

        await redis_client.setex(
            f"paste:{paste.id}",
            300,
            json.dumps(paste.to_dict())
        )

        return paste

    async def get_paste(self, paste_id: str) -> Paste | None:
        cached = await redis_client.get(f"paste:{paste_id}")
        if cached:
            paste_data = json.loads(cached)
            paste = Paste(**paste_data)
            paste.views += 1
            await self.db.commit()
            return paste

        result = await self.db.execute(
            select(Paste).where(Paste.id == paste_id)
        )
        paste = result.scalar_one_or_none()

        if paste:
            if paste.expires_at and paste.expires_at < datetime.utcnow():
                await self.delete_paste(paste_id)
                return None

            paste.views += 1
            await self.db.commit()

            await redis_client.setex(
                f"paste:{paste.id}",
                300,
                json.dumps(paste.to_dict())
            )

        return paste

    async def delete_paste(self, paste_id: str) -> bool:
        result = await self.db.execute(
            select(Paste).where(Paste.id == paste_id)
        )
        paste = result.scalar_one_or_none()

        if paste:
            await self.db.delete(paste)
            await self.db.commit()
            await redis_client.delete(f"paste:{paste_id}")
            return True

        return False

    async def list_pastes(
        self,
        page: int = 1,
        per_page: int = 20,
        language: str = None,
        search: str = None
    ) -> tuple[list[Paste], int]:
        query = select(Paste).where(
            or_(
                Paste.expires_at.is_(None),
                Paste.expires_at > datetime.utcnow()
            )
        )

        if language:
            query = query.where(Paste.language == language)

        if search:
            query = query.where(
                Paste.content.ilike(f"%{search}%") |
                Paste.title.ilike(f"%{search}%")
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        query = query.order_by(Paste.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(query)
        pastes = result.scalars().all()

        return pastes, total

    async def get_stats(self) -> dict:
        total = (await self.db.execute(select(func.count(Paste.id)))).scalar()
        active = (await self.db.execute(
            select(func.count(Paste.id)).where(
                or_(
                    Paste.expires_at.is_(None),
                    Paste.expires_at > datetime.utcnow()
                )
            )
        )).scalar()

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        pastes_today = (await self.db.execute(
            select(func.count(Paste.id)).where(Paste.created_at >= today)
        )).scalar()

        top_langs = (await self.db.execute(
            select(Paste.language, func.count(Paste.id))
            .group_by(Paste.language)
            .order_by(func.count(Paste.id).desc())
            .limit(10)
        )).all()

        return {
            "total_pastes": total,
            "active_pastes": active,
            "pastes_today": pastes_today,
            "top_languages": [{"language": lang, "count": count} for lang, count in top_langs]
        }


async def cleanup_expired_pastes(db: AsyncSession = None):
    own_session = db is None
    if own_session:
        from app.core.database import AsyncSessionLocal
        db = AsyncSessionLocal()

    try:
        result = await db.execute(
            select(Paste.id).where(
                Paste.expires_at.isnot(None),
                Paste.expires_at < datetime.utcnow(),
            )
        )
        expired_ids = [row[0] for row in result.all()]

        if not expired_ids:
            return 0

        for paste_id in expired_ids:
            await redis_client.delete(f"paste:{paste_id}")

        await db.execute(
            Paste.__table__.delete().where(Paste.id.in_(expired_ids))
        )
        await db.commit()

        return len(expired_ids)
    finally:
        if own_session:
            await db.close()

