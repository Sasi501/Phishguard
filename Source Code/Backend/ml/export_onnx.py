"""
PhishGuard — CatBoost → ONNX Exporter
Exports the trained CatBoost URL classifier to ONNX format for use
in the Chrome extension via onnxruntime-web.

Usage:
    python backend/ml/export_onnx.py

Output:
    extension/model/phishguard_url_classifier.onnx
    extension/model/model_meta.json

Feature schema
--------------
The trained CatBoost model is the authoritative feature schema. Every
dimension and every feature name written to the extension is derived from
the model itself (``model.feature_names_``), never from a hand-maintained
list. The export aborts loudly if the model's schema differs from
``ml.feature_extractor.MODEL_FEATURE_NAMES``, or if the exported ONNX input
or output does not match the model.
"""
import os
import sys
import json

ML_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(ML_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)
MODEL_PATH = os.path.join(ML_DIR, "models", "catboost_model.cbm")
OUTPUT_DIR = os.path.join(ROOT_DIR, "extension", "model")
OUTPUT_ONNX = os.path.join(OUTPUT_DIR, "phishguard_url_classifier.onnx")
META_FILE = os.path.join(OUTPUT_DIR, "model_meta.json")

sys.path.insert(0, BACKEND_DIR)

# ONNX graph input / output tensor names. The extension feeds `features` and
# reads `probabilities`.
INPUT_NAME = "features"
OUTPUT_PROBABILITIES = "probabilities"

# Display thresholds written into model_meta.json. These mirror the URL-risk
# thresholds used by ml_service and must never be tuned by this exporter.
DISPLAY_THRESHOLDS = {"phishing": 0.70, "suspicious": 0.40}


def build_meta(model_feature_names) -> dict:
    """
    Build the extension/model/model_meta.json payload from a model schema.

    `model_feature_names` must already have been passed through
    ml.feature_extractor.validate_model_schema.
    """
    names = [str(name) for name in model_feature_names]
    if not names:
        raise ValueError("build_meta() requires a non-empty model feature schema.")
    return {
        "feature_names": names,
        "num_features": len(names),
        "model_file": os.path.basename(OUTPUT_ONNX),
        "input_name": INPUT_NAME,
        "classes": ["safe", "phishing"],
        "thresholds": dict(DISPLAY_THRESHOLDS),
    }


def check_onnx_io(input_name, input_shape, output_name, output_shape, expected_dim,
                  input_name_want=INPUT_NAME, output_name_want=OUTPUT_PROBABILITIES):
    """
    Verify the ONNX input/output declarations against the model schema.

    Raises FeatureSchemaError on any mismatch so an export can never ship a
    graph whose dimensions disagree with the trained model.
    """
    from ml.feature_extractor import FeatureSchemaError

    input_shape = list(input_shape) if input_shape is not None else []
    output_shape = list(output_shape) if output_shape is not None else []

    if input_name != input_name_want:
        raise FeatureSchemaError(
            f"ONNX input is named {input_name!r} but the extension feeds {input_name_want!r}."
        )
    if not input_shape:
        raise FeatureSchemaError("ONNX input declares no shape.")
    if input_shape[-1] != expected_dim:
        raise FeatureSchemaError(
            f"ONNX input dimension is {input_shape[-1]!r} but the trained model "
            f"expects {expected_dim} features."
        )

    if output_name != output_name_want:
        raise FeatureSchemaError(
            f"ONNX output is named {output_name!r} but the extension reads {output_name_want!r}."
        )
    if not output_shape or output_shape[-1] != 2:
        raise FeatureSchemaError(
            f"ONNX {output_name_want!r} output must be a float tensor of shape "
            f"[N, 2] (prob_safe, prob_phishing); observed {output_shape!r}. "
            "Sequence/map outputs cannot be read by onnxruntime-web."
        )

    return True


def expose_probabilities_tensor(onnx_path):
    """
    Make `probabilities` a plain ``tensor(float)[N, 2]`` graph output.

    CatBoost's exporter appends a ``ZipMap`` that materialises the class
    probabilities as ``seq(map(int64, tensor(float)))``. onnxruntime-web
    cannot read sequence/map outputs at all — ``session.run()`` fails with
    "Reading data from non-tensor typed value is not supported" — so on-device
    inference could never produce a result.

    The ZipMap is dropped and ``TreeEnsembleClassifier``'s own
    ``probability_tensor`` is published under the same ``probabilities``
    output name. This is a container change only: no weight, threshold or
    arithmetic is modified, and the values are bit-identical to the ZipMap
    output (verified by tests/test_feature_schema.py).

    Returns the observed output shape.
    Raises FeatureSchemaError if the graph is not in the expected shape.
    """
    from ml.feature_extractor import FeatureSchemaError

    try:
        import onnx
        from onnx import TensorProto, helper
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise FeatureSchemaError(
            "The `onnx` package is required to export a browser-readable graph "
            "(pip install onnx)."
        ) from exc

    model = onnx.load(onnx_path)
    graph = model.graph

    zipmap = next(
        (n for n in graph.node if n.op_type == "ZipMap" and OUTPUT_PROBABILITIES in n.output),
        None,
    )

    if zipmap is None:
        # Nothing to rewrite — just report what is actually there.
        out = next((o for o in graph.output if o.name == OUTPUT_PROBABILITIES), None)
        if out is None or not out.type.HasField("tensor_type"):
            raise FeatureSchemaError(
                f"Graph has no tensor output named {OUTPUT_PROBABILITIES!r}; "
                f"outputs are {[o.name for o in graph.output]}."
            )
        return [str(d.dim_param or d.dim_value) for d in out.type.tensor_type.shape.dim]

    prob_tensor = zipmap.input[0]
    producer = next((n for n in graph.node if prob_tensor in n.output), None)
    if producer is None:
        raise FeatureSchemaError(
            f"ZipMap input {prob_tensor!r} is not produced by any node in the graph."
        )

    num_classes = None
    for attr in producer.attribute:
        if attr.name == "classlabels_int64s":
            num_classes = len(list(attr.ints))
            break
        if attr.name == "classlabels_strings":
            num_classes = len(list(attr.strings))
            break
    if not num_classes:
        raise FeatureSchemaError("Could not determine the number of model classes.")

    graph.node.remove(zipmap)
    producer.output[list(producer.output).index(prob_tensor)] = OUTPUT_PROBABILITIES
    for i, out in enumerate(graph.output):
        if out.name == OUTPUT_PROBABILITIES:
            graph.output[i].CopyFrom(
                helper.make_tensor_value_info(
                    OUTPUT_PROBABILITIES, TensorProto.FLOAT, ["N", num_classes]
                )
            )
    for i in range(len(graph.value_info) - 1, -1, -1):
        if graph.value_info[i].name == prob_tensor:
            del graph.value_info[i]

    try:
        onnx.checker.check_model(model)
    except Exception as exc:  # pragma: no cover - defensive
        raise FeatureSchemaError(f"Rewritten ONNX graph failed validation: {exc}") from exc

    onnx.save(model, onnx_path)
    return ["N", str(num_classes)]


def _verify_onnx_io(onnx_path, expected_dim):
    """
    Open the freshly exported ONNX file and verify its input/output shapes.

    Returns ((input_name, input_shape), (output_name, output_shape)), or None
    when onnxruntime is not installed (reported as skipped, never as passed).
    """
    try:
        import onnxruntime as ort
    except ImportError:
        print("[!] SKIPPED: onnxruntime is not installed — ONNX I/O shapes were NOT verified.")
        return None

    session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    if not inputs or not outputs:
        from ml.feature_extractor import FeatureSchemaError
        raise FeatureSchemaError("Exported ONNX graph has no inputs or no outputs.")

    observed_in = (inputs[0].name, list(inputs[0].shape))
    observed_out = (outputs[0].name, list(outputs[0].shape))
    # `probabilities` is the second graph output; fall back to a name lookup.
    for out in outputs:
        if out.name == OUTPUT_PROBABILITIES:
            observed_out = (out.name, list(out.shape))
            break

    check_onnx_io(
        observed_in[0], observed_in[1],
        observed_out[0], observed_out[1],
        expected_dim,
    )
    return observed_in, observed_out


def export():
    print("=" * 60)
    print("PhishGuard -- CatBoost -> ONNX Export")
    print("=" * 60)

    if not os.path.exists(MODEL_PATH):
        print(f"[!] CatBoost model not found at {MODEL_PATH}")
        print("    Run backend/ml/train_model.py first.")
        sys.exit(1)

    print(f"[*] Loading CatBoost model from: {MODEL_PATH}")
    from catboost import CatBoostClassifier
    from ml.feature_extractor import FeatureSchemaError, validate_model_schema

    model = CatBoostClassifier()
    model.load_model(MODEL_PATH)
    print("[+] Model loaded successfully.")

    # ── Fail loudly on any feature-schema drift ──────────────────────────────
    try:
        model_feature_names = validate_model_schema(model.feature_names_)
    except FeatureSchemaError as exc:
        print("[!] FEATURE SCHEMA MISMATCH — export aborted.")
        print(f"    {exc}")
        sys.exit(1)
    print(
        f"[+] Model feature schema verified: {len(model_feature_names)} features, "
        "declared order matches MODEL_FEATURE_NAMES."
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"[*] Exporting to ONNX: {OUTPUT_ONNX}")
    model.save_model(
        OUTPUT_ONNX,
        format="onnx",
        export_parameters={
            "onnx_domain": "ai.catboost",
            "onnx_model_version": 1,
            "onnx_doc_string": "PhishGuard URL Phishing Classifier",
            "onnx_graph_name": "PhishGuardURLClassifier",
        },
    )
    print(f"[+] ONNX model exported: {OUTPUT_ONNX}")
    print(f"    File size: {os.path.getsize(OUTPUT_ONNX) / 1024:.1f} KB")

    # ── Make `probabilities` readable by onnxruntime-web (container only) ────
    try:
        expose_probabilities_tensor(OUTPUT_ONNX)
        print("[+] `probabilities` published as a float tensor [N, 2] "
              "(ZipMap removed; values unchanged).")
    except FeatureSchemaError as exc:
        print("[!] ONNX OUTPUT MISMATCH — export aborted.")
        print(f"    {exc}")
        sys.exit(1)

    # ── Fail loudly if the exported graph disagrees with the model ───────────
    try:
        observed = _verify_onnx_io(OUTPUT_ONNX, len(model_feature_names))
    except FeatureSchemaError as exc:
        print("[!] ONNX I/O MISMATCH — export aborted.")
        print(f"    {exc}")
        sys.exit(1)
    if observed is not None:
        (in_name, in_shape), (out_name, out_shape) = observed
        print(f"[+] ONNX input verified:  {in_name}{in_shape} (== {len(model_feature_names)} model features)")
        print(f"[+] ONNX output verified: {out_name}{out_shape} tensor(float)")

    # Export feature names so the JS builds the vector in the exact same order
    meta = build_meta(model_feature_names)
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[+] Model metadata saved: {META_FILE}")
    print(f"    Features ({meta['num_features']}): {', '.join(meta['feature_names'])}")

    print("\n" + "=" * 60)
    print("EXPORT COMPLETE!")
    print("=" * 60)
    print("    Load in extension with:")
    print("  const session = await InferenceSession.create('model/phishguard_url_classifier.onnx')")


if __name__ == "__main__":
    export()
