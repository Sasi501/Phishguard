import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  en: {
    translation: {
      "nav": {
        "roadmap": "Roadmap",
        "registry": "Registry",
        "hitl": "HITL Review",
        "settings": "Settings",
        "core_online": "CORE SYSTEM ONLINE",
        "core_checking": "CHECKING CORE STATUS",
        "core_unavailable": "CORE STATUS UNAVAILABLE"
      },
      "hero": {
        "title": "Welcome to PhishGuard",
        "subtitle": "Multi-Modal Intelligence for Phishing Detection",
        "threats_blocked": "Threats Blocked",
        "total_scans": "Total Scans",
        "active_engines": "Active Engines",
        "start_scan": "Start New Scan"
      },
      "scanner": {
        "target_url": "TARGET URL",
        "target_url_placeholder": "https://example.com",
        "advanced_options": "Advanced Options",
        "page_text": "PAGE TEXT (optional)",
        "screenshot": "SCREENSHOT (optional)",
        "scan_target": "SCAN TARGET",
        "scanning": "SCANNING..."
      },
      "settings": {
        "title": "Settings",
        "theme": "Theme",
        "light_mode": "Light Mode",
        "dark_mode": "Dark Mode",
        "language": "Language",
        "animations": "Animations",
        "reduced_motion": "Reduced Motion",
        "close": "Close"
      }
    }
  },
  hi: {
    translation: {
      "nav": {
        "roadmap": "रोडमैप",
        "registry": "रजिस्ट्री",
        "hitl": "HITL समीक्षा",
        "settings": "सेटिंग्स",
        "core_online": "मुख्य सिस्टम ऑनलाइन",
        "core_checking": "मुख्य सिस्टम स्थिति जांच रहे हैं",
        "core_unavailable": "मुख्य सिस्टम स्थिति अनुपलब्ध"
      },
      "hero": {
        "title": "PhishGuard में आपका स्वागत है",
        "subtitle": "AI-संचालित फ़िशिंग URL जांच",
        "threats_blocked": "रोके गए खतरे",
        "total_scans": "कुल स्कैन",
        "active_engines": "सक्रिय इंजन",
        "start_scan": "नया स्कैन शुरू करें"
      },
      "scanner": {
        "target_url": "लक्ष्य URL",
        "target_url_placeholder": "https://example.com",
        "advanced_options": "उन्नत विकल्प",
        "page_text": "पृष्ठ पाठ (वैकल्पिक)",
        "screenshot": "स्क्रीनशॉट (वैकल्पिक)",
        "scan_target": "लक्ष्य स्कैन करें",
        "scanning": "स्कैन कर रहा है..."
      },
      "settings": {
        "title": "सेटिंग्स",
        "theme": "थीम",
        "light_mode": "लाइट मोड",
        "dark_mode": "डार्क मोड",
        "language": "भाषा",
        "animations": "एनिमेशन",
        "reduced_motion": "कम गति",
        "close": "बंद करें"
      }
    }
  },
  ta: {
    translation: {
       "nav": {
        "roadmap": "வழி வரைபடம்",
        "registry": "பதிவேடு",
        "hitl": "HITL ஆய்வு",
        "settings": "அமைப்புகள்",
        "core_online": "முக்கிய அமைப்பு இயங்குகிறது",
        "core_checking": "முக்கிய அமைப்பு நிலையைச் சரிபார்க்கிறது",
        "core_unavailable": "முக்கிய அமைப்பு நிலை கிடைக்கவில்லை"
      },
      "hero": {
        "title": "PhishGuard க்கு வரவேற்கிறோம்",
        "subtitle": "AI-ஆதரவு பெற்ற பிஷிங் URL கண்டறிதல்",
        "threats_blocked": "தடுக்கப்பட்ட அச்சுறுத்தல்கள்",
        "total_scans": "மொத்த ஸ்கேன்கள்",
        "active_engines": "செயலில் உள்ள இயந்திரங்கள்",
        "start_scan": "புதிய ஸ்கேன் தொடங்கவும்"
      },
      "scanner": {
        "target_url": "இலக்கு URL",
        "target_url_placeholder": "https://example.com",
        "advanced_options": "மேம்பட்ட விருப்பங்கள்",
        "page_text": "பக்க உரை (விரும்பினால்)",
        "screenshot": "ஸ்கிரீன்ஷாட் (விரும்பினால்)",
        "scan_target": "இலக்கை ஸ்கேன் செய்",
        "scanning": "ஸ்கேன் செய்கிறது..."
      },
      "settings": {
        "title": "அமைப்புகள்",
        "theme": "தீம்",
        "light_mode": "ஒளி பயன்முறை",
        "dark_mode": "இருண்ட பயன்முறை",
        "language": "மொழி",
        "animations": "அனிமேஷன்கள்",
        "reduced_motion": "குறைக்கப்பட்ட இயக்கம்",
        "close": "மூடு"
      }
    }
  },
  fr: {
    translation: {
       "nav": {
        "roadmap": "Feuille de route",
        "registry": "Registre",
        "hitl": "Revue HITL",
        "settings": "Paramètres",
        "core_online": "SYSTÈME PRINCIPAL EN LIGNE",
        "core_checking": "VÉRIFICATION DU SYSTÈME PRINCIPAL",
        "core_unavailable": "ÉTAT DU SYSTÈME PRINCIPAL INDISPONIBLE"
      },
      "hero": {
        "title": "Bienvenue sur PhishGuard",
        "subtitle": "Détection d'URL de phishing par IA",
        "threats_blocked": "Menaces bloquées",
        "total_scans": "Scans totaux",
        "active_engines": "Moteurs actifs",
        "start_scan": "Lancer un scan"
      },
      "scanner": {
        "target_url": "URL CIBLE",
        "target_url_placeholder": "https://example.com",
        "advanced_options": "Options avancées",
        "page_text": "Texte de la page (optionnel)",
        "screenshot": "Capture d'écran (optionnel)",
        "scan_target": "SCANNER LA CIBLE",
        "scanning": "ANALYSE..."
      },
      "settings": {
        "title": "Paramètres",
        "theme": "Thème",
        "light_mode": "Mode clair",
        "dark_mode": "Mode sombre",
        "language": "Langue",
        "animations": "Animations",
        "reduced_motion": "Mouvement réduit",
        "close": "Fermer"
      }
    }
  }
}

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: "en", // default language
    fallbackLng: "en",
    interpolation: {
      escapeValue: false
    }
  })

export default i18n
