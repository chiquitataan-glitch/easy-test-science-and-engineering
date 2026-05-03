from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.models.document_chunk import DocumentChunk
from app.models.uploaded_file import UploadedFile
from app.models.enums import FileStatus


async def chunk_document(
    db: AsyncSession,
    file_id: str,
    text: str,
    metadata: dict | None = None,
) -> list[dict]:
    if not text or not text.strip():
        stmt = (
            update(UploadedFile)
            .where(UploadedFile.id == file_id)
            .values(status=FileStatus.failed, errorMessage="无有效文本内容")
        )
        await db.execute(stmt)
        await db.commit()
        return []

    metadata = metadata or {}
    page_number = metadata.get("page_number")
    section_title = metadata.get("section_title")
    doc_name = metadata.get("doc_name")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )

    chunk_texts = splitter.split_text(text)

    results = []
    for index, chunk_content in enumerate(chunk_texts):
        char_count = len(chunk_content)
        token_estimate = int(char_count / 1.5)

        chunk = DocumentChunk(
            fileId=file_id,
            chunkIndex=index,
            content=chunk_content,
            charCount=char_count,
            tokenEstimate=token_estimate,
            pageNumber=page_number,
            sectionTitle=section_title,
        )
        db.add(chunk)
        results.append({
            "chunk_id": chunk.id,
            "chunk_index": index,
            "char_count": char_count,
            "token_estimate": token_estimate,
            "doc_name": doc_name,
            "page_number": page_number,
            "section_title": section_title,
        })

    stmt = (
        update(UploadedFile)
        .where(UploadedFile.id == file_id)
        .values(
            chunkCount=len(chunk_texts),
            totalChars=len(text),
            status=FileStatus.chunking,
            errorMessage=None,
        )
    )
    await db.execute(stmt)
    await db.commit()

    return results
