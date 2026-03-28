import { createContext, useContext, useState, useEffect } from 'react'

const LanguageContext = createContext(null)
const LANGUAGE_STORAGE_KEY = 'nirova_language'

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState('en')

  useEffect(() => {
    // Load saved language preference
    const saved = localStorage.getItem(LANGUAGE_STORAGE_KEY)
    if (saved === 'bn' || saved === 'en') {
      setLanguage(saved)
    }
  }, [])

  useEffect(() => {
    // Save language preference
    try {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
    } catch (err) {
      console.error('Failed to save language preference:', err)
    }
  }, [language])

  const toggleLanguage = () => {
    setLanguage(prev => prev === 'en' ? 'bn' : 'en')
  }

  const value = {
    language,
    isEnglish: language === 'en',
    isBengali: language === 'bn',
    setLanguage,
    toggleLanguage,
  }

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) {
    throw new Error('useLanguage must be inside LanguageProvider')
  }
  return ctx
}
