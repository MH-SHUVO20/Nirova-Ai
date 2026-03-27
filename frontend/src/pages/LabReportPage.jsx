import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { visionAPI } from '../utils/api'
import toast from 'react-hot-toast'
import { FiUpload, FiFileText, FiLoader, FiCheckCircle, FiAlertCircle } from 'react-icons/fi'
import { motion, AnimatePresence } from 'framer-motion'

export default function LabReportPage() {
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
      toast.error('Please upload a lab report image or PDF first')
      return
    }

    setLoading(true)
    try {
      const res = await visionAPI.analyzeLab(file)
      setResult(res.data)
      if (res.data?.context_saved === false) {
        toast.error('Analysis done, but context was not saved to database.')
      } else {
        window.dispatchEvent(new CustomEvent('nirovaai:analysis-updated', { detail: { type: 'lab' } }))
      }
      toast.success('Lab analysis complete')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Lab analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
  }

  const tests = result?.analysis?.tests || []
  const abnormalTests = tests.filter((t) => t.status !== 'normal')
  const normalTests = tests.filter((t) => t.status === 'normal')

  return (
    <div className="animate-fade-in w-full">
      <div className="mb-8">
        <h1 className="section-title flex items-center gap-3 mb-1">
          <FiFileText className="text-primary-400" />
          Lab Report Analyzer
        </h1>
        <p className="text-slate-400 text-sm">
          Upload your report image or PDF and get a simple test-by-test explanation with clear next steps.
        </p>
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="card">
            <p className="text-white font-semibold mb-2">Step 1: Upload Report</p>
            <p className="text-slate-400 text-sm">Use a clear image or PDF of your lab report.</p>
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
                <img src={preview} alt="Lab report preview" className="w-full rounded-xl bg-slate-900 max-h-52 object-contain" />
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
                ) : 'Analyze Report'}
              </button>
              <button onClick={reset} className="btn-outline" type="button">Reset</button>
            </div>
          </div>

          <div className="card">
            <p className="text-white font-semibold mb-2">Step 2: Read Highlights</p>
            <p className="text-slate-400 text-sm">Abnormal values are grouped first so you can focus quickly.</p>
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
                  <FiFileText size={34} className="mx-auto text-slate-500 mb-3" />
                  <p className="text-white font-medium">No analysis yet</p>
                  <p className="text-slate-500 text-sm mt-1">Upload and analyze a report to view structured results.</p>
                </div>
              </motion.div>
            )}

            {result && (
              <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                <div className="grid grid-cols-3 gap-3">
                  <div className="card text-center p-4">
                    <p className="text-slate-400 text-xs">Total Tests</p>
                    <p className="text-white text-2xl font-bold">{tests.length}</p>
                  </div>
                  <div className="card text-center p-4 border border-amber-500/30">
                    <p className="text-amber-300 text-xs">Need Attention</p>
                    <p className="text-amber-300 text-2xl font-bold">{abnormalTests.length}</p>
                  </div>
                  <div className="card text-center p-4 border border-green-500/30">
                    <p className="text-green-300 text-xs">Within Range</p>
                    <p className="text-green-300 text-2xl font-bold">{normalTests.length}</p>
                  </div>
                </div>

                {abnormalTests.length > 0 && (
                  <div className="card">
                    <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                      <FiAlertCircle className="text-amber-300" />
                      Tests Requiring Follow-up
                    </h3>
                    <div className="space-y-2">
                      {abnormalTests.map((test, i) => (
                        <div key={`${test.name}-${i}`} className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3">
                          <div className="flex items-center justify-between gap-4">
                            <p className="text-white font-medium text-sm">{test.name}</p>
                            <p className="text-amber-300 font-mono text-sm">{test.value} {test.unit}</p>
                          </div>
                          {test.simple_explanation && (
                            <p className="text-amber-100/80 text-xs mt-1">{test.simple_explanation}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {normalTests.length > 0 && (
                  <div className="card">
                    <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                      <FiCheckCircle className="text-green-300" />
                      Tests Within Expected Range
                    </h3>
                    <div className="space-y-2">
                      {normalTests.map((test, i) => (
                        <div key={`${test.name}-${i}`} className="rounded-xl border border-green-500/30 bg-green-500/10 p-3">
                          <div className="flex items-center justify-between gap-4">
                            <p className="text-white font-medium text-sm">{test.name}</p>
                            <p className="text-green-300 font-mono text-sm">{test.value} {test.unit}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {result?.analysis?.key_findings && (
                  <div className="card border border-primary-500/30">
                    <h3 className="text-white font-semibold mb-2">Summary</h3>
                    <p className="text-slate-300 text-sm leading-relaxed">{result.analysis.key_findings}</p>
                    <p className="text-slate-500 text-xs mt-2">Processed source: {result.source_type || 'unknown'}</p>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
