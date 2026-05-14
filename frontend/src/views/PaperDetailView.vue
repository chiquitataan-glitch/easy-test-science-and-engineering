<template>
  <div class="app">
    <div v-if="loading" class="loading-state">
      <span class="spinner"></span> 加载试卷中...
    </div>

    <div v-else-if="error" class="error-box">
      <div class="error-icon">⚠️</div>
      <div class="error-msg">{{ error }}</div>
      <button class="btn-link" @click="fetchPaper">重试</button>
    </div>

    <template v-else-if="detail.id">
      <div class="detail-toolbar">
        <router-link to="/papers" class="btn-link">← 返回列表</router-link>
        <div class="toolbar-actions">
          <button class="btn-export" @click="handleExport" :disabled="exporting">
            {{ exporting ? '导出中...' : '📥 导出 DOCX' }}
          </button>
          <button class="btn-regenerate" @click="handleRegenerate" :disabled="regenerating">
            <span v-if="regenerating" class="spinner"></span>
            {{ regenerating ? ' 重新生成中...' : '🔄 重新生成' }}
          </button>
        </div>
      </div>

      <div v-if="regenerateError" class="error-box">
        <div class="error-icon">⚠️</div>
        <div class="error-msg">{{ regenerateError }}</div>
      </div>

      <PaperContent v-if="paperData" :paper-data="paperData" :paper-title="detail.paperTitle" :course-name="detail.courseName" />
      <div v-else-if="detail.status === 'failed'" class="error-box">
        <div class="error-icon">⚠️</div>
        <div class="error-msg">
          试卷生成失败
          <div v-if="detail.failReason" style="margin-top:6px;font-size:13px;opacity:0.8;">原因：{{ detail.failReason }}</div>
        </div>
      </div>
      <div v-else class="empty-paper">
        <p>试卷内容加载中或试卷内容为空，请尝试重新生成。</p>
      </div>

      <div class="detail-meta">
        <div v-if="detail.originalPaperId" class="detail-info">
          基于试卷 <router-link :to="`/papers/${detail.originalPaperId}`">{{ detail.originalPaperId }}</router-link> 重新生成
        </div>
        <div class="detail-info">模型：{{ detail.modelName || '-' }}</div>
        <div class="detail-info">Prompt 版本：{{ detail.promptVersion || '-' }}</div>
        <div class="detail-info" v-if="detail.tokenUsage">Token 用量：{{ detail.tokenUsage }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiClient } from '../api/client'
import { refreshUser } from '../stores/authStore'
import PaperContent from '../components/PaperContent.vue'

const route = useRoute()
const router = useRouter()

const detail = ref({})
const paperData = ref(null)
const loading = ref(true)
const error = ref('')
const regenerating = ref(false)
const regenerateError = ref('')
const exporting = ref(false)

async function fetchPaper() {
  loading.value = true
  error.value = ''
  try {
    const data = await apiClient(`/api/papers/${route.params.id}`)
    detail.value = data.data
    paperData.value = data.data.paperJson
  } catch (err) {
    error.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleRegenerate() {
  regenerating.value = true
  regenerateError.value = ''
  try {
    const data = await apiClient(`/api/papers/${route.params.id}/regenerate`, { method: 'POST' })
    await refreshUser()
    router.push(`/papers/${data.data.id}`)
  } catch (err) {
    regenerateError.value = err.message || '重新生成失败'
  } finally {
    regenerating.value = false
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const token = (await import('../stores/authStore')).state.token
    const response = await fetch(`/api/papers/${route.params.id}/export`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) {
      const contentType = response.headers.get('Content-Type') || ''
      if (contentType.includes('application/json')) {
        const errData = await response.json()
        const msg = errData.message || errData.detail || `导出失败 (${response.status})`
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      }
      throw new Error(`导出失败 (HTTP ${response.status})`)
    }
    const contentType = response.headers.get('Content-Type') || ''
    if (!contentType.includes('vnd.openxmlformats') && !contentType.includes('msword')) {
      const text = await response.text()
      try {
        const json = JSON.parse(text)
        throw new Error(json.message || json.detail || '导出失败：服务端返回了非文档格式数据')
      } catch (parseErr) {
        if (parseErr.message !== text) throw parseErr
        throw new Error('导出失败：服务端返回了非预期的响应格式')
      }
    }
    const blob = await response.blob()
    const disposition = response.headers.get('Content-Disposition') || ''
    let filename = '试卷.docx'
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/)
    if (utf8Match) {
      filename = decodeURIComponent(utf8Match[1])
    } else {
      const filenameMatch = disposition.match(/filename="?(.+?)"?$/)
      if (filenameMatch) filename = filenameMatch[1]
    }
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    regenerateError.value = err.message || '导出失败'
  } finally {
    exporting.value = false
  }
}

onMounted(fetchPaper)
</script>
