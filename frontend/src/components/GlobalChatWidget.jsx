import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { FiLoader, FiMessageCircle, FiSend, FiUser, FiX } from 'react-icons/fi'
import { useAuth } from '../context/AuthContext'
import { chatAPI } from '../utils/api'

const SESSION_KEY = 'nirovaai_widget_sessions'

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
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function writeSessionMap(map) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(map))
}

export default function GlobalChatWidget() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const messagesEndRef = useRef(null)

  const [isOpen, setIsOpen] = useState(false)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [contextPreview, setContextPreview] = useState(null)

  const agent = useMemo(() => getAgentConfig(location.pathname), [location.pathname])
  const hideOnFullChatPage = location.pathname === '/app/chat'
  if (hideOnFullChatPage) return null

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isOpen])

  useEffect(() => {
    setInput('')
    setMessages([{ role: 'assistant', content: agent.welcome }])
    setContextPreview(null)

    const sessionMap = readSessionMap()
    setSessionId(sessionMap[agent.mode] || null)
  }, [agent.mode, agent.welcome])

  useEffect(() => {
    if (!isOpen || !user) return
    chatAPI.contextPreview(agent.mode)
      .then((res) => {
        setContextPreview(res.data || null)
      })
      .catch(() => {
        setContextPreview(null)
      })
  }, [isOpen, user, agent.mode])

  useEffect(() => {
    if (!isOpen || !user) return
    const refreshContext = () => {
      chatAPI.contextPreview(agent.mode)
        .then((res) => setContextPreview(res.data || null))
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
    setMessages((prev) => [...prev, { role: 'user', content: message }])

    try {
      const res = await chatAPI.ask({
        message,
        session_id: sessionId,
        agent_mode: agent.mode,
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
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: err.response?.data?.detail || 'I could not process that request. Please try again.',
          isError: true,
        },
      ])
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 w-[360px] max-w-[calc(100vw-2rem)] rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
            <div className="flex items-center gap-2 text-slate-100">
              <FiMessageCircle className="text-primary-400" />
              <span className="font-semibold text-sm">{agent.title}</span>
            </div>
            <button onClick={toggleWidget} className="text-slate-400 hover:text-white transition-colors">
              <FiX size={18} />
            </button>
          </div>

          {!user ? (
            <div className="p-4 space-y-3">
              <p className="text-sm text-slate-300">
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
                  <div className="rounded-lg border border-primary-500/30 bg-primary-500/10 p-2">
                    <p className="text-[11px] text-primary-200 font-medium">{contextPreview.label || 'Context'}</p>
                    <p className="text-[11px] text-slate-300 mt-1 max-h-10 overflow-hidden">{contextPreview.summary}</p>
                  </div>
                </div>
              ) : null}
              <div className="h-80 overflow-y-auto p-3 space-y-3">
                {messages.map((msg, idx) => (
                  <div key={`${msg.role}-${idx}`} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                      msg.role === 'user' ? 'bg-primary-600' : 'bg-slate-700 border border-slate-600'
                    }`}>
                      {msg.role === 'user'
                        ? <FiUser size={12} className="text-white" />
                        : <span className="text-[10px] font-bold text-primary-300">N</span>}
                    </div>
                    <div className={`max-w-[78%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-primary-600 text-white'
                        : msg.isError
                          ? 'bg-red-500/10 border border-red-500/30 text-red-200'
                          : 'bg-slate-800 border border-slate-700 text-slate-200'
                    }`}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                {sending && (
                  <div className="flex items-center gap-2 text-slate-400 text-xs">
                    <FiLoader className="animate-spin" size={14} />
                    AI is thinking...
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="p-3 border-t border-slate-700 flex gap-2">
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
                  className="input-field text-sm py-2 px-3"
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
  )
}
