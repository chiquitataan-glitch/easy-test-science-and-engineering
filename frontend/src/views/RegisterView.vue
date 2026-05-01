<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>注册</h2>
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="displayName">昵称</label>
          <input id="displayName" v-model="displayName" type="text" placeholder="输入昵称（可选）" :disabled="loading" />
        </div>
        <div class="form-group">
          <label for="email">邮箱</label>
          <input id="email" v-model="email" type="email" placeholder="请输入邮箱" :disabled="loading" />
        </div>
        <div class="form-group">
          <label for="password">密码</label>
          <input id="password" v-model="password" type="password" placeholder="至少8位密码" :disabled="loading" />
        </div>
        <div class="form-group">
          <label for="confirmPassword">确认密码</label>
          <input id="confirmPassword" v-model="confirmPassword" type="password" placeholder="再次输入密码" :disabled="loading" />
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <button class="btn-primary" type="submit" :disabled="!canSubmit">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? ' 注册中...' : '注册' }}
        </button>
      </form>
      <p class="auth-link">
        已有账号？<router-link to="/login">立即登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '../stores/authStore'

const router = useRouter()

const displayName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')

const canSubmit = computed(() =>
  email.value.trim() && password.value.length >= 8 && confirmPassword.value && !loading.value
)

async function handleSubmit() {
  if (!canSubmit.value) return

  if (password.value !== confirmPassword.value) {
    error.value = '两次密码不一致'
    return
  }

  if (password.value.length < 8) {
    error.value = '密码长度不能少于8位'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await register(email.value.trim(), password.value, displayName.value.trim() || null)
    router.push('/')
  } catch (err) {
    error.value = err.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>
