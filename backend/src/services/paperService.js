const { PrismaClient } = require('@prisma/client');
const { generatePaper } = require('./paperGenerator');
const { parseFile } = require('./parsers');
const { FileNotFoundError, PermissionDeniedError, PaperNotFoundError, GenerationFailedError } = require('../utils/errors');
const { checkQuota, deductQuota } = require('./quotaService');

const prisma = new PrismaClient();

async function generateAndSave(userId, fileId, courseName, configInput, clientType) {
  const file = await prisma.uploadedFile.findUnique({ where: { id: fileId } });

  if (!file) {
    throw new FileNotFoundError('文件不存在');
  }

  if (file.userId !== userId) {
    throw new PermissionDeniedError('无权使用此文件');
  }

  let parsedText = file.parsedText;

  if (!parsedText) {
    try {
      parsedText = await parseFile(file.path);
      await prisma.uploadedFile.update({
        where: { id: fileId },
        data: { parsedText, status: 'parsed', parsedAt: new Date() }
      });
    } catch (err) {
      throw new GenerationFailedError('文件解析失败，无法生成试卷');
    }
  }

  if (!parsedText || parsedText.trim().length < 50) {
    throw new GenerationFailedError('文件内容太少，无法生成试卷');
  }

  if (!courseName || courseName.trim().length === 0) {
    throw new GenerationFailedError('请提供课程名称');
  }

  await checkQuota(userId);

  const startTime = Date.now();
  let paper;

  try {
    paper = await generatePaper(parsedText, courseName.trim(), configInput);
  } catch (err) {
    throw new GenerationFailedError(err.message || '试卷生成失败');
  }

  const durationMs = Date.now() - startTime;

  const paperRecord = await prisma.generatedPaper.create({
    data: {
      userId,
      fileId,
      courseName: courseName.trim(),
      paperTitle: paper.paper_title || null,
      paperJson: paper,
      parsedTextSnapshot: parsedText,
      config: configInput || null,
      qualityReport: paper.quality_report || null,
      knowledgeSummary: paper.knowledge_summary || null,
      promptVersion: paper.quality_report?.prompt_version || 'generate-v1',
      modelName: 'deepseek-chat',
      tokenUsage: paper.usage?.total_tokens || null,
      status: 'completed',
      clientType: clientType || 'web'
    }
  });

  if (paper.questions && Array.isArray(paper.questions)) {
    const questionData = paper.questions.map((q) => ({
      paperId: paperRecord.id,
      questionNo: q.question_no,
      questionType: q.question_type,
      content: q.content,
      options: q.options || null,
      answer: q.answer,
      analysis: q.analysis || null,
      knowledgePoints: q.knowledge_points || null,
      difficulty: q.difficulty || null,
      score: q.score || null
    }));

    await prisma.paperQuestion.createMany({ data: questionData });
  }

  await prisma.generationLog.create({
    data: {
      paperId: paperRecord.id,
      status: 'completed',
      durationMs,
      tokenUsage: paper.usage?.total_tokens || null
    }
  });

  const questionCount = paper.questions ? paper.questions.length : 0;
  const qualityScore = paper.quality_report?.score ?? null;

  await deductQuota(userId, 'generate', 'paper', paperRecord.id, clientType || 'web');

  return {
    paperId: paperRecord.id,
    paperTitle: paperRecord.paperTitle,
    courseName: paperRecord.courseName,
    questionCount,
    qualityScore,
    paper
  };
}

async function getUserPapers(userId, options = {}) {
  const page = Math.max(1, parseInt(options.page, 10) || 1);
  const pageSize = Math.min(100, Math.max(1, parseInt(options.pageSize, 10) || 20));
  const skip = (page - 1) * pageSize;

  const [papers, total] = await Promise.all([
    prisma.generatedPaper.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
      skip,
      take: pageSize,
      include: {
        uploadedFile: {
          select: { originalName: true }
        }
      }
    }),
    prisma.generatedPaper.count({ where: { userId } })
  ]);

  const items = papers.map((p) => {
    let questionCount = 0;
    let qualityScore = null;

    try {
      const json = typeof p.paperJson === 'string' ? JSON.parse(p.paperJson) : p.paperJson;
      questionCount = json.questions ? json.questions.length : 0;
    } catch (e) { /* ignore */ }

    try {
      const qr = typeof p.qualityReport === 'string' ? JSON.parse(p.qualityReport) : p.qualityReport;
      qualityScore = qr?.score ?? null;
    } catch (e) { /* ignore */ }

    return {
      id: p.id,
      paperTitle: p.paperTitle,
      courseName: p.courseName,
      questionCount,
      status: p.status,
      qualityScore,
      fileName: p.uploadedFile?.originalName || null,
      clientType: p.clientType,
      originalPaperId: p.originalPaperId,
      createdAt: p.createdAt
    };
  });

  return { items, total, page, pageSize };
}

async function getPaperById(id, userId) {
  const paper = await prisma.generatedPaper.findUnique({
    where: { id },
    include: {
      paperQuestions: {
        orderBy: { questionNo: 'asc' }
      },
      uploadedFile: {
        select: { id: true, originalName: true, mimeType: true, size: true }
      }
    }
  });

  if (!paper) {
    throw new PaperNotFoundError('试卷不存在');
  }

  if (paper.userId !== userId) {
    throw new PermissionDeniedError('无权访问此试卷');
  }

  let paperJson = paper.paperJson;
  let config = paper.config;
  let qualityReport = paper.qualityReport;
  let knowledgeSummary = paper.knowledgeSummary;

  try {
    if (typeof paperJson === 'string') paperJson = JSON.parse(paperJson);
  } catch (e) { /* keep as-is */ }
  try {
    if (typeof config === 'string') config = JSON.parse(config);
  } catch (e) { /* keep as-is */ }
  try {
    if (typeof qualityReport === 'string') qualityReport = JSON.parse(qualityReport);
  } catch (e) { /* keep as-is */ }
  try {
    if (typeof knowledgeSummary === 'string') knowledgeSummary = JSON.parse(knowledgeSummary);
  } catch (e) { /* keep as-is */ }

  return {
    id: paper.id,
    paperTitle: paper.paperTitle,
    courseName: paper.courseName,
    status: paper.status,
    clientType: paper.clientType,
    paperJson,
    config,
    qualityReport,
    knowledgeSummary,
    promptVersion: paper.promptVersion,
    modelName: paper.modelName,
    tokenUsage: paper.tokenUsage,
    originalPaperId: paper.originalPaperId,
    file: paper.uploadedFile ? {
      id: paper.uploadedFile.id,
      originalName: paper.uploadedFile.originalName,
      mimeType: paper.uploadedFile.mimeType,
      size: paper.uploadedFile.size
    } : null,
    questions: paper.paperQuestions,
    createdAt: paper.createdAt
  };
}

async function regeneratePaper(paperId, userId, configOverride) {
  const original = await prisma.generatedPaper.findUnique({
    where: { id: paperId }
  });

  if (!original) {
    throw new PaperNotFoundError('试卷不存在');
  }

  if (original.userId !== userId) {
    throw new PermissionDeniedError('无权操作此试卷');
  }

  if (!original.parsedTextSnapshot || original.parsedTextSnapshot.trim().length < 50) {
    throw new GenerationFailedError('原试卷缺少文本快照，无法重新生成');
  }

  await checkQuota(userId);

  const config = configOverride || original.config;

  const startTime = Date.now();
  let paper;

  try {
    paper = await generatePaper(original.parsedTextSnapshot, original.courseName, config);
  } catch (err) {
    throw new GenerationFailedError(err.message || '试卷重新生成失败');
  }

  const durationMs = Date.now() - startTime;

  const normalConfig = config && typeof config === 'object' && !Array.isArray(config) ? config : null;

  const paperRecord = await prisma.generatedPaper.create({
    data: {
      userId,
      fileId: original.fileId,
      courseName: original.courseName,
      paperTitle: paper.paper_title || null,
      paperJson: paper,
      parsedTextSnapshot: original.parsedTextSnapshot,
      config: normalConfig,
      qualityReport: paper.quality_report || null,
      knowledgeSummary: paper.knowledge_summary || null,
      promptVersion: paper.quality_report?.prompt_version || 'generate-v1',
      modelName: 'deepseek-chat',
      tokenUsage: paper.usage?.total_tokens || null,
      status: 'completed',
      clientType: original.clientType,
      originalPaperId: paperId
    }
  });

  if (paper.questions && Array.isArray(paper.questions)) {
    const questionData = paper.questions.map((q) => ({
      paperId: paperRecord.id,
      questionNo: q.question_no,
      questionType: q.question_type,
      content: q.content,
      options: q.options || null,
      answer: q.answer,
      analysis: q.analysis || null,
      knowledgePoints: q.knowledge_points || null,
      difficulty: q.difficulty || null,
      score: q.score || null
    }));

    await prisma.paperQuestion.createMany({ data: questionData });
  }

  await prisma.generationLog.create({
    data: {
      paperId: paperRecord.id,
      status: 'completed',
      durationMs,
      tokenUsage: paper.usage?.total_tokens || null
    }
  });

  const questionCount = paper.questions ? paper.questions.length : 0;
  const qualityScore = paper.quality_report?.score ?? null;

  await deductQuota(userId, 'regenerate', 'paper', paperRecord.id, original.clientType);

  return {
    paperId: paperRecord.id,
    paperTitle: paperRecord.paperTitle,
    courseName: paperRecord.courseName,
    questionCount,
    qualityScore,
    originalPaperId: paperId,
    paper
  };
}

module.exports = { generateAndSave, getUserPapers, getPaperById, regeneratePaper };
