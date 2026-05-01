const path = require('path');

const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];

const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
];

const LABEL = 'PDF / DOCX';

function isAllowedExtension(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  return ALLOWED_EXTENSIONS.includes(ext);
}

function isAllowedMimeType(mimeType) {
  return ALLOWED_MIME_TYPES.includes(mimeType);
}

function getFileExtension(filePath) {
  return path.extname(filePath).toLowerCase();
}

function errorMessage() {
  return `仅支持 ${LABEL} 文件`;
}

module.exports = {
  ALLOWED_EXTENSIONS,
  ALLOWED_MIME_TYPES,
  LABEL,
  isAllowedExtension,
  isAllowedMimeType,
  getFileExtension,
  errorMessage
};
