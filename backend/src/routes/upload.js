const express = require('express');
const multer = require('multer');
const { getFileExtension, isAllowedExtension, errorMessage } = require('../config/fileTypes');

const router = express.Router();

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
  const ext = getFileExtension(file.originalname);
  if (isAllowedExtension(file.originalname)) {
    cb(null, true);
  } else {
    cb(new Error(errorMessage()), false);
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
      type: getFileExtension(req.file.originalname),
      path: req.file.path
    },
    message: 'ok'
  });
});

router.use((err, req, res, next) => {
  if (err.message === errorMessage()) {
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
