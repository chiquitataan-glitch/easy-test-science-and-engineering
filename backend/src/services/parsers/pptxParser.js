const fs = require('fs');
const { parseOffice } = require('officeparser');

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

  return text.trim();
}

module.exports = { extractPptxText };
