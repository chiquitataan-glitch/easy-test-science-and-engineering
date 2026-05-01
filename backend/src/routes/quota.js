const express = require('express');
const { requireAuth } = require('../middleware/auth');
const { getQuotaInfo, getUsageRecords } = require('../services/quotaService');
const { successResponse } = require('../utils/response');

const router = express.Router();

router.get('/me', requireAuth, async (req, res, next) => {
  try {
    const info = await getQuotaInfo(req.user.userId);
    return res.json(successResponse(info, 'ok'));
  } catch (err) {
    next(err);
  }
});

router.get('/usage-records', requireAuth, async (req, res, next) => {
  try {
    const { page, pageSize } = req.query;
    const result = await getUsageRecords(req.user.userId, { page, pageSize });
    return res.json(successResponse(result, 'ok'));
  } catch (err) {
    next(err);
  }
});

module.exports = router;
