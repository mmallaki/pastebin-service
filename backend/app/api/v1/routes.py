from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.schemas import (
    PasteCreate, PasteUpdate, PasteResponse,
    PasteListResponse, StatsResponse
)
from app.services import PasteService
from app.core import settings

router = APIRouter()


@router.post("/pastes", response_model=PasteResponse, status_code=201)
async def create_paste(
    paste_data: PasteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    service = PasteService(db)
    paste = await service.create_paste(
        paste_data,
        ip_address=request.client.host
    )
    return paste.to_dict()


@router.get("/pastes/{paste_id}", response_model=PasteResponse)
async def get_paste(
    paste_id: str,
    db: AsyncSession = Depends(get_db)
):
    service = PasteService(db)
    paste = await service.get_paste(paste_id)

    if not paste:
        raise HTTPException(status_code=404, detail="Paste not found")

    return paste.to_dict()


@router.delete("/pastes/{paste_id}", status_code=204)
async def delete_paste(
    paste_id: str,
    db: AsyncSession = Depends(get_db)
):
    service = PasteService(db)
    deleted = await service.delete_paste(paste_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Paste not found")

    return None


@router.put("/pastes/{paste_id}", response_model=PasteResponse)
async def update_paste(
    paste_id: str,
    paste_data: PasteUpdate,
    db: AsyncSession = Depends(get_db)
):
    service = PasteService(db)
    paste = await service.update_paste(paste_id, paste_data)

    if not paste:
        raise HTTPException(status_code=404, detail="Paste not found")

    return paste.to_dict()


@router.get("/pastes", response_model=PasteListResponse)
async def list_pastes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    language: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    service = PasteService(db)
    pastes, total = await service.list_pastes(
        page=page,
        per_page=per_page,
        language=language,
        search=search
    )

    return {
        "pastes": [p.to_dict() for p in pastes],
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    service = PasteService(db)
    return await service.get_stats()


@router.get("/languages")
async def get_supported_languages():
    return {
        "languages": [
            "python", "javascript", "typescript", "java", "c", "cpp",
            "csharp", "go", "rust", "ruby", "php", "swift", "kotlin",
            "html", "css", "sql", "bash", "powershell", "yaml", "json",
            "markdown", "plaintext"
        ]
    }
