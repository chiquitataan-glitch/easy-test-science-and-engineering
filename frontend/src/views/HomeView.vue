<template>
  <div class="app">
    <h1>AI试卷生成</h1>

    <div class="form-section">
      <div class="form-group">
        <label for="courseName">课程名称</label>
        <input id="courseName" v-model="courseName" type="text" placeholder="例如：化工原理" :disabled="loading" />
      </div>

      <div class="form-group">
        <label for="fileInput">上传资料（支持 PDF / DOCX / PPT / PPTX，可选 3-15 个文件）</label>
        <input id="fileInput" type="file" accept=".pdf,.docx,.ppt,.pptx" multiple @change="handleFileChange" :disabled="loading" />
        <div v-if="selectedFiles.length" class="file-list">
          <span v-for="(f, i) in selectedFiles" :key="i" class="file-name">{{ f.name }}</span>
          <span class="file-count">共 {{ selectedFiles.length }} 个文件</span>
        </div>
        <p class="file-hint">单个文件最大 20MB，至少选择 3 个文件</p>
      </div>

      <div class="config-toggle" @click="showConfig = !showConfig">
        <span class="config-arrow">{{ showConfig ? '▼' : '▶' }}</span>
        出题配置（可选，点击展开）
      </div>

      <div v-if="showConfig" class="config-panel">
        <div class="config-row config-row-header">
          <span>题型</span><span>数量</span><span>分值</span>
        </div>
        <div v-for="t in configTypes" :key="t.key" class="config-row">
          <span class="config-type-label">{{ t.label }}</span>
          <input type="number" min="0" max="50" :value="config.types[t.key].count" @input="e => updateTypeCount(t.key, parseInt(e.target.value) || 0)" :disabled="loading" />
          <input type="number" min="0.5" max="100" step="0.5" :value="config.types[t.key].score" @input="e => updateTypeScore(t.key, parseFloat(e.target.value) || 0)" :disabled="loading" />
        </div>
        <div class="config-summary">总题数：<strong>{{ configTotal }}</strong> 道</div>
        <div class="config-divider"></div>
        <div class="config-row config-row-header">
          <span>难度</span><span>比例</span><span></span>
        </div>
        <div v-for="d in configDifficulties" :key="d.key" class="config-row">
          <span class="config-type-label">{{ d.label }}</span>
          <input type="number" min="0" max="100" step="5" :value="Math.round(config.difficulty[d.key] * 100)" @input="e => updateDifficulty(d.key, (parseInt(e.target.value) || 0) / 100)" :disabled="loading" />
          <span>%</span>
        </div>
      </div>

      <button class="btn-generate" @click="handleGenerate" :disabled="!canGenerate">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? ' 正在生成试卷...' : '生成试卷' }}
      </button>
    </div>

    <div v-if="error" class="error-box">
      <div class="error-icon">⚠️</div>
      <div class="error-msg">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient } from '../api/client'
import { refreshUser } from '../stores/authStore'

const router = useRouter()

const configTypes = [
  { key: 'single_choice', label: '单选题' },
  { key: 'multi_choice', label: '多选题' },
  { key: 'fill_blank', label: '填空题' },
  { key: 'true_false', label: '判断题' },
  { key: 'calculation', label: '计算题' },
  { key: 'short_answer', label: '简答题' }
]

const configDifficulties = [
  { key: 'easy', label: '简单' },
  { key: 'medium', label: '中等' },
  { key: 'hard', label: '困难' }
]

const courseName = ref('')
const selectedFiles = ref([])
const loading = ref(false)
const error = ref('')
const showConfig = ref(false)

const config = reactive({
  types: {
    single_choice: { count: 8, score: 5 },
    multi_choice: { count: 2, score: 5 },
    fill_blank: { count: 10, score: 2 },
    true_false: { count: 10, score: 1 },
    calculation: { count: 4, score: 3 },
    short_answer: { count: 2, score: 4 }
  },
  difficulty: { easy: 0.3, medium: 0.5, hard: 0.2 }
})

const updateTypeCount = (key, val) => { config.types[key].count = val }
const updateTypeScore = (key, val) => { config.types[key].score = val }
const updateDifficulty = (key, val) => { config.difficulty[key] = val }

const canGenerate = computed(() => courseName.value.trim() && selectedFiles.value.length >= 3 && !loading.value)
const configTotal = computed(() => Object.values(config.types).reduce((s, t) => s + t.count, 0))

const handleFileChange = (e) => {
  selectedFiles.value = Array.from(e.target.files || [])
  error.value = ''
}

async function handleGenerate() {
  if (!canGenerate.value) return

  loading.value = true
  error.value = ''

  try {
    const fileIds = []
    for (const file of selectedFiles.value) {
      const formData = new FormData()
      formData.append('file', file)

      try {
        const uploadData = await apiClient('/api/files/upload', {
          method: 'POST',
          body: formData
        })
        fileIds.push(uploadData.data.id)
      } catch (err) {
        if (err.code === 'DUPLICATE_FILE') {
          fileIds.push(err.details.existing_file_id)
        } else {
          throw err
        }
      }
    }

    const apiConfig = showConfig.value ? {
      types: {
        single_choice: { count: config.types.single_choice.count, score: config.types.single_choice.score },
        multi_choice: { count: config.types.multi_choice.count, score: config.types.multi_choice.score },
        fill_blank: { count: config.types.fill_blank.count, score: config.types.fill_blank.score },
        true_false: { count: config.types.true_false.count, score: config.types.true_false.score },
        calculation: { count: config.types.calculation.count, score: config.types.calculation.score },
        short_answer: { count: config.types.short_answer.count, score: config.types.short_answer.score }
      },
      difficulty: { easy: config.difficulty.easy, medium: config.difficulty.medium, hard: config.difficulty.hard }
    } : undefined

    const generateData = await apiClient('/api/papers/generate', {
      method: 'POST',
      body: JSON.stringify({
        documentIds: fileIds,
        courseName: courseName.value.trim(),
        config: apiConfig
      })
    })

    await refreshUser()
    router.push(`/papers/${generateData.data.id}`)
  } catch (err) {
    if (err.code === 'QUOTA_EXCEEDED') {
      error.value = '生成次数已用完。未来支持购买额度。'
    } else {
      error.value = err.message || '生成失败'
    }
  } finally {
    loading.value = false
  }
}
</script>
