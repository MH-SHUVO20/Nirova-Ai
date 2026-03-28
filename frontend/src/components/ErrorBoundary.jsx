import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message || 'Unknown frontend error' }
  }

  componentDidCatch(error, info) {
    // Keep detailed trace in console for debugging.
    // eslint-disable-next-line no-console
    console.error('UI crash caught by ErrorBoundary:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center px-6">
          <div className="max-w-2xl w-full rounded-2xl border border-red-500/40 bg-red-500/10 p-6">
            <h1 className="text-xl font-semibold text-red-300 mb-2">Frontend crash detected</h1>
            <p className="text-slate-200 text-sm mb-3">
              A runtime error occurred. Please hard refresh the page (Ctrl+F5).
            </p>
            <p className="text-theme-muted text-xs break-all">
              Error: {this.state.message}
            </p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

