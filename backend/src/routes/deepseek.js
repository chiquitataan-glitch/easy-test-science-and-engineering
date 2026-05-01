const express = require('express');
const axios = require('axios');

const router = express.Router();

router.post('/test-deepseek', async (req, res) => {
  const { message } = req.body;

  if (!message) {
    return res.status(400).json({
      success: false,
      message: 'message is required'
    });
  }

  const apiKey = process.env.DEEPSEEK_API_KEY;

  if (!apiKey) {
    return res.status(500).json({
      success: false,
      message: 'DEEPSEEK_API_KEY is not configured'
    });
  }

  try {
    const response = await axios.post(
      'https://api.deepseek.com/v1/chat/completions',
      {
        model: 'deepseek-chat',
        messages: [
          {
            role: 'user',
            content: message
          }
        ]
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        }
      }
    );

    res.json({
      success: true,
      data: {
        reply: response.data.choices[0].message.content
      },
      message: 'ok'
    });
  } catch (error) {
    console.error('DeepSeek API error:', error.message);
    res.status(500).json({
      success: false,
      message: error.response?.data?.error?.message || 'Failed to call DeepSeek API'
    });
  }
});

module.exports = router;
