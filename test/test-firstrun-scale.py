#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline controller regressions; no real monitor settings are changed."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("scale", ROOT / "config/includes.chroot/usr/lib/dagric/firstrun-scale.py")
scale = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scale)


class Trials(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.rows = [("eDP-1", 1920, 1080, 100, "1"), ("DP-1", 2560, 1440, 125, "1.25")]
        self.time = 0
        self.calls = []
        self.fail = None
        self.trial = scale.Trials(self.path, self.path / "status.json", self.read, self.change, lambda: self.time)

    def read(self):
        return list(self.rows)

    def change(self, name, value):
        self.calls.append((name, value))
        if self.fail == name:
            raise subprocess.CalledProcessError(1, "fixture")
        self.rows = [(n, w, h, round(float(value)*100), value) if n == name else (n,w,h,p,s)
                     for n,w,h,p,s in self.rows]

    def phase(self):
        return json.loads((self.path / "status.json").read_text())["phase"]

    def test_trial_keep(self):
        self.trial.command("SCALE|150")
        self.assertEqual(self.phase(), "trial")
        self.assertEqual(self.trial.pending.stat().st_mode & 0o777, 0o600)
        self.trial.command("KEEP")
        self.time = 25
        self.trial.tick()
        self.assertFalse(self.trial.pending.exists())
        self.assertEqual([r[3] for r in self.rows], [150,150])

    def test_timeout_restores_each_original_scale(self):
        self.trial.command("SCALE|150")
        self.time = 20
        self.trial.tick()
        self.assertEqual([r[3] for r in self.rows], [100,125])
        self.assertEqual(self.phase(), "reverted")

    def test_late_keep_cannot_resurrect(self):
        self.trial.command("SCALE|150")
        self.time = 21
        self.trial.command("KEEP")
        self.assertEqual([r[3] for r in self.rows], [100,125])

    def test_explicit_revert(self):
        self.trial.command("SCALE|150")
        self.trial.command("REVERT")
        self.assertEqual([r[3] for r in self.rows], [100,125])

    def test_repeated_trial_requires_decision(self):
        self.trial.command("SCALE|150")
        with self.assertRaises(ValueError):
            self.trial.command("SCALE|125")
        self.trial.restore()

    def test_small_screen_is_not_changed(self):
        self.rows = [("eDP-1", 1280, 720, 100, "1")]
        with self.assertRaises(ValueError):
            self.trial.command("SCALE|150")
        self.assertEqual(self.calls, [])
        self.assertFalse(self.trial.pending.exists())

    def test_crash_receipt_is_not_overwritten(self):
        self.trial.pending.write_text("previous receipt")
        with self.assertRaises(ValueError):
            self.trial.command("SCALE|150")
        self.assertEqual(self.trial.pending.read_text(), "previous receipt")

    def test_unsupported_input(self):
        for line in ("SCALE|999", "SCALE|1;touch /tmp/no", "KEEP|150", "UNKNOWN"):
            with self.assertRaises(ValueError):
                self.trial.command(line)
        self.assertEqual(self.calls, [])

    def test_undo_restores_setup_baseline_after_kept_trials(self):
        self.trial.command("SCALE|150")
        self.trial.command("KEEP")
        self.trial.command("SCALE|125")
        self.trial.command("KEEP")
        self.trial.command("UNDO")
        self.assertEqual([r[3] for r in self.rows], [100,125])

    def test_failed_restore_retains_rescue_and_rejects_late_keep(self):
        self.trial.command("SCALE|150")
        self.fail = "DP-1"
        self.time = 22
        self.trial.tick()
        self.assertEqual(self.phase(), "restore-error")
        self.trial.command("KEEP")
        self.assertTrue(self.trial.pending.exists())
        self.fail = None
        self.trial.tick()
        self.assertFalse(self.trial.pending.exists())

    def test_symlink_state_refused(self):
        link = self.path / "link"
        link.symlink_to(self.path, target_is_directory=True)
        with self.assertRaises(ValueError):
            scale.private_directory(link / "new")

    def test_symlink_pending_refused(self):
        other = self.path / "other"
        other.write_text("untouched")
        self.trial.pending.symlink_to(other)
        with self.assertRaises(ValueError):
            self.trial.command("SCALE|150")
        self.assertEqual(other.read_text(), "untouched")


class WorkerLifetime(unittest.TestCase):
    """Real pipe, process, signal and wall-clock tests; only monitor I/O is fake."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.hardware = self.path / "hardware.json"
        self.hardware.write_text(json.dumps([["eDP-1",1920,1080,100,"1"]]))
        self.status = self.path / "status.json"
        script = """
import importlib.util, json, pathlib, sys, time
spec = importlib.util.spec_from_file_location('worker_fixture', sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
hardware = pathlib.Path(sys.argv[2])
status = sys.argv[3]
def read(): return [tuple(row) for row in json.loads(hardware.read_text())]
def change(name, value):
    hardware.write_text(json.dumps([(n,w,h,round(float(value)*100),value) if n == name else (n,w,h,p,s)
                                    for n,w,h,p,s in read()]))
m.Trials.__init__.__defaults__ = (read, change, time.monotonic)
sys.argv = ['fixture', '--status', status]
m.main()
"""
        self.process = subprocess.Popen([sys.executable, "-u", "-c", script,
            str(ROOT / "config/includes.chroot/usr/lib/dagric/firstrun-scale.py"),
            str(self.hardware), str(self.status)], stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            env=dict(os.environ, XDG_STATE_HOME=str(self.path / "state")))
        self.addCleanup(self.stop)
        self.await_phase("idle")

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=8)
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        self.process.stderr.close()

    def await_phase(self, wanted, seconds=5):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.status.exists():
                if json.loads(self.status.read_text())["phase"] == wanted:
                    return
            if self.process.poll() is not None:
                self.fail(self.process.stderr.read().decode())
            time.sleep(0.02)
        self.fail("controller did not reach " + wanted)

    def begin_trial(self):
        self.process.stdin.write(b"SCALE|150\n")
        self.process.stdin.flush()
        self.await_phase("trial")
        self.assertEqual(json.loads(self.hardware.read_text())[0][3], 150)

    def assert_restored(self):
        self.assertEqual(json.loads(self.hardware.read_text())[0][3], 100)
        self.assertFalse((self.path / "state/dagric/display-pending").exists())

    def test_closed_ui_pipe_restores(self):
        self.begin_trial()
        self.process.stdin.close()
        self.assertEqual(self.process.wait(timeout=8), 0)
        self.assert_restored()

    def test_terminated_controller_restores(self):
        self.begin_trial()
        self.process.terminate()
        self.assertEqual(self.process.wait(timeout=8), 0)
        self.assert_restored()

    def test_real_watchdog_restores_with_no_ui_messages(self):
        self.begin_trial()
        self.await_phase("reverted", seconds=23)
        self.assert_restored()


if __name__ == "__main__":
    unittest.main()
