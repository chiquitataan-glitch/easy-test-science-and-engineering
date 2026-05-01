const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

const promptVersions = [
  {
    name: 'generate',
    version: 'v1',
    content: `你是一个专业的试题生成助手。请根据提供的课程内容和配置参数，生成一份结构化的试卷JSON。

要求：
1. 严格遵循提供的配置文件中的所有参数（题型、数量、分值、难度分布）
2. 题目内容必须来源于提供的课程资料
3. 每题必须包含：题号、题型、内容、选项（选择题）、答案、解析、知识点标签、难度、分值
4. 试卷整体必须包含 paper_title 和 course_name
5. 输出必须是合法的 JSON 格式

课程名称：{{course_name}}
课程资料：
{{source_text}}

{{question_config}}`,
    isActive: true
  },
  {
    name: 'selfcheck',
    version: 'v1',
    content: `你是一个试卷质量审核专家。请对以下试卷进行10项自动检查，并尝试修复发现的问题。

检查项：
1. 试卷整体格式是否正确（必须包含 questions 数组）
2. 每道题是否有完整的字段（question_no, question_type, content, answer, analysis, knowledge_points, difficulty, score）
3. 单选题选项是否为4个，答案是否在 A/B/C/D 范围内
4. 多选题选项是否为4个，答案是否至少包含2个选项
5. 判断题答案是否为 √ 或 ×
6. 题型名称是否规范
7. 难度标签是否在 easy/medium/hard 范围内
8. 分值是否为正数
9. 题目是否有重复
10. 知识点是否非空

请返回JSON：
{
  "passed": true/false,
  "issues": [
    { "question_no": 1, "field": "answer", "problem": "描述", "suggestion": "修复建议" }
  ],
  "fixed_paper": { ... 修复后的完整试卷 }
}

试卷JSON：
{{paper_json}}`,
    isActive: true
  }
];

async function main() {
  console.log('Seeding prompt_versions...');

  for (const pv of promptVersions) {
    await prisma.promptVersion.upsert({
      where: {
        name_version: {
          name: pv.name,
          version: pv.version
        }
      },
      update: {
        content: pv.content,
        isActive: pv.isActive
      },
      create: pv
    });
    console.log(`  Upserted prompt: ${pv.name}-${pv.version}`);
  }

  console.log('Seed completed.');
}

main()
  .catch((e) => {
    console.error('Seed failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
