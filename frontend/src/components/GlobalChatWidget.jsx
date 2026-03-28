import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { FiLoader, FiMessageCircle, FiSend, FiUser, FiX } from 'react-icons/fi'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { chatAPI } from '../utils/api'

const SESSION_KEY = 'nirovaai_widget_sessions'
const LATEST_CONTEXT_KEY = 'nirovaai_latest_context'
const MESSAGES_CACHE_KEY = 'nirovaai_widget_messages'
const CONTEXT_PREVIEW_CACHE_KEY = 'nirovaai_context_preview'
const CACHE_SCHEMA_VERSION_KEY = 'nirovaai_widget_cache_schema_version'
const CACHE_SCHEMA_VERSION = 'v2-isolated-mode-cache'

// Auto-cleanup: Remove old global cache key that was causing cross-page sharing
function cleanupOldCache() {
  try {
    const oldKey = MESSAGES_CACHE_KEY
    const raw = localStorage.getItem(oldKey)
    if (raw) {
      localStorage.removeItem(oldKey)
    }
  } catch {
    // Ignore cleanup failures.
  }
}

function migrateCacheIfNeeded() {
  try {
    const existing = localStorage.getItem(CACHE_SCHEMA_VERSION_KEY)
    if (existing === CACHE_SCHEMA_VERSION) return

    const modes = ['dashboard', 'symptoms', 'skin', 'lab', 'dengue', 'prescription', 'timeline', 'chat', 'general']
    modes.forEach((mode) => {
      localStorage.removeItem(`${MESSAGES_CACHE_KEY}_${mode}`)
      localStorage.removeItem(`${CONTEXT_PREVIEW_CACHE_KEY}_${mode}`)
    })
    localStorage.removeItem(SESSION_KEY)
    sessionStorage.removeItem(LATEST_CONTEXT_KEY)
    localStorage.setItem(CACHE_SCHEMA_VERSION_KEY, CACHE_SCHEMA_VERSION)
  } catch {
    // Ignore migration failures.
  }
}

function readMessageCache(mode) {
  try {
    const key = `${MESSAGES_CACHE_KEY}_${mode}`
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : null
  } catch {
    return null
  }
}

function writeMessageCache(mode, messages) {
  try {
    const key = `${MESSAGES_CACHE_KEY}_${mode}`
    localStorage.setItem(key, JSON.stringify(messages))
  } catch {
    // Ignore cache write failures.
  }
}

function clearMessageCache(mode) {
  try {
    localStorage.removeItem(`${MESSAGES_CACHE_KEY}_${mode}`)
  } catch {
    // Silently fail
  }
}

// Context preview caching per mode
function readContextPreviewCache(mode) {
  try {
    const key = `${CONTEXT_PREVIEW_CACHE_KEY}_${mode}`
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

function writeContextPreviewCache(mode, contextData) {
  try {
    const key = `${CONTEXT_PREVIEW_CACHE_KEY}_${mode}`
    localStorage.setItem(key, JSON.stringify(contextData))
  } catch {
    // Ignore cache write failures.
  }
}

function clearContextPreviewCache(mode) {
  try {
    const key = `${CONTEXT_PREVIEW_CACHE_KEY}_${mode}`
    localStorage.removeItem(key)
  } catch {
    // Silently fail
  }
}

const AGENT_CONFIGS = [
  {
    match: (path) => path === '/app',
    mode: 'dashboard',
    title: 'Dashboard Agent',
    welcome: 'I can explain your latest risk trends and suggest what to do next based on your dashboard data.',
    placeholder: 'Ask about your latest health summary...',
  },
  {
    match: (path) => path.startsWith('/app/symptoms'),
    mode: 'symptoms',
    title: 'Symptoms Agent',
    welcome: 'I can help triage your symptoms, suggest what to monitor, and tell you when to seek care.',
    placeholder: 'Ask about your symptoms...',
  },
  {
    match: (path) => path.startsWith('/app/skin'),
    mode: 'skin',
    title: 'Skin Agent',
    welcome: 'I can help interpret your skin analysis and suggest practical next steps and warning signs.',
    placeholder: 'Ask about skin findings...',
  },
  {
    match: (path) => path.startsWith('/app/lab-report'),
    mode: 'lab',
    title: 'Lab Agent',
    welcome: 'I can explain lab report findings in simple terms and suggest follow-up priorities.',
    placeholder: 'Ask about your lab report...',
  },
  {
    match: (path) => path.startsWith('/app/dengue'),
    mode: 'dengue',
    title: 'Dengue Agent',
    welcome: 'I focus on dengue screening guidance based on NS1/IgG/IgM and your symptoms.',
    placeholder: 'Ask about dengue risk and next steps...',
  },
  {
    match: (path) => path.startsWith('/app/prescription'),
    mode: 'prescription',
    title: 'Prescription Agent',
    welcome: 'I can help with medicine schedule clarity and common safety checks.',
    placeholder: 'Ask about medicines and schedule...',
  },
  {
    match: (path) => path.startsWith('/app/timeline'),
    mode: 'timeline',
    title: 'Timeline Agent',
    welcome: 'I can review your trend timeline and help you understand if things are improving or worsening.',
    placeholder: 'Ask about your trends...',
  },
  {
    match: (path) => path.startsWith('/app/chat'),
    mode: 'chat',
    title: 'AI Chat Agent',
    welcome: 'I am your general health assistant. Ask anything and I will guide you clearly.',
    placeholder: 'Ask your health question...',
  },
  {
    match: () => true,
    mode: 'general',
    title: 'AI Assistant',
    welcome: 'Hi, I am your NirovaAI helper. Ask any health question and I will guide you with practical next steps.',
    placeholder: 'Ask your health question...',
  },
]

function getAgentConfig(pathname) {
  return AGENT_CONFIGS.find((cfg) => cfg.match(pathname)) || AGENT_CONFIGS[AGENT_CONFIGS.length - 1]
}

function readSessionMap() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

function writeSessionMap(map) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(map))
}

function readLatestContextMap() {
  try {
    const raw = sessionStorage.getItem(LATEST_CONTEXT_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

function writeLatestContextMap(map) {
  sessionStorage.setItem(LATEST_CONTEXT_KEY, JSON.stringify(map))
}

function getClientContextForMode(mode, map, fallbackPreview) {
  // Strictly isolate context per agent mode - NEVER pool context from other pages
  const scoped = map?.[mode]
  if (scoped) return scoped
  
  // Only the special overview modes can use context from ALL analyses
  // Regular analysis pages (lab, skin, dengue, symptoms) should ONLY show their own context
  if (mode === 'chat' || mode === 'general' || mode === 'dashboard' || mode === 'timeline') {
    const all = Object.values(map || {}).filter(Boolean)
    if (all.length) return all.join(' | ')
  }
  
  // For specialized pages (lab, skin, dengue, symptoms, prescription):
  // Only return fallbackPreview (latest from API), never use other modes' context
  return fallbackPreview || ''
}

function normalizeAssistantText(text) {
  let out = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  out = out.replace(/\*\*/g, '').replace(/__/g, '')
  out = out.replace(/\s+([1-4]\)\s*(Summary|What To Do Now|Red Flags|Follow-?Up))/gi, '\n$1')
  out = out.replace(/([1-4]\)\s*(Summary|What To Do Now|Red Flags|Follow-?Up))\s*\*\s*/gi, '$1\n- ')
  out = out.replace(/\s+\*\s+/g, '\n- ')
  out = out.replace(/\n{3,}/g, '\n\n').trim()
  return out
}

export default function GlobalChatWidget() {
  const { user } = useAuth()
  const { language } = useLanguage()
  const navigate = useNavigate()
  const location = useLocation()
  const messagesEndRef = useRef(null)
  const messageOwnerModeRef = useRef(null)

  // Run one-time cache cleanup/migration to avoid old mixed cache keys.
  useEffect(() => {
    cleanupOldCache()
    migrateCacheIfNeeded()
  }, [])

  const [isOpen, setIsOpen] = useState(false)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [contextPreview, setContextPreview] = useState(null)
  const [transientContext, setTransientContext] = useState('')

  const agent = useMemo(() => getAgentConfig(location.pathname), [location.pathname])
  const hideOnFullChatPage = location.pathname === '/app/chat'

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isOpen])

  useEffect(() => {
    if (messageOwnerModeRef.current !== agent.mode) {
      return
    }
    // Only cache if:
    // 1. More than just the welcome message
    // 2. Contains at least one user message (real conversation)
    // 3. First message is assistant welcome, not a user message
    if (messages.length > 1 && messages.some(m => m.role === 'user') && messages[0].role === 'assistant') {
      writeMessageCache(agent.mode, messages)
    }
  }, [messages, agent.mode])

  useEffect(() => {
    setInput('')
    
    // IMPORTANT: Clear old context when switching modes
    // This prevents context from previous page bleeding into current page
    setContextPreview(null)
    setTransientContext('')
    
    // Try to load cached messages for this agent mode
    const cachedMessages = readMessageCache(agent.mode)
    
    // Only use cache if:
    // 1. Messages exist
    // 2. More than just a welcome message
    // 3. Contains actual user interaction
    if (cachedMessages && cachedMessages.length > 1 && cachedMessages.some(m => m.role === 'user')) {
      setMessages(cachedMessages)
      messageOwnerModeRef.current = agent.mode
    } else {
      // Always start with fresh welcome message for this mode
      setMessages([{ role: 'assistant', content: agent.welcome }])
      messageOwnerModeRef.current = agent.mode
    }
    
    // Load mode-specific context from storage
    const map = readLatestContextMap()
    const contextForMode = map?.[agent.mode] || ''
    setTransientContext(contextForMode)

    // Load mode-specific session
    const sessionMap = readSessionMap()
    const modeSession = sessionMap?.[agent.mode] || null
    setSessionId(modeSession)
  }, [agent.mode, agent.welcome])

  useEffect(() => {
    if (!isOpen || !user) return
    
    // Load cached context immediately for instant display
    const cachedContext = readContextPreviewCache(agent.mode)
    if (cachedContext) {
      setContextPreview(cachedContext)
    }
    
    // Fetch fresh context from API to ensure latest data
    chatAPI.contextPreview(agent.mode)
      .then((res) => {
        const freshContext = res.data || null
        if (freshContext) {
          setContextPreview(freshContext)
          // Save fresh context to cache for next visit
          writeContextPreviewCache(agent.mode, freshContext)
        } else if (!cachedContext) {
          // Only clear if no cache and API returned nothing
          setContextPreview(null)
        }
      })
      .catch(() => {
        // Don't clear cached context on error - keep the last known good data
        if (!cachedContext) {
          setContextPreview(null)
        }
      })
  }, [isOpen, user, agent.mode])

  useEffect(() => {
    if (!user) return
    const refreshContext = (evt) => {
      const detailSummary = evt?.detail?.summary
      const detailType = evt?.detail?.type
      if (typeof detailSummary === 'string' && detailSummary.trim()) {
        const map = readLatestContextMap()
        const key = detailType || agent.mode
        map[key] = detailSummary.trim()
        writeLatestContextMap(map)
        setTransientContext(getClientContextForMode(agent.mode, map, contextPreview?.summary || ''))
      }
      if (!isOpen) return
      chatAPI.contextPreview(agent.mode)
        .then((res) => {
          const freshContext = res.data || null
          setContextPreview(freshContext)
          // Cache the new context for persistence
          if (freshContext) {
            writeContextPreviewCache(agent.mode, freshContext)
          }
        })
        .catch(() => setContextPreview(null))
    }
    window.addEventListener('nirovaai:analysis-updated', refreshContext)
    return () => window.removeEventListener('nirovaai:analysis-updated', refreshContext)
  }, [isOpen, user, agent.mode])

  const toggleWidget = () => {
    setIsOpen((prev) => !prev)
  }

  const sendMessage = async () => {
    const message = input.trim()
    if (!message || sending) return

    if (!user) {
      toast.error('Please sign in to chat with AI assistant.')
      navigate('/login')
      return
    }

    setInput('')
    setSending(true)
    messageOwnerModeRef.current = agent.mode
    setMessages((prev) => [...prev, { role: 'user', content: message }])

    try {
      const res = await chatAPI.ask({
        message,
        session_id: sessionId,
        agent_mode: agent.mode,
        language: language === 'bn' ? 'bn' : 'en',
        client_context: getClientContextForMode(agent.mode, readLatestContextMap(), transientContext || contextPreview?.summary || ''),
      })

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.data?.response || 'I could not generate a response.' },
      ])

      if (res.data?.session_id) {
        setSessionId(res.data.session_id)
        const sessionMap = readSessionMap()
        sessionMap[agent.mode] = res.data.session_id
        writeSessionMap(sessionMap)
      }
    } catch (err) {
      // Generate helpful error message based on status code
      let errorMsg = err.response?.data?.detail || 'I could not process that request. Please try again.'
      
      if (err.response?.status === 401 || err.response?.status === 403) {
        errorMsg = 'Your session has expired. Please log in again and try again.'
      } else if (err.response?.status === 422) {
        errorMsg = 'Invalid request format. Please refresh and try again.'
      } else if (err.response?.status === 500 || err.response?.status === 503) {
        errorMsg = 'Server is temporarily unavailable. Please check if the backend is running and try again.'
      } else if (!err.response) {
        errorMsg = 'Cannot reach the server. Make sure the backend is running on port 8000.'
      }
      
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: errorMsg,
          isError: true,
        },
      ])
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      {!hideOnFullChatPage && (
        <>
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 w-[360px] max-w-[calc(100vw-2rem)] rounded-2xl border shadow-2xl overflow-hidden" style={{
          backgroundColor: 'var(--surface)',
          borderColor: 'var(--border-color)',
        }}>
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{
            borderColor: 'var(--border-color)',
            backgroundColor: 'var(--header-surface)',
          }}>
            <div className="flex items-center gap-2" style={{ color: 'var(--text-main)' }}>
              <FiMessageCircle className="text-primary-500" />
              <span className="font-semibold text-sm">{agent.title}</span>
            </div>
            <button onClick={toggleWidget} className="transition-colors hover:opacity-70" style={{ color: 'var(--text-muted)' }}>
              <FiX size={18} />
            </button>
          </div>

          {!user ? (
            <div className="p-4 space-y-3" style={{ backgroundColor: 'var(--surface)' }}>
              <p className="text-sm" style={{ color: 'var(--text-main)' }}>
                Sign in to use AI chat from anywhere in the app.
              </p>
              <button
                onClick={() => navigate('/login')}
                className="btn-primary w-full text-sm py-2.5"
              >
                Go to Login
              </button>
            </div>
          ) : (
            <>
              {contextPreview?.summary ? (
                <div className="px-3 pt-3">
                  <div className="rounded-lg border p-2" style={{
                    borderColor: 'rgba(59, 130, 246, 0.3)',
                    backgroundColor: 'rgba(59, 130, 246, 0.05)',
                  }}>
                    <p className="text-[11px] font-medium" style={{ color: 'rgb(59, 130, 246)' }}>{contextPreview.label || 'Context'}</p>
                    <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
                      Latest analysis context is loaded for this assistant.
                    </p>
                  </div>
                </div>
              ) : null}
              <div className="h-80 overflow-y-auto p-3 space-y-3" style={{ backgroundColor: 'var(--surface)' }}>
                {messages.map((msg, idx) => (
                  <div key={`${msg.role}-${idx}`} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 border ${
                      msg.role === 'user' ? 'bg-primary-600' : ''
                    }`} style={msg.role === 'user' ? undefined : {
                      backgroundColor: 'var(--surface-soft)',
                      borderColor: 'var(--border-color)',
                    }}>
                      {msg.role === 'user'
                        ? <FiUser size={12} className="text-white" />
                        : <span className="text-[10px] font-bold text-primary-500">N</span>}
                    </div>
                    <div className={`max-w-[78%] rounded-xl px-3 py-2 text-xs leading-relaxed border ${
                      msg.role === 'user'
                        ? 'bg-primary-600 text-white'
                        : msg.isError
                          ? ''
                          : ''
                    }`} style={msg.role === 'user' ? {} : msg.isError ? {
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                      borderColor: 'rgba(239, 68, 68, 0.3)',
                      color: '#dc2626',
                    } : {
                      backgroundColor: 'var(--surface-soft)',
                      borderColor: 'var(--border-color)',
                      color: 'var(--text-main)',
                    }}>
                      <p className="whitespace-pre-wrap">
                        {msg.role === 'assistant' && !msg.isError ? normalizeAssistantText(msg.content) : msg.content}
                      </p>
                    </div>
                  </div>
                ))}
                {sending && (
                  <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                    <FiLoader className="animate-spin" size={14} />
                    AI is thinking...
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="p-3 border-t flex gap-2" style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border-color)' }}>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      sendMessage()
                    }
                  }}
                  placeholder={agent.placeholder}
                  className="flex-1 rounded-lg px-3 py-2 text-sm border focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/50 transition-colors"
                  style={{
                    backgroundColor: 'var(--surface-soft)',
                    color: 'var(--text-main)',
                    borderColor: 'var(--border-color)',
                  }}
                  disabled={sending}
                />
                <button
                  onClick={sendMessage}
                  disabled={sending || !input.trim()}
                  className="btn-primary px-3"
                >
                  {sending ? <FiLoader className="animate-spin" size={16} /> : <FiSend size={16} />}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      <button
        onClick={toggleWidget}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-primary-600 hover:bg-primary-500 text-white shadow-lg shadow-primary-900/40 flex items-center justify-center transition-all"
        aria-label="Open AI chat assistant"
      >
        {isOpen ? <FiX size={22} /> : <FiMessageCircle size={22} />}
      </button>
        </>
      )}
    </>
  )
}
