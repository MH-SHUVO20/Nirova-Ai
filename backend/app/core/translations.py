"""
Multi-language translation service for NirovaAI - Bangladesh Edition
Supports: Bengali (বাংলা) as primary language with regional dialects
Optimized for Bangladesh healthcare context
"""
from typing import Dict, Optional, List
from enum import Enum
import json
from datetime import datetime
import logging

log = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported language variants in NirovaAI BD Edition"""
    ENGLISH = "en"
    BENGALI = "bn"
    CHITTAGONG = "cg"  # Regional dialect (চট্টগ্রাম)
    SYLHET = "sy"      # Regional dialect (সিলেট)
    KHULNA = "kh"      # Regional dialect (খুলনা)
    DHAKA = "dhk"      # Standard Dhaka dialect (ঢাকা)


# Medical terminology mappings (Bangla ↔ English)
MEDICAL_TERMS = {
    # Common symptoms
    "জ্বর": "fever",
    "মাথা ব্যথা": "headache",
    "গলা ব্যথা": "sore throat",
    "কাশি": "cough",
    "ঠান্ডা": "cold",
    "বমি": "vomiting",
    "পেট খারাপ": "stomach upset",
    "ডায়রিয়া": "diarrhea",
    "দুর্বলতা": "weakness",
    "শ্বাসকষ্ট": "difficulty breathing",
    
    # Diseases
    "ডেঙ্গু": "dengue fever",
    "ম্যালেরিয়া": "malaria",
    "টাইফয়েড": "typhoid",
    "করোনা": "COVID-19",
    "ফ্লু": "influenza",
    "চর্মরোগ": "skin disease",
    "চিকেনপক্স": "chickenpox",
    "হাম": "measles",
    "যক্ষ্মা": "tuberculosis",
    
    # Medical tests
    "রক্ত পরীক্ষা": "blood test",
    "ম্যালেরিয়া পরীক্ষা": "malaria test",
    "প্রস্রাব পরীক্ষা": "urine test",
    "এক্স-রে": "X-ray",
    "এলার্জি টেস্ট": "allergy test",
    "ডিএন এ পরীক্ষা": "COVID-19 test",
    "প্লেটিলেট কাউন্ট": "platelet count",
    
    # Actions
    "ডাক্তার দেখান": "see a doctor",
    "হাসপাতালে যান": "go to hospital",
    "ওষুধ খান": "take medicine",
    "বিশ্রাম নিন": "rest",
    "বেশি পানি পান": "drink more water",
    "খান্তি রাখুন": "stay calm",
    "জরুরী সেবা": "emergency service",
}

# Regional dialects (dialectal variations of Bangla)
REGIONAL_DIALECTS = {
    Language.CHITTAGONG: {  # চট্টগ্রাম
        "আছে": "আছে",
        "হবে": "হবো",
        "করবেন": "করবেন",
        "নেই": "নাই",
    },
    Language.SYLHET: {  # সিলেট
        "আছে": "আছে",
        "করবেন": "করমো",
        "না": "নো",
        "হবে": "হবো",
    },
    Language.KHULNA: {  # খুলনা
        "আছে": "আছে",
        "করবেন": "করবেন",
        "না": "না",
        "হবে": "হবে",
    }
}

# Safe emergency messages in multiple languages
EMERGENCY_MESSAGES = {
    Language.ENGLISH: {
        "title": "🚨 MEDICAL EMERGENCY",
        "call_now": "CALL 999 OR 112 IMMEDIATELY",
        "symptoms": "You may be experiencing a medical emergency. Immediate professional help is required.",
        "red_flags": "Critical symptoms detected:",
        "action": "Do not delay. Contact emergency services now.",
    },
    Language.BENGALI: {
        "title": "🚨 চিকিৎসা জরুরি অবস্থা",
        "call_now": "এক্ষুনি ৯৯৯ বা ১১২ এ কল করুন",
        "symptoms": "আপনি একটি জরুরি চিকিৎসা অবস্থার সম্মুখীন হতে পারেন। তাৎক্ষণিক পেশাদার সাহায্য প্রয়োজন।",
        "red_flags": "গুরুতর লক্ষণ সনাক্ত করা হয়েছে:",
        "action": "দেরি করবেন না। এখনই জরুরি সেবা যোগাযোগ করুন।",
    },
    Language.CHITTAGONG: {
        "title": "🚨 চিকিৎসা জরুরি",
        "call_now": "এক্ষুনি ৯৯৯ ডাকো",
        "symptoms": "খানা জরুরি অবস্হায় পড়তে পারো। এক্ষুনি ডাক্তারের কাছে যা লাগবো।",
        "red_flags": "গুরুতর চিনহ্নার ।",
        "action": "দেরি করিও না। এক্ষুনি কল কর।",
    }
}

# Culturally appropriate health guidance for Bangladesh
HEALTH_GUIDANCE = {
    Language.ENGLISH: {
        "hydration": "Drink ORS (oral rehydration solution) or water to stay hydrated",
        "rest": "Rest in a cool place, avoid direct sunlight",
        "doctor": "Visit a doctor or health center for proper diagnosis",
        "dengue_prevention": "Use mosquito net, cover arms and legs, use insect repellent",
        "tropical_disease": "This could be a tropical disease common in Bangladesh",
        "when_to_worry": "Seek immediate care if fever persists >3 days",
    },
    Language.BENGALI: {
        "hydration": "ওআরএস (মৌখিক পুনর্জলীকরণ দ্রবণ) বা জল পান",
        "rest": "ঠান্ডা জায়গায় বিশ্রাম নিন, সরাসরি রোদ এড়ান",
        "doctor": "সঠিক রোগ নির্ণয়ের জন্য একজন ডাক্তার বা স্বাস্থ্য কেন্দ্রে যান",
        "dengue_prevention": "মশারি ব্যবহার করুন, বাহু এবং পা ঢাকুন, কীটনাশক ব্যবহার করুন",
        "tropical_disease": "এটি বাংলাদেশে সাধারণ একটি গ্রীষ্মমণ্ডলীয় রোগ হতে পারে",
        "when_to_worry": "জ্বর ৩ দিনের বেশি স্থায়ী হলে অবিলম্বে চিকিৎসকের পরামর্শ নিন",
    },
    Language.CHITTAGONG: {
        "hydration": "ওআরএস বা পানি খা",
        "rest": "ঠান্ডায় বিশ্রাম লে, রোদ এড়া",
        "doctor": "ডাক্তারের কাছে যা",
        "dengue_prevention": "মশারি লাগা, শার্ট পরা",
        "tropical_disease": "এহানো বাংলাদেশের জ্বরের মতো হতে পারে",
        "when_to_worry": "জ্বর ৩ দিনের বেশি হলে ডাক্তার ডাকা",
    }
}


class TranslationService:
    """Core translation service for NirovaAI"""
    
    def __init__(self):
        self.medical_terms = MEDICAL_TERMS
        self.guidance = HEALTH_GUIDANCE
        self.emergency_messages = EMERGENCY_MESSAGES
        self.dialects = REGIONAL_DIALECTS
    
    def translate_medical_term(
        self, 
        term: str, 
        from_lang: Language = Language.ENGLISH,
        to_lang: Language = Language.BENGALI
    ) -> str:
        """
        Translate medical terms between languages
        
        Args:
            term: The medical term to translate
            from_lang: Source language (default: English)
            to_lang: Target language (default: Bengali)
        
        Returns:
            Translated term or original if not found
        """
        term_lower = term.lower().strip()
        
        # Forward translation (English → Bengali)
        if from_lang == Language.ENGLISH and to_lang == Language.BENGALI:
            for bangla, english in self.medical_terms.items():
                if english.lower() == term_lower:
                    return bangla
        
        # Reverse translation (Bengali → English)
        if from_lang == Language.BENGALI and to_lang == Language.ENGLISH:
            return self.medical_terms.get(term, term)
        
        # Same language translation
        if from_lang == to_lang:
            return term
        
        # Not found, return original
        log.warning(f"Translation not found for: {term} ({from_lang} → {to_lang})")
        return term
    
    def get_health_guidance(
        self,
        guidance_key: str,
        language: Language = Language.ENGLISH
    ) -> str:
        """
        Get culturally appropriate health guidance for condition/action
        
        Args:
            guidance_key: Key for guidance (hydration, rest, doctor, etc.)
            language: Target language
        
        Returns:
            Localized health guidance
        """
        if language not in self.guidance:
            language = Language.ENGLISH
        
        return self.guidance[language].get(
            guidance_key,
            self.guidance[Language.ENGLISH].get(guidance_key, "")
        )
    
    def get_emergency_message(self, language: Language = Language.ENGLISH) -> Dict[str, str]:
        """
        Get emergency messaging in specified language
        
        Args:
            language: Target language
        
        Returns:
            Dictionary with emergency messaging
        """
        if language not in self.emergency_messages:
            language = Language.ENGLISH
        
        return self.emergency_messages[language].copy()
    
    def translate_response(
        self,
        response_text: str,
        from_lang: Language = Language.ENGLISH,
        to_lang: Language = Language.BENGALI,
        preserve_formatting: bool = True
    ) -> str:
        """
        Translate AI response text (basic term replacement with context preservation)
        
        Args:
            response_text: The response to translate
            from_lang: Source language
            to_lang: Target language
            preserve_formatting: Keep formatting (emojis, newlines, etc.)
        
        Returns:
            Translated response
        """
        if from_lang == to_lang:
            return response_text
        
        translated = response_text
        
        # Translate known medical terms while preserving case and context
        for term, translation in self.medical_terms.items():
            if from_lang == Language.ENGLISH and to_lang in [Language.BENGALI, Language.CHITTAGONG, Language.SYLHET]:
                # Case-insensitive replacement
                import re
                pattern = re.compile(re.escape(translation), re.IGNORECASE)
                translated = pattern.sub(term, translated)
        
        return translated
    
    def apply_dialect(
        self,
        text: str,
        dialect: Language = Language.BENGALI
    ) -> str:
        """
        Apply regional dialect variations to Bengali text
        
        Args:
            text: Bengali text to convert
            dialect: Target dialect
        
        Returns:
            Text with dialect applied
        """
        if dialect not in self.dialects:
            return text
        
        dialect_map = self.dialects[dialect]
        result = text
        
        for standard, dialectal in dialect_map.items():
            result = result.replace(standard, dialectal)
        
        return result
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages"""
        return [
            {"code": "en", "name": "English", "native_name": "English"},
            {"code": "bn", "name": "Bengali", "native_name": "বাংলা"},
            {"code": "cg", "name": "Chittagong Dialect", "native_name": "চট্টগ্রাম"},
            {"code": "sy", "name": "Sylhet Dialect", "native_name": "সিলেট"},
            {"code": "kh", "name": "Khulna Dialect", "native_name": "খুলনা"},
        ]
    
    def get_language_by_code(self, code: str) -> Optional[Language]:
        """Get Language enum by code string"""
        try:
            return Language(code)
        except ValueError:
            log.warning(f"Unknown language code: {code}")
            return Language.ENGLISH


# Singleton instance
translation_service = TranslationService()


async def get_translation_service() -> TranslationService:
    """FastAPI dependency for translation service"""
    return translation_service
