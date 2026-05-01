const express = require('express');
const { chat } = require('../services/deepseekClient');

const router = express.Router();

router.post('/test-deepseek', async (req, res) => {
  const { message } = req.body;

  if (!message) {
    return res.status(400).json({
      success: false,
      message: 'message is required'
    });
  }

  try {
    const reply = await chat(
      [{ role: 'user', content: message }],
      { temperature: 0.7, max_tokens: 4096, timeout: 30000 }
    );

    res.json({
      success: true,
      data: { reply },
      message: 'ok'
    });
  } catch (error) {
    console.error('DeepSeek API error:', error.message);
    res.status(500).json({
      success: false,
      message: error.message
    });
  }
});

module.exports = router;
