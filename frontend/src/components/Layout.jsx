import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  FiGrid, FiActivity, FiMessageCircle, FiCamera, FiFileText, FiClipboard,
  FiBarChart2, FiLogOut, FiUser, FiTarget
} from 'react-icons/fi'

const navItems = [
  { to: '/app',           icon: FiGrid,          label: 'Dashboard',  exact: true },
  { to: '/app/symptoms',  icon: FiActivity,       label: 'Symptoms' },
  { to: '/app/dengue',    icon: FiTarget,         label: 'Dengue Detector' },
  { to: '/app/chat',      icon: FiMessageCircle,  label: 'AI Chat' },
  { to: '/app/skin',      icon: FiCamera,         label: 'Skin Check' },
  { to: '/app/lab-report', icon: FiFileText,      label: 'Lab Analyzer' },
  { to: '/app/prescription', icon: FiClipboard,   label: 'Prescription' },
  { to: '/app/timeline',  icon: FiBarChart2,      label: 'Timeline' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-[#0a1628] flex">

      {/* Sidebar */}
      <aside className="w-64 bg-slate-900/80 border-r border-slate-700/50 flex flex-col fixed h-full z-10">

        {/* Logo */}
        <div className="p-6 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary-600 flex items-center justify-center">
              <span className="text-white font-display font-bold text-sm">N</span>
            </div>
            <div>
              <h1 className="font-display font-bold text-white text-lg leading-none">NirovaAI</h1>
              <p className="text-slate-500 text-xs mt-0.5">নিরোভা</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, icon: Icon, label, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-primary-600/20 text-primary-400 border border-primary-500/30'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-slate-700/50">
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-800/50 mb-2">
            <div className="w-8 h-8 rounded-full bg-primary-600/30 flex items-center justify-center">
              <FiUser size={14} className="text-primary-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">{user?.name}</p>
              <p className="text-slate-500 text-xs truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all duration-200 text-sm"
          >
            <FiLogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 ml-64 min-h-screen">
        <div className="w-full px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
