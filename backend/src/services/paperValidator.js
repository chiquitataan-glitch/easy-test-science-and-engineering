const { VALID_TYPES, VALID_DIFFICULTIES } = require('../config/paperConfig');

const REQUIRED_QUESTION_FIELDS = [
  'question_no', 'question_type', 'content',
  'answer', 'analysis', 'knowledge_points', 'difficulty', 'score'
];

function validatePaper(paper, expectedConfig) {
  const warnings = [];
  let fatal = null;

  if (!paper || typeof paper !== 'object') {
    return { valid: false, fatal: '试卷不是有效的 JSON 对象', warnings, score: 0 };
  }

  if (!paper.questions || !Array.isArray(paper.questions)) {
    return { valid: false, fatal: '试卷缺少 questions 数组', warnings, score: 0 };
  }

  if (paper.questions.length === 0) {
    return { valid: false, fatal: '试卷 questions 数组为空', warnings, score: 0 };
  }

  if (!paper.paper_title) {
    warnings.push('试卷缺少 paper_title');
  }

  if (!paper.course_name) {
    warnings.push('试卷缺少 course_name');
  }

  if (!paper.knowledge_summary) {
    warnings.push('试卷缺少 knowledge_summary');
  }

  const seenContents = new Set();
  const validTypes = new Set(VALID_TYPES);

  for (let i = 0; i < paper.questions.length; i++) {
    const q = paper.questions[i];
    const idx = q.question_no || (i + 1);

    if (typeof q !== 'object' || q === null) {
      warnings.push(`第 ${idx} 题不是有效的 JSON 对象`);
      continue;
    }

    for (const field of REQUIRED_QUESTION_FIELDS) {
      if (q[field] === undefined || q[field] === null) {
        warnings.push(`第 ${idx} 题缺少字段：${field}`);
      }
    }

    const qtype = q.question_type;
    if (qtype && !validTypes.has(qtype)) {
      warnings.push(`第 ${idx} 题使用了未知题型：${qtype}`);
    }

    if (q.difficulty && !VALID_DIFFICULTIES.includes(q.difficulty)) {
      warnings.push(`第 ${idx} 题使用了未知难度：${q.difficulty}`);
    }

    if (q.content !== undefined && (typeof q.content !== 'string' || q.content.trim() === '')) {
      warnings.push(`第 ${idx} 题题干为空`);
    }

    if (q.analysis !== undefined && (typeof q.analysis !== 'string' || q.analysis.trim() === '')) {
      warnings.push(`第 ${idx} 题解析为空`);
    }

    if (q.knowledge_points !== undefined && (!Array.isArray(q.knowledge_points) || q.knowledge_points.length === 0)) {
      warnings.push(`第 ${idx} 题知识点为空`);
    }

    if (q.score !== undefined && (typeof q.score !== 'number' || q.score <= 0)) {
      warnings.push(`第 ${idx} 题分值不合理：${q.score}`);
    }

    if (qtype === 'single_choice') {
      const opts = q.options;
      if (!Array.isArray(opts) || opts.length !== 4) {
        warnings.push(`第 ${idx} 单选题选项数应为 4，当前为 ${opts ? opts.length : 0}`);
      }
      if (q.answer && typeof q.answer === 'string' && !/^[A-D]$/.test(q.answer)) {
        warnings.push(`第 ${idx} 单选题答案格式应为 A/B/C/D，当前为：${q.answer}`);
      }
    }

    if (qtype === 'multi_choice') {
      const opts = q.options;
      if (!Array.isArray(opts) || opts.length !== 4) {
        warnings.push(`第 ${idx} 多选题选项数应为 4，当前为 ${opts ? opts.length : 0}`);
      }
      if (q.answer && typeof q.answer === 'string') {
        const parts = q.answer.split(',').map(s => s.trim());
        if (parts.length < 2) {
          warnings.push(`第 ${idx} 多选题答案应至少包含两个选项，当前为：${q.answer}`);
        }
      }
    }

    if (qtype === 'true_false') {
      if (q.answer && typeof q.answer === 'string' && !/^[√×]$/.test(q.answer)) {
        warnings.push(`第 ${idx} 判断题答案应为 √ 或 ×，当前为：${q.answer}`);
      }
    }

    if (qtype === 'calculation') {
      if (q.answer && typeof q.answer === 'string' && q.answer.length < 10) {
        warnings.push(`第 ${idx} 计算题答案过短，可能缺少计算步骤`);
      }
    }

    if (q.content && typeof q.content === 'string') {
      const normalized = q.content.replace(/\s+/g, '').substring(0, 50);
      if (seenContents.has(normalized)) {
        warnings.push(`第 ${idx} 题与前面的题目疑似重复`);
      }
      seenContents.add(normalized);
    }
  }

  const typeCounts = {};
  for (const q of paper.questions) {
    const t = q.question_type;
    if (t) typeCounts[t] = (typeCounts[t] || 0) + 1;
  }

  if (expectedConfig) {
    for (const [type, cfg] of Object.entries(expectedConfig.types)) {
      if (cfg.count === 0) continue;
      const actual = typeCounts[type] || 0;
      if (actual !== cfg.count) {
        warnings.push(`题型 "${type}" 期望 ${cfg.count} 道，实际 ${actual} 道`);
      }
    }
  }

  const score = calculateScore(warnings.length, paper.questions.length);

  return {
    valid: true,
    fatal: null,
    warnings,
    score,
    typeCounts
  };
}

function calculateScore(warningCount, questionCount) {
  let score = 100;
  score -= warningCount * 3;
  if (score < 0) score = 0;
  return score;
}

function buildQualityReport(validationResult) {
  const report = {
    score: validationResult.score,
    warnings: validationResult.warnings,
    suggestions: []
  };

  if (validationResult.score >= 90) {
    report.summary = '试卷质量良好';
  } else if (validationResult.score >= 70) {
    report.summary = '试卷质量一般，存在部分问题';
  } else if (validationResult.score >= 50) {
    report.summary = '试卷质量较差，建议重新生成';
  } else {
    report.summary = '试卷质量严重不达标，建议重新生成';
  }

  if (validationResult.warnings.some(w => w.includes('缺少'))) {
    report.suggestions.push('部分题目字段缺失，建议检查生成 Prompt');
  }
  if (validationResult.warnings.some(w => w.includes('疑似重复'))) {
    report.suggestions.push('存在疑似重复题目，建议手动检查');
  }
  if (validationResult.warnings.some(w => w.includes('期望'))) {
    report.suggestions.push('题型数量与配置不一致，建议重新生成');
  }
  if (validationResult.warnings.some(w => w.includes('知识点'))) {
    report.suggestions.push('部分题目缺少知识点，影响覆盖统计');
  }

  return report;
}

module.exports = { validatePaper, buildQualityReport };
