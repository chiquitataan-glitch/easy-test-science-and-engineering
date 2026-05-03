from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    id: str
    original_name: str
    size_bytes: int
    status: str


class FileListResponse(BaseModel):
    id: str
    original_name: str
    mime_type: str
    size_bytes: int
    status: str
    category: str | None
    created_at: str


class FilePaginatedResponse(BaseModel):
    items: list[FileListResponse]
    total: int
    page: int
    page_size: int


class FileDetailResponse(BaseModel):
    id: str
    original_name: str
    mime_type: str
    size_bytes: int
    status: str
    category: str | None
    category_confidence: float | None
    chunk_count: int
    total_chars: int
    created_at: str


class FileDeleteResponse(BaseModel):
    id: str
    original_name: str
