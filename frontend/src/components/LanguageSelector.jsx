import { useLanguage } from '../context/LanguageContext'
import { FiGlobe } from 'react-icons/fi'

export default function LanguageSelector() {
  const { language, setLanguage } = useLanguage()

  return (
    <div className="inline-flex items-center gap-1 bg-theme-soft border border-theme rounded-full p-1">
      <button
        onClick={() => setLanguage('en')}
        className={`px-3 py-1 rounded-full text-sm font-medium transition-all ${
          language === 'en'
            ? 'bg-primary-600 text-white'
            : 'text-theme hover:bg-theme-soft'
        }`}
      >
        EN
      </button>
      <button
        onClick={() => setLanguage('bn')}
        className={`px-3 py-1 rounded-full text-sm font-medium transition-all ${
          language === 'bn'
            ? 'bg-primary-600 text-white'
            : 'text-theme hover:bg-theme-soft'
        }`}
      >
        বাংলা
      </button>
    </div>
  )
}
