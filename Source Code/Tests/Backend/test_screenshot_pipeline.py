import unittest
from unittest.mock import patch
from vision_module.screenshot_pipeline import capture_screenshot
from vision_module import screenshot_pipeline

class ScreenshotPipelineTests(unittest.TestCase):
    def test_placeholder_screenshot(self):
        res = capture_screenshot('http://example.com')
        self.assertIn('image_bytes', res)
        self.assertIn('width', res)
        self.assertIn('height', res)
        self.assertEqual(res['original_url'], 'http://example.com')

    def test_enabled_capture_validates_destination_before_network_request(self):
        with patch.object(screenshot_pipeline, 'SCREENSHOT_ENABLED', True), \
             patch(
                 'domain_module.redirect_unwrapper.validate_url_for_fetch',
                 side_effect=ValueError('Unsafe destination resolved to blocked address: 127.0.0.1'),
             ), \
             patch('requests.get') as mock_get:
            result = capture_screenshot('http://127.0.0.1:8000/api/scan/')

        mock_get.assert_not_called()
        self.assertFalse(result['is_real_screenshot'])
        self.assertIn('Unsafe destination', result['error'])

if __name__ == '__main__':
    unittest.main()
