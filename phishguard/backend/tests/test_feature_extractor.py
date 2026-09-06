import unittest
from ml.feature_extractor import extract_features

class FeatureExtractorTests(unittest.TestCase):
    def test_basic_features_present(self):
        url = "https://www.example.com/path/to/page?query=1"
        feats = extract_features(url)
        # Ensure new features exist and types are correct
        self.assertIn('num_subdomains', feats)
        self.assertIn('has_unicode', feats)
        self.assertIn('is_punycode', feats)
        self.assertIn('confusable_chars', feats)
        self.assertIn('mixed_script_changes', feats)
        self.assertIsInstance(feats['num_subdomains'], int)
        self.assertIn(feats['has_unicode'], (0,1))

    def test_idn_detection(self):
        url = "http://xn--pypal-4ve.com/signin"
        feats = extract_features(url)
        self.assertEqual(feats['is_punycode'], 1)
        self.assertEqual(feats['has_unicode'], 0)  # punycode label is ascii

if __name__ == '__main__':
    unittest.main()
