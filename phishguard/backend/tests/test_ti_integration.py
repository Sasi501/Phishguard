import unittest
from unittest.mock import patch

from domain_module.ti_integration import check_url_against_feeds

class TIIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Clear TI cache between tests to avoid cross-test contamination
        try:
            import domain_module.ti_integration as ti
            ti._TI_CACHE.clear()
        except Exception:
            pass

    @patch('domain_module.ti_integration._fetch_phishtank_csv')
    def test_phishtank_match(self, mock_fetch):
        # Sample CSV line containing domain
        mock_fetch.return_value = 'url,phish_id,submission_time,verified\nhttp://landing.example/,123,2020-01-01,yes\n'
        res = check_url_against_feeds('http://landing.example/')
        self.assertIn('phishtank', res['ti_sources'])
        self.assertGreater(res['ti_hits'], 0)

    @patch('domain_module.ti_integration._fetch_phishtank_csv')
    def test_phishtank_no_match(self, mock_fetch):
        mock_fetch.return_value = 'url,phish_id\nhttp://other.com,5\n'
        res = check_url_against_feeds('http://landing.example/')
        self.assertEqual(res['ti_hits'], 0)

if __name__ == '__main__':
    unittest.main()
