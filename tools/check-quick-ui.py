#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Require and run the actual Qt Quick regression suite before an ISO build."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
runner = shutil.which('qmltestrunner6') or '/usr/lib/qt6/bin/qmltestrunner'
if not Path(runner).is_file():
    sys.exit('Qt UI validation requires qt6-declarative-dev-tools and qml6-module-qttest; install the build-host dependencies first.')
(ROOT / 'out').mkdir(exist_ok=True)
result = subprocess.run([runner, '-input', str(ROOT / 'test/qml'), '-o', '-,txt'],
                        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}, timeout=150)
sys.exit(result.returncode)
