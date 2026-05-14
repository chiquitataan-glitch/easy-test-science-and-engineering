import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.enums import PaperStatus
from app.models.generated_paper import GeneratedPaper
from app.models.paper_question import PaperQuestion
from app.models.user import User
from app.schemas.paper import GeneratePaperRequest, PaperResponse, QuestionItem
from app.services import paper_generator as paper_generator_service
from app.services.docx_exporter import export_paper_from_model

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.post("/generate", response_model=PaperResponse)
async def generate_paper(
    body: GeneratePaperRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = await paper_generator_service.generate_paper(
            user=current_user,
            course_name=body.courseName,
            doc_ids=body.documentIds,
            config=body.config,
            category=body.category,
            client_type="web",
        )
        return result
    except paper_generator_service.QuotaExceededError as e:
        raise HTTPException(
            status_code=402,
            detail={"code": "QUOTA_EXCEEDED", "message": e.message},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("unexpected error in generate_paper")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_papers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    count_q = select(func.count(GeneratedPaper.id)).where(
        GeneratedPaper.userId == current_user.id
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * pageSize
    result = await db.execute(
        select(GeneratedPaper)
        .where(GeneratedPaper.userId == current_user.id)
        .options(selectinload(GeneratedPaper.paperQuestions))
        .order_by(GeneratedPaper.createdAt.desc())
        .offset(offset)
        .limit(pageSize)
    )
    rows = result.scalars().all()
    items = [_paper_to_list_item(p) for p in rows]

    return {"items": items, "total": total, "page": page, "pageSize": pageSize}


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedPaper)
        .where(GeneratedPaper.id == paper_id)
        .options(selectinload(GeneratedPaper.paperQuestions))
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="paper not found")
    if paper.userId != current_user.id:
        raise HTTPException(status_code=404, detail="paper not found")
    return _paper_to_response(paper)


@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedPaper).where(GeneratedPaper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="paper not found")
    if paper.userId != current_user.id:
        raise HTTPException(status_code=404, detail="paper not found")
    await db.delete(paper)
    await db.commit()
    return {"status": "deleted"}


@router.post("/{paper_id}/regenerate")
async def regenerate_paper(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedPaper).where(GeneratedPaper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="paper not found")
    if paper.userId != current_user.id:
        raise HTTPException(status_code=404, detail="paper not found")

    try:
        doc_ids = paper.documentIds if isinstance(paper.documentIds, list) else []
        result = await paper_generator_service.generate_paper(
            user=current_user,
            course_name=paper.courseName,
            doc_ids=doc_ids,
            config=paper.config,
            category=paper.category or "general",
            client_type="web",
            original_paper_id=paper_id,
        )
        return result
    except paper_generator_service.QuotaExceededError as e:
        raise HTTPException(
            status_code=402,
            detail={"code": "QUOTA_EXCEEDED", "message": e.message},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("unexpected error in regenerate_paper")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{paper_id}/export")
async def export_paper_docx(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedPaper)
        .where(GeneratedPaper.id == paper_id)
        .options(selectinload(GeneratedPaper.paperQuestions))
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="paper not found")
    if paper.userId != current_user.id:
        raise HTTPException(status_code=404, detail="paper not found")

    questions = paper.paperQuestions or []
    if not questions:
        raise HTTPException(status_code=400, detail="no questions to export")

    try:
        docx_bytes = export_paper_from_model(paper, questions)
    except Exception as e:
        logger.exception("failed to export paper %s", paper_id)
        raise HTTPException(status_code=500, detail=str(e))

    filename = f"{paper.paperTitle or paper.courseName or '试卷'}.docx"
    encoded_filename = quote(filename)

    safe_filename = "exam_paper.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{encoded_filename}"
            ),
        },
    )


def _paper_to_list_item(paper: GeneratedPaper) -> dict:
    quality_score = None
    if isinstance(paper.qualityReport, dict):
        quality_score = paper.qualityReport.get("score")
    return {
        "id": paper.id,
        "paperTitle": paper.paperTitle,
        "courseName": paper.courseName,
        "questionCount": len(paper.paperQuestions or []),
        "qualityScore": quality_score,
        "status": paper.status.value if isinstance(paper.status, PaperStatus) else paper.status,
        "createdAt": paper.createdAt.isoformat() if paper.createdAt else None,
    }


def _paper_to_response(paper: GeneratedPaper) -> dict:
    questions = []
    for pq in paper.paperQuestions or []:
        questions.append(
            QuestionItem(
                id=pq.id,
                questionNo=pq.questionNo,
                questionType=pq.questionType,
                content=pq.content,
                options=pq.options,
                answer=pq.answer,
                analysis=pq.analysis,
                knowledgePoints=pq.knowledgePoints,
                difficulty=pq.difficulty,
                score=pq.score,
                sourceChunkIds=pq.sourceChunkIds,
                isCrossDoc=pq.isCrossDoc,
            )
        )

    quality_score = None
    if isinstance(paper.qualityReport, dict):
        quality_score = paper.qualityReport.get("score")

    return {
        "id": paper.id,
        "userId": paper.userId,
        "courseName": paper.courseName,
        "paperTitle": paper.paperTitle,
        "paperJson": paper.paperJson,
        "status": paper.status.value if isinstance(paper.status, PaperStatus) else paper.status,
        "questionCount": len(paper.paperQuestions or []),
        "totalScore": sum(q.score or 0 for q in (paper.paperQuestions or [])),
        "qualityScore": quality_score,
        "durationSeconds": paper.durationSeconds,
        "category": paper.category,
        "config": paper.config,
        "retrievalMode": "rag" if paper.sourceChunks else "prompt",
        "knowledgeSummary": paper.knowledgeSummary,
        "qualityReport": paper.qualityReport,
        "questions": questions,
        "failReason": paper.failReason,
        "modelName": paper.modelName,
        "promptVersion": paper.promptVersion,
        "tokenUsage": paper.tokenUsage,
        "originalPaperId": paper.originalPaperId,
        "createdAt": paper.createdAt.isoformat() if paper.createdAt else None,
    }
