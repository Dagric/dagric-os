#!/usr/bin/env python3
"""Compatibility entry point for the receipt-verified live-footage pipeline.

The previous implementation assembled still Docker screenshots and rendered a
blurred duplicate of the Dagric desktop behind the main desktop. Both behaviors
violate the current Dagric video standard. Keep this filename for existing task
runners, but route every build through the single-layer, continuous-video
pipeline instead.
"""

from __future__ import annotations

import runpy
from pathlib import Path


PIPELINE = Path(__file__).with_name("assemble-real-vm-footage.py")


def main() -> int:
    if not PIPELINE.is_file():
        raise FileNotFoundError(PIPELINE)
    print(
        "Legacy human-campaign builder redirected to the receipt-verified "
        "continuous live-footage pipeline.",
        flush=True,
    )
    runpy.run_path(str(PIPELINE), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
