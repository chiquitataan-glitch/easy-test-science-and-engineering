const express = require('express');
require('dotenv').config();
const deepseekRoutes = require('./routes/deepseek');
const uploadRoutes = require('./routes/upload');
const parseFileRoutes = require('./routes/parseFile');
const generatePaperRoutes = require('./routes/generatePaper');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

app.use('/api', deepseekRoutes);
app.use('/api', uploadRoutes);
app.use('/api', parseFileRoutes);
app.use('/api', generatePaperRoutes);

app.get('/health', (req, res) => {
  res.json({
    success: true,
    data: {
      status: 'ok'
    },
    message: 'ok'
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Backend server running on port ${PORT}`);
});
