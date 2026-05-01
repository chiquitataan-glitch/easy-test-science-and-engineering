<template>
  <div class="app">
    <h1>试卷历史</h1>

    <div v-if="loading" class="loading-state">
      <span class="spinner"></span> 加载中...
    </div>

    <div v-else-if="error" class="error-box">
      <div class="error-icon">⚠️</div>
      <div class="error-msg">{{ error }}</div>
      <button class="btn-link" @click="fetchPapers">重试</button>
    </div>

    <div v-else-if="!items.length" class="empty-state">
      📄 暂无试卷，
      <router-link to="/">去生成</router-link>
    </div>

    <div v-else class="paper-list">
      <div v-for="item in items" :key="item.id" class="paper-row" @click="goDetail(item.id)">
        <div class="paper-row-main">
          <div class="paper-row-title">{{ item.paperTitle || '未命名试卷' }}</div>
          <div class="paper-row-meta">
            <span>{{ item.courseName }}</span>
            <span>·</span>
            <span>{{ item.questionCount }} 题</span>
            <span>·</span>
            <span v-if="item.qualityScore !== null" :class="scoreColor(item.qualityScore)">{{ item.qualityScore }} 分</span>
            <span v-else>- 分</span>
          </div>
        </div>
        <div class="paper-row-extra">
          <span class="paper-status" :class="item.status">{{ statusLabel(item.status) }}</span>
          <span class="paper-date">{{ formatDate(item.createdAt) }}</span>
        </div>
      </div>

      <div class="pagination" v-if="totalPages > 1">
        <button :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient } from '../api/client'

const router = useRouter()

const items = ref([])
const loading = ref(true)
const error = ref('')
const page = ref(1)
const total = ref(0)
const pageSize = ref(20)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

function statusLabel(s) {
  const map = { pending: '解析中', generating: '生成中', completed: '已完成', failed: '失败' }
  return map[s] || s
}

function scoreColor(s) {
  if (s >= 90) return 'score-high'
  if (s >= 70) return 'score-mid'
  return 'score-low'
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function goDetail(id) {
  router.push(`/papers/${id}`)
}

function goPage(p) {
  page.value = p
  fetchPapers()
}

async function fetchPapers() {
  loading.value = true
  error.value = ''
  try {
    const data = await apiClient(`/api/papers?page=${page.value}&pageSize=${pageSize.value}`)
    items.value = data.data.items
    total.value = data.data.total
  } catch (err) {
    error.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchPapers)
</script>
