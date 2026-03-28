import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import { extractErrorMessage } from '../utils/api'
import { FiUser, FiMail, FiLock, FiMapPin, FiArrowRight, FiLoader } from 'react-icons/fi'

const BD_DISTRICTS = [
  'Dhaka','Chittagong','Sylhet','Rajshahi','Khulna',
  'Barisal','Rangpur','Mymensingh','Comilla','Noakhali',
  'Gazipur','Narayanganj','Tangail','Bogra','Dinajpur',
]

export default function RegisterPage() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '', email: '', password: '',
    age: '', district: 'Dhaka', language: 'en'
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) {
      navigate('/app', { replace: true })
    }
  }, [user, navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    setLoading(true)
    try {
      await register({
        ...form,
        email: form.email.trim().toLowerCase(),
        age: parseInt(form.age) || 0,
      })
      toast.success('Account created successfully.')
      navigate('/app', { replace: true })
    } catch (err) {
      toast.error(extractErrorMessage(err) || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const set = (field) => (e) => setForm({...form, [field]: e.target.value})

  return (
    <div className="min-h-screen bg-app flex items-center justify-center px-4 py-12">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-primary-600/8 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-xl bg-primary-600 flex items-center justify-center">
              <span className="text-white font-display font-bold">N</span>
            </div>
            <span className="font-display font-bold text-white text-2xl">NirovaAI</span>
          </Link>
          <h2 className="font-display text-3xl font-bold text-theme">Create account</h2>
          <p className="text-theme-muted mt-2">Set up your secure account to start symptom tracking and AI-guided triage.</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1.5">Full Name</label>
              <div className="relative">
                <FiUser className="absolute left-4 top-1/2 -translate-y-1/2 text-theme-muted" size={16} />
                <input type="text" value={form.name} onChange={set('name')}
                  placeholder="Your name" className="input-field pl-11" required />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1.5">Email</label>
              <div className="relative">
                <FiMail className="absolute left-4 top-1/2 -translate-y-1/2 text-theme-muted" size={16} />
                <input type="email" value={form.email} onChange={set('email')}
                  placeholder="you@example.com" className="input-field pl-11" required />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-theme mb-1.5">Password</label>
              <div className="relative">
                <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-theme-muted" size={16} />
                <input type="password" value={form.password} onChange={set('password')}
                  placeholder="Min 8 characters" className="input-field pl-11" required />
              </div>
            </div>

            {/* Age + District row */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-theme mb-1.5">Age</label>
                <input type="number" value={form.age} onChange={set('age')}
                  placeholder="25" min="1" max="120" className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  <FiMapPin className="inline mr-1" size={12} />District
                </label>
                <select value={form.district} onChange={set('district')} className="input-field">
                  {BD_DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
            </div>

            {/* Language */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Preferred Language</label>
              <div className="grid grid-cols-2 gap-3">
                {[['en','English'],['bn','বাংলা']].map(([val, label]) => (
                  <label key={val}
                    className={`flex items-center justify-center gap-2 p-3 rounded-xl border cursor-pointer transition-all ${
                      form.language === val
                        ? 'border-primary-500 bg-primary-500/10 text-primary-300'
                        : 'border-slate-600 text-slate-400 hover:border-slate-500'
                    }`}>
                    <input type="radio" name="language" value={val}
                      checked={form.language === val} onChange={set('language')}
                      className="hidden" />
                    {label}
                  </label>
                ))}
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
              {loading ? (
                <><FiLoader className="animate-spin" size={16} /> Creating account...</>
              ) : (
                <>Create Account <FiArrowRight size={16} /></>
              )}
            </button>
          </form>

          <p className="text-center text-theme-muted text-sm mt-5">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
