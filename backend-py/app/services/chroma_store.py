import chromadb
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.document_chunk import DocumentChunk

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _client


def get_collection_name(category: str, user_id: str) -> str:
    return f"{category}_{user_id}"


def get_or_create_collection(category: str, user_id: str):
    client = _get_client()
    name = get_collection_name(category, user_id)
    return client.get_or_create_collection(name=name)


async def add_chunks_to_chroma(
    category: str,
    user_id: str,
    chunks: list[dict],
):
    if not chunks:
        return

    from app.services.embedder import embed_chunks

    texts = [c["content"] for c in chunks]
    vectors = embed_chunks(texts)

    collection = get_or_create_collection(category, user_id)

    ids = [f"{c['fileId']}_{c['chunkIndex']}" for c in chunks]
    metadatas = [
        {"file_id": c["fileId"], "chunk_index": c["chunkIndex"], "category": category}
        for c in chunks
    ]

    collection.add(embeddings=vectors, documents=texts, metadatas=metadatas, ids=ids)

    async with async_session() as session:
        for c, chroma_id in zip(chunks, ids):
            result = await session.execute(
                select(DocumentChunk).where(
                    DocumentChunk.fileId == c["fileId"],
                    DocumentChunk.chunkIndex == c["chunkIndex"],
                )
            )
            doc_chunk = result.scalar_one_or_none()
            if doc_chunk:
                doc_chunk.chromaId = chroma_id

        await session.commit()


async def delete_document_vectors(file_id: str, category: str, user_id: str):
    collection = get_or_create_collection(category, user_id)

    async with async_session() as session:
        result = await session.execute(
            select(DocumentChunk).where(DocumentChunk.fileId == file_id)
        )
        chunks = result.scalars().all()
        chroma_ids = [c.chromaId for c in chunks if c.chromaId]

        if chroma_ids:
            collection.delete(ids=chroma_ids)

            for chunk in chunks:
                chunk.chromaId = None

            await session.commit()
