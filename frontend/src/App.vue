<template>
  <div class="app">
    <h1>Easy Test - AI试卷生成</h1>
    <div class="upload-section">
      <input type="file" @change="handleFileChange" />
      <button @click="uploadFile" :disabled="!selectedFile">上传资料</button>
    </div>
    <div v-if="message" class="message">{{ message }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const selectedFile = ref(null)
const message = ref('')

const handleFileChange = (e) => {
  selectedFile.value = e.target.files[0]
}

const uploadFile = async () => {
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  
  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    })
    const data = await res.json()
    message.value = data.message || '上传成功！'
  } catch (err) {
    message.value = '上传失败：' + err.message
  }
}
</script>
