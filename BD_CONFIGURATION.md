# NirovaAI Bangladesh Edition (BD) - Configuration & Setup

## Overview

This document outlines the Bangladesh-specific configuration for NirovaAI. The application has been optimized exclusively for Bangladesh healthcare context with Bangla as the primary language.

---

## 🇧🇩 Language Support

### Supported Variants
- **Bengali (বাংলা)** - Standard Dhaka Bengali - Code: `bn`
- **Chittagong Dialect (চট্টগ্রাম)** - Code: `cg`
- **Sylhet Dialect (সিলেট)** - Code: `sy`
- **Khulna Dialect (খুলনা)** - Code: `kh`
- **Dhaka Dialect (ঢাকা)** - Code: `dhk`

### Key Features
✅ Automatic language detection from user input
✅ Regional dialect variations for medical terms
✅ BD-specific health guidance in all dialects
✅ Emergency messaging in multiple dialects
✅ Culturally appropriate recommendations

---

## 🏥 Bangladesh Healthcare Context

### Common Tropical Diseases
The analytics engine focuses on diseases prevalent in Bangladesh:

| Disease | Prevalence | Season | Risk Factor |
|---------|-----------|--------|------------|
| Diarrhea | Very High | Monsoon | 30 |
| Respiratory Infection | Very High | Winter | 25 |
| Dengue | High | Monsoon | 25 |
| Pneumonia | High | Winter | 20 |
| Malaria | Moderate | Year-round | 20 |
| Typhoid | Moderate | Pre-monsoon | 15 |
| Asthma | Moderate | Year-round | 18 |
| Skin Infection | High | Summer | 15 |
| Hypertension | Moderate | Year-round | 20 |
| Diabetes | Moderate | Year-round | 22 |

### Emergency Contact Numbers (Built-in)
- **Emergency Medical**: 999, 112
- **Ambulance**: 10666 (Dhaka)
- **Health Hotline**: 16263 (Disease Report)
- **Fire**: 999

---

## 📱 API Language Configuration

### Default Language
```python
DEFAULT_LANGUAGE = "bn"  # Bengali
```

### Endpoint Examples

#### Get Supported Languages
```bash
GET /api/language/supported

Response:
{
  "languages": [
    {"code": "bn", "name": "Bengali", "native_name": "বাংলা"},
    {"code": "cg", "name": "Chittagong Dialect", "native_name": "চট্টগ্রাম"},
    {"code": "sy", "name": "Sylhet Dialect", "native_name": "সিলেট"},
    {"code": "kh", "name": "Khulna Dialect", "native_name": "খুলনা"},
    {"code": "dhk", "name": "Dhaka Dialect", "native_name": "ঢাকা"}
  ]
}
```

#### Detect Language Automatically
```bash
POST /api/language/detect
Content-Type: application/json

{
  "text": "আমার জ্বর এবং মাথা ব্যথা আছে",
  "accept_language": "bn-BD,bn;q=0.9"
}

Response:
{
  "detected_language": "bn",
  "confidence": 0.98,
  "dialect": "dh",
  "alternatives": []
}
```

#### Get Health Guidance in Bangla
```bash
POST /api/language/health-guidance
Content-Type: application/json

{
  "guidance_key": "dengue_prevention",
  "language": "bn"
}

Response:
{
  "guidance": "মশারি ব্যবহার করুন, বাহু এবং পা ঢাকুন, কীটনাশক ব্যবহার করুন"
}
```

---

## 🔐 User Preferences

### Default User Language Preference
```json
{
  "user_id": "user_123",
  "language": "bn",
  "dialect": "cg",
  "updated_at": "2026-03-27T10:30:00Z"
}
```

### Set User Preference
```bash
POST /api/language/preference
Authorization: Bearer {token}
Content-Type: application/json

{
  "language": "bn",
  "dialect": "cg"
}
```

---

## 📊 Analytics for BD Health

### Health Risk Score Calculation
The analytics engine uses BD-specific risk factors:

```
Total Risk Score (0-100) =
  Frequency Score (0-30) +
  Severity Score (0-30) +
  Trend Score (0-20) +
  Comorbidity Score (0-20) +
  BD Disease Risk Adjustment
```

### BD Disease Risk Adjustment
```python
risk_adjustments = {
    "dengue": 1.3,           # Higher risk in monsoon
    "respiratory": 1.2,      # Very common in winter
    "diarrhea": 1.25,        # Very common in monsoon
    "malaria": 1.15,         # Moderate endemic risk
}
```

---

## 🌍 Regional Considerations

### Time Zone
```
Asia/Dhaka (UTC+6)
```

### Geographic Coverage
- Primary: All of Bangladesh
- Regional Dialects: District-based variations
- Healthcare System: DGHS (Directorate General of Health Services)

### Currency & Healthcare Costs
- Primary Currency: BDT (Bangladeshi Taka)
- Healthcare varies across urban/rural areas
- Recommendations account for accessibility

---

## 💾 Database Collections

### Users Collection
```javascript
{
  _id: ObjectId,
  email: "user@example.com",
  language_preference: {
    language: "bn",
    dialect: "cg",
    updated_at: ISODate()
  },
  timezone: "Asia/Dhaka"
}
```

### Health Timeline Collection
```javascript
{
  _id: ObjectId,
  user_id: ObjectId,
  event_type: "symptom", // or "diagnosis", "medication"
  bangla_text: "জ্বর এবং মাথা ব্যথা",
  english_text: "fever and headache",
  severity: 7,
  created_at: ISODate(),
  location: "Dhaka"  // optional
}
```

---

## 🚀 Deployment Configuration

### Environment Variables (BD Setup)
```bash
# Language & Localization
DEFAULT_LANGUAGE=bn
TIMEZONE=Asia/Dhaka
COUNTRY_CODE=BD

# Healthcare Context
HEALTH_SYSTEM=DGHS
EMERGENCY_NUMBERS=999,112,10666

# API Settings
LANGUAGE_DETECTION_ENABLED=true
AUTO_DETECT_DIALECT=true
USE_BD_MEDICAL_GUIDELINES=true
```

### Docker Compose for BD
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      DEFAULT_LANGUAGE: "bn"
      TIMEZONE: "Asia/Dhaka"
      COUNTRY_CODE: "BD"
    ports:
      - "8000:8000"
```

---

## 🔍 Medical Terminology (50+ Translated Terms)

### Symptoms (15+)
- জ্বর (Fever)
- মাথা ব্যথা (Headache)
- কাশি (Cough)
- গলা ব্যথা (Sore Throat)
- বমি (Vomiting)
- ডায়রিয়া (Diarrhea)
- দুর্বলতা (Weakness)
- শ্বাসকষ্ট (Difficulty Breathing)
- পেট খারাপ (Stomach Upset)
- চর্মরোগ (Skin Disease)

### Diseases (10+)
- ডেঙ্গু (Dengue)
- ম্যালেরিয়া (Malaria)
- টাইফয়েড (Typhoid)
- করোনা (COVID-19)
- ফ্লু (Influenza)
- চিকেনপক্স (Chickenpox)
- যক্ষ্মা (Tuberculosis)
- নিউমোনিয়া (Pneumonia)
- হাম (Measles)

### Medical Tests (8+)
- রক্ত পরীক্ষা (Blood Test)
- প্লেটিলেট কাউন্ট (Platelet Count)
- ম্যালেরিয়া পরীক্ষা (Malaria Test)
- প্রস্রাব পরীক্ষা (Urine Test)
- এক্স-রে (X-Ray)
- সিটি স্ক্যান (CT Scan)
- আলট্রাসাউন্ড (Ultrasound)

---

## ✅ Health Guidance by Condition

### For Dengue
```
Bengali: "মশারি ব্যবহার করুন, বাহু এবং পা ঢাকুন, কীটনাশক ব্যবহার করুন"
Chittagong: "মশারি লাগা, শার্ট পরা, স্প্রে করা"
```

### For Dehydration (Common in Summer)
```
Bengali: "ওআরএস (মৌখিক পুনর্জলীকরণ দ্রবণ) বা জল পান"
Daraz: "খাওয়ার স্যালাইন খা, পানি খা"
```

### When to Be Worried
```
Bengali: "জ্বর ৩ দিনের বেশি স্থায়ী হলে অবিলম্বে চিকিৎসকের পরামর্শ নিন"
Chittagong: "জ্বর ৩ দিনের বেশি হলে ডাক্তার ডাকা"
```

---

## 📈 Testing Checklist for BD Deployment

- [ ] Language detection works for all BD dialects
- [ ] Medical terms translate correctly (50+ terms verified)
- [ ] Regional dialect variations apply properly
- [ ] Emergency messages appear in correct dialect
- [ ] Health guidance reflects BD context
- [ ] Analytics identify BD-specific diseases correctly
- [ ] Risk scoring uses BD prevalence data
- [ ] Time zone is set to Asia/Dhaka
- [ ] Emergency numbers display correctly
- [ ] Recommendations align with DGHS guidelines

---

## 🔗 References

- IEDCR (Institute of Epidemiology Disease Control & Research): https://iedcr.gov.bd/
- DGHS (Directorate General of Health Services): https://dghs.gov.bd/
- WHO Bangladesh: https://www.who.int/bangladesh
- Emergency Services: 999 (All services)

---

## 📞 Support

For BD-specific healthcare guidance:
- National Health Hotline: **16263**
- COVID-19 Hotline: **333 (from mobile)**
- Mental Health Hotline: **09666 111 333**

---

**Last Updated**: March 27, 2026
**Edition**: Bangladesh Optimized v1.0
**Status**: Production Ready
