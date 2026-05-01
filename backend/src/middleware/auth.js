const { verifyToken } = require('../services/tokenService');

function requireAuth(req, res, next) {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        success: false,
        data: null,
        message: '请先登录',
        error: {
          code: 'AUTH_REQUIRED',
          details: {}
        }
      });
    }

    const token = authHeader.split(' ')[1];
    const decoded = verifyToken(token);

    req.user = {
      userId: decoded.userId,
      clientType: decoded.clientType,
      identityProvider: decoded.identityProvider
    };

    next();
  } catch (err) {
    return res.status(401).json({
      success: false,
      data: null,
      message: err.message || '请先登录',
      error: {
        code: err.code || 'AUTH_REQUIRED',
        details: {}
      }
    });
  }
}

function optionalAuth(req, res, next) {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      req.user = null;
      return next();
    }

    const token = authHeader.split(' ')[1];
    const decoded = verifyToken(token);

    req.user = {
      userId: decoded.userId,
      clientType: decoded.clientType,
      identityProvider: decoded.identityProvider
    };

    next();
  } catch (err) {
    req.user = null;
    next();
  }
}

module.exports = { requireAuth, optionalAuth };
