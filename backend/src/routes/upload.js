const express = require('express');
const multer = require('multer');
const path = require('path');

const router = express.Router();

const ALLOWED_TYPES = ['.pdf', '.docx'];
const MAX_FILE_SIZE = 20 * 1024 * 1024;

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/');
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + '-' + file.originalname);
  }
});

const fileFilter = (req, file, cb) => {
  const ext = path.extname(file.originalname).toLowerCase();
  if (ALLOWED_TYPES.includes(ext)) {
    cb(null, true);
  } else {
    cb(new Error('仅支持 PDF 和 DOCX 文件'), false);
  }
};

const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: MAX_FILE_SIZE
  }
});

router.post('/upload', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({
      success: false,
      message: '请上传文件'
    });
  }

  res.json({
    success: true,
    data: {
      originalName: req.file.originalname,
      size: req.file.size,
      type: path.extname(req.file.originalname).toLowerCase(),
      path: req.file.path
    },
    message: 'ok'
  });
});

router.use((err, req, res, next) => {
  if (err.message === '仅支持 PDF 和 DOCX 文件') {
    return res.status(400).json({
      success: false,
      message: err.message
    });
  }
  if (err.code === 'LIMIT_FILE_SIZE') {
    return res.status(413).json({
      success: false,
      message: '文件大小不能超过 20MB'
    });
  }
  if (err instanceof multer.MulterError) {
    return res.status(400).json({
      success: false,
      message: '文件上传失败'
    });
  }
  next(err);
});

module.exports = router;
