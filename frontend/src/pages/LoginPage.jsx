import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import { extractErrorMessage } from '../utils/api'
import { FiMail, FiLock, FiArrowRight, FiLoader } from 'react-icons/fi'

export default function LoginPage() {
  const { user, login } = useAuth()
  const navigate   = useNavigate()
  const [form, setForm]       = useState({ email: '', password: '' })
  const [loginLoading, setLoginLoading] = useState(false)

  useEffect(() => {
    if (user) {
      navigate('/app', { replace: true })
    }
  }, [user, navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoginLoading(true)
    try {
      const email = form.email.trim().toLowerCase()
      const password = form.password
      await login(email, password)
      toast.success('Welcome back!')
      navigate('/app', { replace: true })
    } catch (err) {
      toast.error(extractErrorMessage(err) || 'Login failed')
    } finally {
      setLoginLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-app flex items-center justify-center px-4 py-8">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-600/8 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-xl bg-primary-600 flex items-center justify-center">
              <span className="text-white font-display font-bold">N</span>
            </div>
            <span className="font-display font-bold text-white text-2xl">NirovaAI</span>
          </Link>
          <h2 className="font-display text-3xl font-bold text-theme">Welcome back</h2>
          <p className="text-theme-muted mt-2">Sign in to continue to your health dashboard.</p>
        </div>

        {/* Form */}
        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-theme mb-2">Email</label>
              <div className="relative">
                <FiMail className="absolute left-4 top-1/2 -translate-y-1/2 text-theme-muted" size={16} />
                <input
                  type="email"
                  value={form.email}
                  onChange={e => setForm({...form, email: e.target.value})}
                  placeholder="you@example.com"
                  className="input-field pl-11"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-theme mb-2">Password</label>
              <div className="relative">
                <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-theme-muted" size={16} />
                <input
                  type="password"
                  value={form.password}
                  onChange={e => setForm({...form, password: e.target.value})}
                  placeholder="••••••••"
                  className="input-field pl-11"
                  required
                />
              </div>
              <div className="mt-2 text-right">
                <Link to="/forgot-password" className="text-sm text-primary-400 hover:text-primary-300 font-medium">
                  Forgot password?
                </Link>
              </div>
            </div>

            <button
              type="submit"
              disabled={loginLoading}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loginLoading ? (
                <><FiLoader className="animate-spin" size={16} /> Signing in...</>
              ) : (
                <>Sign in <FiArrowRight size={16} /></>
              )}
            </button>
          </form>

          <p className="text-center text-theme-muted text-sm mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary-400 hover:text-primary-300 font-medium">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
