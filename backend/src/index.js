const express = require('express');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

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
