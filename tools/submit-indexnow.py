#!/usr/bin/env python3
"""Submit the public Dagric sitemap URLs to IndexNow after a deployment.

The default is a dry run. Pass --submit only after https://dagric.com serves the
current sitemap and the public key file.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITEMAP = ROOT / "site" / "sitemap.xml"
HOST = "dagric.com"
KEY = "0ecaf66dc3a2c9470d4dfd5d60615d25"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def sitemap_urls() -> list[str]:
    document = ET.parse(SITEMAP)
    urls = []
    for node in document.findall(".//sm:url/sm:loc", NS):
        if not node.text:
            continue
        url = node.text.strip()
        if urlsplit(url).netloc != HOST:
            raise ValueError(f"refusing non-{HOST} URL from sitemap: {url}")
        urls.append(url)
    return urls


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--submit",
        action="store_true",
        help="send the request; without this flag only print the payload",
    )
    args = parser.parse_args()

    key_file = ROOT / "site" / f"{KEY}.txt"
    if key_file.read_text(encoding="utf-8").strip() != KEY:
        raise ValueError("IndexNow key file does not match the configured key")

    urls = sitemap_urls()
    if not urls or len(urls) > 10_000:
        raise ValueError(f"unexpected sitemap URL count: {len(urls)}")

    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    if not args.submit:
        print(json.dumps(payload, indent=2))
        print(f"Dry run: {len(urls)} URLs. Pass --submit after deployment.")
        return 0

    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Dagric-IndexNow/1.0 (+https://dagric.com/)",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        print(f"IndexNow accepted {len(urls)} URLs (HTTP {response.status}).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"IndexNow submission failed: {exc}", file=sys.stderr)
        sys.exit(1)
