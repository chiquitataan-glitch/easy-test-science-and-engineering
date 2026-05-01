const express = require('express');
const { requireAuth } = require('../middleware/auth');
const { generateAndSave, getUserPapers, getPaperById, regeneratePaper } = require('../services/paperService');
const { normalizePaperConfig } = require('../config/paperConfig');
const { successResponse, errorResponse } = require('../utils/response');

const router = express.Router();

router.post('/generate', requireAuth, async (req, res, next) => {
  try {
    const { fileId, courseName, config } = req.body;

    if (!fileId) {
      return res.status(400).json(
        errorResponse('VALIDATION_ERROR', '请提供文件ID', { required: ['fileId'] })
      );
    }

    if (!courseName || courseName.trim().length === 0) {
      return res.status(400).json(
        errorResponse('VALIDATION_ERROR', '请提供课程名称', { required: ['courseName'] })
      );
    }

    if (config) {
      try {
        normalizePaperConfig(config);
      } catch (err) {
        return res.status(400).json(
          errorResponse('VALIDATION_ERROR', err.message)
        );
      }
    }

    const result = await generateAndSave(
      req.user.userId,
      fileId,
      courseName,
      config,
      req.user.clientType
    );

    return res.status(201).json(
      successResponse(result, '试卷生成成功')
    );
  } catch (err) {
    next(err);
  }
});

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const { page, pageSize } = req.query;
    const result = await getUserPapers(req.user.userId, { page, pageSize });

    return res.json(successResponse(result, 'ok'));
  } catch (err) {
    next(err);
  }
});

router.get('/:id', requireAuth, async (req, res, next) => {
  try {
    const paper = await getPaperById(req.params.id, req.user.userId);

    return res.json(successResponse(paper, 'ok'));
  } catch (err) {
    next(err);
  }
});

router.post('/:id/regenerate', requireAuth, async (req, res, next) => {
  try {
    const { config } = req.body || {};

    if (config) {
      try {
        normalizePaperConfig(config);
      } catch (err) {
        return res.status(400).json(
          errorResponse('VALIDATION_ERROR', err.message)
        );
      }
    }

    const result = await regeneratePaper(req.params.id, req.user.userId, config || null);

    return res.status(201).json(
      successResponse(result, '试卷重新生成成功')
    );
  } catch (err) {
    next(err);
  }
});

module.exports = router;
