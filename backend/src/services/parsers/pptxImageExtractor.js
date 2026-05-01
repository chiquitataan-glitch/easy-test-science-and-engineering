const JSZip = require('jszip');
const path = require('path');

const MAX_IMAGES = 20;
const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'];

function isImageFile(filename) {
  const ext = path.extname(filename).toLowerCase();
  return IMAGE_EXTENSIONS.includes(ext);
}

function mimeType(filename) {
  const ext = path.extname(filename).toLowerCase();
  if (ext === '.png') return 'image/png';
  if (ext === '.jpg' || ext === '.jpeg') return 'image/jpeg';
  if (ext === '.gif') return 'image/gif';
  if (ext === '.webp') return 'image/webp';
  if (ext === '.bmp') return 'image/bmp';
  return 'application/octet-stream';
}

async function extractImages(buffer) {
  const zip = await new JSZip().loadAsync(buffer);

  const mediaFiles = Object.keys(zip.files)
    .filter(f => f.startsWith('ppt/media/') && isImageFile(f));

  const warnings = [];
  const images = [];
  let processed = 0;

  for (const file of mediaFiles) {
    if (processed >= MAX_IMAGES) {
      warnings.push(`图片数量超过 ${MAX_IMAGES} 张限制，已跳过 ${mediaFiles.length - processed} 张`);
      break;
    }

    const entry = zip.files[file];
    const data = await entry.async('nodebuffer');

    if (data.length > MAX_IMAGE_SIZE) {
      warnings.push(`图片 ${path.basename(file)} 大小 ${(data.length / 1024 / 1024).toFixed(1)}MB 超过限制，已跳过`);
      continue;
    }

    if (data.length === 0) {
      continue;
    }

    images.push({
      name: path.basename(file),
      buffer: data,
      mimeType: mimeType(file),
      base64: data.toString('base64')
    });

    processed++;
  }

  return { images, warnings };
}

module.exports = { extractImages, MAX_IMAGES, MAX_IMAGE_SIZE };
