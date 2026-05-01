const { PrismaClient } = require('@prisma/client');
const { FileNotFoundError, PermissionDeniedError } = require('../utils/errors');

const prisma = new PrismaClient();

async function createFileRecord(data) {
  return prisma.uploadedFile.create({
    data: {
      userId: data.userId,
      originalName: data.originalName,
      mimeType: data.mimeType,
      size: data.size,
      path: data.path,
      hash: data.hash || null,
      storageProvider: data.storageProvider || 'local',
      storageKey: data.storageKey || null,
      parsedText: data.parsedText || null,
      status: data.status || 'pending',
      clientType: data.clientType || 'web'
    }
  });
}

async function getUserFiles(userId, options = {}) {
  const page = Math.max(1, parseInt(options.page, 10) || 1);
  const pageSize = Math.min(100, Math.max(1, parseInt(options.pageSize, 10) || 20));
  const skip = (page - 1) * pageSize;

  const [files, total] = await Promise.all([
    prisma.uploadedFile.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
      skip,
      take: pageSize,
      select: {
        id: true,
        originalName: true,
        mimeType: true,
        size: true,
        status: true,
        clientType: true,
        createdAt: true,
        parsedText: false
      }
    }),
    prisma.uploadedFile.count({ where: { userId } })
  ]);

  const items = files.map((f) => ({
    ...f,
    parsedTextLength: null
  }));

  return { items, total, page, pageSize };
}

async function getFileById(id, userId) {
  const file = await prisma.uploadedFile.findUnique({ where: { id } });

  if (!file) {
    throw new FileNotFoundError('文件不存在');
  }

  if (file.userId !== userId) {
    throw new PermissionDeniedError('无权访问此文件');
  }

  return {
    id: file.id,
    originalName: file.originalName,
    mimeType: file.mimeType,
    size: file.size,
    status: file.status,
    storageProvider: file.storageProvider,
    parsedTextLength: file.parsedText ? file.parsedText.length : 0,
    hash: file.hash,
    clientType: file.clientType,
    createdAt: file.createdAt
  };
}

async function deleteFile(id, userId) {
  const file = await prisma.uploadedFile.findUnique({ where: { id } });

  if (!file) {
    throw new FileNotFoundError('文件不存在');
  }

  if (file.userId !== userId) {
    throw new PermissionDeniedError('无权删除此文件');
  }

  const fs = require('fs');
  try {
    if (file.path && fs.existsSync(file.path)) {
      fs.unlinkSync(file.path);
    }
  } catch (e) {
    console.warn(`[fileService] Failed to delete local file: ${file.path}`, e.message);
  }

  await prisma.uploadedFile.delete({ where: { id } });

  return { id: file.id, originalName: file.originalName };
}

module.exports = { createFileRecord, getUserFiles, getFileById, deleteFile };
