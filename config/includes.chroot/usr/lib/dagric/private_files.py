#!/usr/bin/python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Private, atomic replacement of Dagric-generated local files.

The caller owns the destination directory and decides whether to create it.
This protects the file leaf and the temporary file, not an attacker-controlled
parent directory. It is not a substitute for a privileged helper's path policy.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


def write_private_text(destination: str | Path, contents: str) -> None:
    """Replace one generated file without following existing file links.

    mkstemp creates a new 0600 inode exclusively. Data is private from the first
    byte, even under umask 000, and no predictable .tmp name is opened. Replacing
    the directory entry also leaves any prior symlink/hardlink target intact.
    If writing or syncing fails, the previous output remains available.
    """
    path = Path(destination)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
