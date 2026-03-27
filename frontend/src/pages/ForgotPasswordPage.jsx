import { useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { FiMail, FiArrowLeft, FiSend, FiLoader } from 'react-icons/fi'
import { authAPI } from '../utils/api'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [previewLink, setPreviewLink] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    setPreviewLink('')

    try {
      const res = await authAPI.forgotPassword({ email })
      const apiMessage = res.data?.message || 'If an account exists, reset instructions were sent.'
      setMessage(apiMessage)

      if (res.data?.reset_link_preview) {
        setPreviewLink(res.data.reset_link_preview)
      }

      toast.success('Password reset request submitted')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not process reset request')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a1628] flex items-center justify-center px-4 py-8">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-600/8 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-xl bg-primary-600 flex items-center justify-center">
              <span className="text-white font-display font-bold">N</span>
            </div>
            <span className="font-display font-bold text-white text-2xl">NirovaAI</span>
          </Link>
          <h2 className="font-display text-3xl font-bold text-white">Forgot password</h2>
          <p className="text-slate-400 mt-2">Enter your account email to get reset instructions.</p>
        </div>

        <div className="card space-y-5">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
              <div className="relative">
                <FiMail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="input-field pl-11"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? (
                <><FiLoader className="animate-spin" size={16} /> Sending...</>
              ) : (
                <>Send reset link <FiSend size={16} /></>
              )}
            </button>
          </form>

          {message ? (
            <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-3 text-sm text-slate-300">
              {message}
              {previewLink ? (
                <div className="mt-2 break-all">
                  <span className="text-primary-300">Local preview:</span>{' '}
                  <Link to={new URL(previewLink).pathname + new URL(previewLink).search} className="text-primary-400 hover:text-primary-300 underline">
                    Open reset page
                  </Link>
                </div>
              ) : null}
            </div>
          ) : null}

          <p className="text-center text-slate-400 text-sm">
            <Link to="/login" className="inline-flex items-center gap-2 text-primary-400 hover:text-primary-300 font-medium">
              <FiArrowLeft size={14} /> Back to sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
