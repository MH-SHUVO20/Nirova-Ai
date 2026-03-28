import { useMemo, useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { FiLock, FiArrowLeft, FiCheckCircle, FiLoader } from 'react-icons/fi'
import { authAPI, extractErrorMessage } from '../utils/api'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const initialToken = searchParams.get('token') || ''
  const emailHint = searchParams.get('email') || ''

  const [token, setToken] = useState(initialToken)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const passwordMismatch = useMemo(() => {
    return confirmPassword.length > 0 && newPassword !== confirmPassword
  }, [newPassword, confirmPassword])

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!token.trim()) {
      toast.error('Reset token is required')
      return
    }
    if (newPassword.length < 8) {
      toast.error('New password must be at least 8 characters')
      return
    }
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      await authAPI.resetPassword({ token: token.trim(), new_password: newPassword })
      setDone(true)
      toast.success('Password updated successfully')
      setTimeout(() => navigate('/login', { replace: true }), 1000)
    } catch (err) {
      toast.error(extractErrorMessage(err) || 'Could not reset password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-app flex items-center justify-center px-4 py-8">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-primary-600/8 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-xl bg-primary-600 flex items-center justify-center">
              <span className="text-white font-display font-bold">N</span>
            </div>
            <span className="font-display font-bold text-white text-2xl">NirovaAI</span>
          </Link>
          <h2 className="font-display text-3xl font-bold text-theme">Set new password</h2>
          <p className="text-theme-muted mt-2">
            {emailHint ? `Resetting password for ${emailHint}` : 'Enter your token and new password'}
          </p>
        </div>

        <div className="card space-y-5">
          {done ? (
            <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-emerald-200 flex items-center gap-3">
              <FiCheckCircle size={18} />
              Password reset successful. Redirecting to login...
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-theme mb-2">Reset token</label>
                <input
                  type="text"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Paste reset token"
                  className="input-field"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-theme mb-2">New password</label>
                <div className="relative">
                  <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-theme-muted" size={16} />
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="input-field pl-11"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-theme mb-2">Confirm password</label>
                <div className="relative">
                  <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-theme-muted" size={16} />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    className="input-field pl-11"
                    required
                  />
                </div>
                {passwordMismatch ? (
                  <p className="text-xs text-red-400 mt-1">Passwords do not match.</p>
                ) : null}
              </div>

              <button
                type="submit"
                disabled={loading || passwordMismatch}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {loading ? (
                  <><FiLoader className="animate-spin" size={16} /> Updating...</>
                ) : (
                  <>Update password</>
                )}
              </button>
            </form>
          )}

          <p className="text-center text-theme-muted text-sm">
            <Link to="/login" className="inline-flex items-center gap-2 text-primary-400 hover:text-primary-300 font-medium">
              <FiArrowLeft size={14} /> Back to sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
