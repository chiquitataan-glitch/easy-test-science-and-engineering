const { AppError, ERROR_CODES } = require('../utils/errors');
const { errorResponse } = require('../utils/response');

function errorHandler(err, req, res, _next) {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json(
      errorResponse(err.code, err.message, err.details)
    );
  }

  console.error('[ERROR]', err);

  const isProduction = process.env.NODE_ENV === 'production';
  const message = isProduction ? '服务器内部错误' : err.message || '服务器内部错误';

  return res.status(500).json(
    errorResponse(ERROR_CODES.INTERNAL_ERROR, message)
  );
}

module.exports = { errorHandler };
