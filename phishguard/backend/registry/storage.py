"""
PhishGuard — External Object Storage Interface
Supports simulated cloud storage locally, with boto3/S3 integration when configured.
"""
import os
import shutil
import logging

logger = logging.getLogger(__name__)

# Config
BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "phishguard-model-registry")
STORAGE_PROVIDER = os.environ.get("MODEL_STORAGE_PROVIDER", "mock")  # "mock" or "s3"

# Local folder used to simulate S3/GCS bucket for dev
SIMULATED_BUCKET_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "scratch", "simulated_cloud_bucket")
)

def get_storage_client():
    """Return S3 client if provider is s3 and boto3 is installed, else None."""
    if STORAGE_PROVIDER == "s3":
        try:
            import boto3
            return boto3.client("s3")
        except ImportError:
            logger.warning("[!] boto3 is not installed. Falling back to local mock storage.")
    return None

def upload_model_artifact(model_name: str, version: str, local_filepath: str) -> str:
    """Upload model artifact to remote/simulated storage.

    Returns:
        The remote URI or path where the file was saved.
    """
    filename = os.path.basename(local_filepath)
    s3_key = f"models/{model_name}/{version}/{filename}"

    client = get_storage_client()
    if client:
        try:
            logger.info(f"[*] Uploading {local_filepath} to S3 bucket {BUCKET_NAME} at {s3_key}...")
            client.upload_file(local_filepath, BUCKET_NAME, s3_key)
            return f"s3://{BUCKET_NAME}/{s3_key}"
        except Exception as e:
            logger.error(f"[!] S3 upload failed: {e}. Toggling to mock store.")

    # Mock storage fallback
    dest_path = os.path.join(SIMULATED_BUCKET_DIR, model_name, version, filename)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    logger.info(f"[*] [Mock Cloud Store] Copying {local_filepath} to simulated cloud bucket at {dest_path}")
    shutil.copy2(local_filepath, dest_path)
    return f"mock://{s3_key}"

def download_model_artifact(model_name: str, version: str, dest_filepath: str) -> bool:
    """Download model artifact from remote/simulated storage to a local filepath."""
    filename = os.path.basename(dest_filepath)
    s3_key = f"models/{model_name}/{version}/{filename}"

    client = get_storage_client()
    if client:
        try:
            logger.info(f"[*] Downloading s3://{BUCKET_NAME}/{s3_key} to {dest_filepath}...")
            client.download_file(BUCKET_NAME, s3_key, dest_filepath)
            return True
        except Exception as e:
            logger.error(f"[!] S3 download failed: {e}. Toggling to mock store.")

    # Mock storage fallback
    src_path = os.path.join(SIMULATED_BUCKET_DIR, model_name, version, filename)
    if not os.path.exists(src_path):
        logger.error(f"[!] Simulated cloud artifact not found at: {src_path}")
        return False

    os.makedirs(os.path.dirname(dest_filepath), exist_ok=True)
    logger.info(f"[*] [Mock Cloud Store] Restoring from simulated cloud bucket {src_path} to {dest_filepath}")
    shutil.copy2(src_path, dest_filepath)
    return True
