import { useState, useRef, useEffect } from 'react'
import toast from 'react-hot-toast'
import { createChatSocket, chatAPI } from '../utils/api'
import { FiSend, FiLoader, FiMessageCircle, FiUser } from 'react-icons/fi'
import { motion, AnimatePresence } from 'framer-motion'
import LanguageSelector from '../components/LanguageSelector'
import { useLanguage } from '../context/LanguageContext'

const SUGGESTIONS = [
  'I have high fever and joint pain for 3 days.',
  'What are warning signs of dengue?',
  'My child has a rash and mild fever. What should I monitor?',
  'How can I differentiate dengue and typhoid symptoms?',
  'When should I go to the hospital urgently?',
]

const LATEST_CONTEXT_KEY = 'nirovaai_latest_context'

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

function normalizeAssistantText(text) {
  let out = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  out = out.replace(/\*\*/g, '').replace(/__/g, '')
  out = out.replace(/\s+([1-4]\)\s*(Summary|What To Do Now|Red Flags|Follow-?Up))/gi, '\n$1')
  out = out.replace(/([1-4]\)\s*(Summary|What To Do Now|Red Flags|Follow-?Up))\s*\*\s*/gi, '$1\n- ')
  out = out.replace(/\s+\*\s+/g, '\n- ')
  out = out.replace(/\n{3,}/g, '\n\n').trim()
  return out
}

export default function ChatPage() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'আমি NirovaAI, a primary-level health AI assistant. I can help you understand symptoms and suggest practical next steps.\n\nShare your symptoms, duration, and any test results. I will provide guidance based on Bangladesh-focused health references.\n\nI will also tell you when clinic or hospital follow-up is recommended based on risk.',
    }
  ])
  const [input, setInput]       = useState('')
  const [streaming, setStreaming] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const socketRef    = useRef(null)
  const messagesEnd  = useRef(null)
  const inputRef     = useRef(null)
  const [clientContext, setClientContext] = useState('')

  useEffect(() => {
    chatAPI.history(1, 'chat').then((res) => {
      const latestSession = res.data[0]
      if (latestSession && latestSession.messages?.length > 0) {
        setSessionId(latestSession.session_id)
        setMessages([
          {
            role: 'assistant',
            content: 'I have restored our last conversation. How can I help you today?'
          },
          ...latestSession.messages
        ])
      }
    }).catch(err => {
      toast.error('Failed to load chat history')
    })
  }, [])

  useEffect(() => {
    const map = readLatestContextMap()
    const all = Object.values(map).filter(Boolean)
    setClientContext(all.join(' | '))
  }, [])

  useEffect(() => {
    const onAnalysisUpdated = (evt) => {
      const detailSummary = evt?.detail?.summary
      const detailType = evt?.detail?.type || 'general'
      if (typeof detailSummary !== 'string' || !detailSummary.trim()) return
      const map = readLatestContextMap()
      map[detailType] = detailSummary.trim()
      writeLatestContextMap(map)
      const all = Object.values(map).filter(Boolean)
      setClientContext(all.join(' | '))
    }
    window.addEventListener('nirovaai:analysis-updated', onAnalysisUpdated)
    return () => window.removeEventListener('nirovaai:analysis-updated', onAnalysisUpdated)
  }, [])

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const { language } = useLanguage()

  const sendMessage = async (text) => {
    const message = (text || input).trim()
    if (!message || streaming) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: message }])
    setStreaming(true)

    // Add empty AI message that we'll stream into
    setMessages(prev => [...prev, { role: 'assistant', content: '', isStreaming: true }])

    try {
      const socket = createChatSocket()
      socketRef.current = socket

      socket.onopen = () => {
        socket.send(JSON.stringify({ 
          message, 
          session_id: sessionId, 
          agent_mode: 'chat', 
          client_context: clientContext,
          language: language === 'bn' ? 'bn' : 'en'
        }))
      }

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data)

        if (data.type === 'token') {
          setMessages(prev => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            updated[updated.length - 1] = {
              ...last,
              content: last.content + data.content
            }
            return updated
          })
        } else if (data.type === 'done') {
          setSessionId(data.session_id)
          setStreaming(false)
          setMessages(prev => {
            const updated = [...prev]
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              isStreaming: false,
              content: data.formatted_response || updated[updated.length - 1].content
            }
            return updated
          })
          socket.close()
        } else if (data.type === 'error') {
          setStreaming(false)
          setMessages(prev => {
            const updated = [...prev]
            updated[updated.length - 1] = {
              role: 'assistant',
              content: 'Sorry, I encountered an error. Please try again.',
              isStreaming: false,
              isError: true
            }
            return updated
          })
        }
      }

      socket.onerror = () => {
        // Fallback to REST API if WebSocket fails
        fallbackToRest(message)
      }

    } catch (err) {
      fallbackToRest(message)
    }
  }

  const fallbackToRest = async (message) => {
    try {
      const { chatAPI } = await import('../utils/api')
      const res = await chatAPI.ask({ message, session_id: sessionId, agent_mode: 'chat', client_context: clientContext })
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: res.data.response,
          isStreaming: false
        }
        return updated
      })
      setSessionId(res.data.session_id)
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: 'Connection failed. Please check your internet and try again.',
          isStreaming: false,
          isError: true
        }
        return updated
      })
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] animate-fade-in">
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div className="flex-1">
          <h1 className="section-title flex items-center gap-3 mb-1">
            <FiMessageCircle className="text-primary-400" />
            AI Health Assistant
          </h1>
          <p className="text-theme-muted text-sm">
            Describe your symptoms or ask any health-related questions.
          </p>
        </div>
        <LanguageSelector />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2 mb-4">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
                msg.role === 'user'
                  ? 'bg-primary-600'
                  : 'bg-theme-soft border border-theme'
              }`}>
                {msg.role === 'user'
                  ? <FiUser size={14} className="text-white" />
                  : <span className="text-xs font-bold text-primary-400">N</span>
                }
              </div>

              {/* Bubble */}
              <div className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-primary-600 text-white rounded-tr-sm'
                  : msg.isError
                    ? 'bg-red-500/10 border border-red-500/30 text-red-300 rounded-tl-sm'
                    : 'bg-theme-soft border border-theme text-theme rounded-tl-sm'
              }`}>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {msg.role === 'assistant' && !msg.isError ? normalizeAssistantText(msg.content) : msg.content}
                </p>
                {msg.isStreaming && (
                  <span className="inline-flex gap-0.5 ml-1 mt-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary-400 dot-1" />
                    <span className="w-1.5 h-1.5 rounded-full bg-primary-400 dot-2" />
                    <span className="w-1.5 h-1.5 rounded-full bg-primary-400 dot-3" />
                  </span>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEnd} />
      </div>

      {/* Suggestions (shown when only 1 message) */}
      {messages.length === 1 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {SUGGESTIONS.map(s => (
            <button key={s} onClick={() => sendMessage(s)}
              className="bg-theme-soft hover:bg-theme-soft/70 border border-theme text-theme text-xs px-3 py-2 rounded-xl transition-all">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="flex gap-3">
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
          placeholder="Describe your symptoms or ask a health question..."
          disabled={streaming}
          className="input-field flex-1"
        />
        <button
          onClick={() => sendMessage()}
          disabled={streaming || !input.trim()}
          className="btn-primary px-5 flex items-center gap-2"
        >
          {streaming
            ? <FiLoader className="animate-spin" size={18} />
            : <FiSend size={18} />
          }
        </button>
      </div>
    </div>
  )
}
