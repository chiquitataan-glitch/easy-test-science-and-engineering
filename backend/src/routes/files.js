const express = require('express');
const multer = require('multer');
const path = require('path');
const crypto = require('crypto');
const { requireAuth } = require('../middleware/auth');
const { createFileRecord, getUserFiles, getFileById, deleteFile } = require('../services/fileService');
const { parseFile } = require('../services/parsers');
const { isAllowedExtension, isAllowedMimeType, errorMessage, getFileExtension } = require('../config/fileTypes');
const { successResponse, errorResponse } = require('../utils/response');
const { ValidationError, UnsupportedFileTypeError } = require('../utils/errors');

const router = express.Router();

const MAX_FILE_SIZE = parseInt(process.env.MAX_FILE_SIZE, 10) || 20971520;

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/');
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, `${crypto.randomUUID()}${ext}`);
  }
});

const fileFilter = (req, file, cb) => {
  if (!isAllowedMimeType(file.mimetype) && !isAllowedExtension(file.originalname)) {
    cb(new UnsupportedFileTypeError(errorMessage()), false);
    return;
  }
  cb(null, true);
};

const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: MAX_FILE_SIZE }
});

router.post('/upload', requireAuth, upload.single('file'), async (req, res, next) => {
  if (!req.file) {
    return res.status(400).json(
      errorResponse('VALIDATION_ERROR', '请上传文件')
    );
  }

  const { originalname, mimetype, size, path: filePath } = req.file;
  const ext = getFileExtension(originalname);

  let parsedText = null;
  let status = 'parsed';

  try {
    parsedText = await parseFile(filePath);
  } catch (err) {
    console.warn(`[files] Parse failed for ${originalname}:`, err.message);
    status = 'failed';
  }

  const fileRecord = await createFileRecord({
    userId: req.user.userId,
    originalName: originalname,
    mimeType: mimetype || ext,
    size,
    path: filePath,
    parsedText,
    status,
    clientType: req.user.clientType
  });

  return res.status(201).json(
    successResponse({
      id: fileRecord.id,
      originalName: fileRecord.originalName,
      mimeType: fileRecord.mimeType,
      size: fileRecord.size,
      status: fileRecord.status,
      parsedTextLength: parsedText ? parsedText.length : 0,
      clientType: fileRecord.clientType,
      createdAt: fileRecord.createdAt
    }, '上传成功')
  );
});

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const { page, pageSize } = req.query;
    const result = await getUserFiles(req.user.userId, { page, pageSize });

    return res.json(successResponse(result, 'ok'));
  } catch (err) {
    next(err);
  }
});

router.get('/:id', requireAuth, async (req, res, next) => {
  try {
    const file = await getFileById(req.params.id, req.user.userId);

    return res.json(successResponse(file, 'ok'));
  } catch (err) {
    next(err);
  }
});

router.delete('/:id', requireAuth, async (req, res, next) => {
  try {
    const result = await deleteFile(req.params.id, req.user.userId);

    return res.json(successResponse(result, '删除成功'));
  } catch (err) {
    next(err);
  }
});

router.use((err, req, res, next) => {
  if (err instanceof UnsupportedFileTypeError) {
    return res.status(400).json(
      errorResponse('UNSUPPORTED_FILE_TYPE', err.message)
    );
  }
  if (err.code === 'LIMIT_FILE_SIZE') {
    return res.status(413).json(
      errorResponse('VALIDATION_ERROR', `文件大小不能超过 ${Math.round(MAX_FILE_SIZE / 1024 / 1024)}MB`)
    );
  }
  if (err instanceof multer.MulterError) {
    return res.status(400).json(
      errorResponse('VALIDATION_ERROR', '文件上传失败')
    );
  }
  next(err);
});

module.exports = router;
