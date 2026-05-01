const express = require('express');
require('dotenv').config();
const { validateEnv } = require('./config/env');
const { errorHandler } = require('./middleware/errorHandler');
const deepseekRoutes = require('./routes/deepseek');
const uploadRoutes = require('./routes/upload');
const parseFileRoutes = require('./routes/parseFile');
const generatePaperRoutes = require('./routes/generatePaper');
const authRoutes = require('./routes/auth');
const filesRoutes = require('./routes/files');
const papersRoutes = require('./routes/papers');

validateEnv();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

app.use('/api', deepseekRoutes);
app.use('/api', uploadRoutes);
app.use('/api', parseFileRoutes);
app.use('/api', generatePaperRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/files', filesRoutes);
app.use('/api/papers', papersRoutes);

app.get('/health', (req, res) => {
  res.json({
    success: true,
    data: {
      status: 'ok'
    },
    message: 'ok'
  });
});

app.use(errorHandler);

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Backend server running on port ${PORT}`);
});
