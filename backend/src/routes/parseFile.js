const express = require('express');
const path = require('path');
const fs = require('fs');
const { extractPdfText } = require('../services/pdfExtractor');
const { extractDocxText } = require('../services/docxExtractor');

const router = express.Router();

const SUPPORTED_TYPES = ['.pdf', '.docx'];
const PREVIEW_LENGTH = 1000;

router.post('/parse-file', async (req, res) => {
  const { filePath } = req.body;

  if (!filePath) {
    return res.status(400).json({
      success: false,
      message: '请提供文件路径'
    });
  }

  try {
    const ext = path.extname(filePath).toLowerCase();

    if (!SUPPORTED_TYPES.includes(ext)) {
      return res.status(400).json({
        success: false,
        message: '不支持的文件类型，仅支持 PDF 和 DOCX'
      });
    }

    if (!fs.existsSync(filePath)) {
      return res.status(400).json({
        success: false,
        message: '文件不存在'
      });
    }

    let text = '';

    if (ext === '.pdf') {
      text = await extractPdfText(filePath);
    } else if (ext === '.docx') {
      text = await extractDocxText(filePath);
    }

    res.json({
      success: true,
      data: {
        fileName: path.basename(filePath),
        fileType: ext,
        textLength: text.length,
        preview: text.substring(0, PREVIEW_LENGTH)
      },
      message: 'ok'
    });
  } catch (error) {
    console.error('File parse error:', error.message);

    res.status(400).json({
      success: false,
      message: error.message || '文件解析失败'
    });
  }
});

module.exports = router;
