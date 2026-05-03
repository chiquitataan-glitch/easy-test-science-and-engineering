import time
from langchain_deepseek import DeepSeekEmbeddings
from app.config import settings

BATCH_SIZE = 20
MAX_RETRIES = 3

embeddings = DeepSeekEmbeddings(
    model="deepseek-embed",
    api_key=settings.DEEPSEEK_API_KEY,
    api_base=settings.DEEPSEEK_BASE_URL,
)


def embed_single(text: str) -> list[float]:
    return embeddings.embed_query(text)


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    all_vectors = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        vectors = _embed_batch_with_retry(batch)
        all_vectors.extend(vectors)
    return all_vectors


def _embed_batch_with_retry(batch: list[str]) -> list[list[float]]:
    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            return embeddings.embed_documents(batch)
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                backoff = 2 ** attempt
                time.sleep(backoff)
    raise last_exception
