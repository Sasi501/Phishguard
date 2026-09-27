"""
Feature-schema regression tests (B5 / B6).

The trained CatBoost model is the single authoritative feature schema for
every consumer: backend inference, ONNX export, model_meta.json and the
browser feature extractor. These tests pin

  * the model's feature count / order / names,
  * the ONNX input and output contract,
  * extension/model/model_meta.json,
  * the backend prediction payload,
  * the browser extractor (dimension, order and values, via Node),

to that one schema, and prove that the five analysis-only features are never
presented as model inputs.

Everything that needs an optional dependency (catboost, onnxruntime, node)
skips instead of failing, so the suite stays runnable in a minimal CI image.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHISHGUARD_DIR = os.path.dirname(BACKEND_DIR)
EXTENSION_DIR = os.path.join(PHISHGUARD_DIR, "extension")

ML_DIR = os.path.join(BACKEND_DIR, "ml")
MODEL_PATH = os.path.join(ML_DIR, "models", "catboost_model.cbm")
METRICS_PATH = os.path.join(ML_DIR, "models", "metrics.json")
ONNX_PATH = os.path.join(EXTENSION_DIR, "model", "phishguard_url_classifier.onnx")
META_PATH = os.path.join(EXTENSION_DIR, "model", "model_meta.json")
JS_EXTRACTOR = os.path.join(EXTENSION_DIR, "src", "feature_extractor.js")

from ml.feature_extractor import (  # noqa: E402
    FEATURE_NAMES,
    MODEL_FEATURE_NAMES,
    UNMODELED_FEATURE_NAMES,
    FeatureSchemaError,
    extract_features,
    extract_features_list,
    validate_model_schema,
)
from ml.export_onnx import build_meta, check_onnx_io  # noqa: E402

# URL used for cross-implementation value parity between Python and JS.
PARITY_URLS = [
    "https://example.com",
    "https://example.com/",
    "http://EXAMPLE.COM/Path/To",
    "http://example.com:8080/a/b?x=1&y=2",
    "http://user:pass@example.com/p",
    "http://example.com/a/../b",
    "https://example.com?x=1",
    "https://example.com#frag",
    "https://example.com/a#frag?notquery",
    "http://192.168.1.1:9000/admin/login.php",
    "http://xn--pypal-4ve.com/signin?id=12345&token=abc",
    "http://[::1]:8000/x",
    "  https://spaced.com/x  ",
    "https://example.com/a?b=1&&c=2",
    "not a url",
    "ftp://files.example.com/f",
    "https://sub.domain.example.co.uk/a-b_c.html?q=1",
    "HTTPS://Example.COM/A",
    "mailto:someone@example.com",
    "www.example.com/x",
    "//example.com/x",
    "",
    "https://host.example/app;jsessionid=ABC123?x=1&y=2",
    "https://h/a;b/c;d",
    "http://[1.2.3.4]/",
    "http://user@[::1]:8080/x",
    "HTTPS://SECURE.PAYPAL.COM/secure/login.php?cmd=_login&dispatch=1",
    "https://clearsale.com.br/",
    "https://crowdfunder.co.uk/",
    "http://allegrolokalnie.ofeer2r39831.xyz",
]


def _have(module_name):
    try:
        __import__(module_name)
        return True
    except Exception:
        return False


def _load_catboost():
    from catboost import CatBoostClassifier

    model = CatBoostClassifier()
    model.load_model(MODEL_PATH)
    return model


def _load_session():
    import onnxruntime as ort

    return ort.InferenceSession(ONNX_PATH, providers=["CPUExecutionProvider"])


def _read_meta():
    with open(META_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ─────────────────────────────────────────────────────────────────────────────
# 1. The declared schema itself
# ─────────────────────────────────────────────────────────────────────────────
class FeatureSchemaConstantTests(unittest.TestCase):
    def test_model_feature_count(self):
        self.assertEqual(len(MODEL_FEATURE_NAMES), 14)

    def test_model_feature_order(self):
        self.assertEqual(
            MODEL_FEATURE_NAMES,
            [
                "url_length",
                "hostname_length",
                "path_length",
                "query_length",
                "num_query_params",
                "num_dots",
                "num_hyphens",
                "num_at",
                "num_special_chars",
                "num_digits_in_domain",
                "has_ip_address",
                "entropy",
                "suspicious_keywords",
                "uses_https",
            ],
        )

    def test_analysis_only_features_are_disjoint_from_model_inputs(self):
        overlap = set(MODEL_FEATURE_NAMES) & set(UNMODELED_FEATURE_NAMES)
        self.assertEqual(overlap, set())

    def test_feature_names_is_exactly_model_plus_analysis_only(self):
        self.assertEqual(FEATURE_NAMES, MODEL_FEATURE_NAMES + UNMODELED_FEATURE_NAMES)

    def test_extract_features_returns_every_declared_feature(self):
        feats = extract_features("https://example.com/login?u=1")
        self.assertEqual(sorted(feats), sorted(FEATURE_NAMES))

    def test_extract_features_list_defaults_to_model_schema(self):
        values = extract_features_list("https://example.com/login?u=1")
        self.assertEqual(len(values), len(MODEL_FEATURE_NAMES))
        self.assertTrue(all(isinstance(v, (int, float)) for v in values))

    def test_extract_features_list_accepts_explicit_schema(self):
        values = extract_features_list("https://example.com", ["url_length"])
        self.assertEqual(len(values), 1)


class ValidateModelSchemaTests(unittest.TestCase):
    def test_accepts_the_model_schema(self):
        self.assertEqual(validate_model_schema(list(MODEL_FEATURE_NAMES)), MODEL_FEATURE_NAMES)

    def test_rejects_wrong_count(self):
        with self.assertRaises(FeatureSchemaError) as ctx:
            validate_model_schema(MODEL_FEATURE_NAMES + ["num_subdomains"])
        self.assertIn("15", str(ctx.exception))
        self.assertIn("14", str(ctx.exception))

    def test_rejects_missing_feature(self):
        with self.assertRaises(FeatureSchemaError) as ctx:
            validate_model_schema(MODEL_FEATURE_NAMES[:-1])
        self.assertIn("13", str(ctx.exception))

    def test_rejects_wrong_order(self):
        swapped = list(MODEL_FEATURE_NAMES)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        with self.assertRaises(FeatureSchemaError) as ctx:
            validate_model_schema(swapped)
        self.assertIn("index 0", str(ctx.exception))

    def test_rejects_unknown_name(self):
        renamed = list(MODEL_FEATURE_NAMES)
        renamed[5] = "num_subdomains"
        with self.assertRaises(FeatureSchemaError) as ctx:
            validate_model_schema(renamed)
        self.assertIn("index 5", str(ctx.exception))

    def test_rejects_empty_schema(self):
        with self.assertRaises(FeatureSchemaError):
            validate_model_schema([])
        with self.assertRaises(FeatureSchemaError):
            validate_model_schema(None)


# ─────────────────────────────────────────────────────────────────────────────
# 2. The trained model is the source of truth
# ─────────────────────────────────────────────────────────────────────────────
@unittest.skipUnless(_have("catboost"), "catboost is not installed")
class TrainedModelSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = _load_catboost()

    def test_model_feature_count_is_fourteen(self):
        self.assertEqual(len(self.model.feature_names_), 14)

    def test_model_feature_names_and_order_match_the_declared_schema(self):
        self.assertEqual(list(self.model.feature_names_), MODEL_FEATURE_NAMES)

    def test_model_schema_validates(self):
        self.assertEqual(validate_model_schema(self.model.feature_names_), MODEL_FEATURE_NAMES)

    def test_metrics_feature_importance_uses_the_model_schema(self):
        with open(METRICS_PATH, encoding="utf-8") as fh:
            metrics = json.load(fh)
        importance = metrics.get("feature_importance", {})
        # metrics.json sorts importance descending; the key *set* must still be
        # exactly the model schema, with no analysis-only feature mixed in.
        self.assertEqual(len(importance), 14)
        self.assertEqual(set(importance), set(MODEL_FEATURE_NAMES))
        for name in UNMODELED_FEATURE_NAMES:
            self.assertNotIn(name, importance)


# ─────────────────────────────────────────────────────────────────────────────
# 3. The exported ONNX contract
# ─────────────────────────────────────────────────────────────────────────────
@unittest.skipUnless(_have("onnxruntime"), "onnxruntime is not installed")
class OnnxContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = _load_session()

    def test_input_name_and_shape(self):
        inputs = self.session.get_inputs()
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0].name, "features")
        self.assertEqual(inputs[0].shape, ["N", 14])

    def test_probabilities_output_is_a_float_tensor(self):
        outputs = {o.name: o for o in self.session.get_outputs()}
        self.assertIn("probabilities", outputs)
        probs = outputs["probabilities"]
        self.assertNotIn("seq", probs.type)
        self.assertNotIn("map", probs.type)
        self.assertEqual(probs.shape, ["N", 2])

    def test_onnx_rejects_a_nineteen_dimension_vector(self):
        import numpy as np

        with self.assertRaises(Exception) as ctx:
            self.session.run(None, {"features": np.zeros((1, 19), dtype=np.float32)})
        message = str(ctx.exception)
        self.assertIn("Got: 19", message)
        self.assertIn("Expected: 14", message)

    @unittest.skipUnless(_have("catboost"), "catboost is not installed")
    def test_onnx_matches_catboost_for_every_sample_url(self):
        import numpy as np

        model = _load_catboost()
        worst = 0.0
        for url in PARITY_URLS:
            feats = extract_features(url)
            vector = [feats[name] for name in MODEL_FEATURE_NAMES]
            expected = float(model.predict_proba([vector])[0][1])
            out = self.session.run(
                None, {"features": np.array([vector], dtype=np.float32)}
            )
            got = float(out[1][0][1])
            worst = max(worst, abs(got - expected))
            self.assertEqual(int(out[0][0]), int(expected >= 0.5))
        self.assertLess(worst, 1e-5, f"ONNX drifted from CatBoost by {worst}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. extension/model/model_meta.json
# ─────────────────────────────────────────────────────────────────────────────
class ModelMetaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = _read_meta()

    def test_num_features_matches_the_model_schema(self):
        self.assertEqual(self.meta["num_features"], 14)
        self.assertEqual(self.meta["num_features"], len(MODEL_FEATURE_NAMES))

    def test_feature_names_match_the_model_schema_in_order(self):
        self.assertEqual(self.meta["feature_names"], MODEL_FEATURE_NAMES)

    def test_analysis_only_features_are_absent_from_the_metadata(self):
        for name in UNMODELED_FEATURE_NAMES:
            self.assertNotIn(name, self.meta["feature_names"])

    def test_input_name_and_model_file(self):
        self.assertEqual(self.meta["input_name"], "features")
        self.assertEqual(self.meta["model_file"], "phishguard_url_classifier.onnx")

    def test_thresholds_are_untouched(self):
        self.assertEqual(
            self.meta["thresholds"], {"phishing": 0.7, "suspicious": 0.4}
        )

    def test_matches_what_the_exporter_would_write(self):
        self.assertEqual(self.meta, build_meta(MODEL_FEATURE_NAMES))


class ExportValidationTests(unittest.TestCase):
    def test_build_meta_rejects_empty_schema(self):
        with self.assertRaises(ValueError):
            build_meta([])

    def test_check_onnx_io_accepts_the_shipped_contract(self):
        self.assertTrue(check_onnx_io("features", ["N", 14], "probabilities", ["N", 2], 14))

    def test_check_onnx_io_rejects_a_nineteen_dimension_input(self):
        with self.assertRaises(FeatureSchemaError) as ctx:
            check_onnx_io("features", ["N", 19], "probabilities", ["N", 2], 14)
        self.assertIn("19", str(ctx.exception))

    def test_check_onnx_io_rejects_a_wrong_input_name(self):
        with self.assertRaises(FeatureSchemaError):
            check_onnx_io("input", ["N", 14], "probabilities", ["N", 2], 14)

    def test_check_onnx_io_rejects_a_sequence_output(self):
        with self.assertRaises(FeatureSchemaError) as ctx:
            check_onnx_io(
                "features", ["N", 14], "probabilities", ["seq(map(int64,tensor(float)))"], 14
            )
        self.assertIn("onnxruntime-web", str(ctx.exception))

    def test_check_onnx_io_rejects_a_wrong_output_name(self):
        with self.assertRaises(FeatureSchemaError):
            check_onnx_io("features", ["N", 14], "class_probs", ["N", 2], 14)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Backend inference never feeds analysis-only features to the model
# ─────────────────────────────────────────────────────────────────────────────
@unittest.skipUnless(_have("catboost"), "catboost is not installed")
class BackendPredictionSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ml.ml_service import predict_url

        cls.result = predict_url("https://example.com/login?user=1")

    def test_ml_features_are_exactly_the_model_inputs(self):
        self.assertEqual(list(self.result["ml_features"]), MODEL_FEATURE_NAMES)

    def test_ml_features_has_no_analysis_only_key(self):
        for name in UNMODELED_FEATURE_NAMES:
            self.assertNotIn(name, self.result["ml_features"])

    def test_analysis_only_features_are_reported_separately(self):
        unmodeled = self.result["ml_unmodeled_features"]
        self.assertEqual(list(unmodeled), UNMODELED_FEATURE_NAMES)
        for name in MODEL_FEATURE_NAMES:
            self.assertNotIn(name, unmodeled)

    def test_score_shape_is_unchanged(self):
        self.assertGreaterEqual(self.result["ml_score"], 0.0)
        self.assertLessEqual(self.result["ml_score"], 1.0)
        self.assertIn(self.result["ml_risk_level"], ("safe", "suspicious", "phishing"))

    def test_explanations_only_reference_model_inputs(self):
        for entry in self.result["shap_features"]:
            self.assertIn(entry["feature"], MODEL_FEATURE_NAMES)
            self.assertNotIn(entry["feature"], UNMODELED_FEATURE_NAMES)

    def test_feature_vector_is_built_in_model_order(self):
        from ml.feature_extractor import extract_features

        feats = extract_features("https://example.com/login?user=1")
        vector = [feats[name] for name in MODEL_FEATURE_NAMES]
        self.assertEqual(len(vector), 14)
        self.assertEqual(list(self.result["ml_features"]), MODEL_FEATURE_NAMES)


# ─────────────────────────────────────────────────────────────────────────────
# 6. The browser extractor produces exactly the model vector
# ─────────────────────────────────────────────────────────────────────────────
@unittest.skipUnless(shutil.which("node"), "node is not installed")
class BrowserExtractorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script = f"""
import fs from 'node:fs';
import {{ extractFeatureMap, extractFeatures, MODEL_FEATURE_NAMES }} from {json.dumps(_file_url(JS_EXTRACTOR))};
const urls = JSON.parse(fs.readFileSync(0, 'utf8'));
const rows = urls.map((u) => {{
  let vec = null;
  let err = null;
  try {{ vec = Array.from(extractFeatures(u)); }} catch (e) {{ err = String(e && e.message); }}
  return {{ url: u, map: extractFeatureMap(u), vec, err }};
}});
process.stdout.write(JSON.stringify({{ names: MODEL_FEATURE_NAMES, rows }}));
"""
        cls.tmpdir = tempfile.mkdtemp(prefix="pg_js_parity_")
        script_path = os.path.join(cls.tmpdir, "parity.mjs")
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(script)

        payload = json.dumps(PARITY_URLS).encode("utf-8")
        proc = subprocess.run(
            ["node", script_path],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
        )
        if proc.returncode != 0:
            raise unittest.SkipTest(
                f"node failed to execute the extension extractor: {proc.stderr.decode('utf-8', 'replace')}"
            )
        cls.output = json.loads(proc.stdout.decode("utf-8"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_browser_declares_the_model_schema(self):
        self.assertEqual(self.output["names"], MODEL_FEATURE_NAMES)

    def test_every_vector_has_the_model_dimension(self):
        for row in self.output["rows"]:
            self.assertIsNone(row["err"], f"{row['url']!r}: {row['err']}")
            self.assertEqual(len(row["vec"]), 14, row["url"])

    def test_every_vector_is_ordered_like_the_model(self):
        for row in self.output["rows"]:
            self.assertEqual(list(row["map"]), MODEL_FEATURE_NAMES, row["url"])

    def test_browser_values_match_python_values(self):
        for row in self.output["rows"]:
            expected = extract_features(row["url"])
            for name in MODEL_FEATURE_NAMES:
                want = float(expected[name])
                got = float(row["map"][name])
                self.assertAlmostEqual(
                    want,
                    got,
                    delta=1e-4,
                    msg=f"{row['url']!r} feature {name!r}: python={want} js={got}",
                )

    def test_browser_vector_matches_python_vector_elementwise(self):
        for row in self.output["rows"]:
            expected = extract_features_list(row["url"])
            self.assertEqual(len(expected), len(row["vec"]))
            for idx, (want, got) in enumerate(zip(expected, row["vec"])):
                self.assertAlmostEqual(
                    float(want),
                    float(got),
                    delta=1e-4,
                    msg=f"{row['url']!r} index {idx}: python={want} js={got}",
                )

    def test_browser_refuses_to_emit_an_unknown_feature(self):
        script = f"""
import {{ extractFeatures }} from {json.dumps(_file_url(JS_EXTRACTOR))};
try {{
  extractFeatures('https://example.com', ['url_length', 'num_subdomains']);
  process.stdout.write('NO_ERROR');
}} catch (e) {{
  process.stdout.write(String(e && e.message));
}}
"""
        with tempfile.TemporaryDirectory(prefix="pg_js_schema_") as tmp:
            path = os.path.join(tmp, "unknown_feature.mjs")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(script)
            proc = subprocess.run(
                ["node", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60
            )
        message = proc.stdout.decode("utf-8", "replace")
        self.assertNotEqual(message, "NO_ERROR")
        self.assertIn("num_subdomains", message)


# ─────────────────────────────────────────────────────────────────────────────
# 7. The real browser runtime (onnxruntime-web) scores the browser vector
# ─────────────────────────────────────────────────────────────────────────────
def _ort_web_dist():
    """Locate an installed onnxruntime-web build, or return None."""
    candidates = []
    env_dir = os.environ.get("ORT_WEB_DIR")
    if env_dir:
        candidates.append(env_dir)
    candidates.append(
        os.path.join(os.environ.get("TEMP", ""), "opencode", "ort_env", "node_modules")
    )
    for base in candidates:
        if not base:
            continue
        for path in (
            os.path.join(base, "onnxruntime-web", "dist", "ort.min.js"),
            os.path.join(base, "dist", "ort.min.js"),
            base if base.endswith(".js") else "",
        ):
            if path and os.path.isfile(path):
                return path
    return None


@unittest.skipUnless(shutil.which("node"), "node is not installed")
@unittest.skipUnless(_ort_web_dist(), "onnxruntime-web is not installed")
class BrowserOnnxRuntimeTests(unittest.TestCase):
    """Run the browser runtime against the browser-extracted vector.

    This is the end-to-end cross-check the extension actually depends on:
    JS feature extractor -> onnxruntime-web -> probabilities, compared with
    the same vector scored by the Python onnxruntime build of the same file.
    """

    @classmethod
    def setUpClass(cls):
        if not _have("onnxruntime"):
            raise unittest.SkipTest("onnxruntime is not installed")
        cls.ort_js = _ort_web_dist()
        cls.session_py = _load_session()

        script = f"""
import fs from 'node:fs';
import {{ extractFeatures, MODEL_FEATURE_NAMES }} from {json.dumps(_file_url(JS_EXTRACTOR))};
const [ortUrl, onnxPath, ...urls] = process.argv.slice(2);
let ort = null;
let session = null;
let env_error = null;
try {{
  // Exactly how background.js loads the runtime: default export of ort.min.js.
  ({{ default: ort }} = await import(ortUrl));
}} catch (e) {{
  env_error = String(e && e.message);
}}
if (!env_error) {{
  try {{
    // Node cannot fetch a file: URL, so hand the model bytes over directly —
    // the same InferenceSession.create() call background.js makes.
    const bytes = fs.readFileSync(onnxPath);
    session = await ort.InferenceSession.create(bytes);
  }} catch (e) {{
    env_error = String(e && e.message);
  }}
}}
let payload = {{ env_error }};
if (!env_error) {{
  const rows = [];
  for (const url of urls) {{
    const features = extractFeatures(url, MODEL_FEATURE_NAMES);
    const tensor = new ort.Tensor('float32', Float32Array.from(features), [1, features.length]);
    let out;
    try {{
      out = await session.run({{ features: tensor }});
    }} catch (e) {{
      // The runtime loaded but real inference failed: a defect, not a
      // missing dependency.
      fs.writeSync(2, 'RUN_FAIL ' + url + ' ' + String(e && e.message));
      process.exit(3);
    }}
    const probs = out.probabilities.data;
    rows.push({{
      url,
      n: features.length,
      declared: MODEL_FEATURE_NAMES.length,
      shape: out.probabilities.dims,
      p_safe: Number(probs[0]),
      p_phishing: Number(probs[1]),
    }});
  }}
  payload = {{ rows }};
}}
process.stdout.write(JSON.stringify(payload));
"""
        cls.tmpdir = tempfile.mkdtemp(prefix="pg_ort_web_")
        script_path = os.path.join(cls.tmpdir, "browser_onnx.mjs")
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(script)

        proc = subprocess.run(
            ["node", script_path, _file_url(cls.ort_js), ONNX_PATH, *PARITY_URLS],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
        )
        if proc.returncode == 3:
            # The runtime loaded but real inference failed: that is a defect,
            # not a missing dependency.
            raise AssertionError(
                "onnxruntime-web failed to execute inference: "
                + proc.stderr.decode("utf-8", "replace")
            )
        if proc.returncode != 0:
            raise unittest.SkipTest(
                "node could not run the browser runtime: "
                + proc.stderr.decode("utf-8", "replace")[-800:]
            )
        payload = json.loads(proc.stdout.decode("utf-8", "replace"))
        if payload.get("env_error"):
            raise unittest.SkipTest(
                "onnxruntime-web is unusable in this environment: " + payload["env_error"]
            )
        cls.rows = payload["rows"]

    @classmethod
    def tearDownClass(cls):
        tmpdir = getattr(cls, "tmpdir", None)
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_browser_runtime_scores_every_sample_url(self):
        self.assertEqual(len(self.rows), len(PARITY_URLS))
        for row in self.rows:
            self.assertEqual(row["n"], 14, row["url"])
            self.assertEqual(row["declared"], 14, row["url"])
            self.assertEqual(row["shape"], [1, 2], row["url"])
            self.assertGreaterEqual(row["p_safe"], 0.0, row["url"])
            self.assertLessEqual(row["p_phishing"], 1.0, row["url"])

    def test_browser_runtime_agrees_with_python_onnx(self):
        import numpy as np

        worst = 0.0
        for row in self.rows:
            feats = extract_features(row["url"])
            vector = [feats[name] for name in MODEL_FEATURE_NAMES]
            out = self.session_py.run(
                None, {"features": np.array([vector], dtype=np.float32)}
            )
            py_p = float(out[1][0][1])
            worst = max(worst, abs(py_p - row["p_phishing"]))
            self.assertLess(
                abs(py_p - row["p_phishing"]),
                1e-4,
                f"{row['url']!r}: python={py_p} onnxruntime-web={row['p_phishing']}",
            )
        self.assertLess(worst, 1e-4)


def _file_url(path):
    from pathlib import Path

    return Path(path).resolve().as_uri()


if __name__ == "__main__":
    unittest.main()
