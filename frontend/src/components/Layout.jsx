import { useMemo, useState } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import {
  FiGrid, FiActivity, FiMessageCircle, FiCamera, FiFileText, FiClipboard,
  FiBarChart2, FiLogOut, FiUser, FiTarget, FiMenu, FiX, FiMoon, FiSun
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
  const { isDark, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const pageTitle = useMemo(() => {
    const active = navItems.find((item) => {
      if (item.exact) {
        return location.pathname === item.to
      }
      return location.pathname.startsWith(item.to)
    })
    return active?.label || 'Dashboard'
  }, [location.pathname])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const closeSidebar = () => setSidebarOpen(false)

  return (
    <div className="min-h-screen bg-app transition-colors duration-300 flex">

      {sidebarOpen ? (
        <button
          onClick={closeSidebar}
          className="fixed inset-0 z-20 bg-black/35 md:hidden"
          aria-label="Close navigation"
        />
      ) : null}

      {/* Sidebar */}
      <aside
        className={`w-72 md:w-64 surface-panel border-r border-theme flex flex-col fixed h-full z-30 transition-transform duration-300 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >

        {/* Logo */}
        <div className="p-6 border-b border-theme">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-700/30">
              <span className="text-white font-display font-bold text-sm">N</span>
            </div>
            <div>
              <h1 className="font-display font-bold text-theme text-lg leading-none">NirovaAI</h1>
              <p className="text-theme-muted text-xs mt-0.5">নিরোভা</p>
            </div>
            <button
              onClick={closeSidebar}
              className="ml-auto md:hidden p-2 rounded-lg text-theme-muted hover:text-theme hover:bg-theme-soft transition-colors"
              aria-label="Close menu"
            >
              <FiX size={18} />
            </button>
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
                    ? 'bg-primary-600/20 text-primary-500 border border-primary-500/30'
                    : 'text-theme-muted hover:bg-theme-soft hover:text-theme'
                }`
              }
              onClick={closeSidebar}
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-theme">
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-theme-soft mb-2">
            <div className="w-8 h-8 rounded-full bg-primary-600/30 flex items-center justify-center">
              <FiUser size={14} className="text-primary-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-theme text-sm font-medium truncate">{user?.name}</p>
              <p className="text-theme-muted text-xs truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-theme-muted hover:text-red-500 hover:bg-red-500/10 transition-all duration-200 text-sm"
          >
            <FiLogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 md:ml-64 min-h-screen">
        <header className="sticky top-0 z-20 border-b border-theme bg-theme-header backdrop-blur-md px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="md:hidden p-2 rounded-lg text-theme-muted hover:text-theme hover:bg-theme-soft transition-colors"
              aria-label="Open menu"
            >
              <FiMenu size={18} />
            </button>
            <div>
              <h2 className="font-display text-lg font-semibold text-theme leading-tight">{pageTitle}</h2>
            </div>
          </div>

          <button
            onClick={toggleTheme}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-theme bg-theme-soft text-theme text-sm font-medium hover:shadow-sm transition-all duration-200"
            aria-label="Toggle color mode"
          >
            {isDark ? <FiSun size={16} /> : <FiMoon size={16} />}
            {isDark ? 'Light mood' : 'Night mode'}
          </button>
        </header>

        <div className="w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
