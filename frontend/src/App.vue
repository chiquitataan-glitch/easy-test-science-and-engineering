<template>
  <div class="app">
    <h1>Easy Test - AI试卷生成</h1>

    <div class="form-section">
      <div class="form-group">
        <label for="courseName">课程名称</label>
        <input
          id="courseName"
          v-model="courseName"
          type="text"
          placeholder="例如：化工原理"
          :disabled="loading"
        />
      </div>

      <div class="form-group">
        <label for="fileInput">上传资料（PDF / DOCX / PPT / PPTX）</label>
        <input
          id="fileInput"
          type="file"
          accept=".pdf,.docx,.ppt,.pptx"
          @change="handleFileChange"
          :disabled="loading"
        />
        <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
      </div>

      <div class="config-toggle" @click="showConfig = !showConfig">
        <span class="config-arrow">{{ showConfig ? '▼' : '▶' }}</span>
        出题配置（可选）
      </div>

      <div v-if="showConfig" class="config-panel">
        <div class="config-row config-row-header">
          <span>题型</span>
          <span>数量</span>
          <span>分值</span>
        </div>
        <div v-for="t in configTypes" :key="t.key" class="config-row">
          <span class="config-type-label">{{ t.label }}</span>
          <input
            type="number"
            min="0"
            max="50"
            :value="config.types[t.key].count"
            @input="e => updateTypeCount(t.key, parseInt(e.target.value) || 0)"
            :disabled="loading"
          />
          <input
            type="number"
            min="0.5"
            max="100"
            step="0.5"
            :value="config.types[t.key].score"
            @input="e => updateTypeScore(t.key, parseFloat(e.target.value) || 0)"
            :disabled="loading"
          />
        </div>

        <div class="config-divider"></div>
        <div class="config-row config-row-header">
          <span>难度</span>
          <span>比例</span>
          <span></span>
        </div>
        <div v-for="d in configDifficulties" :key="d.key" class="config-row">
          <span class="config-type-label">{{ d.label }}</span>
          <input
            type="number"
            min="0"
            max="100"
            step="5"
            :value="Math.round(config.difficulty[d.key] * 100)"
            @input="e => updateDifficulty(d.key, (parseInt(e.target.value) || 0) / 100)"
            :disabled="loading"
          />
          <span>%</span>
        </div>
      </div>

      <button
        class="btn-generate"
        @click="handleGenerate"
        :disabled="!canGenerate"
      >
        {{ loading ? '生成中...' : '生成试卷' }}
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="paperData" class="result-section">
      <div class="result-header">
        <div>
          <h2>{{ paperData.paper_title }}</h2>
          <p class="result-meta">共 {{ paperData.questions.length }} 题 · {{ countByType }} · 满分 {{ totalScore }} 分</p>
        </div>
        <span class="course-tag">{{ paperData.course_name }}</span>
      </div>

      <div v-if="paperData.quality_report?.summary" class="quality-summary">
        📊 {{ paperData.quality_report.summary }}
      </div>

      <div v-if="selfCheck" class="self-check-box" :class="selfCheck.passed ? 'check-passed' : 'check-failed'">
        <div class="self-check-header">
          <span class="self-check-icon">{{ selfCheck.passed ? '✅' : '⚠️' }}</span>
          <span class="self-check-title">
            {{ selfCheck.passed ? 'AI 自检通过' : 'AI 自检发现 ' + selfCheck.issues.length + ' 个问题，已自动修复' }}
          </span>
        </div>
        <div v-if="selfCheck.skip_reason" class="self-check-skip">提示：{{ selfCheck.skip_reason }}</div>
        <div v-if="selfCheck.issues && selfCheck.issues.length" class="self-check-issues">
          <div v-for="(issue, i) in selfCheck.issues" :key="i" class="issue-item">
            <span class="issue-no">Q{{ issue.question_no }}</span>
            <span class="issue-field">[{{ issue.field }}]</span>
            <span class="issue-problem">{{ issue.problem }}</span>
            <span class="issue-suggestion">→ {{ issue.suggestion }}</span>
          </div>
        </div>
      </div>

      <div v-for="group in questionGroups" :key="group.type" class="type-section">
        <h3 class="type-title">{{ group.label }}（{{ group.questions.length }}题，共{{ group.totalScore }}分）</h3>

        <div v-for="q in group.questions" :key="q.question_no" class="question-card">
          <div class="question-header">
            <span class="question-no">第{{ q.question_no }}题</span>
            <span class="question-difficulty" :class="q.difficulty">{{ difficultyLabel(q.difficulty) }}</span>
            <span class="question-score">{{ q.score }}分</span>
          </div>

          <div class="question-content">{{ q.content }}</div>

          <div v-if="q.options && q.options.length" class="options">
            <div v-for="opt in q.options" :key="opt.key" class="option" :class="{ 'is-answer': opt.key === q.answer }">
              <span class="option-key">{{ opt.key }}.</span>
              <span class="option-value">{{ opt.value }}</span>
              <span v-if="opt.key === q.answer" class="answer-tag">✓</span>
            </div>
          </div>

          <div v-if="q.answer && !q.options" class="answer-line">
            <strong>答案：</strong>{{ q.answer }}
          </div>

          <div v-if="q.analysis" class="analysis">
            <strong>解析：</strong>{{ q.analysis }}
          </div>

          <div v-if="q.knowledge_points && q.knowledge_points.length" class="knowledge-points">
            <span v-for="kp in q.knowledge_points" :key="kp" class="kp-tag">{{ kp }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'

const TYPE_LABELS = {
  single_choice: '一、单选题',
  multi_choice: '二、多选题',
  fill_blank: '三、填空题',
  true_false: '四、判断题',
  calculation: '五、计算题',
  short_answer: '六、简答题'
}

const TYPE_ORDER = ['single_choice', 'multi_choice', 'fill_blank', 'true_false', 'calculation', 'short_answer']

const DIFFICULTY_LABELS = {
  easy: '简单',
  medium: '中等',
  hard: '困难'
}

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
const selectedFile = ref(null)
const loading = ref(false)
const error = ref('')
const paperData = ref(null)
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
  difficulty: {
    easy: 0.3,
    medium: 0.5,
    hard: 0.2
  }
})

const updateTypeCount = (key, val) => { config.types[key].count = val }
const updateTypeScore = (key, val) => { config.types[key].score = val }
const updateDifficulty = (key, val) => { config.difficulty[key] = val }

const canGenerate = computed(() => {
  return courseName.value.trim() && selectedFile.value && !loading.value
})

const selfCheck = computed(() => {
  return paperData.value?.quality_report?.self_check || null
})

const questionGroups = computed(() => {
  if (!paperData.value) return []
  const groups = {}
  paperData.value.questions.forEach(q => {
    if (!groups[q.question_type]) groups[q.question_type] = []
    groups[q.question_type].push(q)
  })
  return TYPE_ORDER
    .filter(type => groups[type])
    .map(type => ({
      type,
      label: TYPE_LABELS[type],
      questions: groups[type],
      totalScore: groups[type].reduce((s, q) => s + (q.score || 0), 0)
    }))
})

const totalScore = computed(() => {
  if (!paperData.value) return 0
  return paperData.value.questions.reduce((s, q) => s + (q.score || 0), 0)
})

const countByType = computed(() => {
  if (!paperData.value) return ''
  return TYPE_ORDER
    .filter(type => paperData.value.questions.some(q => q.question_type === type))
    .map(type => {
      const count = paperData.value.questions.filter(q => q.question_type === type).length
      return `${TYPE_LABELS[type].replace(/^[一二三四五六]、/, '')}${count}道`
    })
    .join(' · ')
})

const difficultyLabel = (d) => DIFFICULTY_LABELS[d] || d

const handleFileChange = (e) => {
  selectedFile.value = e.target.files[0]
  error.value = ''
}

const configToApi = () => {
  return {
    types: {
      single_choice: { count: config.types.single_choice.count, score: config.types.single_choice.score },
      multi_choice: { count: config.types.multi_choice.count, score: config.types.multi_choice.score },
      fill_blank: { count: config.types.fill_blank.count, score: config.types.fill_blank.score },
      true_false: { count: config.types.true_false.count, score: config.types.true_false.score },
      calculation: { count: config.types.calculation.count, score: config.types.calculation.score },
      short_answer: { count: config.types.short_answer.count, score: config.types.short_answer.score }
    },
    difficulty: {
      easy: config.difficulty.easy,
      medium: config.difficulty.medium,
      hard: config.difficulty.hard
    }
  }
}

const handleGenerate = async () => {
  if (!canGenerate.value) return

  loading.value = true
  error.value = ''
  paperData.value = null

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const uploadRes = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    })
    const uploadData = await uploadRes.json()

    if (!uploadData.success) {
      error.value = uploadData.message || '上传失败'
      loading.value = false
      return
    }

    const generateReq = {
      filePath: uploadData.data.path,
      courseName: courseName.value.trim()
    }

    if (showConfig.value) {
      generateReq.config = configToApi()
    }

    const generateRes = await fetch('/api/generate-paper', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(generateReq)
    })
    const generateData = await generateRes.json()

    if (!generateData.success) {
      error.value = generateData.message || '试卷生成失败'
      loading.value = false
      return
    }

    paperData.value = generateData.data.paper
  } catch (err) {
    error.value = '请求失败：' + err.message
  } finally {
    loading.value = false
  }
}
</script>
