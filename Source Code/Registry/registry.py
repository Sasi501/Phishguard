"""
Simple filesystem-backed model registry for PhishGuard prototypes.

This registry stores model artifacts under backend/registry/models/<name>/<version>/
with a metadata.json alongside the artifact. It provides functions to register
and list models and to retrieve the path to the latest version for loading.

This is intentionally lightweight and intended as a local prototype. Replace
with MLflow/DVC or cloud storage for production.
"""
import os
import json
import shutil
from typing import Optional, Dict, Any

REGISTRY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')


def _version_sort_key(version: str):
    """Order version names numerically so that v2 < v10.

    Plain ``sorted()`` is lexicographic, which ranks 'v10' *before* 'v9' and
    therefore made ``get_latest_model_path()`` resolve to v9 instead of the
    highest registered version. Non-numeric versions sort after numeric ones
    and keep their text order.
    """
    core = version[1:] if version[:1].lower() == 'v' else version
    if core.isdigit():
        return (0, int(core), '')
    return (1, 0, version)


def _sorted_versions(versions) -> list:
    return sorted(versions, key=_version_sort_key)


def _latest_version(name: str) -> Optional[str]:
    model_path = os.path.join(REGISTRY_DIR, name)
    if not os.path.exists(model_path):
        return None
    versions = _sorted_versions(d for d in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, d)))
    return versions[-1] if versions else None


def _model_dir(name: str, version: str) -> str:
    return os.path.join(REGISTRY_DIR, name, version)


def list_models(name: Optional[str] = None) -> Dict[str, Any]:
    """List registered models. If name is provided, return versions for that model."""
    if not os.path.exists(REGISTRY_DIR):
        return {}
    out = {}
    if name:
        model_path = os.path.join(REGISTRY_DIR, name)
        if not os.path.exists(model_path):
            return {}
        versions = _sorted_versions(os.listdir(model_path))
        out[name] = versions
        return out

    for model_name in os.listdir(REGISTRY_DIR):
        path = os.path.join(REGISTRY_DIR, model_name)
        if os.path.isdir(path):
            out[model_name] = _sorted_versions(os.listdir(path))
    return out


def _read_metadata(path: str) -> Dict[str, Any]:
    meta_file = os.path.join(path, 'metadata.json')
    if not os.path.exists(meta_file):
        return {}
    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def get_latest_model_path(name: str) -> Optional[str]:
    """Return the artifact path for the latest version of the named model, or None.

    "Latest" is the numerically highest registered version (v10 > v9 > v2).
    """
    latest = _latest_version(name)
    if latest is None:
        return None
    return get_artifact_path(name, latest)



def register_model(name: str, artifact_src: str, version: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Register a model artifact into the registry.

    Args:
      name: logical model name (e.g., "meta_learner")
      artifact_src: path to the model artifact file to copy into registry
      version: optional explicit version string. If omitted a numeric increment is used.
      metadata: optional dict stored alongside artifact

    Returns: path to the copied artifact in the registry.
    """
    if metadata is None:
        metadata = {}

    if not os.path.exists(artifact_src):
        raise FileNotFoundError(f"Artifact not found: {artifact_src}")

    # Make base model dir
    base = os.path.join(REGISTRY_DIR, name)
    os.makedirs(base, exist_ok=True)

    # Determine version
    if version is None:
        # auto-increment numeric versions (ordered numerically, so v10 -> v11)
        existing = _sorted_versions(
            [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
        ) if os.path.exists(base) else []
        if not existing:
            version = 'v1'
        else:
            # try to parse last numeric suffix
            last = existing[-1]
            core = last[1:] if last[:1].lower() == 'v' else last
            if core.isdigit():
                version = f'v{int(core) + 1}'
            else:
                # fallback to a version that cannot collide with the last one
                version = f'v{len(existing) + 1}'

    dest_dir = _model_dir(name, version)
    os.makedirs(dest_dir, exist_ok=True)

    # Copy artifact
    artifact_name = os.path.basename(artifact_src)
    dest_artifact = os.path.join(dest_dir, artifact_name)
    if os.path.exists(dest_artifact):
        os.remove(dest_artifact)
    shutil.copy2(artifact_src, dest_artifact)

    # Upload to remote / simulated storage
    storage_uri = None
    try:
        from registry.storage import upload_model_artifact
        storage_uri = upload_model_artifact(name, version, dest_artifact)
    except Exception as e:
        pass

    # Write metadata.json
    meta = dict(metadata)
    meta.update({
        'name': name,
        'version': version,
        'artifact': artifact_name,
        'storage_uri': storage_uri
    })
    with open(os.path.join(dest_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    return dest_artifact


def get_model_metadata(name: str, version: Optional[str] = None) -> Dict[str, Any]:
    """Return metadata for a model. If version omitted, returns latest metadata."""
    if version is None:
        version = _latest_version(name)
        if version is None:
            return {}
    path = _model_dir(name, version)
    return _read_metadata(path)


def get_artifact_path(name: str, version: Optional[str] = None) -> Optional[str]:
    """Return the full path to the artifact file for a given model and version. If version omitted, uses latest."""
    if version is None:
        version = _latest_version(name)
        if version is None:
            return None
    
    candidate = _model_dir(name, version)
    artifact_file = None
    
    # Try finding local file
    if os.path.exists(candidate):
        for entry in os.listdir(candidate):
            if entry == 'metadata.json':
                continue
            artifact_file = os.path.join(candidate, entry)
            break

    # If local file missing but candidate directory exists (or metadata is somehow accessible),
    # attempt self-healing from simulated/remote object storage.
    if not artifact_file or not os.path.exists(artifact_file):
        meta = _read_metadata(candidate)
        filename = meta.get('artifact')
        if filename:
            target_dest = os.path.join(candidate, filename)
            try:
                from registry.storage import download_model_artifact
                if download_model_artifact(name, version, target_dest):
                    artifact_file = target_dest
            except Exception:
                pass

    return artifact_file


def promote_model(name: str, version: Optional[str] = None, target_path: Optional[str] = None) -> Optional[str]:
    """
    Promote a model version to be the active artifact for loading by services.
    By default this copies the artifact to ensemble_module/models/<name>.pkl (target_path can override).
    Returns the destination path or None if not found.
    """
    # Resolve source artifact
    model_path = os.path.join(REGISTRY_DIR, name)
    if not os.path.exists(model_path):
        return None
    versions = _sorted_versions(os.listdir(model_path))
    if not versions:
        return None
    if version is None:
        version = versions[-1]
    src_dir = _model_dir(name, version)
    if not os.path.exists(src_dir):
        return None
    # find artifact file
    artifact_file = None
    for f in os.listdir(src_dir):
        if f == 'metadata.json':
            continue
        artifact_file = os.path.join(src_dir, f)
        break
    if artifact_file is None:
        return None

    # Default target path (ensemble meta_learner location)
    if target_path is None:
        target_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ensemble_module', 'models', f"{name}.pkl")
        # ensure target dir exists
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

    shutil.copy2(artifact_file, target_path)

    # Write active pointer
    active_file = os.path.join(REGISTRY_DIR, f"{name}_active.json")
    try:
        with open(active_file, 'w', encoding='utf-8') as f:
            json.dump({'name': name, 'version': version, 'artifact': os.path.basename(artifact_file)}, f)
    except Exception:
        pass

    return target_path
