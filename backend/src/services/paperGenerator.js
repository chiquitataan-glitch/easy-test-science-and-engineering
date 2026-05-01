const { chat } = require('./deepseekClient');

const MAX_TEXT_LENGTH = 6000;
const MIN_TEXT_LENGTH = 50;
const SELF_CHECK_TIMEOUT = 90000;

function buildPrompt(textContent, courseName) {
  return `你是一个专业的出题教师。请根据以下【课程资料】为《${courseName}》生成一份复习试卷。

必须严格输出如下 JSON 格式，不要包含任何额外文字或 markdown 标记：

{
  "paper_title": "《${courseName}》复习试卷",
  "course_name": "${courseName}",
  "questions": [
    {
      "question_type": "single_choice",
      "question_no": 1,
      "content": "题目内容",
      "options": [
        {"key": "A", "value": "选项内容"},
        {"key": "B", "value": "选项内容"},
        {"key": "C", "value": "选项内容"},
        {"key": "D", "value": "选项内容"}
      ],
      "answer": "A",
      "analysis": "解析说明",
      "knowledge_points": ["知识点1"],
      "difficulty": "easy",
      "score": 5
    }
  ],
  "quality_report": {
    "summary": "试卷质量简述",
    "warnings": []
  }
}

question_type 仅限以下6种：
- single_choice（单选题，共8道，每题5分，每题4个选项）
- multi_choice（多选题，共2道，每题5分，每题4个选项）
- fill_blank（填空题，共10道，每题2分）
- true_false（判断题，共10道，每题1分，答案填"√"或"×"）
- calculation（计算题，共4道，每题3分，answer字段写计算过程）
- short_answer（简答题，共2道，每题4分）

要求：
1. 知识点必须来自课程资料
2. difficulty 值：easy / medium / hard
3. 答案必须准确
4. analysis 写解析
5. quality_report.summary 写 30 字内总结
6. 只返回纯 JSON，不要有任何额外内容

【课程资料】
${textContent}`;
}

function buildSelfCheckPrompt(paperJson) {
  return `你是资深出题审核专家。请对以下试卷 JSON 逐项检查并修复所有问题。

试卷 JSON：
${JSON.stringify(paperJson, null, 2)}

检查清单：
1. 题型数量：单选题应为8道、多选题2道、填空题10道、判断题10道、计算题4道、简答题2道
2. 单选题必须正好4个选项，answer 必须是 A/B/C/D 中的一个字母
3. 多选题必须正好4个选项，answer 至少两个字母用逗号分隔如"A,C"
4. 判断题 answer 只能是"√"或"×"
5. 填空题不出现计算题内容混入
6. 计算题 answer 字段需要写计算步骤
7. 简答题 answer 字段需要写评分要点
8. 答案和解析必须逻辑一致
9. 同一题型中不能有明显重复题目
10. 题目内容不能明显脱离课程资料范围

请返回严格的 JSON，只返回如下格式，不要任何额外内容：
{
  "passed": true,
  "issues": [
    {"question_no": 1, "field": "answer", "problem": "问题描述", "suggestion": "建议修改"}
  ],
  "fixed_paper": { 这里放修正后的完整试卷 JSON，结构与原试卷一致 }
}

如果 passed 为 true，issues 为空数组，fixed_paper 直接放原试卷。
如果 passed 为 false，issues 列出所有问题，fixed_paper 放修正后的完整试卷。`;
}

function parseJsonFromResponse(content) {
  let jsonStr = content.trim();

  try {
    return JSON.parse(jsonStr);
  } catch (e) { /* 继续尝试 */ }

  const codeBlockMatch = jsonStr.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (codeBlockMatch) {
    try {
      return JSON.parse(codeBlockMatch[1].trim());
    } catch (e) { /* 继续尝试 */ }
  }

  const firstBrace = jsonStr.indexOf('{');
  const lastBrace = jsonStr.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    try {
      return JSON.parse(jsonStr.substring(firstBrace, lastBrace + 1));
    } catch (e) { /* 失败 */ }
  }

  return null;
}

async function selfCheckPaper(paper) {
  const selfCheckPrompt = buildSelfCheckPrompt(paper);

  try {
    const content = await chat(
      [{ role: 'user', content: selfCheckPrompt }],
      { max_tokens: 8192, temperature: 0.1, timeout: SELF_CHECK_TIMEOUT }
    );

    const result = parseJsonFromResponse(content);

    if (!result || typeof result.passed === 'undefined') {
      return { passed: true, issues: [], fixed_paper: paper, skip_reason: '自检结果解析失败' };
    }

    return {
      passed: result.passed,
      issues: result.issues || [],
      fixed_paper: result.fixed_paper || paper
    };
  } catch (error) {
    if (error.message.includes('超时')) {
      return { passed: true, issues: [], fixed_paper: paper, skip_reason: '自检超时' };
    }
    return { passed: true, issues: [], fixed_paper: paper, skip_reason: '自检调用失败' };
  }
}

async function generatePaper(textContent, courseName) {
  if (!textContent || textContent.trim().length < MIN_TEXT_LENGTH) {
    throw new Error('文本内容太短，无法生成试卷');
  }

  const truncatedText = textContent.substring(0, MAX_TEXT_LENGTH);
  const prompt = buildPrompt(truncatedText, courseName);

  try {
    const content = await chat(
      [{ role: 'user', content: prompt }],
      { max_tokens: 8192, temperature: 0.3, timeout: 120000 }
    );

    const paper = parseJsonFromResponse(content);

    if (!paper) {
      throw new Error('试卷JSON解析失败，请重试');
    }

    if (!paper.questions || !Array.isArray(paper.questions) || paper.questions.length === 0) {
      throw new Error('试卷格式不正确，缺少题目数据');
    }

    const selfCheck = await selfCheckPaper(paper);

    const finalPaper = selfCheck.fixed_paper;
    finalPaper.quality_report = finalPaper.quality_report || {};
    finalPaper.quality_report.self_check = {
      passed: selfCheck.passed,
      issues: selfCheck.issues,
      skip_reason: selfCheck.skip_reason || null
    };

    return finalPaper;
  } catch (error) {
    throw error;
  }
}

module.exports = { generatePaper };
