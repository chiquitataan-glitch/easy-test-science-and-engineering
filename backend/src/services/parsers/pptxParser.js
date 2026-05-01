const fs = require('fs');
const { parseOffice } = require('officeparser');
const { extractImages } = require('./pptxImageExtractor');
const { ocrImageWithFallback } = require('../imageToText');

function extractTextFromNode(node) {
  if (typeof node === 'string') return node;
  let text = '';
  if (node.text) text += node.text + '\n';
  if (node.children) {
    for (const child of node.children) {
      text += extractTextFromNode(child);
    }
  }
  return text;
}

async function extractPptxText(filePath) {
  const buffer = fs.readFileSync(filePath);
  const result = await parseOffice(buffer);
  let text = '';

  if (result.content) {
    for (const slide of result.content) {
      text += extractTextFromNode(slide);
    }
  }

  const { images, warnings: extractWarnings } = await extractImages(buffer);

  for (const w of extractWarnings) {
    console.warn(`[pptx] ${w}`);
  }

  if (images.length > 0) {
    const ocrTexts = [];

    for (const img of images) {
      const ocr = await ocrImageWithFallback(img.base64, img.mimeType);
      if (ocr.text) {
        ocrTexts.push(ocr.text);
      }
      if (ocr.warning) {
        console.warn(`[pptx] ${img.name}: ${ocr.warning}`);
      }
    }

    if (ocrTexts.length > 0) {
      text += '\n\n[图片中的文字内容]\n' + ocrTexts.join('\n---\n') + '\n';
    }
  }

  return text.trim();
}

module.exports = { extractPptxText };
