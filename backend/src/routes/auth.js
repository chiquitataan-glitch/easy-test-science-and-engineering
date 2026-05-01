const express = require('express');
const { register, login, getMe } = require('../services/authService');
const { requireAuth } = require('../middleware/auth');
const { successResponse, errorResponse } = require('../utils/response');

const router = express.Router();

router.post('/register', async (req, res, next) => {
  try {
    const { email, password, displayName, clientType } = req.body;

    if (!email || !password || !clientType) {
      return res.status(400).json(
        errorResponse('VALIDATION_ERROR', '请填写必填字段：email、password、clientType', {
          required: ['email', 'password', 'clientType']
        })
      );
    }

    const result = await register(email, password, displayName, clientType);

    return res.status(201).json(
      successResponse(result, '注册成功')
    );
  } catch (err) {
    next(err);
  }
});

router.post('/login', async (req, res, next) => {
  try {
    const { email, password, clientType } = req.body;

    if (!email || !password || !clientType) {
      return res.status(400).json(
        errorResponse('VALIDATION_ERROR', '请填写必填字段：email、password、clientType', {
          required: ['email', 'password', 'clientType']
        })
      );
    }

    const result = await login(email, password, clientType);

    return res.json(
      successResponse(result, '登录成功')
    );
  } catch (err) {
    next(err);
  }
});

router.get('/me', requireAuth, async (req, res, next) => {
  try {
    const user = await getMe(req.user.userId);

    return res.json(
      successResponse(user, 'ok')
    );
  } catch (err) {
    next(err);
  }
});

router.post('/logout', requireAuth, (req, res) => {
  return res.json(
    successResponse(null, '已退出登录')
  );
});

router.post('/wechat-mini-program-login', (req, res) => {
  return res.status(501).json(
    errorResponse('NOT_IMPLEMENTED', '微信小程序登录将在 V1.0 实现', {
      planned_version: '1.0.0'
    })
  );
});

module.exports = router;
