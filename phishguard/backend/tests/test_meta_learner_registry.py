"""B1 regression tests: the meta-learner that the registry resolves must be a
real, loadable model.

These tests deliberately do NOT mock get_meta_learner / get_latest_model_path:
they exist to catch the state where the registry's "latest" artifact is a
placeholder file rather than a model.
"""
import hashlib
import os
import unittest
import warnings

import joblib
import numpy as np

from registry.registry import (
    get_artifact_path,
    get_latest_model_path,
    get_model_metadata,
)
from ensemble_module import fusion_engine


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MetaLearnerRegistryTests(unittest.TestCase):
    def test_latest_registry_artifact_is_a_loadable_model(self):
        """get_latest_model_path must not resolve to a placeholder artifact."""
        latest = get_latest_model_path("meta_learner")
        self.assertIsNotNone(latest, "registry has no meta_learner artifact")
        self.assertTrue(os.path.exists(latest))

        # The historical failure was a 5-byte b'hello' file.
        self.assertGreater(
            os.path.getsize(latest), 1024,
            f"registry meta_learner artifact is a placeholder: {latest}",
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = joblib.load(latest)
        self.assertTrue(hasattr(model, "predict_proba"), type(model))
        self.assertEqual(model.n_features_in_, 4)

    def test_registry_metadata_points_at_the_resolved_artifact(self):
        latest = get_latest_model_path("meta_learner")
        metadata = get_model_metadata("meta_learner")
        self.assertTrue(metadata, "latest meta_learner has no metadata")
        self.assertEqual(metadata.get("version"), _version_from_path(latest))
        self.assertTrue(get_artifact_path("meta_learner", metadata["version"]))

    def test_active_pointer_resolves_to_a_loadable_model(self):
        """promote_model() output (ensemble_module/models/meta_learner.pkl)
        must be a genuine model, not a placeholder."""
        active_path = fusion_engine.META_LEARNER_PATH
        self.assertTrue(os.path.exists(active_path))
        self.assertGreater(os.path.getsize(active_path), 1024)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = joblib.load(active_path)
        self.assertEqual(model.n_features_in_, 4)

        # The promoted copy must be the same bytes as the registered artifact.
        latest = get_latest_model_path("meta_learner")
        self.assertEqual(_sha256(active_path), _sha256(latest))

    def test_get_meta_learner_loads_without_mocking(self):
        model = fusion_engine.get_meta_learner()
        self.assertIsNotNone(model, "get_meta_learner() returned None")
        self.assertTrue(hasattr(model, "predict_proba"))

    def test_meta_learner_accepts_the_exact_fusion_feature_vector(self):
        """The vector built by calculate_ensemble_score must be accepted."""
        model = fusion_engine.get_meta_learner()
        self.assertIsNotNone(model)

        vector = np.array([[0.4, 0.3, 0.3, 0.6]])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            probabilities = model.predict_proba(vector)[0]
        self.assertEqual(len(probabilities), 2)
        self.assertAlmostEqual(float(probabilities[0]) + float(probabilities[1]), 1.0, places=6)
        self.assertGreaterEqual(float(probabilities[1]), 0.0)
        self.assertLessEqual(float(probabilities[1]), 1.0)

    def test_registry_version_ordering_is_numeric(self):
        """v10 must sort after v9 and after v2 (lexicographic sort broke this)."""
        from registry.registry import _version_sort_key

        versions = ["v1", "v10", "v2", "v9", "v11"]
        self.assertEqual(
            sorted(versions, key=_version_sort_key),
            ["v1", "v2", "v9", "v10", "v11"],
        )


def _version_from_path(path) -> str:
    return os.path.basename(os.path.dirname(path))


if __name__ == "__main__":
    unittest.main()
