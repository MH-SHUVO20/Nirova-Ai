import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { visionAPI } from '../utils/api'
import toast from 'react-hot-toast'
import { FiUpload, FiCamera, FiLoader } from 'react-icons/fi'
import { motion, AnimatePresence } from 'framer-motion'

export default function SkinPage() {
  const [file, setFile]         = useState(null)
  const [preview, setPreview]   = useState(null)
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState(null)

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      setFile(accepted[0])
      setPreview(URL.createObjectURL(accepted[0]))
      setResult(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    maxSize: 10 * 1024 * 1024,
    multiple: false
  })

  const analyze = async () => {
    if (!file) { toast.error('Please upload an image first'); return }
    setLoading(true)
    try {
      const res = await visionAPI.analyzeSkin(file)
      setResult(res.data)
      const a = res.data?.analysis || {}
      const summary = [
        a.condition ? `condition=${a.condition}` : '',
        a.severity ? `severity=${a.severity}` : '',
        a.confidence ? `confidence=${a.confidence}` : '',
        a.recommended_action ? `action=${a.recommended_action}` : '',
      ].filter(Boolean).join(', ')
      window.dispatchEvent(new CustomEvent('nirovaai:analysis-updated', { detail: { type: 'skin', summary } }))
      if (res.data?.context_saved === false) {
        toast.error('Analysis done, but context was not saved to database.')
      }
      toast.success('Analysis complete!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => { setFile(null); setPreview(null); setResult(null) }

  const severityColor = (sev) => {
    if (!sev) return 'text-slate-300'
    if (sev.includes('severe') || sev.includes('urgent')) return 'text-red-400'
    if (sev.includes('moderate')) return 'text-amber-400'
    return 'text-green-400'
  }

  const actionColor = (action) => {
    if (!action) return 'border-slate-500/30 bg-slate-500/10 text-slate-300'
    if (action.includes('urgent')) return 'border-red-500/30 bg-red-500/10 text-red-300'
    if (action.includes('see_doctor') || action.includes('see doctor')) return 'border-amber-500/30 bg-amber-500/10 text-amber-300'
    return 'border-green-500/30 bg-green-500/10 text-green-300'
  }

  return (
    <div className="animate-fade-in w-full">
      <div className="mb-8">
        <h1 className="section-title flex items-center gap-3">
          <FiCamera className="text-primary-400" />
          Skin Condition Analyzer
        </h1>
        <p className="text-theme-muted">Upload a clear skin photo for AI-assisted condition analysis and guidance.</p>
      </div>

      {/* Drop zone */}
      {!preview ? (
        <div {...getRootProps()}
          className={`card border-2 border-dashed cursor-pointer transition-all text-center py-16 ${
            isDragActive
              ? 'border-primary-500 bg-primary-500/5'
              : 'border-slate-600 hover:border-primary-500/50 hover:bg-slate-700/30'
          }`}>
          <input {...getInputProps()} />
          <FiUpload size={40} className="text-theme-muted mx-auto mb-4" />
          <p className="text-white font-medium mb-1">
            {isDragActive ? 'Release to upload' : 'Drop a file here or click to upload'}
          </p>
          <p className="text-theme-muted text-sm">
            JPG, PNG, WEBP up to 10MB
          </p>
          <p className="text-theme-muted text-xs mt-2">Use a clear, well-lit close-up image for best results.</p>
        </div>
      ) : (
        <div className="card mb-4">
          <div className="relative">
            <img src={preview} alt="Uploaded"
              className="w-full max-h-64 object-contain rounded-xl bg-theme-soft" />
            <button onClick={reset}
              className="absolute top-2 right-2 bg-theme-soft/80 hover:bg-red-500/80 text-white w-8 h-8 rounded-full flex items-center justify-center transition-all">
              ✕
            </button>
          </div>
          <p className="text-theme-muted text-sm mt-3 text-center">{file?.name}</p>
        </div>
      )}

      {preview && !result && (
        <button onClick={analyze} disabled={loading}
          className="btn-primary w-full flex items-center justify-center gap-2 py-4 mt-4">
          {loading ? (
            <><FiLoader className="animate-spin" size={18} /> Processing image...</>
          ) : 'Analyze Skin Condition'}
        </button>
      )}

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 space-y-4"
          >
            {result.analysis && (
              <div className="card">
                <h3 className="font-display text-lg font-bold text-white mb-4">
                  Skin Analysis Result
                </h3>

                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-theme-muted text-sm mb-1">Identified Condition</p>
                    <p className="font-display text-2xl font-bold text-white">
                      {result.analysis.condition}
                    </p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${
                    result.analysis.confidence === 'high'
                      ? 'bg-green-500/20 text-green-300'
                      : result.analysis.confidence === 'medium'
                        ? 'bg-amber-500/20 text-amber-300'
                        : 'bg-slate-500/20 text-slate-300'
                  }`}>
                    {result.analysis.confidence} confidence
                  </span>
                </div>

                {result.analysis.severity && (
                  <div className={`p-3 rounded-xl border mb-4 ${actionColor(result.analysis.severity)}`}>
                    <p className="text-sm font-medium">
                      🔍 Severity: {result.analysis.severity}
                    </p>
                  </div>
                )}

                {result.analysis.description && (
                  <p className="text-theme text-sm leading-relaxed mb-4">
                    {result.analysis.description}
                  </p>
                )}

                {result.analysis.recommended_action && (
                  <div className={`p-3 rounded-xl border ${actionColor(result.analysis.recommended_action)}`}>
                    <p className="text-sm font-semibold">
                      ⚡ Action: {result.analysis.recommended_action?.replace(/_/g, ' ')}
                    </p>
                    {result.analysis.home_care && (
                      <p className="text-xs mt-1 opacity-80">{result.analysis.home_care}</p>
                    )}
                  </div>
                )}

                <p className="text-theme-muted text-xs mt-4 italic">`r`n                  Disclaimer: This analysis is informational and not a medical diagnosis.`r`n                </p>
              </div>
            )}

            <button onClick={reset} className="btn-outline w-full text-sm">
              Analyze Another Image
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

