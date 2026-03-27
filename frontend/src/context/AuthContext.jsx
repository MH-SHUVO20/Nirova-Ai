import { createContext, useContext, useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { authAPI } from '../utils/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Try to get user from the server on load, which implicitly validates cookie
    const loadUser = async () => {
      try {
        const res = await authAPI.getMe()
        if (res.data) {
          setUser(res.data)
        }
      } catch (err) {
        setUser(null)
        localStorage.removeItem('nirovaai_user')
        const status = err?.response?.status
        if (status && status !== 401) {
          toast.error('Server unavailable. Please try again shortly.')
        }
      } finally {
        setLoading(false)
      }
    }
    
    // Fallback: Check if we have standard cached user to avoid blink
    const savedUser = localStorage.getItem('nirovaai_user')
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser))
      } catch {
        localStorage.removeItem('nirovaai_user')
        toast.error('Corrupted user session. Please log in again.')
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
      await authAPI.logout()
    } catch(e) {
      toast.error('Logout failed. Please try again.')
    }
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
