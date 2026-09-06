"""
PhishGuard — Training Data Downloader
Downloads phishing URLs from PhishTank and legitimate URLs from Tranco Top 1M,
then merges them into a single labeled dataset.
"""

import csv
import io
import os
import zipfile

import requests
import pandas as pd


DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(DATA_DIR, "dataset.csv")


def download_phishtank(max_urls=50000):
    """Download verified phishing URLs from PhishTank."""
    print("[*] Downloading PhishTank data...")
    # PhishTank provides a CSV of verified phishing URLs
    url = "http://data.phishtank.com/data/online-valid.csv"
    headers = {"User-Agent": "phishguard/1.0"}

    try:
        r = requests.get(url, headers=headers, timeout=120)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[!] PhishTank download failed: {e}")
        print("[*] Falling back to OpenPhish feed...")
        return download_openphish(max_urls)

    # Parse CSV
    reader = csv.DictReader(io.StringIO(r.text))
    urls = []
    for row in reader:
        if len(urls) >= max_urls:
            break
        phish_url = row.get("url", "").strip()
        if phish_url and phish_url.startswith("http"):
            urls.append(phish_url)

    print(f"[+] Got {len(urls)} phishing URLs from PhishTank")

    # Supplement with OpenPhish if we need more
    if len(urls) < max_urls:
        extra = download_openphish(max_urls - len(urls))
        urls.extend(extra)
        print(f"[+] Total phishing URLs: {len(urls)}")

    return urls[:max_urls]


def download_openphish(max_urls=50000):
    """Download phishing URLs from OpenPhish community feed."""
    print("[*] Downloading OpenPhish feed...")
    url = "https://openphish.com/feed.txt"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        urls = [
            line.strip()
            for line in r.text.splitlines()
            if line.strip() and line.strip().startswith("http")
        ]
        print(f"[+] Got {len(urls)} phishing URLs from OpenPhish")
        return urls[:max_urls]
    except requests.RequestException as e:
        print(f"[!] OpenPhish download failed: {e}")
        return []


def download_tranco(max_urls=50000):
    """Download legitimate domains from Tranco Top 1M list."""
    print("[*] Downloading Tranco Top 1M list...")
    # Tranco provides a daily-updated CSV of top domains
    url = "https://tranco-list.eu/top-1m.csv.zip"

    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[!] Tranco download failed: {e}")
        return []

    # Extract CSV from ZIP
    z = zipfile.ZipFile(io.BytesIO(r.content))
    csv_name = z.namelist()[0]
    csv_data = z.read(csv_name).decode("utf-8")

    urls = []
    reader = csv.reader(io.StringIO(csv_data))
    for row in reader:
        if len(urls) >= max_urls:
            break
        if len(row) >= 2:
            domain = row[1].strip()
            if domain:
                # Convert domain to full URL
                urls.append(f"https://{domain}/")

    print(f"[+] Got {len(urls)} legitimate URLs from Tranco")
    return urls[:max_urls]


def build_dataset(phishing_count=50000, legit_count=50000):
    """
    Download both datasets, label them, merge, shuffle, and save.
    Label: 1 = phishing, 0 = legitimate
    """
    print("=" * 60)
    print("PhishGuard — Dataset Builder")
    print("=" * 60)

    # Download
    phishing_urls = download_phishtank(phishing_count)
    legit_urls = download_tranco(legit_count)

    if not phishing_urls:
        print("[!] ERROR: No phishing URLs downloaded. Cannot build dataset.")
        return None
    if not legit_urls:
        print("[!] ERROR: No legitimate URLs downloaded. Cannot build dataset.")
        return None

    # Build DataFrame
    phishing_df = pd.DataFrame({"url": phishing_urls, "label": 1})
    legit_df = pd.DataFrame({"url": legit_urls, "label": 0})

    # Merge and shuffle
    dataset = pd.concat([phishing_df, legit_df], ignore_index=True)
    dataset = dataset.drop_duplicates(subset="url")
    dataset = dataset.sample(frac=1, random_state=42).reset_index(drop=True)

    # Save
    dataset.to_csv(DATASET_PATH, index=False)
    print(f"\n{'=' * 60}")
    print(f"[+] Dataset saved to: {DATASET_PATH}")
    print(f"[+] Total URLs: {len(dataset)}")
    print(f"    Phishing: {len(dataset[dataset['label'] == 1])}")
    print(f"    Legitimate: {len(dataset[dataset['label'] == 0])}")
    print(f"{'=' * 60}")

    return dataset


if __name__ == "__main__":
    build_dataset()
