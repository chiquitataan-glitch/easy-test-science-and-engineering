const { chat } = require('./deepseekClient');
const { renderPrompt } = require('./promptManager');

const MAX_TEXT_LENGTH = 6000;
const MIN_TEXT_LENGTH = 50;
const SELF_CHECK_TIMEOUT = 90000;

const GENERATE_PROMPT = 'generate-v1';
const SELFCHECK_PROMPT = 'selfcheck-v1';

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
  const selfCheckPrompt = renderPrompt(SELFCHECK_PROMPT, {
    paper_json: JSON.stringify(paper, null, 2)
  });

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
  const prompt = renderPrompt(GENERATE_PROMPT, {
    course_name: courseName,
    source_text: truncatedText
  });

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
    finalPaper.quality_report.prompt_version = GENERATE_PROMPT;

    return finalPaper;
  } catch (error) {
    throw error;
  }
}

module.exports = { generatePaper };
