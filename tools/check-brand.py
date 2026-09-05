#!/usr/bin/env python3
"""Enforce Dagric's public naming, message, and master-color hierarchy."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SYSTEM = json.loads((SITE / "brand-system.json").read_text(encoding="utf-8"))


def require(text: str, token: str, label: str, failures: list[str]) -> None:
    if token not in text:
        failures.append(f"{label}: missing {token!r}")


def main() -> int:
    failures: list[str] = []
    organization = SYSTEM.get("organization", {})
    expected_identity = {
        "legalName": "IMPRESSIONSDIRECT360 LLC",
        "brandName": "Dagric",
        "productName": "Dagric OS",
        "paidEditionName": "Dagric OS Pro",
    }
    for key, expected in expected_identity.items():
        if organization.get(key) != expected:
            failures.append(f"brand-system.json: {key} must be {expected!r}")

    public_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in SITE.rglob("*.html")
        if path.name != "family.html"
    )
    if re.search(r"\bDGR Operations\b", public_text, re.IGNORECASE):
        failures.append("public website contains retired name DGR Operations")
    if re.search(r"\bImpressions\s+Direct\s+360\s+LLC\b", public_text, re.IGNORECASE):
        failures.append("public website contains an inaccurate spaced legal entity name")
    if re.search(r"\bDAGRiC\b", public_text):
        failures.append("public website contains retired casing DAGRiC")

    homepage = (SITE / "index.html").read_text(encoding="utf-8")
    require(homepage, "Your computer.", "site/index.html", failures)
    require(homepage, "Yours again.", "site/index.html", failures)
    release = json.loads((SITE / "manifest/release.json").read_text(encoding="utf-8"))
    if release.get("distribution", {}).get("status") == "held":
        require(homepage, 'href="/download">Check release status</a>', "site/index.html", failures)
        require(homepage, "Release testing in progress.", "site/index.html", failures)
        if re.search(r">\s*(?:Try Dagric OS Free|Download free)\s*</a>", homepage):
            failures.append("site/index.html: immediate-download CTA conflicts with held release")
    else:
        require(homepage, "Try Dagric OS Free", "site/index.html", failures)
    require(homepage, "Watch the 60-second tour", "site/index.html", failures)
    require(homepage, "No Dagric telemetry", "site/index.html", failures)

    about = (SITE / "about.html").read_text(encoding="utf-8")
    require(about, 'id="brand-architecture"', "site/about.html", failures)
    for name in expected_identity.values():
        require(about, name, "site/about.html", failures)

    review = (SITE / "review.html").read_text(encoding="utf-8")
    require(review, "/brand-system.json", "site/review.html", failures)
    require(review, "Official description", "site/review.html", failures)

    css = (SITE / "assets/site.css").read_text(encoding="utf-8")
    for name, value in SYSTEM.get("visualSystem", {}).get("masterColors", {}).items():
        if name in {"logoBlue", "logoMint"}:
            continue
        if value.lower() not in css.lower():
            failures.append(f"site/assets/site.css: missing master color {name} {value}")

    flow = (ROOT / "docs/DAGRIC-FLOW.md").read_text(encoding="utf-8")
    require(flow, "product-experience theme", "docs/DAGRIC-FLOW.md", failures)
    require(flow, "does not replace the master", "docs/DAGRIC-FLOW.md", failures)

    if failures:
        print("brand-check: FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print("brand-check: identity, hierarchy, messaging, and master colors passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
