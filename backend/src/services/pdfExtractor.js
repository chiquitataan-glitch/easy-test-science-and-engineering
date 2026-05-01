const fs = require('fs');

async function extractPdfText(filePath) {
  const pdfParse = require('pdf-parse');
  const buffer = fs.readFileSync(filePath);
  const data = await pdfParse(buffer);
  return data.text || '';
}

module.exports = { extractPdfText };
