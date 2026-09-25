import unittest
from unittest.mock import patch

from ensemble_module import fusion_engine

class FusionEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_fusion_with_ml_and_domain_only(self):
        # Mock ML and domain to return deterministic scores
        with patch('ensemble_module.fusion_engine.predict_url') as mock_ml, \
             patch('ensemble_module.fusion_engine.analyze_domain') as mock_domain:
            mock_ml.return_value = {'ml_score': 0.9, 'ml_top_features': []}
            mock_domain.return_value = {'domain_score': 0.2, 'domain_signals': []}

            res = await fusion_engine.calculate_ensemble_score('http://example.com')
            self.assertIn('ensemble_score_percent', res)
            self.assertIn('individual_scores_percent', res)
            self.assertGreaterEqual(res['ensemble_score_percent'], 0.0)

    async def test_fusion_with_text_and_nlp(self):
        with patch('ensemble_module.fusion_engine.analyze_text_with_nlp') as mock_nlp, \
             patch('ensemble_module.fusion_engine.predict_url') as mock_ml, \
             patch('ensemble_module.fusion_engine.analyze_domain') as mock_domain:
            mock_ml.return_value = {'ml_score': 0.1, 'ml_top_features': []}
            mock_domain.return_value = {'domain_score': 0.0, 'domain_signals': []}
            mock_nlp.return_value = {'nlp_score': 0.8, 'suspicious_keywords': ['urgent']}

            res = await fusion_engine.calculate_ensemble_score('http://example.com', text='Urgent: click')
            self.assertEqual(res['individual_scores_percent']['nlp'] > 0, True)
            self.assertIn('xai_summary', res)

    async def test_fusion_with_image_and_vision(self):
        with patch('ensemble_module.fusion_engine.analyze_image_with_vision') as mock_vision, \
             patch('ensemble_module.fusion_engine.predict_url') as mock_ml:
            mock_ml.return_value = {'ml_score': 0.0, 'ml_top_features': []}
            mock_vision.return_value = {'vision_score': 0.6, 'suspicious_regions': [{'region':'logo','confidence':0.9}]}

            res = await fusion_engine.calculate_ensemble_score('http://example.com', image_bytes=b'fakebytes')
            self.assertIn('individual_scores_percent', res)
            self.assertGreater(res['individual_scores_percent']['vision'], 0)

    async def test_xai_response_for_risky_result(self):
        with patch('ensemble_module.fusion_engine.predict_url') as mock_ml, \
             patch('ensemble_module.fusion_engine.analyze_domain') as mock_domain, \
             patch('ensemble_module.fusion_engine.analyze_text_with_nlp') as mock_nlp:
            mock_ml.return_value = {
                'ml_score': 0.82,
                'ml_risk_level': 'phishing',
                'shap_features': [{'feature': 'subdomain_count', 'value': 4, 'shap_value': 0.31}]
            }
            mock_domain.return_value = {
                'domain_score': 0.45,
                'domain_risk_level': 'suspicious',
                'domain_signals': ['domain_relatively_new'],
                'metadata': {'age_days': 120, 'ssl_valid': False, 'ti_summary': {'ti_hits': 0}},
                'ti_details': {'ti_hits': 0, 'ti_sources': []}
            }
            mock_nlp.return_value = {
                'nlp_score': 0.68,
                'nlp_risk_level': 'suspicious',
                'suspicious_keywords': ['urgent'],
                'shap_features': [{'feature': 'urgent', 'value': 'urgent', 'shap_value': 0.42}]
            }

            res = await fusion_engine.calculate_ensemble_score('https://suspicious.example.com', text='Urgent action required')
            self.assertIn('xai', res)
            self.assertIn('summary', res['xai'])
            self.assertTrue(len(res['xai']['risk_factors']) >= 1)
            self.assertTrue(len(res['xai']['engine_signals']) >= 2)
            self.assertTrue(len(res['xai']['feature_importance']) >= 1)

    async def test_xai_response_for_safe_result(self):
        with patch('ensemble_module.fusion_engine.predict_url') as mock_ml, \
             patch('ensemble_module.fusion_engine.analyze_domain') as mock_domain, \
             patch('ensemble_module.fusion_engine.analyze_text_with_nlp') as mock_nlp:
            mock_ml.return_value = {
                'ml_score': 0.1,
                'ml_risk_level': 'safe',
                'shap_features': [{'feature': 'url_length', 'value': 18, 'shap_value': -0.12}]
            }
            mock_domain.return_value = {
                'domain_score': 0.05,
                'domain_risk_level': 'safe',
                'domain_signals': [],
                'metadata': {'age_days': 2000, 'ssl_valid': True, 'ti_summary': {'ti_hits': 0}},
                'ti_details': {'ti_hits': 0, 'ti_sources': []}
            }
            mock_nlp.return_value = {
                'nlp_score': 0.02,
                'nlp_risk_level': 'safe',
                'suspicious_keywords': [],
                'shap_features': []
            }

            res = await fusion_engine.calculate_ensemble_score('https://example.com', text='Hello there')
            self.assertIn('xai', res)
            self.assertTrue(len(res['xai']['safety_factors']) >= 1)
            self.assertIn('no threat-intelligence match', (res['xai']['summary'] + ' ' + res['xai']['safety_factors'][0]['description']).lower())

    async def test_redirect_provenance_is_exposed_without_changing_score_policy(self):
        redirect_analysis = {
            'original_url': 'https://short.example/a',
            'final_url': 'https://landing.example/login',
            'redirect_chain': [
                {'url': 'https://short.example/a', 'status_code': 302},
                {'url': 'https://landing.example/login', 'status_code': 200},
            ],
            'num_redirects': 1,
            'loop_detected': False,
            'suspicious_redirects': False,
            'has_meta_refresh': False,
            'resolution_state': 'completed',
            'errors': [],
        }
        domain_result = {
            'domain_score': 0.2,
            'domain_signals': [],
            'metadata': {
                'age_days': None,
                'ssl_valid': True,
                'ti_summary': {'ti_hits': 0, 'ti_sources': []},
            },
            'redirect_analysis': redirect_analysis,
        }

        with patch('ensemble_module.fusion_engine.predict_url', return_value={'ml_score': 0.1}), \
             patch('ensemble_module.fusion_engine.analyze_domain', return_value=domain_result) as mock_domain:
            res = await fusion_engine.calculate_ensemble_score('https://short.example/a')

        self.assertEqual(mock_domain.call_count, 1)
        self.assertEqual(res['redirect_analysis'], redirect_analysis)
        self.assertEqual(res['xai']['redirect_analysis'], redirect_analysis)
        self.assertEqual(res['xai']['redirect_evidence'][0]['title'], 'Redirect chain detected')
        self.assertIn('final resolved URL', res['xai']['redirect_evidence'][1]['description'])
        self.assertEqual(res['individual_scores_percent']['ml'], 10.0)
        self.assertEqual(res['individual_scores_percent']['domain'], 20.0)
        signals = {signal['engine']: signal for signal in res['xai']['engine_signals']}
        self.assertEqual(signals['URL Intelligence']['source'], 'url_ml')
        self.assertEqual(signals['URL Intelligence']['score_type'], 'engine_signal')
        self.assertEqual(signals['URL Intelligence']['url_scope'], 'original_url')
        self.assertEqual(signals['Domain Intelligence']['url_scope'], 'final_url')
        self.assertEqual(signals['Threat Intelligence']['url_scope'], 'final_url')

if __name__ == '__main__':
    unittest.main()
