from sqlalchemy import Column, String, Text, DateTime, Integer, Index
from sqlalchemy.sql import func
import uuid
import secrets
import string

from app.core.database import Base


def generate_share_key():
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


class Paste(Base):
    __tablename__ = "pastes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    share_key = Column(String(8), unique=True, index=True, default=generate_share_key)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    language = Column(String(50), default="text")
    expiration = Column(String(20), default="never")
    views = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_pastes_created_at", "created_at"),
        Index("idx_pastes_expires_at", "expires_at"),
        Index("idx_pastes_language", "language"),
    )

    def to_dict(self):
        def _fmt(val):
            return val.isoformat() if hasattr(val, 'isoformat') else val

        return {
            "id": self.id,
            "share_key": self.share_key,
            "title": self.title,
            "content": self.content,
            "language": self.language,
            "expiration": self.expiration,
            "views": self.views,
            "created_at": _fmt(self.created_at),
            "updated_at": _fmt(self.updated_at),
            "expires_at": _fmt(self.expires_at),
        }
