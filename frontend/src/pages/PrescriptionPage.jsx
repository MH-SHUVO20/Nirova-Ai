import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { visionAPI } from '../utils/api'
import toast from 'react-hot-toast'
import { FiUpload, FiClipboard, FiLoader, FiAlertTriangle, FiClock } from 'react-icons/fi'
import { motion, AnimatePresence } from 'framer-motion'

export default function PrescriptionPage() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const onDrop = useCallback((accepted) => {
    if (!accepted.length) return
    const selected = accepted[0]
    setFile(selected)
    setPreview(selected.type.startsWith('image/') ? URL.createObjectURL(selected) : null)
    setResult(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpg', '.jpeg', '.png', '.webp'],
      'application/pdf': ['.pdf'],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  })

  const analyze = async () => {
    if (!file) {
      toast.error('Please upload a prescription image or PDF first')
      return
    }

    setLoading(true)
    try {
      const res = await visionAPI.analyzePrescription(file)
      setResult(res.data)
      if (res.data?.context_saved === false) {
        toast.error('Analysis done, but context was not saved to database.')
      } else {
        window.dispatchEvent(new CustomEvent('nirovaai:analysis-updated', { detail: { type: 'prescription' } }))
      }
      toast.success('Prescription analysis complete')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Prescription analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
  }

  const meds = result?.analysis?.medications || []
  const schedule = result?.analysis?.daily_schedule || []
  const safetyFlags = result?.analysis?.safety_flags || []

  return (
    <div className="animate-fade-in w-full">
      <div className="mb-8">
        <h1 className="section-title flex items-center gap-3 mb-1">
          <FiClipboard className="text-primary-400" />
          Prescription Analyzer
        </h1>
        <p className="text-slate-400 text-sm">
          Upload a prescription image or PDF to extract medicine details, schedule hints, and safety reminders.
        </p>
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="card">
            <p className="text-white font-semibold mb-2">Step 1: Upload Prescription</p>
            <p className="text-slate-400 text-sm">Clear photos work best. PDFs are supported too.</p>

            <div
              {...getRootProps()}
              className={`mt-4 border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                isDragActive
                  ? 'border-primary-500 bg-primary-500/5'
                  : 'border-slate-600 hover:border-primary-500/50 hover:bg-slate-700/20'
              }`}
            >
              <input {...getInputProps()} />
              <FiUpload size={28} className="mx-auto text-slate-500 mb-2" />
              <p className="text-sm text-white">Drop file or click to upload</p>
              <p className="text-xs text-slate-500 mt-1">JPG, PNG, WEBP, PDF up to 10MB</p>
            </div>

            {preview && (
              <div className="mt-4">
                <img src={preview} alt="Prescription preview" className="w-full rounded-xl bg-slate-900 max-h-52 object-contain" />
                <p className="text-slate-400 text-xs mt-2 truncate">{file?.name}</p>
              </div>
            )}

            {file && !preview && (
              <div className="mt-4 rounded-xl border border-slate-600 bg-slate-900/60 p-4">
                <p className="text-slate-300 text-sm">Selected file</p>
                <p className="text-white text-sm font-medium mt-1 truncate">{file?.name}</p>
                <p className="text-slate-500 text-xs mt-1">PDF preview is not shown. Analysis still works.</p>
              </div>
            )}

            <div className="flex gap-2 mt-4">
              <button onClick={analyze} disabled={loading || !file} className="btn-primary flex-1">
                {loading ? (
                  <span className="inline-flex items-center gap-2"><FiLoader className="animate-spin" size={16} /> Analyzing...</span>
                ) : 'Analyze Prescription'}
              </button>
              <button onClick={reset} className="btn-outline" type="button">Reset</button>
            </div>
          </div>

          <div className="card">
            <p className="text-white font-semibold mb-2">Step 2: Verify Before Taking</p>
            <p className="text-slate-400 text-sm">Always confirm medicine names and doses with your doctor or pharmacist.</p>
          </div>
        </div>

        <div className="lg:col-span-3">
          <AnimatePresence>
            {!result && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="card h-full min-h-[340px] flex items-center justify-center"
              >
                <div className="text-center">
                  <FiClipboard size={34} className="mx-auto text-slate-500 mb-3" />
                  <p className="text-white font-medium">No analysis yet</p>
                  <p className="text-slate-500 text-sm mt-1">Upload and analyze a prescription to view structured output.</p>
                </div>
              </motion.div>
            )}

            {result && (
              <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                <div className="grid grid-cols-3 gap-3">
                  <div className="card text-center p-4">
                    <p className="text-slate-400 text-xs">Medicines Found</p>
                    <p className="text-white text-2xl font-bold">{meds.length}</p>
                  </div>
                  <div className="card text-center p-4 border border-red-500/30">
                    <p className="text-red-300 text-xs">Safety Flags</p>
                    <p className="text-red-300 text-2xl font-bold">{safetyFlags.length}</p>
                  </div>
                  <div className="card text-center p-4 border border-primary-500/30">
                    <p className="text-primary-300 text-xs">Clarity</p>
                    <p className="text-primary-300 text-2xl font-bold capitalize">{result?.analysis?.clarity_score || 'n/a'}</p>
                  </div>
                </div>

                <div className="card">
                  <h3 className="text-white font-semibold mb-3">Detected Medicines</h3>
                  {meds.length === 0 ? (
                    <p className="text-slate-400 text-sm">No medicine data could be extracted clearly.</p>
                  ) : (
                    <div className="space-y-2">
                      {meds.map((m, i) => (
                        <div key={`${m.name}-${i}`} className="rounded-xl border border-slate-600 bg-slate-900/50 p-3">
                          <p className="text-white font-medium text-sm">{m.name || 'unclear'}</p>
                          <p className="text-slate-300 text-xs mt-1">
                            {m.strength || 'unknown'} | {m.dose_instruction || 'instruction unclear'} | {m.frequency || 'frequency unclear'} | {m.duration || 'duration unclear'}
                          </p>
                          {m.purpose && <p className="text-slate-400 text-xs mt-1">Purpose: {m.purpose}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="card">
                  <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                    <FiClock className="text-primary-300" />
                    Suggested Daily Schedule
                  </h3>
                  {schedule.length === 0 ? (
                    <p className="text-slate-400 text-sm">No structured schedule could be extracted.</p>
                  ) : (
                    <div className="space-y-2">
                      {schedule.map((slot, i) => (
                        <div key={`${slot.time}-${i}`} className="rounded-xl border border-primary-500/30 bg-primary-500/10 p-3">
                          <p className="text-primary-200 text-sm font-semibold capitalize">{slot.time}</p>
                          <p className="text-slate-200 text-xs mt-1">{(slot.medicines || []).join(', ') || 'No medicine listed'}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="card border border-amber-500/30">
                  <h3 className="text-amber-300 font-semibold mb-2 flex items-center gap-2">
                    <FiAlertTriangle />
                    Safety Notes
                  </h3>
                  {safetyFlags.length === 0 ? (
                    <p className="text-slate-300 text-sm">No specific safety flags were detected.</p>
                  ) : (
                    <div className="space-y-1">
                      {safetyFlags.map((flag, i) => (
                        <p key={`${flag}-${i}`} className="text-amber-200 text-sm">- {flag}</p>
                      ))}
                    </div>
                  )}
                  {result?.analysis?.follow_up_advice && (
                    <p className="text-slate-300 text-sm mt-3">Follow-up: {result.analysis.follow_up_advice}</p>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
