const axios = require('axios');

const DEFAULT_API_URL = 'https://api.deepseek.com/v1/chat/completions';
const DEFAULT_MODEL = 'deepseek-chat';

function getApiKey() {
  const key = process.env.DEEPSEEK_API_KEY;
  if (!key) {
    throw new Error('DeepSeek API Key 未配置');
  }
  return key;
}

function buildHeaders(apiKey) {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${apiKey}`
  };
}

async function chat(messages, options = {}) {
  const {
    model = DEFAULT_MODEL,
    temperature,
    max_tokens: maxTokens,
    response_format: responseFormat,
    timeout = 120000
  } = options;

  const apiKey = getApiKey();

  const body = {
    model,
    messages
  };

  if (temperature !== undefined) body.temperature = temperature;
  if (maxTokens !== undefined) body.max_tokens = maxTokens;
  if (responseFormat !== undefined) body.response_format = responseFormat;

  try {
    const response = await axios.post(
      process.env.DEEPSEEK_API_URL || DEFAULT_API_URL,
      body,
      {
        headers: buildHeaders(apiKey),
        timeout
      }
    );

    return response.data.choices[0].message.content;
  } catch (error) {
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      throw new Error('DeepSeek API 调用超时');
    }

    const detail = error.response?.data?.error?.message || error.message;
    throw new Error(`DeepSeek API 调用失败：${detail}`);
  }
}

module.exports = { chat };
