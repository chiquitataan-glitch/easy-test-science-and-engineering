const express = require('express');
const path = require('path');
const fs = require('fs');
const { extractPdfText } = require('../services/pdfExtractor');
const { extractDocxText } = require('../services/docxExtractor');
const { generatePaper } = require('../services/paperGenerator');

const router = express.Router();

const SUPPORTED_TYPES = ['.pdf', '.docx'];

router.post('/generate-paper', async (req, res) => {
  const { filePath, courseName } = req.body;

  if (!filePath) {
    return res.status(400).json({
      success: false,
      message: '请提供文件路径'
    });
  }

  if (!courseName || courseName.trim().length === 0) {
    return res.status(400).json({
      success: false,
      message: '请提供课程名称'
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

    if (!text || text.trim().length === 0) {
      return res.status(400).json({
        success: false,
        message: '文件中未提取到文本内容'
      });
    }

    const paper = await generatePaper(text, courseName.trim());

    res.json({
      success: true,
      data: {
        courseName: courseName.trim(),
        paper: paper,
        textLength: text.length
      },
      message: 'ok'
    });
  } catch (error) {
    console.error('Generate paper error:', error.message);

    res.status(400).json({
      success: false,
      message: error.message || '试卷生成失败'
    });
  }
});

module.exports = router;
