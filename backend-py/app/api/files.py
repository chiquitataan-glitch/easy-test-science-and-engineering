import math
import os

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.enums import FileStatus
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.file import (
    FileDeleteResponse,
    FileDetailResponse,
    FileListResponse,
    FilePaginatedResponse,
    FileUploadResponse,
)
from app.services.file_service import (
    ALLOWED_EXTENSIONS,
    MIME_MAP,
    delete_file_record,
    process_file_extraction,
    save_uploaded_file,
)

router = APIRouter(prefix="/api/files", tags=["files"])


def _file_to_list_item(f) -> dict:
    return {
        "id": f.id,
        "original_name": f.originalName,
        "mime_type": f.mimeType,
        "size_bytes": f.size,
        "status": f.status,
        "category": f.category,
        "created_at": f.createdAt.isoformat() if f.createdAt else "",
    }


def _file_to_detail(f) -> dict:
    return {
        "id": f.id,
        "original_name": f.originalName,
        "mime_type": f.mimeType,
        "size_bytes": f.size,
        "status": f.status,
        "category": f.category,
        "category_confidence": f.categoryConfidence,
        "chunk_count": f.chunkCount,
        "total_chars": f.totalChars,
        "created_at": f.createdAt.isoformat() if f.createdAt else "",
    }


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UNSUPPORTED_FILE_TYPE",
        )

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="FILE_TOO_LARGE",
        )

    tmp_path, file_hash, ext_saved = save_uploaded_file(content, file.filename or "unknown")

    existing = await db.execute(
        select(UploadedFile).where(
            and_(UploadedFile.userId == current_user.id, UploadedFile.hash == file_hash)
        )
    )
    dup = existing.scalar_one_or_none()
    if dup is not None:
        if dup.status in (FileStatus.failed, FileStatus.pending):
            await db.delete(dup)
            await db.commit()
        else:
            os.remove(tmp_path)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_FILE",
                    "existing_file_id": dup.id,
                },
            )

    mime_type = MIME_MAP.get(ext_saved, "application/octet-stream")
    file_record = UploadedFile(
        userId=current_user.id,
        originalName=file.filename or "unknown",
        mimeType=mime_type,
        size=len(content),
        path=tmp_path,
        hash=file_hash,
        status=FileStatus.pending,
    )
    db.add(file_record)
    await db.commit()
    await db.refresh(file_record)

    background_tasks.add_task(process_file_extraction, file_record.id)

    return {
        "id": file_record.id,
        "original_name": file_record.originalName,
        "size_bytes": file_record.size,
        "status": file_record.status,
    }


@router.get("/", response_model=FilePaginatedResponse)
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    category: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conditions = [UploadedFile.userId == current_user.id]
    if status:
        conditions.append(UploadedFile.status == status)
    if category:
        conditions.append(UploadedFile.category == category)

    count_q = select(func.count(UploadedFile.id)).where(and_(*conditions))
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    q = (
        select(UploadedFile)
        .where(and_(*conditions))
        .order_by(UploadedFile.createdAt.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    rows = result.scalars().all()

    items = [_file_to_list_item(r) for r in rows]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    if file_record.userId != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _file_to_detail(file_record)


@router.delete("/{file_id}", response_model=FileDeleteResponse)
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    if file_record.userId != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    deleted = await delete_file_record(file_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    return deleted
