#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the actual QML splash for its Settings preview, with no imitation.
Requires Qt 6 Quick Test and the same Qt SVG/Core modules as the OS.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
def main():
    runner = shutil.which("qmltestrunner6") or "/usr/lib/qt6/bin/qmltestrunner"
    if not Path(runner).is_file():
        sys.exit("Qt 6 qmltestrunner is required; run under the Debian build environment.")
    subprocess.run([runner, "-input", str(ROOT / "tools/qml/render-splash.qml")],
                   cwd=ROOT, check=True,
                   env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
if __name__ == "__main__":
    main()
