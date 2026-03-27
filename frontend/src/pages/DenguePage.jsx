import { useMemo, useState } from 'react'
import { FiAlertTriangle, FiDroplet, FiLoader, FiMapPin, FiTarget } from 'react-icons/fi'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import { symptomsAPI } from '../utils/api'

const DENGUE_SYMPTOMS = [
  'high_fever',
  'mild_fever',
  'headache',
  'pain_behind_the_eyes',
  'joint_pain',
  'muscle_pain',
  'vomiting',
  'nausea',
  'skin_rash',
  'fatigue',
  'abdominal_pain',
  'red_spots_over_body',
]

const RISK_STYLES = {
  high: 'border-red-500/40 bg-red-500/10 text-red-200',
  medium: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
  low: 'border-green-500/40 bg-green-500/10 text-green-200',
}

function deriveRisk(predictedClass, confidence) {
  const label = String(predictedClass || '').toLowerCase()
  if (label.includes('positive') || confidence >= 0.7) return 'high'
  if (confidence >= 0.45) return 'medium'
  return 'low'
}

export default function DenguePage() {
  const { user } = useAuth()
  const [ns1, setNs1] = useState('')
  const [igg, setIgg] = useState('')
  const [igm, setIgm] = useState('')
  const [selectedSymptoms, setSelectedSymptoms] = useState([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const hasAnyValue = ns1 !== '' || igg !== '' || igm !== ''
  const parseOrNull = (value) => (value === '' ? null : parseInt(value, 10))

  const riskTier = useMemo(() => {
    if (!result) return null
    return deriveRisk(result.predicted_class, result.confidence || 0)
  }, [result])

  const toggleSymptom = (symptom) => {
    setSelectedSymptoms((prev) =>
      prev.includes(symptom) ? prev.filter((s) => s !== symptom) : [...prev, symptom]
    )
  }

  const runPrediction = async () => {
    if (!hasAnyValue) {
      toast.error('Select at least one lab value')
      return
    }

    setLoading(true)
    try {
      const res = await symptomsAPI.predictDengue({
        symptoms: selectedSymptoms,
        ns1_result: parseOrNull(ns1),
        igg_result: parseOrNull(igg),
        igm_result: parseOrNull(igm),
        age: user?.age || null,
        district: user?.district || null,
      })
      setResult(res.data?.prediction?.dengue_prediction || null)
      if (res.data?.context_saved === false) {
        toast.error('Prediction done, but context was not saved to database.')
      } else {
        window.dispatchEvent(new CustomEvent('nirovaai:analysis-updated', { detail: { type: 'dengue' } }))
      }
      toast.success('Dengue prediction ready')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Dengue prediction failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="animate-fade-in w-full">
      <div className="mb-8">
        <h1 className="section-title flex items-center gap-3">
          <FiTarget className="text-primary-400" />
          Dengue Detector
        </h1>
        <p className="text-slate-400">Dedicated dengue risk estimation from NS1/IgG/IgM with symptom-aware triage tips.</p>
      </div>

      <div className="grid xl:grid-cols-12 gap-6">
        <div className="xl:col-span-7 space-y-6">
          <div className="card">
            <h3 className="text-sm font-semibold text-slate-300 mb-2">Lab Inputs</h3>
            <p className="text-xs text-slate-500 mb-4">Use 1 for Positive, 0 for Negative. At least one value is required.</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">NS1</label>
                <select value={ns1} onChange={(e) => setNs1(e.target.value)} className="input-field">
                  <option value="">Unknown</option>
                  <option value="0">Negative</option>
                  <option value="1">Positive</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">IgG</label>
                <select value={igg} onChange={(e) => setIgg(e.target.value)} className="input-field">
                  <option value="">Unknown</option>
                  <option value="0">Negative</option>
                  <option value="1">Positive</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">IgM</label>
                <select value={igm} onChange={(e) => setIgm(e.target.value)} className="input-field">
                  <option value="">Unknown</option>
                  <option value="0">Negative</option>
                  <option value="1">Positive</option>
                </select>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="text-sm font-semibold text-slate-300 mb-2">Optional Symptom Signals</h3>
            <p className="text-xs text-slate-500 mb-4">Add current symptoms to enrich dengue context and AI history.</p>
            <div className="flex flex-wrap gap-2">
              {DENGUE_SYMPTOMS.map((symptom) => {
                const active = selectedSymptoms.includes(symptom)
                return (
                  <button
                    key={symptom}
                    type="button"
                    onClick={() => toggleSymptom(symptom)}
                    className={`px-3 py-1.5 rounded-lg text-xs transition-all ${
                      active
                        ? 'bg-primary-600 text-white border border-primary-400/40'
                        : 'bg-slate-700/70 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {symptom.replace(/_/g, ' ')}
                  </button>
                )
              })}
            </div>

            <button
              onClick={runPrediction}
              disabled={loading || !hasAnyValue}
              className="btn-primary w-full mt-5 flex items-center justify-center gap-2"
            >
              {loading ? <><FiLoader className="animate-spin" size={16} /> Running...</> : 'Run Dengue Prediction'}
            </button>
          </div>
        </div>

        <div className="xl:col-span-5 space-y-6">
          {!result && (
            <div className="card border border-slate-700/60 min-h-[230px] flex items-center justify-center">
              <div className="text-center">
                <FiTarget className="mx-auto text-slate-500 mb-2" size={24} />
                <p className="text-white text-sm font-medium">No dengue result yet</p>
                <p className="text-slate-500 text-xs mt-1">Run prediction to view risk tier and recommended actions.</p>
              </div>
            </div>
          )}

          {result && (
            <>
              <div className={`card border ${RISK_STYLES[riskTier] || RISK_STYLES.low}`}>
                <p className="text-xs uppercase tracking-wide opacity-80 mb-2">Dengue Risk</p>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-lg font-semibold">{result.predicted_class || 'Unknown'}</p>
                    <p className="text-xs opacity-80 mt-1">Model: {result.model || 'N/A'}</p>
                  </div>
                  <div className="text-2xl font-bold">{Math.round((result.confidence || 0) * 100)}%</div>
                </div>
              </div>

              <div className="card border border-primary-500/30">
                <h3 className="text-white font-semibold mb-2">Recommended Action</h3>
                <p className="text-slate-200 text-sm leading-relaxed">
                  {result.recommendation || 'Monitor closely and consult clinician if symptoms worsen.'}
                </p>
              </div>

              <div className="card border border-cyan-500/30">
                <h3 className="text-cyan-300 font-semibold mb-2 flex items-center gap-2">
                  <FiDroplet size={15} /> Hydration and Monitoring
                </h3>
                <ul className="text-slate-200 text-sm space-y-1">
                  <li>- Drink water or ORS frequently.</li>
                  <li>- Recheck fever every 6-8 hours.</li>
                  <li>- Use paracetamol for fever unless doctor advised otherwise.</li>
                </ul>
              </div>

              <div className="card border border-red-500/30">
                <h3 className="text-red-300 font-semibold mb-2 flex items-center gap-2">
                  <FiAlertTriangle size={15} /> Emergency Warning Signs
                </h3>
                <ul className="text-red-200 text-sm space-y-1">
                  <li>- Severe abdominal pain</li>
                  <li>- Bleeding from nose or gums</li>
                  <li>- Persistent vomiting</li>
                  <li>- Breathing difficulty or unusual drowsiness</li>
                </ul>
                <div className="mt-3 text-xs text-slate-400 flex items-center gap-2">
                  <FiMapPin size={12} /> Seek urgent in-person care if any warning sign appears.
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
