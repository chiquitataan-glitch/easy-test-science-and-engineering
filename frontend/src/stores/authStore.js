import { reactive, computed } from 'vue'

const state = reactive({
  user: null,
  token: null,
  initialized: false
})

async function initAuth() {
  const savedToken = localStorage.getItem('access_token')
  if (!savedToken) {
    state.initialized = true
    return
  }

  state.token = savedToken

  try {
    const res = await fetch('/api/auth/me', {
      headers: { 'Authorization': `Bearer ${savedToken}` }
    })
    const data = await res.json()

    if (data.success) {
      state.user = data.data
    } else {
      clearAuth()
    }
  } catch (e) {
    clearAuth()
  }

  state.initialized = true
}

async function login(email, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, clientType: 'web' })
  })
  const data = await res.json()

  if (!data.success) {
    throw new Error(data.message || '登录失败')
  }

  state.token = data.data.token
  state.user = data.data.user
  localStorage.setItem('access_token', data.data.token)

  return data.data
}

async function register(email, password, displayName) {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, displayName, clientType: 'web' })
  })
  const data = await res.json()

  if (!data.success) {
    throw new Error(data.message || '注册失败')
  }

  state.token = data.data.token
  state.user = data.data.user
  localStorage.setItem('access_token', data.data.token)

  return data.data
}

function clearAuth() {
  state.user = null
  state.token = null
  localStorage.removeItem('access_token')
}

function logout() {
  fetch('/api/auth/logout', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${state.token}` }
  }).catch(() => {})
  clearAuth()
}

const isLoggedIn = computed(() => !!state.token && !!state.user)
const userDisplayName = computed(() => state.user?.displayName || state.user?.email || '')
const quotaRemaining = computed(() => state.user?.quota?.remaining ?? null)

export { state, initAuth, login, register, logout, clearAuth, isLoggedIn, userDisplayName, quotaRemaining }
