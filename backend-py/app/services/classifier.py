import json
import os
import logging
from pathlib import Path
from typing import Tuple

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.uploaded_file import UploadedFile

logger = logging.getLogger(__name__)

VALID_CATEGORIES = ["math", "cs", "english", "medicine", "law", "general"]

CLASSIFIER_SYSTEM_PROMPT = """You are a document subject classifier. Analyze the document excerpt and classify it into exactly one of these categories:

- math: Mathematics, including algebra, calculus, geometry, statistics, probability theory, mathematical modeling, etc.
- cs: Computer Science, including programming, algorithms, data structures, artificial intelligence, software engineering, databases, networks, operating systems, etc.
- english: English language learning, English grammar, English writing, English literature, English reading comprehension, TOEFL/IELTS preparation, etc.
- medicine: Medicine, healthcare, anatomy, pharmacology, pathology, clinical medicine, nursing, medical terminology, etc.
- law: Law, legal studies, regulations, contracts, jurisprudence, constitutional law, criminal law, civil law, etc.
- general: Any other subject that does not clearly fit the above five categories, such as history, philosophy, art, business, general knowledge, etc.

Return ONLY a JSON object with no markdown, no code blocks, no extra text:
{"category": "<one of: math, cs, english, medicine, law, general>", "confidence": <float between 0 and 1>}

Confidence guidelines:
- 0.9-1.0: Very clear subject with strong domain-specific terminology
- 0.7-0.9: Likely match but some ambiguity
- 0.5-0.7: Uncertain, could be multiple categories
- 0.0-0.5: Cannot determine, should be "general"
"""


async def classify_document(text: str) -> Tuple[str, float]:
    if not settings.DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not configured, returning general")
        return ("general", 0.0)

    truncated = text[:2000]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                        {"role": "user", "content": truncated},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]

        result = json.loads(raw_content)
        category = result.get("category", "general").strip().lower()
        confidence = float(result.get("confidence", 0))

        if category not in VALID_CATEGORIES:
            category = "general"

        if confidence < 0.6:
            category = "general"

        logger.info(f"Classification result: category={category}, confidence={confidence}")
        return (category, confidence)

    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"DeepSeek API request failed: {e}")
        return ("general", 0.0)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse classification response: {e}")
        return ("general", 0.0)
    except Exception as e:
        logger.error(f"Unexpected classification error: {e}")
        return ("general", 0.0)


async def classify_and_move_file(db: AsyncSession, file_record: UploadedFile) -> None:
    if not file_record.parsedText:
        logger.warning(f"File {file_record.id} has no parsed text, marking as general")
        file_record.category = "general"
        file_record.categoryConfidence = 0.0
        await db.commit()
        return

    category, confidence = await classify_document(file_record.parsedText)

    file_record.category = category
    file_record.categoryConfidence = confidence

    ext = Path(file_record.originalName).suffix
    new_relative = os.path.join(category, file_record.userId, f"{file_record.id}{ext}")
    new_path = os.path.join(settings.UPLOAD_DIR, new_relative)

    os.makedirs(os.path.dirname(new_path), exist_ok=True)

    old_path = file_record.path
    if old_path and os.path.isfile(old_path) and os.path.abspath(old_path) != os.path.abspath(new_path):
        import shutil
        shutil.move(old_path, new_path)

    file_record.path = new_path
    await db.commit()

    logger.info(
        f"File {file_record.id} classified as '{category}' "
        f"(confidence: {confidence:.4f}), moved to {new_path}"
    )
