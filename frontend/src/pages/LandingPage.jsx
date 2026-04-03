import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTheme } from '../context/ThemeContext'
import {
  FiActivity,
  FiMessageCircle,
  FiCamera,
  FiMapPin,
  FiArrowRight,
  FiShield,
  FiBarChart2,
  FiAlertTriangle,
  FiFileText,
  FiMoon,
  FiSun,
} from 'react-icons/fi'

const features = [
  {
    icon: FiActivity,
    title: 'Symptom Tracker',
    desc: 'Document daily symptoms and monitor risk trends using validated clinical scoring methods.',
    color: 'from-teal-500 to-cyan-500',
  },
  {
    icon: FiMessageCircle,
    title: 'AI Second Opinion',
    desc: 'Receive structured guidance grounded in Bangladesh clinical guidance and global public-health references.',
    color: 'from-purple-500 to-indigo-500',
  },
  {
    icon: FiCamera,
    title: 'Skin Analysis',
    desc: 'Upload skin images for AI-assisted triage with clear follow-up recommendations.',
    color: 'from-orange-500 to-amber-500',
  },
  {
    icon: FiMapPin,
    title: 'Dengue Detector',
    desc: 'Assess dengue risk using Bangladesh-focused analysis trained on representative local clinical data.',
    color: 'from-red-500 to-pink-500',
  },
  {
    icon: FiBarChart2,
    title: 'Health Timeline',
    desc: 'View trend charts for severity and risk score with 7/14/30-day views.',
    color: 'from-sky-500 to-blue-500',
  },
  {
    icon: FiAlertTriangle,
    title: 'Risk Alerts',
    desc: 'Automatic high-risk alerts are generated from prediction confidence and triage logic.',
    color: 'from-rose-500 to-red-500',
  },
  {
    icon: FiFileText,
    title: 'Lab Report AI',
    desc: 'Upload report images/PDFs for structured test extraction and simplified explanations.',
    color: 'from-amber-500 to-orange-500',
  },
  {
    icon: FiMessageCircle,
    title: 'Context-Aware AI Chat',
    desc: 'AI chat uses your recent symptom logs and saved scan analyses to provide more personalized follow-up guidance.',
    color: 'from-violet-500 to-purple-500',
  },
]

const stats = [
  { value: '8',     label: 'Live User Features' },
  { value: '1',     label: 'AI Assistant' },
  { value: '41',    label: 'Conditions Modeled' },
  { value: '3',     label: 'Vision Workflows' },
]

export default function LandingPage() {
  const { isDark, toggleTheme } = useTheme()

  return (
    <div className="min-h-screen bg-app overflow-hidden">

      {/* Background mesh gradient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-600/8 rounded-full blur-3xl" />
      </div>

      {/* Nav */}
      <nav className="relative z-10 flex flex-col sm:flex-row items-center justify-between px-4 sm:px-8 py-4 sm:py-6 max-w-7xl mx-auto gap-4 sm:gap-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary-600 flex items-center justify-center">
            <span className="text-white font-display font-bold">N</span>
          </div>
          <span className="font-display font-bold text-theme text-xl">NirovaAI</span>
          <span className="text-theme-muted text-sm ml-1">নিরোভা</span>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={toggleTheme}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-theme bg-theme-soft text-theme text-sm font-medium hover:shadow-sm transition-all duration-200"
            aria-label="Toggle color mode"
          >
            {isDark ? <FiSun size={16} /> : <FiMoon size={16} />}
            {isDark ? 'Light mood' : 'Night mode'}
          </button>
          <Link to="/login"
            className="text-theme-muted hover:text-theme transition-colors font-medium text-sm">
            Sign in
          </Link>
          <Link to="/register"
            className="btn-primary text-sm py-2.5 px-5">
            Get Started Free
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-8 pt-12 sm:pt-20 pb-16 sm:pb-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
        >
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-primary-500/10 border border-primary-500/30 text-primary-300 px-4 py-2 rounded-full text-sm font-medium mb-8">
            <FiShield size={14} />
            Built for Bangladesh healthcare contexts
          </div>

          {/* Headline */}
          <h1 className="font-display text-3xl xs:text-4xl sm:text-6xl md:text-7xl font-bold text-theme leading-tight mb-6">
            Earlier Insight,
            <br />
            <span className="gradient-text">Better Health Decisions</span>
          </h1>

          <p className="text-theme-muted text-base sm:text-xl max-w-2xl mx-auto mb-8 sm:mb-10 leading-relaxed">
            NirovaAI is a primary-level health AI assistant that helps you monitor symptoms,
            assess risk for dengue and other common conditions,
            and receive practical guidance to support timely clinical care.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4">
            <Link to="/register"
              className="btn-primary flex items-center gap-2 text-base px-8 py-4">
              Start Tracking Free
              <FiArrowRight size={18} />
            </Link>
            <Link to="/login"
              className="btn-outline text-base px-8 py-4">
              Sign In
            </Link>
          </div>
        </motion.div>

        {/* Stats row */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6 max-w-3xl mx-auto mt-10 sm:mt-20"
        >
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="font-display text-2xl sm:text-3xl font-bold text-primary-400 mb-1">
                {stat.value}
              </div>
              <div className="text-theme-muted text-xs sm:text-sm">{stat.label}</div>
            </div>
          ))}
        </motion.div>
      </section>

      {/* Features */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-8 pb-16 sm:pb-24">
        <div className="text-center mb-16">
          <h2 className="font-display text-4xl font-bold text-theme mb-4">
            What You Can Use Right Now
          </h2>
          <p className="text-theme-muted text-lg max-w-xl mx-auto">
            These are active features currently available in the product today.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="card-hover group"
            >
              <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${feature.color} p-2.5 mb-4`}>
                <feature.icon size={28} className="text-white" />
              </div>
              <h3 className="font-display text-xl font-semibold text-theme mb-2">
                {feature.title}
              </h3>
              <p className="text-theme-muted leading-relaxed">
                {feature.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-theme px-4 sm:px-8 py-6 sm:py-8 max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 sm:gap-0">
          <p className="text-theme-muted text-xs sm:text-sm">
            © 2026 NirovaAI — Built for Bangladesh
          </p>
          <p className="text-theme-muted text-xs">
            Disclaimer: Primary-level health guidance only; not a replacement for clinical diagnosis.
          </p>
        </div>
      </footer>
    </div>
  )
}
