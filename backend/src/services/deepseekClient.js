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

    const status = error.response?.status;
    if (status === 401 || status === 403) {
      throw new Error('DeepSeek API 认证失败，请检查 API Key');
    }
    if (status === 429) {
      throw new Error('DeepSeek API 请求过于频繁，请稍后重试');
    }
    if (status === 400) {
      throw new Error('DeepSeek API 请求参数错误，请检查输入内容');
    }
    throw new Error('DeepSeek API 调用失败，请稍后重试');
  }
}

module.exports = { chat };
