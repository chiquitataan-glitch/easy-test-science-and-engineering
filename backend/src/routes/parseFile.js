const express = require('express');
const path = require('path');
const fs = require('fs');
const { requireAuth } = require('../middleware/auth');
const { getFileExtension, isAllowedExtension, LABEL } = require('../config/fileTypes');
const { parseFile } = require('../services/parsers');

const router = express.Router();

const PREVIEW_LENGTH = 1000;

function isSafePath(filePath) {
  const resolved = path.resolve(filePath);
  const uploadsDir = path.resolve(process.env.UPLOAD_DIR || './uploads');
  return resolved.startsWith(uploadsDir);
}

router.post('/parse-file', requireAuth, async (req, res) => {
  const { filePath } = req.body;

  if (!filePath) {
    return res.status(400).json({
      success: false,
      message: '请提供文件路径'
    });
  }

  try {
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

    if (!isSafePath(filePath)) {
      return res.status(400).json({
        success: false,
        message: '无效的文件路径'
      });
    }

    const text = await parseFile(filePath);
    const ext = getFileExtension(filePath);

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
