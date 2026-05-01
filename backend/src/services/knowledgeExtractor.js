function extractKnowledgeCoverage(paper) {
  const questions = paper.questions || [];

  const knowledgeMap = {};
  let questionsWithKnowledge = 0;
  let questionsWithoutKnowledge = [];

  for (const q of questions) {
    const kps = q.knowledge_points;
    if (!Array.isArray(kps) || kps.length === 0) {
      questionsWithoutKnowledge.push(q.question_no || '?');
      continue;
    }

    questionsWithKnowledge++;

    for (const kp of kps) {
      if (!knowledgeMap[kp]) {
        knowledgeMap[kp] = {
          name: kp,
          question_nos: [],
          difficulty_distribution: { easy: 0, medium: 0, hard: 0 }
        };
      }
      knowledgeMap[kp].question_nos.push(q.question_no || '?');
      const diff = q.difficulty || 'medium';
      if (knowledgeMap[kp].difficulty_distribution[diff] !== undefined) {
        knowledgeMap[kp].difficulty_distribution[diff]++;
      }
    }
  }

  const points = Object.values(knowledgeMap).sort((a, b) => b.question_nos.length - a.question_nos.length);
  const total = points.length;

  let description = '';
  if (total >= 8) {
    description = '知识点覆盖广泛，分布均衡';
  } else if (total >= 5) {
    description = '知识点覆盖较全面';
  } else if (total >= 3) {
    description = '知识点覆盖一般';
  } else {
    description = '知识点覆盖不足，建议补充课程资料';
  }

  const gaps = [];
  if (questionsWithoutKnowledge.length > 0) {
    gaps.push(`${questionsWithoutKnowledge.length} 道题未标注知识点`);
  }
  if (total < Math.max(questions.length * 0.6, 3)) {
    gaps.push('知识点总数偏少，可能存在覆盖盲区');
  }

  return {
    total,
    points,
    questions_with_knowledge: questionsWithKnowledge,
    questions_without_knowledge: questionsWithoutKnowledge,
    description,
    gaps
  };
}

function enrichQualityReport(paper, qualityReport) {
  const result = { ...qualityReport };

  if (!paper.questions || !Array.isArray(paper.questions)) {
    return result;
  }

  const coverage = extractKnowledgeCoverage(paper);

  result.knowledge_coverage = {
    total_points: coverage.total,
    questions_with_knowledge: coverage.questions_with_knowledge,
    questions_without_knowledge: coverage.questions_without_knowledge,
    top_points: coverage.points.slice(0, 5).map(p => ({ name: p.name, count: p.question_nos.length })),
    description: coverage.description,
    gaps: coverage.gaps
  };

  for (const gap of coverage.gaps) {
    if (!result.warnings.includes(gap)) {
      result.warnings.push(gap);
    }
  }

  if (coverage.total >= 8) {
    result.suggestions.push('知识点覆盖较全面，可用于正式测验');
  } else if (coverage.total < 3) {
    result.suggestions.push('知识点覆盖不足，建议上传更完整的课程资料');
  }

  return result;
}

module.exports = { extractKnowledgeCoverage, enrichQualityReport };
