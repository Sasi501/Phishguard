import unittest
from unittest.mock import patch

from domain_module.ti_integration import check_url_against_feeds

class TIIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Clear TI cache between tests to avoid cross-test contamination
        try:
            import domain_module.ti_integration as ti
            ti._TI_CACHE.clear()
            ti._TI_URL_INDEX.clear()
            ti._TI_DOMAIN_INDEX.clear()
            ti._TI_SOURCE_MAP.clear()
            ti._LAST_SYNC_TIME = 0.0
            for source in ti._TI_SOURCE_STATUS:
                ti._TI_SOURCE_STATUS[source] = {
                    "status": "unavailable",
                    "reason": "Feed has not been synchronized.",
                }
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

    @patch('domain_module.ti_integration.fetch_openphish_feed', return_value=[])
    @patch('domain_module.ti_integration.fetch_urlhaus_feed', return_value=[])
    @patch('domain_module.ti_integration._fetch_phishtank_csv', return_value=None)
    def test_no_available_feeds_is_not_reported_as_a_clean_ti_miss(
        self,
        _mock_phishtank,
        _mock_urlhaus,
        _mock_openphish,
    ):
        result = check_url_against_feeds('http://landing.example/')

        self.assertEqual(result['ti_hits'], 0)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(len(result['unavailable_sources']), 3)
        self.assertIn('No threat-intelligence feeds', result['reason'])

if __name__ == '__main__':
    unittest.main()
