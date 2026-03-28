import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { healthAPI } from '../utils/api'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { FiBarChart2, FiAlertTriangle, FiCheckCircle, FiRefreshCw, FiDownload } from 'react-icons/fi'

export default function TimelinePage() {
  const [data, setData]       = useState(null)
  const [summary, setSummary] = useState(null)
  const [days, setDays]       = useState(30)
  const [loading, setLoading] = useState(true)
  const [resolvingId, setResolvingId] = useState(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      healthAPI.timeline(days),
      healthAPI.summary()
    ]).then(([tRes, sRes]) => {
      setData(tRes.data)
      setSummary(sRes.data)
    }).catch(() => {
      toast.error('Failed to load timeline data')
    })
    .finally(() => setLoading(false))
  }, [days])

  const chartData = data?.timeline?.map(entry => ({
    date:     format(parseISO(entry.date), 'MMM d'),
    severity: entry.severity,
    risk:     Math.round((entry.risk_score || 0) * 100),
    disease:  entry.predicted_disease,
  })) || []

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-theme-soft border border-theme rounded-xl px-4 py-3 text-sm">
        <p className="text-theme-muted mb-1">{label}</p>
        {payload.map((p) => (
          <p key={p.name} style={{ color: p.color }}>
            {p.name}: {p.value}{p.name === 'risk' ? '%' : '/10'}
          </p>
        ))}
      </div>
    )
  }

  const exportCsv = () => {
    if (!data?.timeline?.length) return

    const header = ['date', 'severity', 'risk_score', 'predicted_disease', 'triage_color']
    const rows = data.timeline.map((entry) => [
      entry.date,
      entry.severity,
      entry.risk_score,
      entry.predicted_disease || '',
      entry.triage_color || '',
    ])

    const csv = [header, ...rows]
      .map((row) => row.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(','))
      .join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `nirova_timeline_${days}d.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const markRecovered = async (alertId) => {
    if (!alertId || resolvingId) return
    setResolvingId(alertId)
    try {
      await healthAPI.resolveAlert(alertId)
      setData((prev) => {
        if (!prev?.active_alerts) return prev
        const active_alerts = prev.active_alerts.filter((a) => a.id !== alertId)
        return {
          ...prev,
          active_alerts,
          summary: {
            ...prev.summary,
            active_alert_count: active_alerts.length,
          },
        }
      })
      toast.success('Alert marked as recovered.')
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to mark alert as recovered')
    } finally {
      setResolvingId(null)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <FiRefreshCw className="animate-spin text-primary-400" size={32} />
    </div>
  )

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="section-title flex items-center gap-3 mb-1">
            <FiBarChart2 className="text-primary-400" />
            Health Timeline
          </h1>
          <p className="text-theme-muted">Review your symptom history, risk trajectory, and active alerts.</p>
        </div>
        {/* Period selector */}
        <div className="flex gap-2">
          {[7, 14, 30].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                days === d
                  ? 'bg-primary-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}>
              {d}d
            </button>
          ))}
          <button
            onClick={exportCsv}
            disabled={!data?.timeline?.length}
            className="px-4 py-2 rounded-xl text-sm font-medium bg-theme-soft text-theme hover:bg-theme-soft/70 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <FiDownload size={14} /> Export CSV
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Logs',     value: data?.summary?.total_logs || 0 },
          { label: 'Avg Severity',   value: `${data?.summary?.average_severity || 0}/10` },
          { label: 'Max Risk',       value: `${Math.round((data?.summary?.max_risk_score || 0)*100)}%` },
          { label: 'Active Alerts',  value: data?.summary?.active_alert_count || 0 },
        ].map(stat => (
          <div key={stat.label} className="card text-center">
            <div className="font-display text-2xl font-bold text-primary-400">{stat.value}</div>
            <div className="text-theme-muted text-xs mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      {chartData.length > 0 ? (
        <div className="space-y-6 mb-6">
          {/* Severity chart */}
          <div className="card">
            <h3 className="font-semibold text-white mb-4">Symptom Severity Over Time</h3>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="sevGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#14b8a6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis domain={[0, 10]} tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="severity" stroke="#14b8a6"
                  fill="url(#sevGrad)" strokeWidth={2} dot={{ fill: '#14b8a6', r: 3 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Risk chart */}
          <div className="card">
            <h3 className="font-semibold text-white mb-4">Disease Risk Score (%)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="risk" name="risk" stroke="#f59e0b"
                  fill="url(#riskGrad)" strokeWidth={2} dot={{ fill: '#f59e0b', r: 3 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="card text-center py-16 mb-6">
          <FiBarChart2 size={40} className="text-theme-muted mx-auto mb-4" />
          <p className="text-theme-muted">No data yet. Start logging symptoms to see your timeline!</p>
        </div>
      )}

      {/* AI Summary */}
      {summary?.summary && (
        <div className="card mb-6">
          <h3 className="font-semibold text-white mb-3">AI Monthly Summary</h3>
          <p className="text-theme text-sm leading-relaxed">{summary.summary}</p>
          {summary.top_symptoms?.length > 0 && (
            <div className="mt-4">
              <p className="text-slate-500 text-xs mb-2">Most frequent symptoms</p>
              <div className="flex flex-wrap gap-2">
                {summary.top_symptoms.map(({ symptom, count }) => (
                  <span key={symptom}
                    className="bg-slate-700 text-slate-300 text-xs px-3 py-1 rounded-full">
                    {symptom.replace(/_/g, ' ')} × {count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Active Alerts */}
      {data?.active_alerts?.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <FiAlertTriangle className="text-amber-400" size={18} />
            Active Alerts ({data.active_alerts.length})
          </h3>
          <div className="space-y-3">
            {data.active_alerts.map((alert, i) => (
              <div key={i}
                className="flex items-start justify-between p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                <div>
                  <p className="text-white font-medium">{alert.disease}</p>
                  <p className="text-amber-300/70 text-sm mt-0.5">{alert.recommended_action}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span className="text-amber-400 font-mono font-bold">
                    {Math.round(alert.probability * 100)}%
                  </span>
                  <button
                    onClick={() => markRecovered(alert.id)}
                    disabled={resolvingId === alert.id}
                    className="text-xs px-3 py-1 rounded-lg border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    {resolvingId === alert.id ? 'Updating...' : 'Mark Recovered'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
