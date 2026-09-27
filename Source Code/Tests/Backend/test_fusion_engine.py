import unittest
from unittest.mock import Mock, patch

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

    async def test_xai_reuses_the_same_engine_result_used_by_fusion(self):
        ml_result = {
            'ml_score': 0.12,
            'ml_risk_level': 'safe',
            'shap_features': [{'feature': 'url_length', 'value': 18, 'shap_value': -0.08}],
        }
        with patch.object(fusion_engine, 'ML_READY', True), \
             patch.object(fusion_engine, 'DOMAIN_READY', False), \
             patch.object(fusion_engine, 'NLP_READY', False), \
             patch.object(fusion_engine, 'VISION_READY', False), \
             patch('ensemble_module.fusion_engine.predict_url', return_value=ml_result) as mock_ml, \
             patch('ensemble_module.fusion_engine.get_meta_learner', return_value=None):
            result = await fusion_engine.calculate_ensemble_score('https://example.com')

        mock_ml.assert_called_once_with('https://example.com')
        url_signal = next(
            signal for signal in result['xai']['engine_signals']
            if signal['source'] == 'url_ml'
        )
        self.assertEqual(url_signal['score'], 12.0)
        self.assertEqual(result['xai']['url_ml_evidence'], {
            'raw_model_probability_percent': 12.0,
            'engine_signal_percent': 12.0,
            'engine_signal_adjustment': None,
        })
        self.assertIn('Low-risk URL signal', [factor['title'] for factor in result['xai']['safety_factors']])
        self.assertAlmostEqual(result['ensemble_score_percent'], 12.0)

    async def test_xai_distinguishes_raw_url_probability_from_moderated_engine_signal(self):
        redirect = {
            'original_url': 'https://example.com',
            'final_url': 'https://example.com',
            'redirect_chain': [{'url': 'https://example.com', 'status_code': 200}],
            'num_redirects': 0,
            'loop_detected': False,
            'suspicious_redirects': False,
            'has_meta_refresh': False,
            'resolution_state': 'completed',
            'errors': [],
        }
        domain_result = {
            'status': 'available',
            'domain_score': 0.2,
            'domain_risk_level': 'safe',
            'domain_signals': [],
            'metadata': {
                'age_days': 2000,
                'ssl_valid': True,
                'ti_summary': {'ti_hits': 0, 'ti_sources': []},
            },
            'ti_status': {'status': 'available'},
            'ti_details': {'ti_hits': 0, 'ti_sources': []},
            'redirect_analysis': redirect,
        }
        with patch.object(fusion_engine, 'ML_READY', True), \
             patch.object(fusion_engine, 'DOMAIN_READY', True), \
             patch.object(fusion_engine, 'NLP_READY', True), \
             patch.object(fusion_engine, 'VISION_READY', True), \
             patch('ensemble_module.fusion_engine.predict_url', return_value={'ml_score': 0.98}), \
             patch('ensemble_module.fusion_engine.analyze_domain', return_value=domain_result), \
             patch('ensemble_module.fusion_engine.analyze_text_with_nlp', return_value={'nlp_score': 0.2}), \
             patch('ensemble_module.fusion_engine.analyze_image_with_vision', return_value={'vision_score': 0.3}), \
             patch('ensemble_module.fusion_engine.get_meta_learner', return_value=None):
            result = await fusion_engine.calculate_ensemble_score(
                'https://example.com',
                text='submitted text',
                image_bytes=b'image',
            )

        url_signal = next(
            signal for signal in result['xai']['engine_signals']
            if signal['source'] == 'url_ml'
        )
        self.assertEqual(result['individual_scores_percent']['ml'], 4.9)
        self.assertEqual(url_signal['score'], result['individual_scores_percent']['ml'])
        self.assertEqual(result['xai']['url_ml_evidence'], {
            'raw_model_probability_percent': 98.0,
            'engine_signal_percent': 4.9,
            'engine_signal_adjustment': 'domain_age_moderation',
        })
        self.assertNotEqual(url_signal['score'], result['ensemble_score_percent'])
        factor = next(factor for factor in result['xai']['risk_factors'] if factor['source'] == 'url')
        self.assertIn('Raw URL-model probability: 98.00%', factor['description'])
        self.assertIn('URL ML engine signal used in fusion: 4.90%', factor['description'])
        self.assertIn('domain-age moderation', factor['description'])
        self.assertNotIn('phishing probability of 0.98', factor['description'])

    async def test_restricted_engines_are_excluded_from_partial_fusion(self):
        redirect = {
            'original_url': 'http://127.0.0.1:8000/api/scan/',
            'final_url': 'http://127.0.0.1:8000/api/scan/',
            'redirect_chain': [{
                'url': 'http://127.0.0.1:8000/api/scan/',
                'status_code': None,
                'note': 'unsafe_url',
            }],
            'num_redirects': 0,
            'loop_detected': False,
            'suspicious_redirects': False,
            'has_meta_refresh': False,
            'resolution_state': 'blocked',
            'blocked_reason': 'Unsafe destination resolved to blocked address: 127.0.0.1',
            'errors': ['unsafe_url:Unsafe destination resolved to blocked address: 127.0.0.1'],
        }
        domain_result = {
            'status': 'restricted',
            'reason': redirect['blocked_reason'],
            'domain_score': None,
            'domain_signals': [],
            'metadata': {'status': 'restricted', 'reason': redirect['blocked_reason']},
            'ti_status': {'status': 'available'},
            'ti_details': {'ti_hits': 0, 'ti_sources': []},
            'redirect_analysis': redirect,
        }
        with patch.object(fusion_engine, 'ML_READY', True), \
             patch.object(fusion_engine, 'DOMAIN_READY', True), \
             patch.object(fusion_engine, 'NLP_READY', False), \
             patch.object(fusion_engine, 'VISION_READY', False), \
             patch('ensemble_module.fusion_engine.predict_url', return_value={'ml_score': 0.42}), \
             patch('ensemble_module.fusion_engine.analyze_domain', return_value=domain_result), \
             patch('ensemble_module.fusion_engine.get_meta_learner') as mock_meta:
            result = await fusion_engine.calculate_ensemble_score(
                'http://127.0.0.1:8000/api/scan/',
                vision_status={'status': 'restricted', 'reason': 'Unsafe screenshot target', 'applicable': True},
            )

        mock_meta.assert_not_called()
        self.assertEqual(result['analysis_status'], 'partial')
        self.assertEqual(result['fusion_method'], 'weighted_available_engines')
        self.assertEqual(result['ensemble_score_percent'], 42.0)
        self.assertEqual(result['individual_scores_percent'], {'ml': 42.0})
        self.assertIn('not itself evidence of phishing', result['xai_summary'])
        signals = {signal['source']: signal for signal in result['xai']['engine_signals']}
        self.assertEqual(signals['url_ml']['score'], 42.0)
        self.assertEqual(signals['domain_intelligence']['status'], 'restricted')
        self.assertNotIn('score', signals['domain_intelligence'])
        self.assertEqual(result['redirect_analysis']['resolution_state'], 'blocked')

    async def test_complete_public_scan_keeps_existing_meta_learner_inputs(self):
        redirect = {
            'original_url': 'https://example.com',
            'final_url': 'https://example.com',
            'redirect_chain': [{'url': 'https://example.com', 'status_code': 200}],
            'num_redirects': 0,
            'loop_detected': False,
            'suspicious_redirects': False,
            'has_meta_refresh': False,
            'resolution_state': 'completed',
            'errors': [],
        }
        domain_result = {
            'status': 'available',
            'domain_score': 0.4,
            'domain_risk_level': 'suspicious',
            'domain_signals': [],
            'metadata': {'age_days': None, 'ssl_valid': False, 'ti_summary': {'ti_hits': 0, 'ti_sources': []}},
            'ti_status': {'status': 'available'},
            'ti_details': {'ti_hits': 0, 'ti_sources': []},
            'redirect_analysis': redirect,
        }
        classifier = Mock()
        classifier.predict_proba.return_value = [[0.25, 0.75]]
        with patch.object(fusion_engine, 'ML_READY', True), \
             patch.object(fusion_engine, 'DOMAIN_READY', True), \
             patch.object(fusion_engine, 'NLP_READY', True), \
             patch.object(fusion_engine, 'VISION_READY', True), \
             patch('ensemble_module.fusion_engine.predict_url', return_value={'ml_score': 0.1}), \
             patch('ensemble_module.fusion_engine.analyze_domain', return_value=domain_result), \
             patch('ensemble_module.fusion_engine.analyze_text_with_nlp', return_value={'nlp_score': 0.2}), \
             patch('ensemble_module.fusion_engine.analyze_image_with_vision', return_value={'vision_score': 0.3}), \
             patch('ensemble_module.fusion_engine.get_meta_learner', return_value=classifier):
            result = await fusion_engine.calculate_ensemble_score(
                'https://example.com',
                text='submitted text',
                image_bytes=b'image',
            )

        classifier.predict_proba.assert_called_once()
        self.assertEqual(classifier.predict_proba.call_args.args[0].tolist(), [[0.1, 0.2, 0.3, 0.4]])
        self.assertEqual(result['ensemble_score_percent'], 75.0)
        self.assertEqual(result['fusion_method'], 'meta_learner')
        self.assertEqual(result['analysis_status'], 'complete')

    async def test_unavailable_ti_does_not_change_complete_scan_fusion(self):
        redirect = {
            'original_url': 'https://example.com',
            'final_url': 'https://example.com',
            'redirect_chain': [{'url': 'https://example.com', 'status_code': 200}],
            'num_redirects': 0,
            'loop_detected': False,
            'suspicious_redirects': False,
            'has_meta_refresh': False,
            'resolution_state': 'completed',
            'errors': [],
        }
        domain_result = {
            'status': 'available',
            'domain_score': 0.4,
            'domain_risk_level': 'suspicious',
            'domain_signals': [],
            'metadata': {'age_days': None, 'ssl_valid': False},
            'ti_status': {
                'status': 'unavailable',
                'reason': 'No threat-intelligence feeds are currently available.',
                'url_scope': 'final_url',
            },
            'ti_details': {
                'ti_hits': 0,
                'ti_sources': [],
                'status': 'unavailable',
            },
            'redirect_analysis': redirect,
        }
        classifier = Mock()
        classifier.predict_proba.return_value = [[0.35, 0.65]]
        with patch.object(fusion_engine, 'ML_READY', True), \
             patch.object(fusion_engine, 'DOMAIN_READY', True), \
             patch.object(fusion_engine, 'NLP_READY', True), \
             patch.object(fusion_engine, 'VISION_READY', True), \
             patch('ensemble_module.fusion_engine.predict_url', return_value={'ml_score': 0.1}), \
             patch('ensemble_module.fusion_engine.analyze_domain', return_value=domain_result), \
             patch('ensemble_module.fusion_engine.analyze_text_with_nlp', return_value={'nlp_score': 0.2}), \
             patch('ensemble_module.fusion_engine.analyze_image_with_vision', return_value={'vision_score': 0.3}), \
             patch('ensemble_module.fusion_engine.get_meta_learner', return_value=classifier):
            result = await fusion_engine.calculate_ensemble_score(
                'https://example.com',
                text='submitted text',
                image_bytes=b'image',
            )

        classifier.predict_proba.assert_called_once()
        self.assertEqual(classifier.predict_proba.call_args.args[0].tolist(), [[0.1, 0.2, 0.3, 0.4]])
        self.assertEqual(result['ensemble_score_percent'], 65.0)
        self.assertEqual(result['fusion_method'], 'meta_learner')
        self.assertEqual(result['analysis_status'], 'partial')
        ti_signal = next(
            signal for signal in result['xai']['engine_signals']
            if signal['source'] == 'threat_intelligence'
        )
        self.assertEqual(ti_signal['status'], 'unavailable')

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

    def test_feature_evidence_preserves_attribution_method(self):
        features = fusion_engine._build_feature_importance(
            {'shap_features': [{'feature': 'url_length', 'value': 32, 'shap_value': 0.17}]},
            {'shap_features': [{'feature': 'urgent', 'shap_value': 0.21}]},
            {'gradcam_features': [{'feature': 'activation region', 'gradcam_activation': 0.63}]},
        )

        by_feature = {item['feature']: item for item in features}
        self.assertEqual(by_feature['url_length']['method'], 'shap')
        self.assertEqual(by_feature['urgent']['method'], 'shap')
        self.assertEqual(by_feature['activation region']['method'], 'grad_cam')
        self.assertEqual(by_feature['url_length']['impact'], 0.17)

    def test_feature_importance_fallback_is_not_mislabeled_as_shap(self):
        features = fusion_engine._build_feature_importance(
            {'shap_features': [{'feature': 'url_length', 'value': 32, 'importance': 7.5}]},
            {'shap_features': [{'feature': 'urgent', 'shap_value': 0.5}]},
            {'gradcam_features': []},
        )

        by_feature = {item['feature']: item for item in features}
        self.assertEqual(by_feature['url_length']['method'], 'catboost_feature_importance')
        self.assertEqual(by_feature['urgent']['method'], 'shap')

    def test_xai_exposes_compact_domain_and_ti_evidence_additively(self):
        domain_evidence, threat_evidence = fusion_engine._build_domain_xai_evidence(
            {
                'status': 'available',
                'final_url': 'https://landing.example/login',
                'domain_score': 0.25,
                'domain_risk_level': 'safe',
                'metadata': {
                    'domain': 'landing.example',
                    'registrable_domain': 'landing.example',
                    'age_days': 1200,
                    'ssl_valid': True,
                    'ssl_issuer': 'Example CA',
                    'resolved_ips': ['93.184.216.34'],
                    'mx_records': ['mail.example'],
                    'rdns': 'host.example',
                    'internal_field': 'not exposed',
                },
                'ti_status': {
                    'status': 'available',
                    'url_scope': 'final_url',
                    'unavailable_sources': ['phishtank'],
                },
                'ti_details': {
                    'status': 'available',
                    'ti_hits': 0,
                    'ti_sources': [],
                    'is_exact_url_match': False,
                },
            },
            None,
        )

        self.assertEqual(domain_evidence['domain_score'], 0.25)
        self.assertEqual(domain_evidence['final_url'], 'https://landing.example/login')
        self.assertEqual(domain_evidence['metadata']['resolved_ips'], ['93.184.216.34'])
        self.assertNotIn('internal_field', domain_evidence['metadata'])
        self.assertEqual(threat_evidence['status'], 'available')
        self.assertEqual(threat_evidence['url_scope'], 'final_url')
        self.assertEqual(threat_evidence['unavailable_sources'], ['phishtank'])
        self.assertEqual(threat_evidence['ti_hits'], 0)

    def test_missing_gradcam_dependency_produces_no_synthetic_features(self):
        import builtins
        from vision_module.vision_service import VisionService

        original_import = builtins.__import__

        def import_without_gradcam(name, *args, **kwargs):
            if name == 'pytorch_grad_cam':
                raise ImportError('Grad-CAM intentionally unavailable in this test')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=import_without_gradcam):
            features = VisionService()._extract_gradcam_features(None)

        self.assertEqual(features, [])

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
                'domain': 'landing.example',
                'registrable_domain': 'landing.example',
                'age_days': None,
                'ssl_valid': True,
                'ssl_issuer': 'Example CA',
                'resolved_ips': ['93.184.216.34'],
                'mx_records': [],
                'ti_summary': {
                    'status': 'available',
                    'ti_hits': 0,
                    'ti_sources': [],
                    'is_exact_url_match': False,
                },
            },
            'final_url': 'https://landing.example/login',
            'ti_status': {'status': 'available', 'url_scope': 'final_url'},
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
        self.assertEqual(
            res['xai']['domain_intelligence']['final_url'],
            'https://landing.example/login',
        )
        self.assertEqual(
            res['xai']['domain_intelligence']['metadata']['ssl_issuer'],
            'Example CA',
        )
        self.assertEqual(res['xai']['threat_intelligence']['url_scope'], 'final_url')
        self.assertEqual(res['xai']['threat_intelligence']['status'], 'available')
        self.assertEqual(res['xai']['threat_intelligence']['ti_hits'], 0)

if __name__ == '__main__':
    unittest.main()
