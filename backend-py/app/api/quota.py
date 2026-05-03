from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.generated_paper import GeneratedPaper
from app.models.generation_log import GenerationLog
from app.models.user import User

router = APIRouter(prefix="/api/quota", tags=["quota"])


@router.get("/")
async def get_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {
        "remainingGenerations": current_user.remainingGenerations,
        "membershipType": current_user.membershipType,
    }


@router.get("/me")
async def get_quota_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_papers_result = await db.execute(
        select(func.count(GeneratedPaper.id)).where(
            GeneratedPaper.userId == current_user.id
        )
    )
    total_papers = total_papers_result.scalar() or 0

    total_gen_result = await db.execute(
        select(func.count(GenerationLog.id)).where(
            GenerationLog.userId == current_user.id
        )
    )
    total_generations = total_gen_result.scalar() or 0

    quota_total = current_user.remainingGenerations
    if current_user.membershipType != "free":
        quota_total = -1

    return {
        "quotaTotal": quota_total,
        "quotaUsed": total_generations,
        "quotaRemaining": quota_total if quota_total == -1 else max(0, quota_total - total_generations),
        "membershipType": current_user.membershipType,
        "membershipExpire": current_user.membershipExpire.isoformat() if current_user.membershipExpire else None,
        "totalPapers": total_papers,
        "remainingGenerations": current_user.remainingGenerations,
    }


@router.get("/history")
async def get_quota_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GenerationLog)
        .where(GenerationLog.userId == current_user.id)
        .order_by(GenerationLog.createdAt.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action": log.mode,
            "status": log.status,
            "questionCount": log.questionCount,
            "tokenUsed": log.tokenUsed,
            "durationMs": log.durationMs,
            "createdAt": log.createdAt.isoformat() if log.createdAt else None,
        }
        for log in logs
    ]
