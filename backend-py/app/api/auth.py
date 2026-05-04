from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user, bearer_scheme
from app.models.enums import IdentityProvider
from app.models.generated_paper import GeneratedPaper
from app.models.generation_log import GenerationLog
from app.models.user import User, UserIdentity
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse, UserStats
from app.services.auth_service import create_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _provider_str(identity) -> str:
    p = identity.provider
    return p.value if hasattr(p, 'value') else str(p)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.provider == IdentityProvider.password,
            UserIdentity.identifier == body.email,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    password_hash = hash_password(body.password)

    user = User(
        displayName=body.displayName,
        role="user",
        membershipType="free",
        remainingGenerations=settings.DEFAULT_FREE_GENERATIONS,
    )
    db.add(user)
    await db.flush()

    identity = UserIdentity(
        userId=user.id,
        provider=IdentityProvider.password,
        identifier=body.email,
        passwordHash=password_hash,
    )
    db.add(identity)
    await db.commit()

    token = create_token(user.id, user.role, user.membershipType)
    user_resp = _user_to_response(user, body.email, [
        {"id": identity.id, "provider": _provider_str(identity), "identifier": identity.identifier}
    ])
    return TokenResponse(token=token, user=user_resp)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.provider == IdentityProvider.password,
            UserIdentity.identifier == body.email,
        )
    )
    identity = result.scalar_one_or_none()

    if identity is None or identity.passwordHash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
        )

    if not verify_password(body.password, identity.passwordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
        )

    user_result = await db.execute(
        select(User).options(selectinload(User.identities)).where(User.id == identity.userId)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
        )

    token = create_token(user.id, user.role, user.membershipType)
    user_resp = _user_to_response(
        user, body.email,
        [{"id": i.id, "provider": _provider_str(i), "identifier": i.identifier} for i in (user.identities or [])]
    )
    return TokenResponse(token=token, user=user_resp)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_gen_result = await db.execute(
        select(func.count(GenerationLog.id)).where(GenerationLog.userId == current_user.id)
    )
    total_generations = total_gen_result.scalar() or 0

    total_papers_result = await db.execute(
        select(func.count(GeneratedPaper.id)).where(GeneratedPaper.userId == current_user.id)
    )
    total_papers = total_papers_result.scalar() or 0

    month_gen_result = await db.execute(
        select(func.count(GenerationLog.id)).where(
            GenerationLog.userId == current_user.id,
            GenerationLog.createdAt >= month_start,
        )
    )
    month_generations = month_gen_result.scalar() or 0

    stats = UserStats(
        totalGenerations=total_generations,
        totalPapers=total_papers,
        monthGenerations=month_generations,
    )

    email = ""
    for ident in current_user.identities:
        if _provider_str(ident) == "password":
            email = ident.identifier
            break

    resp = _user_to_response(
        current_user, email,
        [{"id": i.id, "provider": _provider_str(i), "identifier": i.identifier} for i in (current_user.identities or [])]
    )
    resp.stats = stats
    return resp


@router.post("/logout")
async def logout(
    credentials=Depends(bearer_scheme),
):
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    credentials=Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="AUTH_REQUIRED",
        )

    token = create_token(user.id, user.role, user.membershipType)
    return TokenResponse(token=token)


def _user_to_response(user: User, email: str = "", identities: list[dict] | None = None) -> UserResponse:
    return UserResponse(
        id=user.id,
        displayName=user.displayName,
        email=email,
        role=user.role,
        membershipType=user.membershipType,
        membershipExpire=user.membershipExpire,
        remainingGenerations=user.remainingGenerations,
        identities=identities or [],
    )
