const ERROR_CODES = {
  AUTH_REQUIRED: 'AUTH_REQUIRED',
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',
  PERMISSION_DENIED: 'PERMISSION_DENIED',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  FILE_NOT_FOUND: 'FILE_NOT_FOUND',
  PAPER_NOT_FOUND: 'PAPER_NOT_FOUND',
  QUOTA_EXCEEDED: 'QUOTA_EXCEEDED',
  UNSUPPORTED_FILE_TYPE: 'UNSUPPORTED_FILE_TYPE',
  PARSE_FAILED: 'PARSE_FAILED',
  GENERATION_FAILED: 'GENERATION_FAILED',
  INTERNAL_ERROR: 'INTERNAL_ERROR'
};

class AppError extends Error {
  constructor(statusCode, code, message, details = {}) {
    super(message);
    this.name = 'AppError';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

class AuthRequiredError extends AppError {
  constructor(message = '请先登录') {
    super(401, ERROR_CODES.AUTH_REQUIRED, message);
  }
}

class InvalidCredentialsError extends AppError {
  constructor(message = '用户名或密码错误') {
    super(401, ERROR_CODES.INVALID_CREDENTIALS, message);
  }
}

class TokenExpiredError extends AppError {
  constructor(message = '登录已过期，请重新登录') {
    super(401, ERROR_CODES.TOKEN_EXPIRED, message);
  }
}

class PermissionDeniedError extends AppError {
  constructor(message = '无权访问此资源') {
    super(403, ERROR_CODES.PERMISSION_DENIED, message);
  }
}

class ValidationError extends AppError {
  constructor(message, details = {}) {
    super(400, ERROR_CODES.VALIDATION_ERROR, message, details);
  }
}

class FileNotFoundError extends AppError {
  constructor(message = '文件不存在') {
    super(404, ERROR_CODES.FILE_NOT_FOUND, message);
  }
}

class PaperNotFoundError extends AppError {
  constructor(message = '试卷不存在') {
    super(404, ERROR_CODES.PAPER_NOT_FOUND, message);
  }
}

class QuotaExceededError extends AppError {
  constructor(message = '使用次数已用完') {
    super(403, ERROR_CODES.QUOTA_EXCEEDED, message);
  }
}

class UnsupportedFileTypeError extends AppError {
  constructor(message = '不支持的文件类型') {
    super(400, ERROR_CODES.UNSUPPORTED_FILE_TYPE, message);
  }
}

class ParseFailedError extends AppError {
  constructor(message = '文件解析失败') {
    super(500, ERROR_CODES.PARSE_FAILED, message);
  }
}

class GenerationFailedError extends AppError {
  constructor(message = '试卷生成失败') {
    super(500, ERROR_CODES.GENERATION_FAILED, message);
  }
}

module.exports = {
  ERROR_CODES,
  AppError,
  AuthRequiredError,
  InvalidCredentialsError,
  TokenExpiredError,
  PermissionDeniedError,
  ValidationError,
  FileNotFoundError,
  PaperNotFoundError,
  QuotaExceededError,
  UnsupportedFileTypeError,
  ParseFailedError,
  GenerationFailedError
};
