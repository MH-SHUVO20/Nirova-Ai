import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import EmergencyHospitals from '../components/EmergencyHospitals'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { healthAPI, symptomsAPI } from '../utils/api'
import { FiActivity, FiAlertTriangle, FiMessageCircle, FiCamera, FiArrowRight, FiTrendingUp, FiFileText, FiClipboard, FiTarget } from 'react-icons/fi'
import { motion } from 'framer-motion'

export default function DashboardPage() {
  const { user } = useAuth()
  const [timeline, setTimeline] = useState(null)
  const [latest, setLatest]     = useState(null)
  const [loading, setLoading]   = useState(true)

  useEffect(() => {
    Promise.all([
      healthAPI.timeline(7),
      symptomsAPI.latest()
    ]).then(([tRes, lRes]) => {
      setTimeline(tRes.data)
      setLatest(lRes.data)
    }).catch(() => {
      toast.error('Failed to load dashboard data')
    })
    .finally(() => setLoading(false))
  }, [])

  const triageColors = {
    red:    'bg-red-500/20 text-red-300 border-red-500/40',
    yellow: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    green:  'bg-green-500/20 text-green-300 border-green-500/40',
  }
  const latestConfidence = latest?.risk_score || 0
  const isLowConfidence = latestConfidence < 0.3
  const latestTitle = isLowConfidence
    ? 'Low-confidence result (more symptoms needed)'
    : latest?.predicted_disease
  const latestSubtitle = isLowConfidence
    ? 'Current data is insufficient for a reliable disease label. Log more symptoms or recheck soon.'
    : null

  const quickActions = [
    { to: '/app/symptoms', icon: FiActivity,      label: 'Log Symptoms',   color: 'from-teal-600 to-cyan-600',   desc: 'Track today\'s health' },
    { to: '/app/dengue',   icon: FiTarget,        label: 'Dengue Detector', color: 'from-rose-600 to-red-600',   desc: 'Dedicated NS1/IgG/IgM risk check' },
    { to: '/app/chat',     icon: FiMessageCircle, label: 'AI Chat',        color: 'from-purple-600 to-indigo-600', desc: 'Ask health questions' },
    { to: '/app/skin',     icon: FiCamera,        label: 'Skin Check',     color: 'from-orange-600 to-amber-600', desc: 'Analyze skin condition' },
    { to: '/app/lab-report', icon: FiFileText,    label: 'Lab Analyzer',   color: 'from-cyan-700 to-sky-700',     desc: 'Upload image or PDF report' },
    { to: '/app/prescription', icon: FiClipboard, label: 'Prescription',   color: 'from-emerald-700 to-teal-700', desc: 'Extract medicines and schedule' },
    { to: '/app/timeline', icon: FiTrendingUp,    label: 'View Timeline',  color: 'from-slate-600 to-slate-700',  desc: 'Full health history' },
  ]

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-white">
          Good {getTimeOfDay()}, {user?.name?.split(' ')[0]}
        </h1>
        <p className="text-slate-400 mt-1">Here is your health overview for today.</p>
      </div>

      {/* Active alerts */}
      {timeline?.active_alerts?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5 mb-6"
        >
          <div className="flex items-center gap-3 mb-3">
            <FiAlertTriangle className="text-red-400" size={20} />
            <h3 className="font-semibold text-red-300">Active Health Alert</h3>
          </div>
          {timeline.active_alerts.slice(0, 2).map((alert, i) => (
            <div key={i} className="flex items-start justify-between">
              <div>
                <p className="text-white font-medium">{alert.disease}</p>
                <p className="text-red-300/70 text-sm mt-0.5">{alert.recommended_action}</p>
              </div>
              <span className="text-red-400 font-mono text-sm">
                {Math.round(alert.probability * 100)}%
              </span>
            </div>
          ))}
        </motion.div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Logs This Week', value: timeline?.summary?.total_logs || 0, unit: 'entries' },
          { label: 'Avg Severity',   value: timeline?.summary?.average_severity || 0, unit: '/ 10' },
          { label: 'Max Risk Score', value: `${Math.round((timeline?.summary?.max_risk_score || 0) * 100)}`, unit: '%' },
        ].map((stat) => (
          <div key={stat.label} className="card text-center">
            <div className="font-display text-3xl font-bold text-primary-400">{stat.value}</div>
            <div className="text-slate-500 text-xs mt-1">{stat.unit}</div>
            <div className="text-slate-400 text-sm mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Latest prediction */}
      {latest?.predicted_disease && (
        <div className={`card border mb-6 ${isLowConfidence ? triageColors.yellow : (triageColors[latest.triage_color] || triageColors.green)}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm opacity-70 mb-1">Latest AI Prediction</p>
              <p className="text-white font-display text-xl font-bold">{latestTitle}</p>
              {latestSubtitle && (
                <p className="text-sm opacity-80 mt-1 max-w-xl">{latestSubtitle}</p>
              )}
              <div className="flex gap-2 mt-2 flex-wrap">
                {latest.symptoms?.slice(0, 4).map(s => (
                  <span key={s} className="symptom-tag text-xs">{s.replace(/_/g, ' ')}</span>
                ))}
              </div>
            </div>
            <div className="text-right">
              <div className="font-mono text-2xl font-bold">
                {Math.round(latestConfidence * 100)}%
              </div>
              <div className="text-xs opacity-70 mt-1">confidence</div>
            </div>
          </div>
        </div>
      )}

      {/* Quick actions */}
      <h2 className="font-display text-lg font-semibold text-white mb-4">Quick Actions</h2>
      <div className="grid grid-cols-2 gap-4">
        {quickActions.map(({ to, icon: Icon, label, color, desc }) => (
          <Link key={to} to={to}
            className="card-hover group flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center flex-shrink-0`}>
              <Icon size={22} className="text-white" />
            </div>
            <div className="flex-1">
              <div className="text-white font-semibold">{label}</div>
              <div className="text-slate-400 text-sm">{desc}</div>
            </div>
            <FiArrowRight className="text-slate-500 group-hover:text-primary-400 transition-colors" size={16} />
          </Link>
        ))}
      </div>

      <div className="card mt-6 border border-red-500/20 bg-red-500/5">
        <h3 className="text-white font-semibold mb-3">Emergency Support</h3>
        <p className="text-slate-300 text-sm mb-4">If you have severe symptoms such as breathing difficulty, bleeding, confusion, or persistent high fever, seek emergency care immediately.</p>
        <div className="flex flex-wrap gap-3">
          <a href="tel:999" className="btn-outline text-sm">Call National Emergency 999</a>
          <a href="tel:16263" className="btn-outline text-sm">Call Health Helpline 16263</a>
        </div>
      </div>
      <EmergencyHospitals />
    </div>
  )
}

function getTimeOfDay() {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
}
