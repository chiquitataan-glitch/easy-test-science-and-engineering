const express = require('express');
const fs = require('fs');
const { isAllowedExtension, LABEL } = require('../config/fileTypes');
const { parseFile } = require('../services/parsers');
const { generatePaper } = require('../services/paperGenerator');
const { normalizePaperConfig } = require('../config/paperConfig');

const router = express.Router();

router.post('/generate-paper', async (req, res) => {
  const { filePath, courseName, config } = req.body;

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
    normalizePaperConfig(config);
  } catch (error) {
    return res.status(400).json({
      success: false,
      message: error.message
    });
  }

  if (!isAllowedExtension(filePath)) {
    return res.status(400).json({
      success: false,
      message: `不支持的文件类型，仅支持 ${LABEL}`
    });
  }

  if (!fs.existsSync(filePath)) {
    return res.status(400).json({
      success: false,
      message: '文件不存在'
    });
  }

  try {
    const text = await parseFile(filePath);

    if (!text || text.trim().length === 0) {
      return res.status(400).json({
        success: false,
        message: '文件中未提取到文本内容'
      });
    }

    const paper = await generatePaper(text, courseName.trim(), config);

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
