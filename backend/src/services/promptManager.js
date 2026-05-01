const fs = require('fs');
const path = require('path');

const PROMPTS_DIR = path.resolve(__dirname, '../prompts');

function loadPrompt(promptName) {
  const filePath = path.join(PROMPTS_DIR, `${promptName}.txt`);

  if (!fs.existsSync(filePath)) {
    throw new Error(`Prompt 文件不存在：${promptName}`);
  }

  return fs.readFileSync(filePath, 'utf-8');
}

function renderPrompt(promptName, variables = {}) {
  let template = loadPrompt(promptName);

  for (const [key, value] of Object.entries(variables)) {
    template = template.replaceAll(`{{${key}}}`, value);
  }

  return template;
}

module.exports = { loadPrompt, renderPrompt };
