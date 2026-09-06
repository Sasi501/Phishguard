import unittest
from vision_module.screenshot_pipeline import capture_screenshot

class ScreenshotPipelineTests(unittest.TestCase):
    def test_placeholder_screenshot(self):
        res = capture_screenshot('http://example.com')
        self.assertIn('image_bytes', res)
        self.assertIn('width', res)
        self.assertIn('height', res)
        self.assertEqual(res['original_url'], 'http://example.com')

if __name__ == '__main__':
    unittest.main()
