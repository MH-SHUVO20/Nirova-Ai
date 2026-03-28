"""
Language detection and preference management for NirovaAI - Bangladesh Edition
Detects user language from headers, parameters, and user preferences
Optimized for Bangladesh with Bangla as primary language
"""
from typing import Optional
import logging
from enum import Enum
from textblob import TextBlob
import re

log = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported language variants for Bangladesh"""
    ENGLISH = "en"
    BENGALI = "bn"
    CHITTAGONG = "cg"
    SYLHET = "sy"
    KHULNA = "kh"
    DHAKA = "dhk"


# Common Bengali words for detection
BENGALI_KEYWORDS = {
    "আমার": "my",
    "আপনি": "you",
    "কি": "what",
    "কেন": "why",
    "কখন": "when",
    "যে": "that",
    "এটি": "this",
    "করতে": "to do",
    "চাই": "want",
    "আছে": "have",
    "নেই": "don't have",
    "ব্যথা": "pain",
    "জ্বর": "fever",
    "কাশি": "cough",
    "বমি": "vomit",
    "ডেঙ্গু": "dengue",
    "ডাক্তার": "doctor",
    "ওষুধ": "medicine",
    "হাসপাতাল": "hospital",
    "সাহায্য": "help",
    "ধন্যবাদ": "thank you",
}

# Regional dialect markers
DIALECT_MARKERS = {
    Language.CHITTAGONG: {
        "এর": "র",  # Chittagong uses "র" instead of "এর"
        "করবেন": "করবেন",
        "হবে": "হবো",
        "আছে": "আছে",
    },
    Language.SYLHET: {
        "করবেন": "করমো",
        "নেই": "নো",
        "হবে": "হবো",
    },
    Language.KHULNA: {
        "হ্য": "ই",  # Khulna uses different pronunciation
    }
}


class LanguageDetector:
    """Detect user language from various sources"""
    
    def __init__(self):
        self.bengali_keywords = BENGALI_KEYWORDS
        self.dialect_markers = DIALECT_MARKERS
    
    def detect_from_text(self, text: str) -> Optional[Language]:
        """
        Detect language from text content using keyword matching and patterns
        
        Args:
            text: Text to analyze
        
        Returns:
            Detected language or None
        """
        if not text or len(text) < 5:
            return None
        
        text_lower = text.lower()
        
        # Count Bengali unicode range characters (Bengali script: U+0980 to U+09FF)
        bengali_char_count = sum(1 for char in text if '\u0980' <= char <= '\u09FF')
        total_chars = len(text)
        
        # If >30% Bengali characters, detect as Bengali family language
        if bengali_char_count / total_chars > 0.3:
            dialect = self._detect_dialect(text)
            return dialect if dialect else Language.BENGALI
        
        # Check for Bengali keywords
        keyword_matches = sum(1 for keyword in self.bengali_keywords.keys() if keyword in text)
        if keyword_matches > 2:
            dialect = self._detect_dialect(text)
            return dialect if dialect else Language.BENGALI
        
        # Default to English if no Bengali detected
        return Language.ENGLISH
    
    def _detect_dialect(self, text: str) -> Optional[Language]:
        """
        Detect regional Bengali dialect
        
        Args:
            text: Bengali text to analyze
        
        Returns:
            Detected dialect or None
        """
        # Chittagong dialect markers
        if re.search(r'(হবো|করবেন|র\s)', text):
            return Language.CHITTAGONG
        
        # Sylhet dialect markers
        if re.search(r'(করমো|নো|হবো)', text):
            return Language.SYLHET
        
        # Khulna dialect markers
        if re.search(r'(ই\s|ইত)', text):
            return Language.KHULNA
        
        return None
    
    def detect_from_headers(self, accept_language: Optional[str] = None) -> Optional[Language]:
        """
        Detect language from Accept-Language HTTP header
        
        Args:
            accept_language: Accept-Language header value
        
        Returns:
            Detected language or None
        """
        if not accept_language:
            return None
        
        # Parse Accept-Language header (e.g., "bn-BD,bn;q=0.9,en;q=0.8")
        langs = [lang.split(';')[0].strip().lower() for lang in accept_language.split(',')]
        
        for lang in langs:
            # Check for Bengali variants
            if lang.startswith('bn'):
                # Try to detect specific dialect from region
                if 'bd' in lang or 'bd' in accept_language.lower():  # Bangladesh
                    return Language.BENGALI
            
            # Check for English
            if lang.startswith('en'):
                return Language.ENGLISH
        
        return None
    
    def detect_from_timezone(self, timezone: Optional[str] = None) -> Optional[Language]:
        """
        Suggest language based on timezone (useful for regional deployment)
        
        Args:
            timezone: User's timezone
        
        Returns:
            Suggested language
        """
        if not timezone:
            return None
        
        bangladesh_timezones = ['Asia/Dhaka', 'UTC+6', 'Bangladesh Standard Time']
        if any(tz in timezone for tz in bangladesh_timezones):
            return Language.BENGALI
        
        return Language.ENGLISH
    
    def detect_from_ip_geolocation(self, country_code: Optional[str] = None) -> Optional[Language]:
        """
        Suggest language based on country code
        
        Args:
            country_code: ISO country code (e.g., 'BD' for Bangladesh)
        
        Returns:
            Suggested language
        """
        if not country_code:
            return None
        
        if country_code.upper() == 'BD':  # Bangladesh
            return Language.BENGALI
        
        return Language.ENGLISH
    
    def detect_language(
        self,
        text: Optional[str] = None,
        accept_language: Optional[str] = None,
        timezone: Optional[str] = None,
        country_code: Optional[str] = None,
        user_preference: Optional[str] = None,
        default_language: Language = Language.ENGLISH
    ) -> Language:
        """
        Comprehensive language detection from multiple sources
        Priority: user_preference > text > headers > geolocation > default
        
        Args:
            text: User input text to analyze
            accept_language: Accept-Language HTTP header
            timezone: User timezone
            country_code: ISO country code
            user_preference: Stored user language preference
            default_language: Fallback language
        
        Returns:
            Detected language (highest priority first)
        """
        # Highest priority: explicit user preference
        if user_preference:
            try:
                return Language(user_preference)
            except ValueError:
                log.warning(f"Unknown user preference language: {user_preference}")
        
        # Second priority: text content analysis
        if text:
            detected = self.detect_from_text(text)
            if detected:
                return detected
        
        # Third priority: Accept-Language header
        if accept_language:
            detected = self.detect_from_headers(accept_language)
            if detected:
                return detected
        
        # Fourth priority: Geolocation
        if timezone:
            detected = self.detect_from_timezone(timezone)
            if detected:
                return detected
        
        if country_code:
            detected = self.detect_from_ip_geolocation(country_code)
            if detected:
                return detected
        
        # Fallback to default
        return default_language
    
    def get_language_by_code(self, code: str) -> Optional[Language]:
        """Get Language enum by code"""
        try:
            return Language(code)
        except ValueError:
            return None


# Singleton instance
language_detector = LanguageDetector()


async def get_language_detector() -> LanguageDetector:
    """FastAPI dependency for language detector"""
    return language_detector


class LanguageContext:
    """Context holder for user's language preference and settings"""
    
    def __init__(
        self,
        language: Language = Language.ENGLISH,
        dialect: Optional[Language] = None,
        user_id: Optional[str] = None
    ):
        self.language = language
        self.dialect = dialect or language  # Use main language if no dialect specified
        self.user_id = user_id
        self.prefer_roman_numerals = False  # For age/dose preference
        self.created_at = None
    
    def to_dict(self) -> dict:
        """Convert context to dictionary"""
        return {
            "language": self.language.value,
            "dialect": self.dialect.value,
            "user_id": self.user_id,
            "prefer_roman_numerals": self.prefer_roman_numerals,
            "created_at": self.created_at,
        }
    
    def __str__(self) -> str:
        return f"LanguageContext(language={self.language}, dialect={self.dialect}, user={self.user_id})"
