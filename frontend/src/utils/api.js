import axios from 'axios'
import toast from 'react-hot-toast'

const BASE_URL = '/api'
const isAuthEndpoint = (url = '') => {
  return typeof url === 'string' && url.startsWith('/auth/')
}

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  withCredentials: true,
})

const extractErrorMessage = (error) => {
  const detail = error?.response?.data?.detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    return first?.msg || first?.message || 'Invalid request data.'
  }
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return null
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

api.interceptors.request.use((config) => {
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config || {}
    const status = error.response?.status
    const method = (config.method || '').toLowerCase()

    // Auto-retry idempotent startup requests so pages don't appear empty
    // when backend is warming/reloading.
    const shouldRetry =
      method === 'get' &&
      !isAuthEndpoint(config.url) &&
      (error.code === 'ECONNABORTED' || !error.response || [502, 503, 504].includes(status))

    if (shouldRetry) {
      config.__retryCount = config.__retryCount || 0
      if (config.__retryCount < 2) {
        config.__retryCount += 1
        await wait(500 * config.__retryCount)
        return api(config)
      }
    }

    if (error.config?.silent) {
      return Promise.reject(error)
    }

    const isAuth = isAuthEndpoint(error.config?.url)

    // Auth screens handle their own errors; avoid duplicate global toasts.
    if (isAuth) {
      return Promise.reject(error)
    }

    if (status === 401) {
      localStorage.removeItem('nirovaai_user')
      window.location.href = '/login'
    } else if (status === 500) {
      toast.error('A server error occurred. Please try again later.')
    } else if (error.code === 'ECONNABORTED') {
      toast.error('Request timed out. AI analysis may take longer; please try again.')
    } else {
      const message = extractErrorMessage(error)
      if (message) {
        toast.error(message)
      } else {
        toast.error('An unexpected error occurred.')
      }
    }
    return Promise.reject(error)
  }
)

export { extractErrorMessage }

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
  getMe:    ()     => api.get('/auth/me'),
  health:   ()     => api.get('/auth/health'),
  logout:   ()     => api.post('/auth/logout'),
  logoutCleanup: () => api.post('/chat/logout-cleanup'),
  forgotPassword: (data) => api.post('/auth/forgot-password', data),
  resetPassword: (data) => api.post('/auth/reset-password', data),
}

export const symptomsAPI = {
  log:     (data) => api.post('/symptoms/log', data),
  predict: (data) => api.post('/symptoms/predict', data),
  predictDengue: (data) => api.post('/symptoms/predict-dengue', data),
  history: (limit = 30) => api.get(`/symptoms/history?limit=${limit}`),
  latest:  () => api.get('/symptoms/latest'),
  getExcludedDiseases: () => api.get('/symptoms/excluded-diseases', { silent: true }),
  addExcludedDisease: (disease) => api.post('/symptoms/excluded-diseases', { disease }),
  removeExcludedDisease: (disease) => api.delete(`/symptoms/excluded-diseases/${encodeURIComponent(disease)}`),
}

export const chatAPI = {
  ask: (data) => api.post('/chat/ask', data),
  history: (limit = 10, agent_mode = 'chat') =>
    api.get(`/chat/history?limit=${limit}&agent_mode=${encodeURIComponent(agent_mode)}`),
  contextPreview: (agentMode = 'general') => api.get(
    `/chat/context-preview?agent_mode=${encodeURIComponent(agentMode)}`,
    { silent: true }
  ),
}

export const healthAPI = {
  timeline: (days = 30) => api.get(`/health/timeline?days=${days}`),
  alerts:   () => api.get('/health/alerts'),
  summary:  () => api.get('/health/summary'),
  resolveAlert: (id) => api.patch(`/health/alerts/${id}/resolve`),
}

export const visionAPI = {
  analyzeSkin: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/vision/skin', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000
    })
  },
  analyzeLab: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/vision/lab-report', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000
    })
  },
  analyzePrescription: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/vision/prescription', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000
    })
  },
}

export const createChatSocket = () => {
  let wsUrl = BASE_URL
  if (wsUrl.startsWith('/')) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    wsUrl = `${protocol}//${window.location.host}${wsUrl}`
  } else {
    wsUrl = wsUrl.replace('http', 'ws').replace('https', 'wss')
  }
  return new WebSocket(`${wsUrl}/chat/ws`)
}

export default api
