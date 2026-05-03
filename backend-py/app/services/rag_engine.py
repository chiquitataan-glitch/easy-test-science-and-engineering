import logging
from difflib import SequenceMatcher

from sqlalchemy import select

from app.database import async_session
from app.models.document_chunk import DocumentChunk
from app.models.uploaded_file import UploadedFile
from app.services import chroma_store

logger = logging.getLogger(__name__)

MAX_TOKEN_BUDGET = 4000
MAX_K = 100
MIN_K = 10
DEDUP_SIMILARITY_THRESHOLD = 0.95
DEGRADED_MIN_CHUNKS = 3


async def retrieve_relevant_chunks(
    doc_ids: list[str],
    question_count: int,
    category: str,
    user_id: str,
) -> dict:
    K = max(MIN_K, min(question_count * 2, MAX_K))

    if not doc_ids:
        logger.warning("doc_ids is empty, returning degraded result")
        return {"chunks": [], "retrieval_degraded": True}

    query_text = await _build_query_text(doc_ids)

    raw_results = _query_chroma(query_text, K, category, user_id, doc_ids)
    if raw_results is None:
        logger.warning("Chroma query failed, returning degraded result")
        return {"chunks": [], "retrieval_degraded": True}

    if not raw_results:
        logger.info("Chroma returned 0 results")
        return {"chunks": [], "retrieval_degraded": True}

    chunks = _parse_chroma_results(raw_results)
    if not chunks:
        return {"chunks": [], "retrieval_degraded": True}

    chunks.sort(key=lambda x: x["score"], reverse=True)

    chunks = _dedup_by_content(chunks, DEDUP_SIMILARITY_THRESHOLD)

    chunks = await _populate_token_estimates(chunks)

    chunks = _truncate_by_token_budget(chunks, MAX_TOKEN_BUDGET)

    chunks = await _enrich_with_doc_name(chunks)

    retrieval_degraded = len(chunks) < DEGRADED_MIN_CHUNKS

    return {
        "chunks": [
            {
                "chunk_id": c["chunk_id"],
                "doc_id": c["doc_id"],
                "doc_name": c["doc_name"],
                "content": c["content"],
                "score": c["score"],
            }
            for c in chunks
        ],
        "retrieval_degraded": retrieval_degraded,
    }


async def _build_query_text(doc_ids: list[str]) -> str:
    async with async_session() as session:
        result = await session.execute(
            select(DocumentChunk.sectionTitle)
            .where(DocumentChunk.fileId.in_(doc_ids))
        )
        section_titles = [row[0] for row in result.fetchall() if row[0]]

        result = await session.execute(
            select(UploadedFile.originalName)
            .where(UploadedFile.id.in_(doc_ids))
        )
        doc_names = [row[0] for row in result.fetchall() if row[0]]

    seen = set()
    parts = []
    for name in doc_names:
        if name and name not in seen:
            seen.add(name)
            parts.append(name)
    for title in section_titles:
        if title and title not in seen:
            seen.add(title)
            parts.append(title)

    if not parts:
        return " "

    return " ".join(parts)


def _query_chroma(
    query_text: str,
    K: int,
    category: str,
    user_id: str,
    doc_ids: list[str],
) -> dict | None:
    try:
        collection = chroma_store.get_or_create_collection(category, user_id)
        result = collection.query(
            query_texts=[query_text],
            n_results=K,
            where={"file_id": {"$in": doc_ids}},
            include=["documents", "metadatas", "distances"],
        )
        return result
    except Exception as e:
        logger.error("Chroma query error: %s", e)
        return None


def _parse_chroma_results(raw: dict) -> list[dict]:
    ids_list = raw.get("ids", [[]])
    docs_list = raw.get("documents", [[]])
    metas_list = raw.get("metadatas", [[]])
    dists_list = raw.get("distances", [[]])

    ids = ids_list[0] if ids_list else []
    docs = docs_list[0] if docs_list else []
    metas = metas_list[0] if metas_list else []
    dists = dists_list[0] if dists_list else []

    chunks = []
    for i in range(len(ids)):
        content = docs[i] if i < len(docs) else ""
        meta = metas[i] if i < len(metas) else {}
        distance = dists[i] if i < len(dists) else 1.0
        score = 1.0 / (1.0 + distance)

        file_id = meta.get("file_id", "")
        chunk_index = meta.get("chunk_index", 0)

        chunks.append({
            "file_id": file_id,
            "chunk_index": chunk_index,
            "content": content,
            "score": round(score, 6),
            "chunk_id": "",
            "doc_id": file_id,
            "doc_name": "",
            "token_estimate": 0,
        })

    return chunks


def _dedup_by_content(chunks: list[dict], threshold: float) -> list[dict]:
    if len(chunks) <= 1:
        return chunks

    keep = [True] * len(chunks)

    for i in range(len(chunks)):
        if not keep[i]:
            continue
        for j in range(i + 1, len(chunks)):
            if not keep[j]:
                continue
            sim = SequenceMatcher(None, chunks[i]["content"], chunks[j]["content"]).ratio()
            if sim > threshold:
                keep[j] = False

    return [c for c, k in zip(chunks, keep) if k]


async def _populate_token_estimates(chunks: list[dict]) -> list[dict]:
    pairs = [(c["file_id"], c["chunk_index"]) for c in chunks]

    async with async_session() as session:
        conditions = [
            (DocumentChunk.fileId == fid) & (DocumentChunk.chunkIndex == ci)
            for fid, ci in pairs
        ]
        if not conditions:
            return chunks

        from sqlalchemy import or_
        result = await session.execute(
            select(DocumentChunk).where(or_(*conditions))
        )
        db_chunks = result.scalars().all()

    lookup = {}
    for dc in db_chunks:
        lookup[(dc.fileId, dc.chunkIndex)] = dc

    for c in chunks:
        key = (c["file_id"], c["chunk_index"])
        dc = lookup.get(key)
        if dc:
            c["chunk_id"] = dc.id
            if dc.tokenEstimate and dc.tokenEstimate > 0:
                c["token_estimate"] = dc.tokenEstimate
            else:
                c["token_estimate"] = max(1, len(c["content"]) // 2)

    return chunks


def _truncate_by_token_budget(chunks: list[dict], max_tokens: int) -> list[dict]:
    kept = []
    total = 0
    for c in chunks:
        est = c.get("token_estimate", 0)
        if total + est > max_tokens:
            break
        kept.append(c)
        total += est
    return kept


async def _enrich_with_doc_name(chunks: list[dict]) -> list[dict]:
    doc_ids = list({c["doc_id"] for c in chunks if c["doc_id"]})
    if not doc_ids:
        return chunks

    async with async_session() as session:
        result = await session.execute(
            select(UploadedFile.id, UploadedFile.originalName)
            .where(UploadedFile.id.in_(doc_ids))
        )
        name_map = {row[0]: row[1] for row in result.fetchall()}

    for c in chunks:
        c["doc_name"] = name_map.get(c["doc_id"], "")

    return chunks
