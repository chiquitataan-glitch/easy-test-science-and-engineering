const jwt = require('jsonwebtoken');
const { TokenExpiredError, AuthRequiredError } = require('../utils/errors');

function signToken(userId, clientType, identityProvider) {
  const payload = {
    sub: userId,
    userId,
    clientType,
    identityProvider,
    iat: Math.floor(Date.now() / 1000)
  };

  const secret = process.env.JWT_SECRET;
  const expiresIn = process.env.JWT_EXPIRES_IN;

  return jwt.sign(payload, secret, { expiresIn });
}

function verifyToken(token) {
  if (!token) {
    throw new AuthRequiredError('请先登录');
  }

  try {
    return jwt.verify(token, process.env.JWT_SECRET);
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      throw new TokenExpiredError('登录已过期，请重新登录');
    }
    throw new AuthRequiredError('无效的登录凭证');
  }
}

module.exports = { signToken, verifyToken };
