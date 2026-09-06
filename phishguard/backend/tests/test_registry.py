import unittest
import os
import tempfile
from registry.registry import register_model, get_latest_model_path, list_models, get_model_metadata

class RegistryTests(unittest.TestCase):
    def test_register_and_get_latest(self):
        # create a small temp file to act as an artifact
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, 'artifact.bin')
            with open(src, 'wb') as f:
                f.write(b'hello')

            dest = register_model('meta_learner', src)
            self.assertTrue(os.path.exists(dest))

            latest = get_latest_model_path('meta_learner')
            self.assertIsNotNone(latest)
            self.assertTrue(os.path.exists(latest))

            models = list_models('meta_learner')
            self.assertIn('meta_learner', models)

            meta = get_model_metadata('meta_learner')
            self.assertIsInstance(meta, dict)

    def test_self_healing_from_storage(self):
        # Create a small temp file to act as an artifact
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, 'artifact.bin')
            with open(src, 'wb') as f:
                f.write(b'self-healing-data')

            dest = register_model('self_healing_test', src)
            self.assertTrue(os.path.exists(dest))

            # Read metadata to check storage URI
            meta = get_model_metadata('self_healing_test')
            self.assertIn('storage_uri', meta)
            self.assertTrue(meta['storage_uri'].startswith('mock://') or meta['storage_uri'].startswith('s3://'))

            # Delete the local model file to trigger self-healing
            os.remove(dest)
            self.assertFalse(os.path.exists(dest))

            # Retrieve artifact path again - this should download it from mock storage
            from registry.registry import get_artifact_path
            restored_path = get_artifact_path('self_healing_test')
            self.assertIsNotNone(restored_path)
            self.assertTrue(os.path.exists(restored_path))

            # Verify contents are correct
            with open(restored_path, 'rb') as f:
                content = f.read()
            self.assertEqual(content, b'self-healing-data')

if __name__ == '__main__':
    unittest.main()

