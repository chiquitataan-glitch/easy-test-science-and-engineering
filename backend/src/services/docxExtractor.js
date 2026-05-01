const fs = require('fs');
const mammoth = require('mammoth');

async function extractDocxText(filePath) {
  const buffer = fs.readFileSync(filePath);
  const result = await mammoth.extractRawText({ buffer });
  return result.value || '';
}

module.exports = { extractDocxText };
