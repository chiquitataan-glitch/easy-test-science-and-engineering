from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.auth import router as auth_router
from app.api.files import router as files_router
from app.api.papers import router as papers_router
from app.api.quota import router as quota_router
from app.api.admin import router as admin_router
from app.database import init_db
from app.middleware.response import response_wrapper

app = FastAPI(title="Easy Test API", version="0.2.0")

app.middleware("http")(response_wrapper)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(files_router)
app.include_router(papers_router)
app.include_router(quota_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.on_event("startup")
async def on_startup():
    await init_db()
