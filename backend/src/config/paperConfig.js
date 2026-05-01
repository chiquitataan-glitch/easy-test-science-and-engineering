const VALID_TYPES = [
  'single_choice',
  'multi_choice',
  'fill_blank',
  'true_false',
  'calculation',
  'short_answer'
];

const VALID_DIFFICULTIES = ['easy', 'medium', 'hard'];

const DEFAULT_PAPER_CONFIG = {
  types: {
    single_choice: { count: 8, score: 5 },
    multi_choice: { count: 2, score: 5 },
    fill_blank: { count: 10, score: 2 },
    true_false: { count: 10, score: 1 },
    calculation: { count: 4, score: 3 },
    short_answer: { count: 2, score: 4 }
  },
  difficulty: {
    easy: 0.3,
    medium: 0.5,
    hard: 0.2
  }
};

function normalizePaperConfig(input) {
  if (!input || Object.keys(input).length === 0) {
    return { ...DEFAULT_PAPER_CONFIG };
  }

  const merged = {
    types: { ...DEFAULT_PAPER_CONFIG.types },
    difficulty: { ...DEFAULT_PAPER_CONFIG.difficulty }
  };

  if (input.types) {
    for (const [key, val] of Object.entries(input.types)) {
      if (!VALID_TYPES.includes(key)) {
        throw new Error(`未知题型：${key}`);
      }

      const count = val.count;
      if (count === undefined) continue;

      if (typeof count !== 'number' || !Number.isInteger(count) || count < 0) {
        throw new Error(`题型 ${key} 的 count 必须是非负整数，当前值：${count}`);
      }

      const score = val.score;
      if (score !== undefined) {
        if (typeof score !== 'number' || score <= 0) {
          throw new Error(`题型 ${key} 的 score 必须是正数，当前值：${score}`);
        }
        merged.types[key].score = score;
      }

      merged.types[key].count = count;
    }
  }

  if (input.difficulty) {
    let ratioSum = 0;

    for (const [key, val] of Object.entries(input.difficulty)) {
      if (!VALID_DIFFICULTIES.includes(key)) {
        throw new Error(`未知难度：${key}`);
      }
      if (typeof val !== 'number' || val < 0 || val > 1) {
        throw new Error(`难度 ${key} 比例必须在 0~1 之间，当前值：${val}`);
      }
      merged.difficulty[key] = val;
    }

    for (const key of VALID_DIFFICULTIES) {
      ratioSum += merged.difficulty[key];
    }

    if (Math.abs(ratioSum - 1) > 0.01) {
      throw new Error(`难度比例之和必须为 1，当前值：${ratioSum.toFixed(3)}`);
    }
  }

  return merged;
}

function totalCount(config) {
  let sum = 0;
  for (const v of Object.values(config.types)) {
    sum += v.count;
  }
  return sum;
}

function buildQuestionConfigText(config) {
  const typeNames = {
    single_choice: '单选题',
    multi_choice: '多选题',
    fill_blank: '填空题',
    true_false: '判断题',
    calculation: '计算题',
    short_answer: '简答题'
  };

  const lines = [];
  lines.push('试卷题型配置如下：');

  for (const [key, val] of Object.entries(config.types)) {
    if (val.count === 0) {
      lines.push(`- ${typeNames[key]}：不生成`);
    } else {
      lines.push(`- ${typeNames[key]}：${val.count}道，每题${val.score}分`);
    }
  }

  const easy = Math.round(config.difficulty.easy * 100);
  const medium = Math.round(config.difficulty.medium * 100);
  const hard = Math.round(config.difficulty.hard * 100);
  lines.push(`\n难度分布：简单 ${easy}%、中等 ${medium}%、困难 ${hard}%`);

  return lines.join('\n');
}

module.exports = {
  VALID_TYPES,
  VALID_DIFFICULTIES,
  DEFAULT_PAPER_CONFIG,
  normalizePaperConfig,
  totalCount,
  buildQuestionConfigText
};
