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

if __name__ == '__main__':
    unittest.main()

