const { getFileExtension, isAllowedExtension } = require('../../config/fileTypes');
const { extractPdfText } = require('../pdfExtractor');
const { extractDocxText } = require('../docxExtractor');
const { extractPptxText } = require('./pptxParser');
const { extractPptText } = require('./pptParser');

const PARSER_MAP = {
  '.pdf': extractPdfText,
  '.docx': extractDocxText,
  '.pptx': extractPptxText,
  '.ppt': extractPptText
};

async function parseFile(filePath) {
  const ext = getFileExtension(filePath);

  if (!isAllowedExtension(filePath)) {
    throw new Error(`不支持的文件类型：${ext}`);
  }

  const parser = PARSER_MAP[ext];

  if (!parser) {
    throw new Error(`未找到解析器：${ext}`);
  }

  return parser(filePath);
}

module.exports = { parseFile };
