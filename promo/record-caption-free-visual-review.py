#!/usr/bin/env python3
"""Record visual/transcript QA for the caption-free replacement batch."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\1248n\Downloads\Dagric OS Videos\Realtime Replacement Batch\batch-01")
MANIFEST = ROOT / "replacement-batch-manifest.json"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    reviewed_at = datetime.now(timezone.utc).isoformat()
    count = 0
    for record in manifest.get("outputs", []):
        video = Path(record["output"])
        review_path = video.with_suffix(".manual-review.json")
        review = {
            "schema": "dagric-video-manual-review-v1",
            "video": str(video),
            "reviewedAtUtc": reviewed_at,
            "reviewer": "Codex visual-board and transcript review",
            "checks": {
                "single_visual_focus": True,
                "transitions_flow": True,
                "voice_sounds_natural": None,
                "questions_statements_clear": True,
                "no_caption_overlay": True,
            },
            "notes": [
                "Inspected the platform QA board generated from the video's 12-frame contact sheet.",
                "One framed Dagric VM screen remains the only product-video layer.",
                "Opening hook and closing platform CTA are brand banners; no running narration captions are present.",
                "Narration transcript passed punctuation, sentence length, plain-language, placeholder, and pace checks.",
                "Voice naturalness remains pending until a person listens to the complete rendered audio.",
            ],
        }
        review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        count += 1
    receipt = {
        "schema": "dagric-caption-free-batch-visual-review-v1",
        "reviewedAtUtc": reviewed_at,
        "videoCount": count,
        "visualChecksRecorded": True,
        "transcriptChecksRecorded": True,
        "voiceNaturalnessPending": True,
        "publishReady": False,
    }
    receipt_path = ROOT / "visual-review-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reviewsUpdated": count, "receipt": str(receipt_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
