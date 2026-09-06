"""
PhishGuard — Multilingual Phishing Keywords
Comprehensive dictionary of phishing-related keywords across 10 languages.
Used for rule-based keyword extraction in the multilingual NLP pipeline.
"""

MULTILINGUAL_KEYWORDS: dict = {
    "en": [
        "urgent", "password", "suspend", "verify", "account", "login",
        "win", "gift", "claim", "click", "confirm", "update", "alert",
        "security", "bank", "credit", "debit", "expire", "immediately",
        "validate", "action required", "limited time", "suspended",
    ],

    "hi": [
        # Hindi — phishing keywords
        "खाता", "पासवर्ड", "सत्यापित", "तत्काल", "बैंक", "जीत",
        "उपहार", "दावा", "अपडेट", "अलर्ट", "सुरक्षा", "क्रेडिट",
        "डेबिट", "समाप्त", "निलंबित", "तुरंत", "लॉगिन", "सत्यापन",
        "पुष्टि करें", "कार्रवाई आवश्यक",
    ],

    "ta": [
        # Tamil — phishing keywords
        "கணக்கு", "கடவுச்சொல்", "சரிபார்க்க", "அவசரம்", "வங்கி",
        "வெற்றி", "பரிசு", "கோரல்", "புதுப்பிக்க", "எச்சரிக்கை",
        "பாதுகாப்பு", "கடன்", "காலாவதி", "இடைநிறுத்தப்பட்டது",
        "உடனடியாக", "உள்நுழைவு", "உறுதிப்படுத்தவும்",
    ],

    "te": [
        # Telugu — phishing keywords
        "ఖాతా", "పాస్‌వర్డ్", "ధృవీకరించు", "అత్యవసర", "బ్యాంక్",
        "గెలుపు", "బహుమతి", "క్లెయిమ్", "నవీకరణ", "హెచ్చరిక",
        "భద్రత", "క్రెడిట్", "గడువు", "నిలిపివేయబడింది",
        "వెంటనే", "లాగిన్", "నిర్ధారించు",
    ],

    "ml": [
        # Malayalam — phishing keywords
        "അക്കൗണ്ട്", "പാസ്‌വേഡ്", "പരിശോധിക്കുക", "അടിയന്തര",
        "ബാങ്ക്", "വിജയം", "സമ്മാനം", "ക്ലെയിം", "അപ്‌ഡേറ്റ്",
        "മുന്നറിയിപ്പ്", "സുരക്ഷ", "ക്രെഡിറ്റ്", "കാലഹരണപ്പെട്ടു",
        "സസ്‌പെൻഡ്", "ഉടൻ", "ലോഗിൻ", "സ്ഥിരീകരിക്കുക",
    ],

    "kn": [
        # Kannada — phishing keywords
        "ಖಾತೆ", "ಪಾಸ್‌ವರ್ಡ್", "ಪರಿಶೀಲಿಸಿ", "ತುರ್ತು", "ಬ್ಯಾಂಕ್",
        "ಗೆಲುವು", "ಉಡುಗೊರೆ", "ಕ್ಲೇಮ್", "ನವೀಕರಿಸಿ", "ಎಚ್ಚರಿಕೆ",
        "ಭದ್ರತೆ", "ಕ್ರೆಡಿಟ್", "ಅವಧಿ ಮೀರಿದೆ", "ಅಮಾನತು",
        "ತಕ್ಷಣ", "ಲಾಗಿನ್", "ದೃಢೀಕರಿಸಿ",
    ],

    "bn": [
        # Bengali — phishing keywords
        "অ্যাকাউন্ট", "পাসওয়ার্ড", "যাচাই করুন", "জরুরি", "ব্যাংক",
        "জয়", "উপহার", "দাবি", "আপডেট", "সতর্কতা",
        "নিরাপত্তা", "ক্রেডিট", "মেয়াদোত্তীর্ণ", "স্থগিত",
        "অবিলম্বে", "লগইন", "নিশ্চিত করুন",
    ],

    "ar": [
        # Arabic — phishing keywords
        "حساب", "كلمة المرور", "تحقق", "عاجل", "بنك",
        "فوز", "هدية", "مطالبة", "تحديث", "تنبيه",
        "أمان", "ائتمان", "انتهت الصلاحية", "معلق",
        "فوراً", "تسجيل الدخول", "تأكيد",
    ],

    "ur": [
        # Urdu — phishing keywords
        "اکاؤنٹ", "پاس ورڈ", "تصدیق", "فوری", "بینک",
        "جیت", "تحفہ", "دعویٰ", "اپ ڈیٹ", "الرٹ",
        "سیکیورٹی", "کریڈٹ", "میعاد ختم", "معطل",
        "فوراً", "لاگ ان", "تصدیق کریں",
    ],

    "fr": [
        # French — phishing keywords
        "compte", "mot de passe", "vérifier", "urgent", "banque",
        "gagné", "cadeau", "réclamer", "mise à jour", "alerte",
        "sécurité", "crédit", "expiré", "suspendu",
        "immédiatement", "connexion", "confirmer",
    ],
}


def get_phishing_keywords(lang_code: str) -> list:
    """Return phishing keywords for the given ISO 639-1 language code.
    Falls back to English if language not found."""
    return MULTILINGUAL_KEYWORDS.get(lang_code, MULTILINGUAL_KEYWORDS["en"])


def extract_keywords_multilingual(text: str, lang_code: str) -> list:
    """Find phishing keywords in text for a given language."""
    keywords = get_phishing_keywords(lang_code)
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]
