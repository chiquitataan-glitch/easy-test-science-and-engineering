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

    <template v-else-if="paperData">
      <div class="detail-toolbar">
        <router-link to="/papers" class="btn-link">← 返回列表</router-link>
        <button class="btn-regenerate" @click="handleRegenerate" :disabled="regenerating">
          <span v-if="regenerating" class="spinner"></span>
          {{ regenerating ? ' 重新生成中...' : '🔄 重新生成' }}
        </button>
      </div>

      <div v-if="regenerateError" class="error-box">
        <div class="error-icon">⚠️</div>
        <div class="error-msg">{{ regenerateError }}</div>
      </div>

      <PaperContent :paper-data="paperData" :paper-title="detail.paperTitle" :course-name="detail.courseName" />

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
    router.push(`/papers/${data.data.paperId}`)
  } catch (err) {
    regenerateError.value = err.message || '重新生成失败'
  } finally {
    regenerating.value = false
  }
}

onMounted(fetchPaper)
</script>
