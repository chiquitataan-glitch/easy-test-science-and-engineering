from fastapi import APIRouter

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def get_stats():
    return {}


@router.get("/users")
async def list_users():
    return []
