#!/usr/bin/python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""UI-independent Wayland scale trials. No root, network, or arbitrary commands.

stdin: SCALE|100/125/150, KEEP, REVERT, UNDO. EOF/signals/timeouts restore
unconfirmed changes. The existing login rescue consumes display-pending after
a machine crash. The QML view reads the atomic status file, never a success guess.
"""
import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import time


def private_directory(path):
    path = Path(path).absolute()
    for part in reversed([path, *path.parents]):
        if part.is_symlink():
            raise ValueError("symlink state directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.stat().st_uid != os.getuid():
        raise ValueError("state directory is not owned by this user")
    return path


def atomic(path, content):
    temp = path.with_name(path.name + ".tmp-" + str(os.getpid()))
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def outputs():
    result = subprocess.run(
        ["sh", "-c", ". /usr/lib/dagric/display-common.sh; dg_outputs"],
        check=True, capture_output=True, text=True, timeout=5)
    rows = []
    for line in result.stdout.splitlines():
        name, width, height, percent, scale = line.split("\t")
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", name):
            raise ValueError("invalid connector")
        value = float(scale)
        if not math.isfinite(value) or not 0.5 <= value <= 8:
            raise ValueError("invalid scale")
        rows.append((name, int(width), int(height), int(percent), scale))
    if not rows or len(rows) > 16 or len({r[0] for r in rows}) != len(rows):
        raise ValueError("no unambiguous connected screens")
    return rows


def apply(name, scale):
    subprocess.run(["kscreen-doctor", f"output.{name}.scale.{scale}"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)


class Trials:
    def __init__(self, state, status, read=outputs, change=apply, clock=time.monotonic):
        self.pending = state / "display-pending"
        self.status = status
        self.read, self.change, self.clock = read, change, clock
        self.old = None
        self.baseline = None
        self.deadline = 0
        self.target = 0
        self.revision = 0
        self.allowed = []
        try:
            rows = self.read()
            self.allowed = [v for v in (100, 125, 150)
                            if all(w * 100 // v >= 800 and h * 100 // v >= 600 for _,w,h,_,_ in rows)]
            self.report("idle")
        except (OSError, ValueError, subprocess.SubprocessError):
            self.report("error")

    def report(self, phase):
        self.revision += 1
        atomic(self.status, json.dumps({"phase": phase, "scale": self.target,
                                       "revision": self.revision,
                                       "allowed": self.allowed,
                                       "remaining": max(0, math.ceil(self.deadline - self.clock()))}))

    def restore(self, phase="reverted"):
        if self.old is not None:
            # Keep the durable rescue file if ANY output failed to restore.
            failed = False
            for name, _, _, _, scale in self.old:
                try:
                    self.change(name, scale)
                except (OSError, ValueError, subprocess.SubprocessError):
                    failed = True
            if failed:
                self.report("restore-error")
                return False
            self.target = self.old[0][3]
            self.old = None
            self.pending.unlink(missing_ok=True)
        self.deadline = 0
        self.report(phase)
        return True

    def tick(self):
        if self.old is not None and self.clock() >= self.deadline:
            self.restore()

    def command(self, line):
        self.tick()
        if line.startswith("SCALE|"):
            if line not in ("SCALE|100", "SCALE|125", "SCALE|150"):
                raise ValueError("unsupported scale")
            if self.old is not None or self.pending.exists() or self.pending.is_symlink():
                raise ValueError("another display trial needs to finish first")
            rows = self.read()
            target = int(line.split("|")[1])
            if any(w * 100 // target < 800 or h * 100 // target < 600 for _, w, h, _, _ in rows):
                raise ValueError("this size would leave too little usable screen space")
            # Exclusive creation: never replace another tool's crash recovery.
            fd = os.open(self.pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                out.write("".join(f"{r[0]}\t{r[4]}\n" for r in rows))
                out.flush()
                os.fsync(out.fileno())
            self.old = rows
            if self.baseline is None:
                self.baseline = rows
            self.target = target
            self.deadline = self.clock() + 20
            try:
                for row in rows:
                    self.change(row[0], str(target / 100))
                current = self.read()
                if {r[0] for r in current} != {r[0] for r in rows} or any(r[3] != target for r in current):
                    raise ValueError("display did not accept the requested size")
                self.tick()
                if self.old is not None:
                    self.report("trial")
            except (OSError, ValueError, subprocess.SubprocessError):
                self.restore("error")
        elif line == "KEEP":
            if self.old is None or self.clock() >= self.deadline:
                return  # An expired trial cannot be confirmed by a late click.
            self.pending.unlink()
            self.old = None
            self.deadline = 0
            self.report("kept")
        elif line == "REVERT":
            self.restore()
        elif line == "UNDO":
            if not self.restore():
                return
            if self.baseline is not None:
                rows = self.baseline
                fd = os.open(self.pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as out:
                    out.write("".join(f"{r[0]}\t{r[4]}\n" for r in rows))
                    out.flush()
                    os.fsync(out.fileno())
                self.old = rows
                self.restore()
        else:
            raise ValueError("unknown request")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", type=Path, required=True)
    args = parser.parse_args()
    state = private_directory(Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "dagric")
    private_directory(args.status.parent)
    lock = os.open(state / "display-trial.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    if not stat.S_ISREG(os.fstat(lock).st_mode):
        raise ValueError("invalid display lock")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    trial = Trials(state, args.status)
    def stop(*unused):
        raise SystemExit(0)
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, stop)
    buffer = b""
    try:
        while True:
            trial.tick()
            readable, _, _ = select.select([sys.stdin], [], [], 0.25)
            if not readable:
                continue
            chunk = os.read(sys.stdin.fileno(), 1024)
            if not chunk:
                break
            buffer += chunk
            if len(buffer) > 4096:
                raise ValueError("oversized display request")
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                try:
                    trial.command(line.decode("ascii"))
                except (OSError, ValueError, subprocess.SubprocessError):
                    trial.report("error")
    finally:
        if trial.old is not None:
            trial.restore()
        os.close(lock)


if __name__ == "__main__":
    main()
