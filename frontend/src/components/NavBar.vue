<template>
  <nav class="navbar">
    <div class="navbar-inner">
      <router-link to="/" class="navbar-brand">Easy Test</router-link>
      <div class="navbar-links">
        <template v-if="isLoggedIn">
          <span class="navbar-user">{{ userDisplayName }}</span>
          <span v-if="quotaRemaining !== null" class="navbar-quota">
            剩余 {{ quotaRemaining }} 次
          </span>
          <button class="btn-link" @click="handleLogout">退出</button>
        </template>
        <template v-else>
          <router-link to="/login" class="btn-link">登录</router-link>
          <router-link to="/register" class="btn-link">注册</router-link>
        </template>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { isLoggedIn, userDisplayName, quotaRemaining, logout } from '../stores/authStore'

const router = useRouter()

function handleLogout() {
  logout()
  router.push('/login')
}
</script>
