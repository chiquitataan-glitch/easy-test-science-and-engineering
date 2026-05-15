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
from app.services.knowledge_skeleton import extract_knowledge_skeleton

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
        'calculation': {'count': 2, 'score': 8},
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
    knowledge_skeleton: Optional[dict] = None,
    density_tier: str = 'none',
) -> str:
    config = _normalize_config(config)
    active_types = _get_active_types(config)
    has_skeleton = knowledge_skeleton is not None and bool(knowledge_skeleton.get("knowledge_points"))

    parts = []

    parts.append(_build_system_header(has_skeleton=has_skeleton))

    if has_skeleton:
        parts.append(_build_knowledge_section(knowledge_skeleton))

    parts.append(_build_reference_section(retrieved_chunks))

    parts.append(_build_config_section(config))

    parts.append(_build_rules_section(has_skeleton=has_skeleton, density_tier=density_tier))

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


def _build_system_header(has_skeleton: bool = False):
    if has_skeleton:
        return (
            '你是一个专业的出题教师。请根据以下【知识点骨架】和【参考资料】为指定课程生成一份高质量复习试卷。\n'
            '知识点骨架定义了必须覆盖的核心知识范围，你必须围绕这些知识点出题，\n'
            '但题目的具体表述、考查角度、选项设计应当每次不同，确保试卷的多样性和新颖性。\n'
            '你必须严格遵循下方的格式要求和规则，输出纯 JSON，不包含任何额外文字或 markdown 标记。'
        )
    return (
        '你是一个专业的出题教师。请根据以下【参考资料】为指定课程生成一份高质量复习试卷。\n'
        '你必须严格遵循下方的格式要求和规则，输出纯 JSON，不包含任何额外文字或 markdown 标记。'
    )


def _build_knowledge_section(skeleton: dict) -> str:
    lines = ['=== 第一部分：知识点骨架（必须覆盖） ===', '']
    lines.append('本次试卷必须覆盖以下知识点，每个知识点至少出一道题：')
    lines.append('')

    points = skeleton.get("knowledge_points", [])
    for i, kp in enumerate(points, 1):
        name = kp.get("name", "")
        key_concepts = kp.get("key_concepts", [])
        key_formulas = kp.get("key_formulas", [])

        lines.append(f'{i}. {name}')
        if key_concepts:
            lines.append(f'   - 核心概念：{"、".join(key_concepts)}')
        if key_formulas:
            lines.append(f'   - 关键公式：{"；".join(key_formulas)}')
        lines.append('')

    lines.append('出题要求：')
    lines.append('- 你可以自由选择每个知识点的考查角度（定义、应用、辨析、计算等）')
    lines.append('- 题目表述和选项设计必须每次不同，确保多样性')
    lines.append('- 不要直接复制参考资料中的原文作为题目')

    return '\n'.join(lines)


def _build_reference_section(retrieved_chunks: list) -> str:
    lines = ['=== 第二部分：参考上下文（辅助出题，不要直接照搬） ===', '']
    if not retrieved_chunks:
        lines.append('（无参考资料，务必严格按照知识点骨架和课程名称进行出题，不要凭空编造内容）')
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
    lines = ['=== 第三部分：出题配置 ===', '']

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


def _build_rules_section(has_skeleton: bool = False, density_tier: str = "none") -> str:
    knowledge_source = (
        "知识点必须来自参考资料或知识点骨架，命名要具体明确"
        if has_skeleton
        else "知识点必须来自参考资料，命名要具体明确"
    )

    skeleton_rules = ''
    if has_skeleton:
        skeleton_rules = '''
6. **多样性规则**：
   - 每次生成必须选择不同的出题角度和题目表述
   - 禁止直接复制参考资料中的原文作为题目内容
   - 同一知识点的题目应从不同侧面考查（如：定义、应用、辨析、计算）
   - 选项设计应具有合理的干扰性，不要使用明显荒谬的干扰项
   - 知识点必须来自知识点骨架列表，确保覆盖范围

7. **知识点覆盖规则**：
   - 知识点骨架中列出的每个知识点必须至少被一道题覆盖
   - knowledge_points 字段中的知识点名称应与骨架中的名称对应
   - 如果某个知识点无法出题，在 quality_report.warnings 中说明原因'''

    density_rules = ''
    if density_tier == "none":
        density_rules = '''
8. **无公式内容难度规则**：
   - 由于课程内容不含公式，每道题必须覆盖至少2个知识点（知识点数量翻倍）
   - 侧重概念理解、辨析和应用场景考查
   - 不要求计算类题目'''
    elif density_tier == "low":
        density_rules = '''
8. **低公式密度难度规则**：
   - 困难题必须包含计算推导过程，要求给出完整解题步骤
   - 中等题可适当加入简单计算或公式应用
   - 简单题侧重概念理解和基本判断'''
    elif density_tier == "high":
        density_rules = '''
8. **高公式密度难度规则**：
   - 中等题必须包含一定量的计算，要求运用公式求解
   - 困难题必须包含大量计算和公式推导，要求完整的数学推导过程
   - 简单题可包含基础公式直接应用
   - 计算题的 analysis 必须包含详细的推导步骤和中间结果'''

    return f'''=== 第四部分：严格规则 ===

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
   - {knowledge_source}
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
   - 严禁遗漏任何必填字段{skeleton_rules}{density_rules}'''


def _build_output_schema_section(active_types: list) -> str:
    lines = ['=== 第五部分：输出 JSON Schema ===', '']
    lines.append('你必须输出以下结构的纯 JSON：')
    lines.append('')

    question_type_enum = '|'.join(active_types) if active_types else 'single_choice|multi_choice|fill_blank|short_answer|essay'

    lines.append('```json')
    lines.append('{')
    lines.append('  "paper_title": "《课程名》复习试卷",')
    lines.append('  "course_name": "课程名称",')
    lines.append('  "questions": [')
    lines.append('    {')
    lines.append(f'      "question_type": "{question_type_enum}",')
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
DIVERSITY_RETRY_THRESHOLD = 0.5
MAX_DIVERSITY_RETRIES = 1

_FORMULA_STRONG_PATTERNS = re.compile(r'[∑∫∏√∞≈≤≥≠±×÷]')
_FORMULA_GREEK = re.compile(r'[αβγδεζηθικλμνξπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ]')
_FORMULA_SUPERSCRIPT = re.compile(r'[a-zA-Z][²³ⁿ]|[²³ⁿ][a-zA-Z]')
_FORMULA_COMPOUND_UNIT = re.compile(r'/m[²³]|/s[²³]|·s\b|·kg\b')
_FORMULA_EQUALS = re.compile(r'=')
_FORMULA_FRACTION = re.compile(r'[a-zA-Z]/[a-zA-Z]|\d/[a-zA-Z]')
_FORMULA_SUBSCRIPT = re.compile(r'[a-zA-Z]\d[a-zA-Z\d]|[a-zA-Z]\d+[a-zA-Z]')
_FORMULA_ANSWER_EXCLUDE = re.compile(r'^(答案|选项|解析)[是为：:]')
_FORMULA_PURE_ANSWER = re.compile(r'^[A-D]\s*[=＝]\s*[A-D]$')
_FORMULA_DEFINITION = re.compile(r'(是指|就是|即)[^∑∫∏√∞≈≤≥≠±×÷²³ⁿαβγδεζηθικλμνξπρστυφχψω]*$')


def _is_formula_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) < 4:
        return False

    if _FORMULA_ANSWER_EXCLUDE.match(stripped):
        return False
    if _FORMULA_PURE_ANSWER.match(stripped):
        return False
    if _FORMULA_DEFINITION.search(stripped) and not _FORMULA_STRONG_PATTERNS.search(stripped):
        return False

    score = 0

    if _FORMULA_STRONG_PATTERNS.search(stripped):
        score += 2
    if _FORMULA_GREEK.search(stripped) and _FORMULA_EQUALS.search(stripped):
        score += 2
    if _FORMULA_SUPERSCRIPT.search(stripped):
        score += 2
    if _FORMULA_COMPOUND_UNIT.search(stripped):
        score += 2

    weak_hits = 0
    if _FORMULA_EQUALS.search(stripped):
        right_side = stripped.split('=', 1)[-1].strip()
        left_side = stripped.split('=', 1)[0]
        if _FORMULA_GREEK.search(right_side) or re.search(r'[+\-*/^]', right_side):
            weak_hits += 1
        if _FORMULA_SUBSCRIPT.search(left_side) and _FORMULA_SUBSCRIPT.search(right_side):
            score += 2
    if _FORMULA_FRACTION.search(stripped):
        weak_hits += 1
    if _FORMULA_SUBSCRIPT.search(stripped) and not _FORMULA_EQUALS.search(stripped):
        weak_hits += 1
    if _FORMULA_GREEK.search(stripped) and not _FORMULA_EQUALS.search(stripped):
        weak_hits += 1

    score += min(weak_hits, 2)

    return score >= 2


def _detect_formula_density(chunks: list[dict]) -> dict:
    all_lines = []
    for chunk in chunks:
        content = chunk.get("content", "")
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped:
                all_lines.append(stripped)

    total_lines = len(all_lines)
    if total_lines == 0:
        return {"ratio": 0.0, "tier": "none", "formula_lines": 0, "total_lines": 0}

    formula_lines = sum(1 for line in all_lines if _is_formula_line(line))
    ratio = formula_lines / total_lines

    if formula_lines == 0:
        tier = "none"
    elif ratio <= 0.3:
        tier = "low"
    else:
        tier = "high"

    return {
        "ratio": round(ratio, 3),
        "tier": tier,
        "formula_lines": formula_lines,
        "total_lines": total_lines,
    }


_NUMERIC_PATTERN = re.compile(r'\b(\d+\.?\d*)\s*([a-zA-ZμΩ²³/·]+)?\b')
_CHINESE_SEGMENT = re.compile(r'[\u4e00-\u9fff]+')
_KP_SPLITTER = re.compile(r'[与和及、，,]')


def _split_kp_segments(kp: str) -> list[str]:
    parts = _KP_SPLITTER.split(kp)
    segments = []
    for p in parts:
        p = p.strip()
        if len(p) >= 2:
            segments.append(p)
    return segments


def _extract_source_keywords(chunks: list[dict]) -> list[str]:
    keywords = set()
    for chunk in chunks:
        content = chunk.get("content", "")
        for seg in _CHINESE_SEGMENT.findall(content):
            for length in range(2, min(len(seg) + 1, 7)):
                for i in range(len(seg) - length + 1):
                    keywords.add(seg[i:i + length])
    return keywords


def _extract_source_numerics(chunks: list[dict]) -> set[str]:
    numerics = set()
    for chunk in chunks:
        content = chunk.get("content", "")
        for m in _NUMERIC_PATTERN.finditer(content):
            numerics.add(m.group(1))
    return numerics


def _verify_knowledge_points(paper_json: dict, source_keywords: list[str]) -> dict:
    questions = paper_json.get("questions", [])
    all_points = []
    for q in questions:
        for kp in q.get("knowledge_points", []):
            all_points.append(kp)

    if not all_points:
        return {"total_points": 0, "verified": 0, "suspicious": [], "pass_rate": 1.0}

    unique_points = list(dict.fromkeys(all_points))
    suspicious = []
    verified = 0

    for kp in unique_points:
        found = False
        kp_segs = _split_kp_segments(kp)
        if not kp_segs:
            kp_segs = [seg for seg in _CHINESE_SEGMENT.findall(kp) if len(seg) >= 2]
        for seg in kp_segs:
            if len(seg) < 2:
                continue
            if any(seg in sk for sk in source_keywords):
                found = True
                break
        if not found and kp_segs:
            suspicious.append(kp)
        else:
            verified += 1

    pass_rate = verified / len(unique_points) if unique_points else 1.0
    return {
        "total_points": len(unique_points),
        "verified": verified,
        "suspicious": suspicious,
        "pass_rate": round(pass_rate, 3),
    }


def _verify_numerics(paper_json: dict, source_numerics: set[str]) -> dict:
    questions = paper_json.get("questions", [])
    unverified = []
    checked = 0

    for q in questions:
        text = q.get("content", "") + " " + q.get("answer", "")
        nums_in_q = _NUMERIC_PATTERN.findall(text)
        for num_val, _unit in nums_in_q:
            if '.' in num_val:
                continue
            int_val = num_val
            if int_val in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'):
                continue
            if int_val not in source_numerics:
                unverified.append({"value": int_val, "question_id": q.get("id", "")})
            checked += 1

    return {
        "checked_numerics": checked,
        "unverified_numerics": unverified,
        "numeric_pass_rate": round(1 - len(unverified) / checked, 3) if checked > 0 else 1.0,
    }


def _verify_factuality(paper_json: dict, chunks: list[dict]) -> dict:
    source_keywords = _extract_source_keywords(chunks)
    source_numerics = _extract_source_numerics(chunks)

    kp_result = _verify_knowledge_points(paper_json, source_keywords)
    num_result = _verify_numerics(paper_json, source_numerics)

    overall_pass = kp_result["pass_rate"] >= 0.7 and num_result["numeric_pass_rate"] >= 0.5

    return {
        "knowledge_points": kp_result,
        "numerics": num_result,
        "overall_pass": overall_pass,
    }


async def _fetch_recent_paper_contents(user_id: str, course_name: str, limit: int = 1) -> list[list[str]]:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(GeneratedPaper.paperJson)
                .where(
                    GeneratedPaper.userId == user_id,
                    GeneratedPaper.courseName == course_name,
                    GeneratedPaper.status == PaperStatus.completed,
                )
                .order_by(GeneratedPaper.createdAt.desc())
                .limit(limit)
            )
            rows = result.all()
            papers = []
            for row in rows:
                pj = row[0]
                if pj and isinstance(pj, dict):
                    contents = [q.get("content", "") for q in pj.get("questions", [])]
                    papers.append(contents)
            return papers
    except Exception as e:
        logger.warning("failed to fetch recent papers for diversity check: %s", e)
        return []


def _calculate_diversity_overlap(new_contents: list[str], history_contents: list[list[str]]) -> dict:
    if not history_contents:
        return {"checked": False, "reason": "no_history"}

    all_history = set()
    for hc in history_contents:
        all_history.update(hc)

    new_set = set(new_contents)
    overlap = new_set & all_history
    overlap_rate = len(overlap) / len(new_set) if new_set else 0.0

    return {
        "checked": True,
        "overlap_count": len(overlap),
        "overlap_rate": round(overlap_rate, 3),
        "history_paper_count": len(history_contents),
        "new_question_count": len(new_set),
        "needs_retry": overlap_rate > DIVERSITY_RETRY_THRESHOLD,
    }


def _build_diversity_retry_prompt(original_prompt: str, overlap_items: set[str]) -> str:
    sample_overlap = list(overlap_items)[:5]
    overlap_text = "\n".join(f"  - {item[:80]}..." if len(item) > 80 else f"  - {item}" for item in sample_overlap)

    return original_prompt + f"""

=== 多样性重试要求 ===
上一次生成的试卷与历史试卷重复率过高，以下题目与历史试卷重复：
{overlap_text}

请务必：
1. 更换题目表述和考查角度，避免与上述重复
2. 保持知识点覆盖不变
3. 增加题目创新性，从不同维度考查同一知识点
"""


def _build_generation_response(
    paper_id: str,
    user_id: str,
    course_name: str,
    status: str,
    paper_json: dict | None = None,
    duration_seconds: float = 0.0,
    category: str = "general",
    config: dict | None = None,
    retrieval_mode: str = "rag",
    token_usage: int = 0,
    error_message: str | None = None,
    original_paper_id: str | None = None,
) -> dict:
    if status == "failed":
        return {
            "id": paper_id,
            "userId": user_id,
            "courseName": course_name,
            "paperTitle": None,
            "paperJson": {},
            "status": status,
            "questionCount": 0,
            "totalScore": None,
            "qualityScore": None,
            "durationSeconds": duration_seconds,
            "category": category,
            "config": config,
            "retrievalMode": retrieval_mode,
            "knowledgeSummary": None,
            "qualityReport": None,
            "questions": [],
            "failReason": error_message,
            "modelName": "deepseek-chat",
            "promptVersion": "v1",
            "tokenUsage": token_usage,
            "originalPaperId": original_paper_id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

    questions = [
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
    ]

    return {
        "id": paper_id,
        "userId": user_id,
        "courseName": course_name,
        "paperTitle": paper_json.get("paper_title", ""),
        "paperJson": paper_json,
        "status": status,
        "questionCount": len(questions),
        "totalScore": sum(q.get("score", 0) for q in paper_json.get("questions", [])),
        "qualityScore": None,
        "durationSeconds": duration_seconds,
        "category": category,
        "config": config,
        "retrievalMode": retrieval_mode,
        "knowledgeSummary": paper_json.get("knowledge_summary"),
        "qualityReport": paper_json.get("quality_report"),
        "questions": questions,
        "failReason": None,
        "modelName": "deepseek-chat",
        "promptVersion": "v1",
        "tokenUsage": token_usage,
        "originalPaperId": original_paper_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


class GenerationRetryManager:

    def __init__(self, max_retries: int = 2, has_skeleton: bool = False):
        self.max_retries = max_retries
        self.has_skeleton = has_skeleton
        self.attempt_count = 0
        self.last_error = None

    async def execute_with_retry(self, prompt: str, config: dict):
        current_prompt = prompt

        for attempt in range(self.max_retries + 1):
            self.attempt_count = attempt + 1
            try:
                raw_response, total_tokens = await _call_deepseek_chat(current_prompt, has_skeleton=self.has_skeleton)
                paper_json = _parse_and_validate(raw_response, config)
                return paper_json, raw_response, total_tokens, ""
            except Exception as e:
                self.last_error = str(e)
                logger.warning("attempt %d/%d failed: %s", attempt + 1, self.max_retries + 1, e)
                if attempt < self.max_retries:
                    current_prompt = _build_prompt_retry(current_prompt, e)

        return None, None, 0, self.last_error or "生成失败"


async def _prepare_generation_context(
    doc_ids: list[str],
    question_count: int,
    category: str,
    user_id: str
) -> dict:
    rag_result = await retrieve_relevant_chunks(doc_ids, question_count, category, user_id)
    retrieved_chunks = rag_result.get("chunks", [])
    retrieval_degraded = rag_result.get("retrieval_degraded", False)

    if retrieval_degraded:
        retrieved_chunks = await _load_document_texts_for_prompt(doc_ids)
        logger.info("RAG degraded, loaded %d document texts for prompt fallback", len(retrieved_chunks))

    mode = "prompt" if retrieval_degraded else "rag"
    retrieval_k = 0 if retrieval_degraded else max(10, min(question_count * 2, 100))

    return {
        "chunks": retrieved_chunks,
        "mode": mode,
        "retrieval_k": retrieval_k,
    }


async def _handle_generation_failure(
    user: User,
    doc_ids: list[str],
    course_name: str,
    category: str,
    config: dict,
    question_count: int,
    error_message: str,
    duration_seconds: float,
    client_type: str,
    original_paper_id: str | None,
    generation_context: dict,
    token_usage: int = 0,
) -> dict:
    await _refund_quota(user)

    persisted = await _persist_failed_paper(
        user.id, doc_ids, course_name, category, config,
        error_message, duration_seconds, client_type
    )

    await _write_generation_log(
        user_id=user.id, paper_id=persisted["id"], doc_ids=doc_ids,
        question_count=question_count,
        token_used=token_usage, duration_ms=round(duration_seconds * 1000),
        retrieval_k=generation_context["retrieval_k"],
        mode=generation_context["mode"], status="failed",
        error_message=error_message,
    )

    return _build_generation_response(
        paper_id=persisted["id"],
        user_id=user.id,
        course_name=course_name,
        status="failed",
        duration_seconds=duration_seconds,
        category=category,
        config=config,
        retrieval_mode=generation_context["mode"],
        token_usage=token_usage,
        error_message=error_message,
        original_paper_id=original_paper_id,
    )


async def _handle_generation_success(
    user: User,
    doc_ids: list[str],
    course_name: str,
    paper_json: dict,
    raw_response: str,
    category: str,
    config: dict,
    question_count: int,
    duration_seconds: float,
    token_usage: int,
    client_type: str,
    original_paper_id: str | None,
    generation_context: dict,
) -> dict:
    paper_data = await _persist_paper(
        user_id=user.id, doc_ids=doc_ids, course_name=course_name,
        paper_json=paper_json, raw_response=raw_response,
        category=category, source_chunks=generation_context["chunks"],
        config=config, duration_seconds=duration_seconds,
        model_name="deepseek-chat", token_usage=token_usage,
        client_type=client_type, original_paper_id=original_paper_id,
    )

    await _write_generation_log(
        user_id=user.id, paper_id=paper_data["id"], doc_ids=doc_ids,
        question_count=question_count, token_used=token_usage,
        duration_ms=round(duration_seconds * 1000),
        retrieval_k=generation_context["retrieval_k"],
        mode=generation_context["mode"], status="completed",
    )

    return _build_generation_response(
        paper_id=paper_data["id"],
        user_id=user.id,
        course_name=course_name,
        status="completed",
        paper_json=paper_json,
        duration_seconds=duration_seconds,
        category=category,
        config=config,
        retrieval_mode=generation_context["mode"],
        token_usage=token_usage,
        original_paper_id=original_paper_id,
    )


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

    generation_context = await _prepare_generation_context(
        doc_ids, question_count, category, user.id
    )

    skeleton = None
    try:
        skeleton = await extract_knowledge_skeleton(
            chunks=generation_context["chunks"],
            course_name=course_name,
        )
    except Exception as e:
        logger.warning("knowledge skeleton extraction failed, proceeding without skeleton: %s", e)

    formula_density = _detect_formula_density(generation_context["chunks"])
    density_tier = formula_density["tier"]
    logger.info(
        "formula density: tier=%s, ratio=%.1f%%, formula_lines=%d/%d",
        density_tier, formula_density["ratio"] * 100,
        formula_density["formula_lines"], formula_density["total_lines"],
    )

    prompt = build_generation_prompt(
        retrieved_chunks=generation_context["chunks"],
        config=normalized_config,
        category=category,
        course_name=course_name,
        knowledge_skeleton=skeleton,
        density_tier=density_tier,
    )

    has_skeleton = skeleton is not None and bool(skeleton.get("knowledge_points"))

    retry_manager = GenerationRetryManager(max_retries=MAX_RETRIES, has_skeleton=has_skeleton)
    paper_json, raw_response, total_tokens, error_message = await retry_manager.execute_with_retry(
        prompt, normalized_config
    )

    duration_seconds = round(time.time() - start_time, 2)

    if paper_json is None:
        return await _handle_generation_failure(
            user=user,
            doc_ids=doc_ids,
            course_name=course_name,
            category=category,
            config=normalized_config,
            question_count=question_count,
            error_message=error_message,
            duration_seconds=duration_seconds,
            client_type=client_type,
            original_paper_id=original_paper_id,
            generation_context=generation_context,
            token_usage=total_tokens,
        )

    # --- diversity post-check ---
    new_contents = [q.get("content", "") for q in paper_json.get("questions", [])]
    history_contents = await _fetch_recent_paper_contents(user.id, course_name, limit=1)
    diversity_result = _calculate_diversity_overlap(new_contents, history_contents)

    if diversity_result.get("needs_retry"):
        overlap_items = set(new_contents) & set().union(*history_contents) if history_contents else set()
        logger.info(
            "diversity check: overlap_rate=%.1f%%, retrying generation",
            diversity_result["overlap_rate"] * 100,
        )
        diversity_prompt = _build_diversity_retry_prompt(prompt, overlap_items)
        try:
            raw_retry, tokens_retry = await _call_deepseek_chat(diversity_prompt, has_skeleton=has_skeleton)
            paper_retry = _parse_and_validate(raw_retry, normalized_config)
            retry_contents = [q.get("content", "") for q in paper_retry.get("questions", [])]
            retry_diversity = _calculate_diversity_overlap(retry_contents, history_contents)

            if not retry_diversity.get("needs_retry"):
                paper_json = paper_retry
                raw_response = raw_retry
                total_tokens += tokens_retry
                diversity_result = retry_diversity
                diversity_result["retried"] = True
                diversity_result["retry_improved"] = True
                logger.info("diversity retry succeeded: overlap_rate=%.1f%%", retry_diversity["overlap_rate"] * 100)
            else:
                diversity_result["retried"] = True
                diversity_result["retry_improved"] = False
                logger.info("diversity retry did not improve, keeping original")
        except Exception as e:
            diversity_result["retried"] = True
            diversity_result["retry_improved"] = False
            diversity_result["retry_error"] = str(e)
            logger.warning("diversity retry failed: %s", e)

    if skeleton:
        qr = paper_json.setdefault("quality_report", {})
        qr.setdefault("warnings", [])
        qr["knowledge_skeleton"] = {
            "total_points": skeleton.get("total", 0),
            "points": [kp["name"] for kp in skeleton.get("knowledge_points", [])],
            "coverage_note": skeleton.get("coverage_note", ""),
        }
    else:
        qr = paper_json.setdefault("quality_report", {})
        qr.setdefault("warnings", [])
        qr["warnings"].append("知识点骨架提取未执行，试卷知识点覆盖未经骨架约束")

    qr = paper_json.setdefault("quality_report", {})
    qr["diversity_check"] = diversity_result
    qr["formula_density"] = formula_density

    factuality = _verify_factuality(paper_json, generation_context["chunks"])
    qr["factuality_check"] = factuality
    if not factuality["overall_pass"]:
        qr.setdefault("warnings", [])
        suspicious_kps = factuality["knowledge_points"].get("suspicious", [])
        if suspicious_kps:
            qr["warnings"].append(f"以下知识点未在源内容中找到依据：{', '.join(suspicious_kps[:5])}")
        unverified_nums = factuality["numerics"].get("unverified_numerics", [])
        if unverified_nums:
            qr["warnings"].append(f"有 {len(unverified_nums)} 个数值未在源内容中找到依据")

    return await _handle_generation_success(
        user=user,
        doc_ids=doc_ids,
        course_name=course_name,
        paper_json=paper_json,
        raw_response=raw_response,
        category=category,
        config=normalized_config,
        question_count=question_count,
        duration_seconds=duration_seconds,
        token_usage=total_tokens,
        client_type=client_type,
        original_paper_id=original_paper_id,
        generation_context=generation_context,
    )


async def _validate_and_wait_docs(doc_ids: list[str], user_id: str) -> list[str]:
    count = len(doc_ids)
    if count < 3 or count > settings.MAX_FILES_PER_PAPER:
        raise ValueError(f"doc_ids count must be 3-{settings.MAX_FILES_PER_PAPER}, got {count}")

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

    return valid_ids


async def _load_document_texts_for_prompt(doc_ids: list[str]) -> list[dict]:
    MAX_TOTAL_CHARS = 120000
    chars_per_doc = max(1000, min(3000, MAX_TOTAL_CHARS // max(len(doc_ids), 1)))
    async with async_session() as session:
        result = await session.execute(
            select(UploadedFile).where(UploadedFile.id.in_(doc_ids))
        )
        files = {f.id: f for f in result.scalars().all()}

    chunks = []
    total_chars = 0
    for fid in doc_ids:
        f = files.get(fid)
        if not f or not f.parsedText:
            continue
        remaining = MAX_TOTAL_CHARS - total_chars
        if remaining <= 0:
            break
        limit = min(chars_per_doc, remaining)
        text = f.parsedText[:limit]
        total_chars += len(text)
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


async def _call_deepseek_chat(prompt: str, has_skeleton: bool = False) -> tuple[str, int]:
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not configured")

    temperature = 0.85 if has_skeleton else 0.7
    top_p = 0.9 if has_skeleton else 0.85

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
                "temperature": temperature,
                "top_p": top_p,
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
        lower = expected - 4
        upper = expected + 4
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
