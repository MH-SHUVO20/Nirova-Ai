import { useEffect, useState } from 'react'
import { FiPhoneCall, FiMapPin } from 'react-icons/fi'
import { extractErrorMessage, symptomsAPI } from '../utils/api'
import toast from 'react-hot-toast'
import { FiPlus, FiX, FiLoader, FiAlertTriangle, FiCheckCircle, FiActivity } from 'react-icons/fi'
import { motion, AnimatePresence } from 'framer-motion'

// Common Bangladesh-relevant symptoms
const COMMON_SYMPTOMS = [
  'high_fever','mild_fever','headache','joint_pain','muscle_pain',
  'vomiting','nausea','fatigue','cough','breathlessness',
  'abdominal_pain','diarrhoea','loss_of_appetite','weakness',
  'chills','shivering','sweating','skin_rash','itching',
  'chest_pain','back_pain','dizziness','weight_loss',
  'pain_behind_the_eyes','red_spots_over_body',
]

const TRIAGE_CONFIG = {
  red:    { bg: 'bg-red-500/10',    border: 'border-red-500/30',    text: 'text-red-300',    icon: FiAlertTriangle, label: 'High Risk' },
  yellow: { bg: 'bg-amber-500/10',  border: 'border-amber-500/30',  text: 'text-amber-300',  icon: FiAlertTriangle, label: 'Medium Risk' },
  green:  { bg: 'bg-green-500/10',  border: 'border-green-500/30',  text: 'text-green-300',  icon: FiCheckCircle,   label: 'Low Risk' },
}

export default function SymptomsPage() {
  const [selected, setSelected]   = useState([])
  const [custom, setCustom]       = useState('')
  const [severity, setSeverity]   = useState(5)
  const [notes, setNotes]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [result, setResult]       = useState(null)
  const [excludedDiseases, setExcludedDiseases] = useState([])
  const [excludeInput, setExcludeInput] = useState('')

  useEffect(() => {
    symptomsAPI.getExcludedDiseases()
      .then((res) => {
        const items = res?.data?.excluded_diseases
        setExcludedDiseases(Array.isArray(items) ? items : [])
      })
      .catch(() => {
        setExcludedDiseases([])
      })
  }, [])

  const addSymptom = (symptom) => {
    const clean = symptom.toLowerCase().replace(/\s+/g, '_')
    if (!selected.includes(clean)) setSelected([...selected, clean])
  }

  const removeSymptom = (s) => setSelected(selected.filter(x => x !== s))

  const addCustom = () => {
    if (custom.trim()) {
      addSymptom(custom.trim())
      setCustom('')
    }
  }

  const handleSubmit = async () => {
    if (selected.length === 0) {
      toast.error('Please add at least one symptom')
      return
    }
    setLoading(true)
    try {
      const res = await symptomsAPI.log({ symptoms: selected, severity, notes })
      setResult(res.data)
      const p = res.data?.prediction || {}
      const summary = [
        p.predicted_disease ? `disease=${p.predicted_disease}` : '',
        typeof p.confidence === 'number' ? `confidence=${Math.round(p.confidence * 100)}%` : '',
        p.triage_color ? `triage=${p.triage_color}` : '',
        selected.length ? `symptoms=${selected.slice(0, 5).join(',')}` : '',
      ].filter(Boolean).join(', ')
      window.dispatchEvent(new CustomEvent('nirovaai:analysis-updated', { detail: { type: 'symptoms', summary } }))
      if (res.data?.context_saved === false) {
        toast.error('Symptoms analyzed, but context was not saved to database.')
      }
      toast.success('Symptoms logged!')
    } catch (err) {
      const message = extractErrorMessage(err)
      toast.error(message || 'Failed to log symptoms')
    } finally {
      setLoading(false)
    }
  }

  const addExcludedDisease = async () => {
    const value = excludeInput.trim()
    if (!value) return
    try {
      const res = await symptomsAPI.addExcludedDisease(value)
      const items = res?.data?.excluded_diseases
      setExcludedDiseases(Array.isArray(items) ? items : excludedDiseases)
      setExcludeInput('')
      toast.success('Disease removed from prediction list')
    } catch (err) {
      toast.error(extractErrorMessage(err) || 'Failed to update removed diseases')
    }
  }

  const removeExcludedDisease = async (disease) => {
    try {
      const res = await symptomsAPI.removeExcludedDisease(disease)
      const items = res?.data?.excluded_diseases
      setExcludedDiseases(Array.isArray(items) ? items : excludedDiseases.filter((d) => d !== disease))
      toast.success('Disease added back to predictions')
    } catch (err) {
      toast.error(extractErrorMessage(err) || 'Failed to restore disease')
    }
  }

  const triage = result?.prediction?.triage_color || 'green'
  const cfg = TRIAGE_CONFIG[triage] || TRIAGE_CONFIG.green

  const emergencyDrugs = result?.prediction?.emergency_drug_suggestions || []
  const isEmergency = triage === 'red'

  return (
    <div className="animate-fade-in w-full">
      {/* Urgent emergency banner */}
      {isEmergency && (
        <div className="card border border-red-500/60 bg-red-500/10 mb-6 animate-pulse">
          <div className="flex items-center gap-3 mb-2">
            <FiAlertTriangle className="text-red-400" size={22} />
            <span className="font-bold text-red-300 text-lg">Possible Medical Emergency</span>
          </div>
          <p className="text-slate-200 text-sm mb-2">Your symptoms may indicate a serious condition. Please seek emergency care immediately.</p>
          <div className="flex flex-wrap gap-2 mb-2">
            <a href="tel:999" className="btn-outline text-xs flex items-center gap-1"><FiPhoneCall /> Call 999</a>
            <a href="tel:16263" className="btn-outline text-xs flex items-center gap-1"><FiPhoneCall /> Health Helpline</a>
            <a href="https://goo.gl/maps/6Qw6v8v8v8v8v8v8A" target="_blank" rel="noopener noreferrer" className="btn-outline text-xs flex items-center gap-1"><FiMapPin /> Nearest Hospital</a>
          </div>
          {emergencyDrugs.length > 0 && (
            <div className="mt-2">
              <h4 className="text-red-300 font-semibold text-sm mb-1">Emergency Medicine Advice</h4>
              <ul className="list-disc ml-5 text-slate-200 text-xs">
                {emergencyDrugs.map((d, i) => (
                  <li key={i}><span className="font-bold">{d.name}:</span> {d.dose ? d.dose + '. ' : ''}{d.note}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      <div className="mb-8">
        <h1 className="section-title flex items-center gap-3">
          <FiActivity className="text-primary-400" />
          Log Today's Symptoms
        </h1>
        <p className="text-theme-muted">Select your symptoms to generate a risk-oriented clinical guidance summary.</p>
      </div>

      {/* Common symptoms grid */}
      <div className="card mb-5">
        <h3 className="text-sm font-semibold text-theme mb-3">Common symptoms (select as applicable)</h3>
        <div className="flex flex-wrap gap-2">
          {COMMON_SYMPTOMS.map(s => (
            <button key={s} onClick={() => addSymptom(s)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                selected.includes(s)
                  ? 'bg-primary-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}>
              {s.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Custom symptom input */}
      <div className="card mb-5">
        <h3 className="text-sm font-semibold text-theme mb-3">Add another symptom</h3>
        <div className="flex gap-2">
          <input
            value={custom}
            onChange={e => setCustom(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addCustom()}
            placeholder="e.g. neck stiffness, runny nose..."
            className="input-field flex-1"
          />
          <button onClick={addCustom} className="btn-primary px-4">
            <FiPlus size={18} />
          </button>
        </div>
      </div>

      {/* Selected symptoms */}
      {selected.length > 0 && (
        <div className="card mb-5">
          <h3 className="text-sm font-semibold text-theme mb-3">
            Selected Symptoms ({selected.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            <AnimatePresence>
              {selected.map(s => (
                <motion.div
                  key={s}
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  className="flex items-center gap-1.5 bg-primary-500/20 text-primary-300 border border-primary-500/30 px-3 py-1.5 rounded-full text-sm"
                >
                  {s.replace(/_/g, ' ')}
                  <button onClick={() => removeSymptom(s)}
                    className="text-primary-400 hover:text-white ml-1">
                    <FiX size={12} />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {/* Severity slider */}
      <div className="card mb-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-theme">Overall Severity</h3>
          <span className={`font-mono font-bold text-lg ${
            severity >= 8 ? 'text-red-400' : severity >= 5 ? 'text-amber-400' : 'text-green-400'
          }`}>{severity}/10</span>
        </div>
        <input type="range" min="1" max="10" value={severity}
          onChange={e => setSeverity(parseInt(e.target.value))}
          className="w-full accent-primary-500 cursor-pointer"
        />
        <div className="flex justify-between text-xs text-theme-muted mt-1">
          <span>Mild</span><span>Moderate</span><span>Severe</span>
        </div>
      </div>

      {/* Notes */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold text-theme mb-3">Additional Notes (optional)</h3>
        <textarea value={notes} onChange={e => setNotes(e.target.value)}
          placeholder="Any other observations..."
          rows={3}
          className="input-field resize-none"
        />
      </div>

      {/* Removed diseases preferences */}
      <div className="card mb-6">
        <h3 className="text-sm font-semibold text-theme mb-3">Remove Diseases From Prediction List</h3>
        <p className="text-theme-muted text-xs mb-3">Diseases added here will be excluded from symptom prediction results.</p>
        <div className="flex gap-2 mb-3">
          <input
            value={excludeInput}
            onChange={(e) => setExcludeInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addExcludedDisease()}
            placeholder="e.g. common cold"
            className="input-field flex-1"
          />
          <button onClick={addExcludedDisease} className="btn-primary px-4">Remove</button>
        </div>
        {excludedDiseases.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {excludedDiseases.map((disease) => (
              <span key={disease} className="flex items-center gap-1.5 bg-slate-700 text-slate-200 px-3 py-1.5 rounded-full text-sm">
                {disease}
                <button onClick={() => removeExcludedDisease(disease)} className="text-slate-300 hover:text-white" title="Add back to predictions">
                  <FiX size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Submit button */}
      <button onClick={handleSubmit} disabled={loading || selected.length === 0}
        className="btn-primary w-full flex items-center justify-center gap-2 text-base py-4 mb-8">
        {loading ? (
          <><FiLoader className="animate-spin" size={18} /> Running AI assessment...</>
        ) : (
          'Submit Symptoms and View Assessment'
        )}
      </button>

      {/* Result */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`card border ${cfg.bg} ${cfg.border}`}
          >
            <div className="flex items-center gap-3 mb-4">
              <cfg.icon className={cfg.text} size={22} />
              <div>
                <span className={`font-semibold ${cfg.text}`}>{cfg.label}</span>
                
              </div>
            </div>

            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="text-theme-muted text-sm mb-1">Predicted Condition</p>
                <p className="font-display text-2xl font-bold text-white">
                  {result.prediction?.predicted_disease}
                </p>
              </div>
              <div className={`font-display text-3xl font-bold ${cfg.text}`}>
                {Math.round((result.prediction?.confidence || 0) * 100)}%
              </div>
            </div>

            <div className={`p-3 rounded-xl ${cfg.bg} border ${cfg.border} mb-4`}>
              <p className={`text-sm font-medium ${cfg.text}`}>
                ⚡ {result.prediction?.recommended_action}
              </p>
            </div>

            {/* Top 3 */}
            {result.prediction?.top3_predictions?.length > 0 && (
              <div>
                <p className="text-theme-muted text-xs mb-2">Other possibilities</p>
                <div className="space-y-2">
                  {result.prediction.top3_predictions.slice(1).map((p, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="text-slate-300 text-sm">{p.disease}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                          <div className="h-full bg-primary-500 rounded-full"
                            style={{ width: `${p.probability * 100}%` }} />
                        </div>
                        <span className="text-slate-400 text-xs font-mono w-10 text-right">
                          {Math.round(p.probability * 100)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <p className="text-theme-muted text-xs mt-4 italic">
              Disclaimer: এই সেবা কেবল তথ্যগত সহায়তা দেয়; এটি নিবন্ধিত চিকিৎসকের পরামর্শ, রোগ নির্ণয় বা চিকিৎসার বিকল্প নয়।
            </p>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}

