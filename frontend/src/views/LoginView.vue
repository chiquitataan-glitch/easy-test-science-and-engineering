<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>登录</h2>
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="email">邮箱</label>
          <input id="email" v-model="email" type="email" placeholder="请输入邮箱" :disabled="loading" />
        </div>
        <div class="form-group">
          <label for="password">密码</label>
          <input id="password" v-model="password" type="password" placeholder="请输入密码" :disabled="loading" />
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <button class="btn-primary" type="submit" :disabled="!canSubmit">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? ' 登录中...' : '登录' }}
        </button>
      </form>
      <p class="auth-link">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../stores/authStore'

const router = useRouter()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const canSubmit = computed(() => email.value.trim() && password.value && !loading.value)

async function handleSubmit() {
  if (!canSubmit.value) return

  loading.value = true
  error.value = ''

  try {
    await login(email.value.trim(), password.value)
    router.push('/')
  } catch (err) {
    error.value = err.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>
