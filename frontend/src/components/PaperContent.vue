<template>
  <div class="result-section">
    <div class="result-header">
      <div>
        <h2>{{ paperData.paper_title || paperTitle || '试卷' }}</h2>
        <p class="result-meta">
          共 {{ safeQuestions.length }} 题 · {{ countByType }} · 满分 {{ totalScore }} 分
          <span v-if="promptVersion" class="prompt-ver"> | Prompt: {{ promptVersion }}</span>
        </p>
      </div>
      <div class="result-tags">
        <span class="course-tag">{{ paperData.course_name || courseName || '' }}</span>
      </div>
    </div>

    <div v-if="qualityScore !== null" class="quality-score-bar">
      <div class="score-label">质量评分</div>
      <div class="score-track">
        <div class="score-fill" :class="scoreLevel" :style="{ width: qualityScore + '%' }"></div>
      </div>
      <div class="score-num" :class="scoreLevel">{{ qualityScore }} 分</div>
    </div>

    <div v-if="paperData.quality_report?.summary" class="quality-summary" :class="summaryLevel">
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

    <div v-if="paperData.quality_report?.warnings?.length" class="validator-warnings">
      <div class="vw-title">⚠️ 校验警告</div>
      <div v-for="(w, i) in paperData.quality_report.warnings" :key="'vw'+i" class="vw-item">{{ w }}</div>
    </div>

    <div v-if="paperData.quality_report?.suggestions?.length" class="suggestions-box">
      <div class="sug-title">💡 建议</div>
      <div v-for="(s, i) in paperData.quality_report.suggestions" :key="'sg'+i" class="sug-item">{{ s }}</div>
    </div>

    <div v-if="knowledgeCoverage" class="knowledge-coverage-box">
      <div class="kc-title">📚 知识点覆盖</div>
      <div class="kc-summary">{{ knowledgeCoverage.description }}</div>
      <div class="kc-stats">
        <span>{{ knowledgeCoverage.total_points }} 个知识点</span>
        <span>·</span>
        <span>{{ knowledgeCoverage.questions_with_knowledge }}/{{ safeQuestions.length }} 题已标注</span>
      </div>
      <div v-if="knowledgeCoverage.top_points?.length" class="kc-top-list">
        <span v-for="kp in knowledgeCoverage.top_points" :key="kp.name" class="kc-top-tag">
          {{ kp.name }}（{{ kp.count }}题）
        </span>
      </div>
      <div v-if="knowledgeCoverage.gaps?.length" class="kc-gaps">
        <div v-for="(g, i) in knowledgeCoverage.gaps" :key="'kg'+i" class="kc-gap-item">⚠ {{ g }}</div>
      </div>
    </div>

    <div v-if="paperData.knowledge_summary" class="ks-box">
      <div class="ks-title">📖 AI 知识点汇总</div>
      <div class="ks-desc">{{ paperData.knowledge_summary.description }}</div>
      <div class="ks-stats">共 {{ paperData.knowledge_summary.total }} 个知识点</div>
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
          <div v-for="opt in q.options" :key="opt.key" class="option" :class="{ 'is-answer': isCorrectOption(q, opt.key) }">
            <span class="option-key">{{ opt.key }}.</span>
            <span class="option-value">{{ opt.value }}</span>
            <span v-if="isCorrectOption(q, opt.key)" class="answer-tag">✓</span>
          </div>
        </div>

        <div v-if="q.answer && !q.options?.length" class="answer-line">
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
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  paperData: { type: Object, required: true },
  paperTitle: { type: String, default: null },
  courseName: { type: String, default: null }
})

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

const promptVersion = computed(() => {
  return props.paperData?.quality_report?.prompt_version || null
})

const qualityScore = computed(() => {
  const s = props.paperData?.quality_report?.score
  return (s !== undefined && s !== null) ? s : null
})

const scoreLevel = computed(() => {
  if (qualityScore.value === null) return ''
  if (qualityScore.value >= 90) return 'score-high'
  if (qualityScore.value >= 70) return 'score-mid'
  return 'score-low'
})

const summaryLevel = computed(() => {
  if (qualityScore.value === null) return ''
  if (qualityScore.value >= 90) return 'quality-good'
  if (qualityScore.value >= 70) return 'quality-warn'
  return 'quality-bad'
})

const selfCheck = computed(() => {
  return props.paperData?.quality_report?.self_check || null
})

const knowledgeCoverage = computed(() => {
  return props.paperData?.quality_report?.knowledge_coverage || null
})

const safeQuestions = computed(() => {
  const qs = props.paperData?.questions
  return Array.isArray(qs) ? qs : []
})

const questionGroups = computed(() => {
  if (!safeQuestions.value.length) return []
  const groups = {}
  safeQuestions.value.forEach(q => {
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
  return safeQuestions.value.reduce((s, q) => s + (q.score || 0), 0)
})

const countByType = computed(() => {
  if (!safeQuestions.value.length) return ''
  return TYPE_ORDER
    .filter(type => safeQuestions.value.some(q => q.question_type === type))
    .map(type => {
      const count = safeQuestions.value.filter(q => q.question_type === type).length
      return `${TYPE_LABELS[type].replace(/^[一二三四五六]、/, '')}${count}道`
    })
    .join(' · ')
})

const difficultyLabel = (d) => DIFFICULTY_LABELS[d] || d

const isCorrectOption = (q, key) => {
  if (!q.answer) return false
  if (q.question_type === 'multi_choice') {
    return q.answer.split(',').map(s => s.trim()).includes(key)
  }
  return q.answer === key
}
</script>
