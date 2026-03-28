import { createContext, useContext, useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { authAPI } from '../utils/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadUser = async () => {
      const savedUser = localStorage.getItem('nirovaai_user')
      try {
        const res = await authAPI.getMe()
        if (res.data) {
          setUser(res.data)
          localStorage.setItem('nirovaai_user', JSON.stringify(res.data))
        } else {
          setUser(null)
          localStorage.removeItem('nirovaai_user')
        }
      } catch (err) {
        const status = err?.response?.status
        if (status === 401) {
          setUser(null)
          localStorage.removeItem('nirovaai_user')
        } else {
          if (savedUser) {
            try { setUser(JSON.parse(savedUser)) }
            catch { setUser(null); localStorage.removeItem('nirovaai_user') }
          } else {
            setUser(null)
          }
        }
      } finally {
        setLoading(false)
      }
    }
    loadUser()
  }, [])

  const login = async (email, password) => {
    const res = await authAPI.login({ email, password })
    const { user_id, name, email: userEmail, user: respUser } = res.data
    const resolvedUser = {
      id: user_id || respUser?.id,
      name: name || respUser?.name,
      email: userEmail || respUser?.email,
    }

    localStorage.setItem('nirovaai_user', JSON.stringify(resolvedUser))
    setUser(resolvedUser)
    return res.data
  }

  const register = async (formData) => {
    const res = await authAPI.register(formData)
    const { user_id, name, email } = res.data

    const userData = { id: user_id, name, email }
    localStorage.setItem('nirovaai_user', JSON.stringify(userData))
    setUser(userData)
    return res.data
  }

  const logout = async () => {
    try {
      await authAPI.logoutCleanup()
      await authAPI.logout()
    } catch(e) {
      toast.error('Logout had partial issues. Local session was cleared.')
    }

    // Destroy all local and session chat/context caches for a fresh next login.
    Object.keys(localStorage).forEach((key) => {
      if (key.startsWith('nirovaai_')) {
        localStorage.removeItem(key)
      }
    })
    Object.keys(sessionStorage).forEach((key) => {
      if (key.startsWith('nirovaai_')) {
        sessionStorage.removeItem(key)
      }
    })

    localStorage.removeItem('nirovaai_user')
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
