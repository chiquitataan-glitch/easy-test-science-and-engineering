import asyncio
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select, update

from app.config import settings
from app.database import async_session
from app.models.enums import PaperStatus, FileStatus, ClientType
from app.models.generated_paper import GeneratedPaper
from app.models.generation_log import GenerationLog
from app.models.paper_question import PaperQuestion
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.services.rag_engine import retrieve_relevant_chunks

logger = logging.getLogger(__name__)

TYPE_NAMES = {
    'single_choice': '单选题',
    'multi_choice': '多选题',
    'fill_blank': '填空题',
    'true_false': '判断题',
    'calculation': '计算题',
    'short_answer': '简答题',
    'essay': '论述题',
}

ALL_VALID_TYPES = list(TYPE_NAMES.keys())

VALID_DIFFICULTIES = ['easy', 'medium', 'hard']

DEFAULT_CONFIG = {
    'types': {
        'single_choice': {'count': 8, 'score': 5},
        'multi_choice': {'count': 2, 'score': 5},
        'fill_blank': {'count': 10, 'score': 2},
        'true_false': {'count': 0, 'score': 2},
        'calculation': {'count': 0, 'score': 8},
        'short_answer': {'count': 2, 'score': 4},
        'essay': {'count': 1, 'score': 10},
    },
    'difficulty': {
        'easy': 0.3,
        'medium': 0.5,
        'hard': 0.2,
    },
}


def build_generation_prompt(
    retrieved_chunks: list,
    config: Optional[dict] = None,
    category: str = 'general',
    course_name: str = '未命名课程',
) -> str:
    config = _normalize_config(config)
    active_types = _get_active_types(config)

    parts = []

    parts.append(_build_system_header())

    parts.append(_build_reference_section(retrieved_chunks))

    parts.append(_build_config_section(config))

    parts.append(_build_rules_section())

    parts.append(_build_output_schema_section(active_types))

    return '\n\n'.join(parts)


def _normalize_config(config: Optional[dict]) -> dict:
    if not config:
        return DEFAULT_CONFIG

    merged_types = {}
    for key in ALL_VALID_TYPES:
        merged_types[key] = {
            'count': config.get('types', {}).get(key, {}).get('count', 0),
            'score': config.get('types', {}).get(key, {}).get('score', 0),
        }

    merged_difficulty = {}
    for key in VALID_DIFFICULTIES:
        merged_difficulty[key] = config.get('difficulty', {}).get(key, DEFAULT_CONFIG['difficulty'][key])

    total = sum(merged_difficulty.values())
    if abs(total - 1.0) > 0.01:
        for key in merged_difficulty:
            merged_difficulty[key] = merged_difficulty[key] / total

    return {'types': merged_types, 'difficulty': merged_difficulty}


def _get_active_types(config: dict) -> list:
    return [key for key, val in config.get('types', {}).items() if val.get('count', 0) > 0]


def _build_system_header():
    return (
        '你是一个专业的出题教师。请根据以下【参考资料】为指定课程生成一份高质量复习试卷。\n'
        '你必须严格遵循下方的格式要求和规则，输出纯 JSON，不包含任何额外文字或 markdown 标记。'
    )


def _build_reference_section(retrieved_chunks: list) -> str:
    lines = ['=== 第一部分：参考资料 ===', '']
    if not retrieved_chunks:
        lines.append('（无参考资料，务必严格按照课程名称和常识进行出题，不要凭空编造内容）')
        return '\n'.join(lines)

    for i, chunk in enumerate(retrieved_chunks, 1):
        if isinstance(chunk, dict):
            text = chunk.get('content', chunk.get('text', str(chunk)))
            source = chunk.get('source', '')
            if source:
                lines.append(f'[文档 {i}] 来源：{source}')
            lines.append(text)
        else:
            lines.append(f'[文档 {i}] {str(chunk)}')
        lines.append('')

    return '\n'.join(lines)


def _build_config_section(config: dict) -> str:
    lines = ['=== 第二部分：出题配置 ===', '']

    lines.append('题型与分值：')
    for key, val in config.get('types', {}).items():
        label = TYPE_NAMES.get(key, key)
        if val['count'] == 0:
            lines.append(f'  - {label}：不生成')
        else:
            lines.append(f'  - {label}：{val["count"]} 道，每题 {val["score"]} 分')

    diff = config.get('difficulty', {})
    easy_pct = round(diff.get('easy', 0.3) * 100)
    medium_pct = round(diff.get('medium', 0.5) * 100)
    hard_pct = round(diff.get('hard', 0.2) * 100)
    lines.append(f'\n难度分布：简单 {easy_pct}%、中等 {medium_pct}%、困难 {hard_pct}%')

    return '\n'.join(lines)


def _build_rules_section() -> str:
    return '''=== 第三部分：严格规则 ===

请严格遵守以下规则：

1. **题型规则**：
   - 单选题：必须包含 4 个选项（A/B/C/D），answer 为单个大写字母
   - 多选题：必须包含 4 个选项，answer 为多个字母用逗号分隔，如 "A,C,D"
   - 填空题：answer 为正确答案文字，content 中使用 "______" 标记填空位置
   - 判断题：options 包含 A.正确 B.错误，answer 为 "A" 或 "B"，analysis 须解释理由
   - 计算题：content 为计算问题，answer 为完整计算步骤和最终结果，analysis 为解题思路
   - 简答题：answer 为评分要点和参考答案，content 为题目要求
   - 论述题：answer 为完整的参考答案，需包含层次结构，content 为论述题目

2. **题目质量规则**：
   - 每道题必须有 knowledge_points 字段，至少包含 1 个具体知识点
   - 知识点必须来自参考资料，命名要具体明确
   - 答案必须准确无误
   - analysis 字段必须包含详细解析或评分要点

3. **输出规则**：
   - 严格按照配置中指定的各题型数量和分值生成题目
   - 严格按照难度比例分配（easy/medium/hard）
   - 题目编号从 1 开始连续递增
   - 必须输出 knowledge_summary 汇总所有知识点

4. **综合题规则**：
   - 如果题目需要结合多份参考资料才能作答，设置 is_cross_doc 为 true
   - 综合题应在 analysis 中说明涉及的知识跨度和综合能力要求

5. **严禁事项**：
   - 严禁编造参考资料中不存在的事实或数据
   - 严禁直接复制示例题目
   - 严禁输出非 JSON 格式的内容
   - 严禁遗漏任何必填字段'''


def _build_output_schema_section(active_types: list) -> str:
    lines = ['=== 第四部分：输出 JSON Schema ===', '']
    lines.append('你必须输出以下结构的纯 JSON：')
    lines.append('')
    lines.append('```json')
    lines.append('{')
    lines.append('  "paper_title": "《课程名》复习试卷",')
    lines.append('  "course_name": "课程名称",')
    lines.append('  "questions": [')
    lines.append('    {')
    lines.append('      "question_type": "single_choice|multi_choice|fill_blank|short_answer|essay",')
    lines.append('      "question_no": 1,')
    lines.append('      "content": "题目内容",')
    lines.append('      "options": [')
    lines.append('        {"key": "A", "value": "选项内容"},')
    lines.append('        {"key": "B", "value": "选项内容"},')
    lines.append('        {"key": "C", "value": "选项内容"},')
    lines.append('        {"key": "D", "value": "选项内容"}')
    lines.append('      ],')
    lines.append('      "answer": "正确答案",')
    lines.append('      "analysis": "解析或评分要点",')
    lines.append('      "knowledge_points": ["知识点1", "知识点2"],')
    lines.append('      "difficulty": "easy|medium|hard",')
    lines.append('      "score": 5,')
    lines.append('      "is_cross_doc": false')
    lines.append('    }')
    lines.append('  ],')
    lines.append('  "knowledge_summary": {')
    lines.append('    "points": [')
    lines.append('      {')
    lines.append('        "name": "知识点名称",')
    lines.append('        "question_nos": [1, 3],')
    lines.append('        "difficulty_distribution": {"easy": 1, "medium": 0, "hard": 0}')
    lines.append('      }')
    lines.append('    ],')
    lines.append('    "total": 8,')
    lines.append('    "description": "知识点覆盖情况简述"')
    lines.append('  },')
    lines.append('  "quality_report": {')
    lines.append('    "summary": "试卷质量简述（30字内）",')
    lines.append('    "warnings": []')
    lines.append('  }')
    lines.append('}')
    lines.append('```')
    lines.append('')

    type_hints = []
    if 'single_choice' in active_types or 'multi_choice' in active_types:
        type_hints.append('- 选择题（single_choice/multi_choice）：options 必须包含 4 个选项，每个选项含 key 和 value')
    if 'fill_blank' in active_types:
        type_hints.append('- 填空题（fill_blank）：options 为空数组 []，content 中用 "______" 标记填空位置')
    if 'true_false' in active_types:
        type_hints.append('- 判断题（true_false）：options 包含 [{"key":"A","value":"正确"},{"key":"B","value":"错误"}]，answer 为 "A" 或 "B"')
    if 'calculation' in active_types:
        type_hints.append('- 计算题（calculation）：options 为空数组 []，answer 写完整计算步骤和结果，analysis 写解题思路')
    if 'short_answer' in active_types:
        type_hints.append('- 简答题（short_answer）：options 为空数组 []，answer 写评分要点')
    if 'essay' in active_types:
        type_hints.append('- 论述题（essay）：options 为空数组 []，answer 写完整参考答案，需有层次结构')

    if type_hints:
        lines.append('当前题型字段说明：')
        lines.extend(type_hints)

    return '\n'.join(lines)


MAX_RETRIES = 2
API_TIMEOUT = 120.0


async def generate_paper(
    user: User,
    course_name: str,
    doc_ids: list[str],
    config: Optional[dict] = None,
    category: str = "general",
    client_type: str = "web",
    original_paper_id: str | None = None,
) -> dict:
    start_time = time.time()

    doc_ids = await _validate_and_wait_docs(doc_ids, user.id)

    normalized_config = _normalize_config(config)
    question_count = sum(v["count"] for v in normalized_config["types"].values())

    await _check_and_deduct_quota(user)

    rag_result = await retrieve_relevant_chunks(doc_ids, question_count, category, user.id)
    retrieved_chunks = rag_result.get("chunks", [])
    retrieval_degraded = rag_result.get("retrieval_degraded", False)

    if retrieval_degraded:
        retrieved_chunks = await _load_document_texts_for_prompt(doc_ids)
        logger.info("RAG degraded, loaded %d document texts for prompt fallback", len(retrieved_chunks))

    mode = "prompt" if retrieval_degraded else "rag"
    retrieval_k = 0 if retrieval_degraded else max(10, min(question_count * 2, 100))

    prompt = build_generation_prompt(
        retrieved_chunks=retrieved_chunks,
        config=normalized_config,
        category=category,
        course_name=course_name,
    )

    raw_response = None
    paper_json = None
    total_tokens = 0
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            raw_response, total_tokens = await _call_deepseek_chat(prompt)
            paper_json = _parse_and_validate(raw_response, normalized_config)
            break
        except Exception as e:
            last_error = str(e)
            logger.warning("attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES + 1, e)
            if attempt < MAX_RETRIES:
                prompt = _build_prompt_retry(prompt, e)

    duration_seconds = round(time.time() - start_time, 2)

    if paper_json is None:
        await _refund_quota(user)
        persisted = await _persist_failed_paper(user.id, doc_ids, course_name, category, normalized_config, last_error, duration_seconds, client_type)
        failed_paper_id = persisted["id"]
        await _write_generation_log(
            user_id=user.id, paper_id=failed_paper_id, doc_ids=doc_ids, question_count=question_count,
            token_used=total_tokens, duration_ms=round(duration_seconds * 1000),
            retrieval_k=retrieval_k, mode=mode, status="failed",
            error_message=last_error,
        )
        return {
            "id": failed_paper_id,
            "userId": user.id,
            "courseName": course_name,
            "paperTitle": None,
            "paperJson": {},
            "status": "failed",
            "questionCount": 0,
            "totalScore": None,
            "qualityScore": None,
            "durationSeconds": duration_seconds,
            "category": category,
            "config": normalized_config,
            "retrievalMode": mode,
            "knowledgeSummary": None,
            "qualityReport": None,
            "questions": [],
            "failReason": last_error,
            "modelName": "deepseek-chat",
            "promptVersion": "v1",
            "tokenUsage": total_tokens,
            "originalPaperId": original_paper_id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

    paper_data = await _persist_paper(
        user_id=user.id, doc_ids=doc_ids, course_name=course_name,
        paper_json=paper_json, raw_response=raw_response,
        category=category, source_chunks=retrieved_chunks,
        config=normalized_config, duration_seconds=duration_seconds,
        model_name="deepseek-chat", token_usage=total_tokens,
        client_type=client_type, original_paper_id=original_paper_id,
    )

    await _write_generation_log(
        user_id=user.id, paper_id=paper_data["id"], doc_ids=doc_ids,
        question_count=question_count, token_used=total_tokens,
        duration_ms=round(duration_seconds * 1000),
        retrieval_k=retrieval_k, mode=mode, status="completed",
    )

    result = {
        "id": paper_data["id"],
        "userId": user.id,
        "courseName": course_name,
        "paperTitle": paper_json.get("paper_title", ""),
        "status": "completed",
        "questionCount": len(paper_json.get("questions", [])),
        "totalScore": sum(q.get("score", 0) for q in paper_json.get("questions", [])),
        "durationSeconds": duration_seconds,
        "category": category,
        "config": normalized_config,
        "retrievalMode": mode,
        "knowledgeSummary": paper_json.get("knowledge_summary"),
        "qualityReport": paper_json.get("quality_report"),
        "questions": [
            {
                "id": q.get("id", ""),
                "questionNo": q["question_no"],
                "questionType": q["question_type"],
                "content": q["content"],
                "options": q.get("options", []),
                "answer": q["answer"],
                "analysis": q.get("analysis"),
                "knowledgePoints": q.get("knowledge_points", []),
                "difficulty": q.get("difficulty", ""),
                "score": q.get("score", 0),
                "sourceChunkIds": q.get("sourceChunkIds", []),
                "isCrossDoc": q.get("is_cross_doc", False),
            }
            for q in paper_json.get("questions", [])
        ],
        "failReason": None,
        "createdAt": paper_data["created_at"],
    }

    return result


async def _validate_and_wait_docs(doc_ids: list[str], user_id: str) -> list[str]:
    count = len(doc_ids)
    if count < 3 or count > 15:
        raise ValueError(f"doc_ids count must be 3-15, got {count}")

    POLL_INTERVAL = 2
    MAX_WAIT = 60

    async with async_session() as session:
        result = await session.execute(
            select(UploadedFile).where(UploadedFile.id.in_(doc_ids))
        )
        files = {f.id: f for f in result.scalars().all()}

    missing = set(doc_ids) - set(files.keys())
    if missing:
        raise ValueError(f"documents not found: {missing}")

    for f in files.values():
        if f.userId != user_id:
            raise ValueError(f"document {f.id} does not belong to user {user_id}")

    waiting_ids = [
        fid for fid, f in files.items()
        if f.status not in (FileStatus.ready, FileStatus.failed)
    ]
    dead_ids = [fid for fid, f in files.items() if f.status == FileStatus.failed]

    if waiting_ids:
        from app.services.file_service import process_file_extraction

        for fid in waiting_ids:
            f = files.get(fid)
            if f and f.status in (FileStatus.pending, FileStatus.parsed):
                logger.info("re-queuing stalled file %s for processing", fid)
                asyncio.create_task(process_file_extraction(fid))

        logger.info("waiting for %d files to process: %s", len(waiting_ids), waiting_ids)
        elapsed = 0
        while elapsed < MAX_WAIT:
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

            async with async_session() as session:
                result = await session.execute(
                    select(UploadedFile).where(UploadedFile.id.in_(waiting_ids))
                )
                refreshed = {f.id: f for f in result.scalars().all()}

            still_waiting = []
            for fid in waiting_ids:
                f = refreshed.get(fid)
                if not f:
                    continue
                if f.status == FileStatus.ready:
                    logger.info("file %s is now ready", fid)
                elif f.status == FileStatus.failed:
                    logger.warning("file %s failed during processing", fid)
                    dead_ids.append(fid)
                else:
                    still_waiting.append(fid)

            waiting_ids = still_waiting
            if not waiting_ids:
                break

        if waiting_ids:
            logger.warning("timed out waiting for files: %s", waiting_ids)

    valid_ids = [fid for fid in doc_ids if fid not in dead_ids]
    if len(valid_ids) < 1:
        raise ValueError("all uploaded files failed to process")
    if len(valid_ids) < 3:
        logger.warning("only %d valid files out of %d, proceeding anyway", len(valid_ids), len(doc_ids))
        if len(valid_ids) < 1:
            raise ValueError("no valid files available for generation")

    return valid_ids


async def _load_document_texts_for_prompt(doc_ids: list[str]) -> list[dict]:
    MAX_CHARS_PER_DOC = 3000
    async with async_session() as session:
        result = await session.execute(
            select(UploadedFile).where(UploadedFile.id.in_(doc_ids))
        )
        files = {f.id: f for f in result.scalars().all()}

    chunks = []
    for fid in doc_ids:
        f = files.get(fid)
        if not f or not f.parsedText:
            continue
        text = f.parsedText[:MAX_CHARS_PER_DOC]
        chunks.append({
            "content": text,
            "fileId": fid,
            "chunkIndex": 0,
            "score": 1.0,
            "fileName": f.originalName,
        })

    if not chunks:
        logger.warning("no document texts available for prompt fallback")
    return chunks


class QuotaExceededError(Exception):
    def __init__(self, message: str = "no remaining generations"):
        self.message = message
        super().__init__(message)


async def _check_and_deduct_quota(user: User):
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                select(User.remainingGenerations, User.membershipType, User.membershipExpire)
                .where(User.id == user.id)
                .with_for_update()
            )
            row = result.one_or_none()
            if not row:
                raise ValueError("user not found")

            db_remaining, db_membership, db_membership_expire = row

            if db_membership != "free":
                if db_membership_expire and db_membership_expire.replace(tzinfo=timezone.utc) < now:
                    raise QuotaExceededError("membership expired")
                if db_remaining == -1:
                    return
                if db_remaining <= 0:
                    raise QuotaExceededError("no remaining generations")
                stmt = (
                    update(User)
                    .where(User.id == user.id, User.remainingGenerations == db_remaining)
                    .values(remainingGenerations=db_remaining - 1)
                )
                await session.execute(stmt)
                user.remainingGenerations = db_remaining - 1
                return

            if db_remaining <= 0:
                raise QuotaExceededError("no remaining generations")

            stmt = (
                update(User)
                .where(User.id == user.id, User.remainingGenerations == db_remaining)
                .values(remainingGenerations=db_remaining - 1)
            )
            await session.execute(stmt)
            user.remainingGenerations = db_remaining - 1


async def _refund_quota(user: User):
    if user.remainingGenerations == -1:
        return

    async with async_session() as session:
        async with session.begin():
            stmt = (
                update(User)
                .where(User.id == user.id)
                .values(remainingGenerations=User.remainingGenerations + 1)
            )
            await session.execute(stmt)
            user.remainingGenerations += 1


async def _call_deepseek_chat(prompt: str) -> tuple[str, int]:
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not configured")

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业的出题教师。请严格输出纯 JSON，不包含任何额外文字或 markdown 标记。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 8000,
            },
        )
        response.raise_for_status()
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        total_tokens = usage.get("total_tokens", 0)
        return raw_content, total_tokens


def _parse_and_validate(raw_response: str, config: dict) -> dict:
    json_str = _extract_json(raw_response)
    try:
        paper = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON response: {e}")

    if "questions" not in paper or not isinstance(paper["questions"], list):
        raise ValueError("missing or invalid questions array")

    questions = paper["questions"]
    if not questions:
        raise ValueError("empty questions array")

    expected_types = {}
    for qtype, qconfig in config.get("types", {}).items():
        if qconfig.get("count", 0) > 0:
            expected_types[qtype] = qconfig["count"]

    actual_types = {}
    for q in questions:
        qt = q.get("question_type", "")
        actual_types[qt] = actual_types.get(qt, 0) + 1

    missing = []
    for qtype, count in expected_types.items():
        actual = actual_types.get(qtype, 0)
        if actual < count:
            missing.append(f"{qtype}(expected {count}, got {actual})")

    if missing:
        raise ValueError(f"missing question types: {', '.join(missing)}")

    required_difficulties = config.get("difficulty", {})
    expected_diff_counts = {}
    total_q = len(questions)
    for diff_key, ratio in required_difficulties.items():
        expected_diff_counts[diff_key] = round(total_q * ratio)

    actual_diff_counts = {}
    for q in questions:
        d = q.get("difficulty", "medium")
        actual_diff_counts[d] = actual_diff_counts.get(d, 0) + 1

    for diff_key, expected in expected_diff_counts.items():
        actual = actual_diff_counts.get(diff_key, 0)
        lower = expected - 2
        upper = expected + 2
        if actual < lower or actual > upper:
            raise ValueError(
                f"difficulty '{diff_key}' count {actual} out of range [{lower}, {upper}]"
            )

    for i, q in enumerate(questions):
        q.setdefault("question_no", i + 1)
        q.setdefault("options", [])
        q.setdefault("analysis", "")
        q.setdefault("knowledge_points", [])
        q.setdefault("difficulty", "medium")
        q.setdefault("score", 0)
        q.setdefault("is_cross_doc", False)
        q.setdefault("sourceChunkIds", [])

    return paper


def _extract_json(text: str) -> str:
    text = text.strip()
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        return json_match.group(0)
    return text


def _build_prompt_retry(original_prompt: str, error: Exception) -> str:
    retry_note = f"""
=== 重试要求 ===
上一次生成失败，错误：{error}

请务必：
1. 只输出纯 JSON，不要包含任何 markdown 标记（如 ```json 或 ```）
2. 严格按照配置中的题型和数量生成
3. 确保所有必填字段存在
4. 题目编号从 1 开始连续递增
"""
    return original_prompt + retry_note


async def _persist_paper(
    user_id: str, doc_ids: list[str], course_name: str,
    paper_json: dict, raw_response: str,
    category: str, source_chunks: list,
    config: dict, duration_seconds: float,
    model_name: str, token_usage: int,
    client_type: str,
    original_paper_id: str | None = None,
) -> dict:
    paper_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    paper = GeneratedPaper(
        id=paper_id,
        userId=user_id,
        documentIds=doc_ids,
        courseName=course_name,
        paperTitle=paper_json.get("paper_title", ""),
        paperJson=paper_json,
        rawResponse=raw_response,
        category=category,
        sourceChunks=source_chunks,
        durationSeconds=duration_seconds,
        config=config,
        qualityReport=paper_json.get("quality_report"),
        knowledgeSummary=paper_json.get("knowledge_summary"),
        promptVersion="v1",
        modelName=model_name,
        tokenUsage=token_usage,
        status=PaperStatus.completed,
        clientType=ClientType(client_type) if client_type in {e.value for e in ClientType} else ClientType.web,
        originalPaperId=original_paper_id,
    )

    questions = []
    for q in paper_json.get("questions", []):
        options = q.get("options")
        pq = PaperQuestion(
            id=str(uuid.uuid4()),
            paperId=paper_id,
            questionNo=q["question_no"],
            questionType=q["question_type"],
            content=q["content"],
            options=options if options else None,
            answer=q["answer"],
            analysis=q.get("analysis"),
            knowledgePoints=q.get("knowledge_points"),
            difficulty=q.get("difficulty"),
            score=q.get("score"),
            sourceChunkIds=q.get("sourceChunkIds"),
            isCrossDoc=q.get("is_cross_doc", False),
        )
        questions.append(pq)

    async with async_session() as session:
        session.add(paper)
        for pq in questions:
            session.add(pq)
        await session.commit()

    return {"id": paper_id, "created_at": now.isoformat()}


async def _persist_failed_paper(
    user_id: str, doc_ids: list[str], course_name: str,
    category: str, config: dict, fail_reason: str,
    duration_seconds: float, client_type: str,
):
    paper_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    paper = GeneratedPaper(
        id=paper_id,
        userId=user_id,
        documentIds=doc_ids,
        courseName=course_name,
        paperTitle=None,
        paperJson={},
        rawResponse=None,
        category=category,
        sourceChunks=None,
        durationSeconds=duration_seconds,
        config=config,
        qualityReport=None,
        knowledgeSummary=None,
        promptVersion="v1",
        modelName="deepseek-chat",
        tokenUsage=0,
        status=PaperStatus.failed,
        clientType=ClientType(client_type) if client_type in {e.value for e in ClientType} else ClientType.web,
        failReason=fail_reason,
    )

    async with async_session() as session:
        session.add(paper)
        await session.commit()

    return {"id": paper_id, "created_at": now.isoformat()}


async def _write_generation_log(
    user_id: str, paper_id: str | None, doc_ids: list[str],
    question_count: int, token_used: int, duration_ms: int,
    retrieval_k: int, mode: str, status: str,
    error_message: str | None = None,
):
    log_entry = GenerationLog(
        userId=user_id,
        paperId=paper_id,
        docIds=doc_ids,
        questionCount=question_count,
        tokenUsed=token_used,
        durationMs=duration_ms,
        retrievalK=retrieval_k,
        mode=mode,
        status=status,
        errorMessage=error_message,
    )

    async with async_session() as session:
        session.add(log_entry)
        await session.commit()
