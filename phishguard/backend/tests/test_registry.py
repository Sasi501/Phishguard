import unittest
import os
import tempfile

import registry.registry as registry_module
import registry.storage as storage_module
from registry.registry import (
    register_model,
    get_artifact_path,
    get_latest_model_path,
    get_model_metadata,
    list_models,
)


class IsolatedRegistryTestCase(unittest.TestCase):
    """Runs registry tests against a throwaway registry and object store.

    ``REGISTRY_DIR`` and ``SIMULATED_BUCKET_DIR`` are module-level singletons
    that point at the *production* directories. A test that registers an
    artifact without isolating them writes a placeholder file (b'hello') into
    the production ``meta_learner`` namespace, after which
    ``get_latest_model_path('meta_learner')`` resolves to a stub instead of a
    model (defect B1). Isolation keeps the suite from corrupting the
    registry it is meant to test.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = self._tmp.name

        self._saved_registry_dir = registry_module.REGISTRY_DIR
        self._saved_bucket_dir = storage_module.SIMULATED_BUCKET_DIR

        registry_module.REGISTRY_DIR = os.path.join(root, 'registry')
        storage_module.SIMULATED_BUCKET_DIR = os.path.join(root, 'bucket')
        os.makedirs(registry_module.REGISTRY_DIR, exist_ok=True)
        os.makedirs(storage_module.SIMULATED_BUCKET_DIR, exist_ok=True)

    def tearDown(self):
        registry_module.REGISTRY_DIR = self._saved_registry_dir
        storage_module.SIMULATED_BUCKET_DIR = self._saved_bucket_dir
        self._tmp.cleanup()

    def _write_artifact(self, directory: str, name: str, payload: bytes) -> str:
        path = os.path.join(directory, name)
        with open(path, 'wb') as handle:
            handle.write(payload)
        return path


class RegistryTests(IsolatedRegistryTestCase):
    def test_register_and_get_latest(self):
        # create a small temp file to act as an artifact
        with tempfile.TemporaryDirectory() as td:
            src = self._write_artifact(td, 'artifact.bin', b'hello')

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
            src = self._write_artifact(td, 'artifact.bin', b'self-healing-data')

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
            restored_path = get_artifact_path('self_healing_test')
            self.assertIsNotNone(restored_path)
            self.assertTrue(os.path.exists(restored_path))

            # Verify contents are correct
            with open(restored_path, 'rb') as f:
                content = f.read()
            self.assertEqual(content, b'self-healing-data')


class VersionOrderingTests(IsolatedRegistryTestCase):
    def test_auto_increment_does_not_clobber_double_digit_versions(self):
        """Registering past v9 must create v10, then v11 — not overwrite v10.

        Lexicographic ordering ranked 'v9' as the last version, so every
        registration silently replaced v10.
        """
        with tempfile.TemporaryDirectory() as td:
            src = self._write_artifact(td, 'artifact.bin', b'payload')
            for index in range(1, 13):
                register_model('ordering_probe', src)
                with open(get_latest_model_path('ordering_probe'), 'rb') as handle:
                    # newest registration is always the latest resolved artifact
                    self.assertEqual(handle.read(), b'payload')

            versions = list_models('ordering_probe')['ordering_probe']
            self.assertEqual(
                versions,
                [f'v{index}' for index in range(1, 13)],
                'versions must be ordered numerically, not lexicographically',
            )

    def test_latest_is_the_numerically_highest_version(self):
        with tempfile.TemporaryDirectory() as td:
            old = self._write_artifact(td, 'v2.bin', b'old-model')
            new = self._write_artifact(td, 'v10.bin', b'new-model')

            register_model('ordering_probe', old, version='v2')
            register_model('ordering_probe', new, version='v10')

            latest = get_latest_model_path('ordering_probe')
            self.assertEqual(os.path.basename(os.path.dirname(latest)), 'v10')
            with open(latest, 'rb') as handle:
                self.assertEqual(handle.read(), b'new-model')

            metadata = get_model_metadata('ordering_probe')
            self.assertEqual(metadata['version'], 'v10')


if __name__ == '__main__':
    unittest.main()
