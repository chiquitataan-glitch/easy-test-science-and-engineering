import { state, clearAuth } from '../stores/authStore'

const BASE_URL = ''

async function apiClient(path, options = {}) {
  const headers = { ...options.headers }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const token = state.token
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers
  })

  const data = await res.json()

  if (!data.success) {
    const code = data.error?.code

    if (code === 'AUTH_REQUIRED' || code === 'TOKEN_EXPIRED') {
      clearAuth()
    }

    const err = new Error(data.message || '请求失败')
    err.code = code
    err.status = res.status
    err.details = data.error?.details
    throw err
  }

  return data
}

export { apiClient }
