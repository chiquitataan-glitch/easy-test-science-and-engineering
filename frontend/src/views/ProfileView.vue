<template>
  <div class="app">
    <h1>个人中心</h1>

    <div v-if="loading" class="loading-state">
      <span class="spinner"></span> 加载中...
    </div>

    <div v-else-if="error" class="error-box">
      <div class="error-icon">⚠️</div>
      <div class="error-msg">{{ error }}</div>
    </div>

    <template v-else>
      <div class="profile-card">
        <div class="profile-avatar">👤</div>
        <div class="profile-info">
          <div class="profile-name">{{ displayName }}</div>
          <div class="profile-email">{{ email }}</div>
        </div>
      </div>

      <div class="quota-card">
        <h3>生成额度</h3>
        <div class="quota-bar">
          <div class="quota-fill" :class="quotaLevel" :style="{ width: quotaPercent + '%' }"></div>
        </div>
        <div class="quota-numbers">
          <span>已用 <strong>{{ quotaUsed }}</strong> 次</span>
          <span>共 <strong>{{ quotaTotal }}</strong> 次</span>
          <span>剩余 <strong :class="quotaLevel">{{ quotaRemaining }}</strong> 次</span>
        </div>
        <div v-if="quotaRemaining === 0" class="quota-warn">
          ⚠️ 额度已用完，未来支持购买额度。
        </div>
      </div>

      <div class="identity-card" v-if="identities.length">
        <h3>登录方式</h3>
        <div v-for="idn in identities" :key="idn.id" class="identity-row">
          <span class="identity-provider">{{ providerLabel(idn.provider) }}</span>
          <span class="identity-identifier">{{ idn.identifier }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiClient } from '../api/client'

const user = ref({})
const quotaTotal = ref(0)
const quotaUsed = ref(0)
const quotaRemaining = ref(0)
const loading = ref(true)
const error = ref('')

const displayName = computed(() => user.value.displayName || '-')
const email = computed(() => {
  const pw = (user.value.identities || []).find(i => i.provider === 'password')
  return pw?.identifier || '-'
})
const identities = computed(() => user.value.identities || [])

const quotaPercent = computed(() => {
  if (quotaTotal.value === 0) return 0
  return Math.round((quotaUsed.value / quotaTotal.value) * 100)
})

const quotaLevel = computed(() => {
  if (quotaRemaining.value === 0) return 'quota-low'
  const pct = quotaPercent.value
  if (pct >= 80) return 'quota-warn'
  return 'quota-good'
})

function providerLabel(p) {
  const map = { password: '邮箱密码', wechat_mini_program: '微信小程序', phone: '手机号' }
  return map[p] || p
}

onMounted(async () => {
  try {
    const [userData, quotaData] = await Promise.all([
      apiClient('/api/auth/me'),
      apiClient('/api/quota/me')
    ])
    user.value = userData.data
    quotaTotal.value = quotaData.data.quotaTotal
    quotaUsed.value = quotaData.data.quotaUsed
    quotaRemaining.value = quotaData.data.quotaRemaining
  } catch (err) {
    error.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>
