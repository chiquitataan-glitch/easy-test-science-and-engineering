import json
import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

EXTRACT_TIMEOUT = 60.0
EXTRACT_MAX_TOKENS = 3000
MAX_KNOWLEDGE_POINTS = 30

EXTRACT_PROMPT = """你是一个知识点分析专家。请从以下【课程资料】中提取结构化的知识点骨架。

严格规则：
1. 只提取资料中明确出现的知识点，不要推断或扩展
2. 每个知识点必须有 name 和 key_concepts（至少1个）
3. key_formulas 可为空列表（如果该知识点不涉及公式）
4. 知识点命名要具体明确，不要过于笼统
5. 最多提取 {max_points} 个知识点
6. 只输出纯 JSON，不要包含任何额外文字或 markdown 标记

输出格式：
{{
  "knowledge_points": [
    {{
      "name": "知识点名称",
      "key_concepts": ["核心概念1", "核心概念2"],
      "key_formulas": ["公式1", "公式2"],
      "source_hint": "来源提示"
    }}
  ],
  "total": 8,
  "coverage_note": "知识点覆盖情况简述"
}}

【课程资料】
{source_text}"""


def _build_source_text(chunks: list[dict], max_chars: int | None = None) -> str:
    if max_chars is None:
        max_chars = min(6000 + len(chunks) * 400, 20000)
    parts = []
    total = 0
    for i, chunk in enumerate(chunks, 1):
        if isinstance(chunk, dict):
            text = chunk.get("content", chunk.get("text", str(chunk)))
            source = chunk.get("doc_name", chunk.get("source", ""))
        else:
            text = str(chunk)
            source = ""

        entry = f"[文档 {i}]"
        if source:
            entry += f" 来源：{source}"
        entry += f"\n{text}"

        if total + len(entry) > max_chars:
            remaining = max_chars - total
            if remaining > 100:
                entry = entry[:remaining] + "\n...(截断)"
                parts.append(entry)
            break

        parts.append(entry)
        total += len(entry)

    return "\n\n".join(parts)


def _parse_skeleton_response(raw: str) -> dict | None:
    json_str = raw.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    code_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', json_str)
    if code_match:
        try:
            return json.loads(code_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r'\{[\s\S]*\}', json_str)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _validate_skeleton(skeleton: dict) -> dict:
    points = skeleton.get("knowledge_points", [])
    if not isinstance(points, list):
        points = []

    valid_points = []
    for p in points:
        if not isinstance(p, dict):
            continue

        name = p.get("name", "").strip()
        if not name:
            continue

        key_concepts = p.get("key_concepts", [])
        if not isinstance(key_concepts, list):
            key_concepts = []
        key_concepts = [str(c).strip() for c in key_concepts if str(c).strip()]

        key_formulas = p.get("key_formulas", [])
        if not isinstance(key_formulas, list):
            key_formulas = []
        key_formulas = [str(f).strip() for f in key_formulas if str(f).strip()]

        source_hint = str(p.get("source_hint", "")).strip()

        valid_points.append({
            "name": name,
            "key_concepts": key_concepts,
            "key_formulas": key_formulas,
            "source_hint": source_hint,
        })

    valid_points = valid_points[:MAX_KNOWLEDGE_POINTS]

    return {
        "knowledge_points": valid_points,
        "total": len(valid_points),
        "coverage_note": skeleton.get("coverage_note", ""),
    }


async def extract_knowledge_skeleton(
    chunks: list[dict],
    course_name: str,
) -> dict | None:
    if not chunks:
        logger.warning("no chunks provided for skeleton extraction")
        return None

    source_text = _build_source_text(chunks)

    if len(source_text.strip()) < 50:
        logger.warning("source text too short for skeleton extraction: %d chars", len(source_text))
        return None

    prompt = EXTRACT_PROMPT.format(
        max_points=MAX_KNOWLEDGE_POINTS,
        source_text=source_text,
    )

    try:
        skeleton = await _call_extract_llm(prompt, course_name)
        if skeleton:
            logger.info(
                "extracted %d knowledge points for course '%s'",
                skeleton["total"],
                course_name,
            )
        return skeleton
    except Exception as e:
        logger.warning("knowledge skeleton extraction failed: %s", e)
        return None


async def _call_extract_llm(prompt: str, course_name: str) -> dict | None:
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not configured")

    async with httpx.AsyncClient(timeout=EXTRACT_TIMEOUT) as client:
        response = await client.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是一个知识点分析专家。请严格输出纯 JSON，"
                            "不包含任何额外文字或 markdown 标记。"
                            "只提取资料中明确出现的知识点，不要推断或扩展。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": EXTRACT_MAX_TOKENS,
            },
        )
        response.raise_for_status()
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]

    skeleton = _parse_skeleton_response(raw_content)
    if skeleton is None:
        logger.warning("failed to parse skeleton JSON for course '%s'", course_name)
        return None

    return _validate_skeleton(skeleton)
