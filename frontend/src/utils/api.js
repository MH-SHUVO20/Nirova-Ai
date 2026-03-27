import axios from 'axios'
import toast from 'react-hot-toast'

// Use relative API path /api by default, which maps to Vite proxy in dev
const BASE_URL = import.meta.env.VITE_API_URL || '/api'
const isAuthEndpoint = (url = '') => {
  return typeof url === 'string' && url.startsWith('/auth/')
}

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.config?.silent) {
      return Promise.reject(error)
    }

    const status = error.response?.status
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
    } else if (error.response?.data?.detail) {
      toast.error(error.response.data.detail)
    } else {
      toast.error('An unexpected error occurred.')
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
  getMe:    ()     => api.get('/auth/me'),
  health:   ()     => api.get('/auth/health'),
  logout:   ()     => api.post('/auth/logout'),
  forgotPassword: (data) => api.post('/auth/forgot-password', data),
  resetPassword: (data) => api.post('/auth/reset-password', data),
}

export const symptomsAPI = {
  log:     (data) => api.post('/symptoms/log', data),
  predict: (data) => api.post('/symptoms/predict', data),
  predictDengue: (data) => api.post('/symptoms/predict-dengue', data),
  history: (limit = 30) => api.get(`/symptoms/history?limit=${limit}`),
  latest:  () => api.get('/symptoms/latest'),
}

export const chatAPI = {
  ask: (data) => api.post('/chat/ask', data),
  history: (limit = 10) => api.get(`/chat/history?limit=${limit}`),
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
    return api.post('/vision/analyze-skin', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000
    })
  },
  analyzeLab: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/vision/analyze-lab', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000
    })
  },
  analyzePrescription: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/vision/analyze-prescription', form, {
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
