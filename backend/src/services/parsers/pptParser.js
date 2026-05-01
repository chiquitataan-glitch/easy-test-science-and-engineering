const { execFile } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { extractPptxText } = require('./pptxParser');

const CONVERT_TIMEOUT = 60000;

function findSoffice() {
  if (process.platform === 'win32') {
    return 'soffice.exe';
  }
  return 'soffice';
}

function execSoffice(args, timeout) {
  return new Promise((resolve, reject) => {
    const child = execFile(findSoffice(), args, { timeout }, (error, stdout, stderr) => {
      if (error) {
        if (error.killed) {
          reject(new Error('PPT 文件转换超时，请检查文件是否损坏或转为 .pptx 后重试'));
        } else {
          reject(new Error(`PPT 文件转换失败：${error.message}`));
        }
        return;
      }
      resolve(stdout);
    });
  });
}

async function extractPptText(filePath) {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptconv-'));
  const inputName = path.basename(filePath);
  const outputName = inputName.replace(/\.ppt$/i, '.pptx');
  const outputPath = path.join(tmpDir, outputName);

  try {
    fs.copyFileSync(filePath, path.join(tmpDir, inputName));

    await execSoffice([
      '--headless',
      '--convert-to', 'pptx',
      '--outdir', tmpDir,
      path.join(tmpDir, inputName)
    ], CONVERT_TIMEOUT);

    if (!fs.existsSync(outputPath)) {
      const files = fs.readdirSync(tmpDir).filter(f => f.endsWith('.pptx'));
      if (files.length === 0) {
        throw new Error('PPT 文件转换失败：未生成 .pptx 文件，文件可能已损坏');
      }
      const text = await extractPptxText(path.join(tmpDir, files[0]));
      return text;
    }

    const text = await extractPptxText(outputPath);
    return text;
  } catch (error) {
    if (error.message && (
      error.message.includes('ENOENT') ||
      error.message.includes('soffice') ||
      error.message.includes('not found')
    )) {
      throw new Error('当前环境未安装 LibreOffice，无法解析 .ppt 文件，请转换为 .pptx 后上传');
    }
    throw error;
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

module.exports = { extractPptText };
