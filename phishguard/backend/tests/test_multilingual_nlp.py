"""
PhishGuard — Multilingual NLP Tests
Tests language detection and phishing classification across multiple languages.
Uses keyword-fallback mode so tests pass without downloading large models.
"""
import unittest
import os
import sys

# Ensure backend root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMultilingualKeywords(unittest.TestCase):
    def test_english_keywords_present(self):
        from nlp.multilingual_keywords import get_phishing_keywords
        keywords = get_phishing_keywords("en")
        self.assertIn("urgent", keywords)
        self.assertIn("password", keywords)

    def test_hindi_keywords_present(self):
        from nlp.multilingual_keywords import get_phishing_keywords
        keywords = get_phishing_keywords("hi")
        self.assertGreater(len(keywords), 5)
        # Must contain Hindi words
        self.assertTrue(any("\u0900" <= c <= "\u097f" for kw in keywords for c in kw))

    def test_tamil_keywords_present(self):
        from nlp.multilingual_keywords import get_phishing_keywords
        keywords = get_phishing_keywords("ta")
        self.assertGreater(len(keywords), 5)

    def test_unknown_language_falls_back_to_english(self):
        from nlp.multilingual_keywords import get_phishing_keywords
        keywords = get_phishing_keywords("zz")  # unknown code
        en_keywords = get_phishing_keywords("en")
        self.assertEqual(keywords, en_keywords)

    def test_extract_keywords_english(self):
        from nlp.multilingual_keywords import extract_keywords_multilingual
        text = "URGENT: Your account has been suspended. Please verify your password immediately."
        found = extract_keywords_multilingual(text, "en")
        self.assertIn("urgent", found)
        self.assertIn("account", found)
        self.assertGreater(len(found), 2)

    def test_extract_keywords_hindi(self):
        from nlp.multilingual_keywords import extract_keywords_multilingual
        # "Your account has been suspended. Please verify immediately."
        text = "आपका खाता निलंबित कर दिया गया है। कृपया तुरंत सत्यापित करें।"
        found = extract_keywords_multilingual(text, "hi")
        self.assertIn("खाता", found)
        self.assertGreater(len(found), 0)

    def test_extract_keywords_tamil(self):
        from nlp.multilingual_keywords import extract_keywords_multilingual
        # "Your account will be suspended. Please verify immediately."
        text = "உங்கள் கணக்கு இடைநிறுத்தப்படும். உடனே சரிபார்க்கவும்."
        found = extract_keywords_multilingual(text, "ta")
        self.assertIn("கணக்கு", found)


class TestLanguageDetection(unittest.TestCase):
    def test_detect_english(self):
        from nlp.nlp_service import detect_language
        lang = detect_language("Your account has been suspended. Please verify your password.")
        self.assertEqual(lang, "en")

    def test_detect_returns_string(self):
        from nlp.nlp_service import detect_language
        lang = detect_language("hello world")
        self.assertIsInstance(lang, str)
        self.assertGreater(len(lang), 0)


class TestMultilingualNLPService(unittest.TestCase):
    def test_keyword_fallback_english(self):
        from nlp.nlp_service import MultilingualNLPService
        svc = MultilingualNLPService()
        result = svc._keyword_fallback(
            "URGENT: Your account has been suspended. Verify password now.", "en"
        )
        self.assertIn("nlp_score", result)
        self.assertIn("nlp_risk_level", result)
        self.assertIn("detected_language", result)
        self.assertEqual(result["model"], "keyword-fallback")
        self.assertGreater(result["nlp_score"], 0)

    def test_keyword_fallback_hindi(self):
        from nlp.nlp_service import MultilingualNLPService
        svc = MultilingualNLPService()
        result = svc._keyword_fallback("आपका खाता निलंबित कर दिया गया है।", "hi")
        self.assertEqual(result["detected_language"], "hi")
        self.assertGreater(result["nlp_score"], 0)

    def test_analyze_text_with_nlp_routing(self):
        from nlp.nlp_service import analyze_text_with_nlp
        result = analyze_text_with_nlp(
            "URGENT: Your bank account is suspended. Verify your password now."
        )
        self.assertIn("nlp_score", result)
        self.assertIn("nlp_risk_level", result)
        self.assertIn("detected_language", result)
        self.assertIn(result["nlp_risk_level"], ["safe", "suspicious", "phishing"])

    def test_is_nlp_available(self):
        from nlp.nlp_service import is_nlp_available
        # Should always return True since multilingual fallback is always available
        self.assertIsInstance(is_nlp_available(), bool)


if __name__ == "__main__":
    unittest.main()
