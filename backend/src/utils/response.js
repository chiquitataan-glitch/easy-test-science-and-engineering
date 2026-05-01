function successResponse(data = null, message = 'ok') {
  return {
    success: true,
    data,
    message,
    error: null
  };
}

function errorResponse(code, message, details = {}) {
  return {
    success: false,
    data: null,
    message,
    error: {
      code,
      details
    }
  };
}

module.exports = { successResponse, errorResponse };
