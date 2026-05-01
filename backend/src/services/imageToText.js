const { chat } = require('./deepseekClient');

const MAX_OCR_TIMEOUT = 30000;

async function ocrImage(base64, mimeType) {
  return chat(
    [{
      role: 'user',
      content: [
        { type: 'text', text: '请提取图片中的所有文字内容。如果是公式，用 LaTeX 描述。' },
        { type: 'image_url', image_url: { url: `data:${mimeType};base64,${base64}` } }
      ]
    }],
    { max_tokens: 1024, timeout: MAX_OCR_TIMEOUT }
  );
}

async function ocrImageWithFallback(base64, mimeType) {
  try {
    const text = await ocrImage(base64, mimeType);
    return { text: text.trim(), skipped: false };
  } catch (error) {
    const msg = error.message || '';

    if (msg.includes('image_url') || msg.includes('invalid_request_error')) {
      return {
        text: '',
        skipped: true,
        warning: 'Vision API 不可用（当前模型不支持图片），已跳过图片 OCR'
      };
    }

    if (msg.includes('超时')) {
      return {
        text: '',
        skipped: true,
        warning: '图片 OCR 超时，已跳过'
      };
    }

    return {
      text: '',
      skipped: true,
      warning: `图片 OCR 失败：${msg}`
    };
  }
}

module.exports = { ocrImageWithFallback, MAX_OCR_TIMEOUT };
