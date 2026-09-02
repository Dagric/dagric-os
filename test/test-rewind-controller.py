#!/usr/bin/env python3
"""Failure-boundary tests for the privileged Rewind controller."""

import importlib.machinery
import pathlib
import sys
import unittest
import io
import types
from contextlib import redirect_stdout
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
LIB = ROOT / "config/includes.chroot/usr/lib/dagric"
sys.path.insert(0, str(LIB))
loader = importlib.machinery.SourceFileLoader("rewind_controller", str(LIB / "rewind-ctl"))
controller = loader.load_module()


class ExportTests(unittest.TestCase):
    def test_unsupported_filesystem_never_demands_root(self):
        with mock.patch.object(controller, "availability", return_value=(False, "filesystem", "ext4")), \
             mock.patch.object(controller, "require_root") as require_root:
            state = controller.export_state()
        self.assertFalse(state["ready"])
        self.assertEqual("ext4", state["filesystem"])
        require_root.assert_not_called()


class StartSafetyTests(unittest.TestCase):
    def test_low_space_refuses_before_creating_a_snapshot(self):
        usage = types.SimpleNamespace(free=controller.MIN_SNAPSHOT_FREE_BYTES - 1)
        current = mock.Mock()
        current.exists.return_value = False
        with mock.patch.object(controller, "require_ready"), \
             mock.patch.object(controller, "CURRENT", current), \
             mock.patch.object(controller.shutil, "disk_usage", return_value=usage), \
             mock.patch.object(controller, "create_snapshot") as create:
            with self.assertRaisesRegex(controller.RewindError, "at least 1 GB"):
                controller.start_session.__wrapped__("software")
        create.assert_not_called()

    def test_damaged_current_metadata_is_quarantined_and_does_not_trap_rewind(self):
        usage = types.SimpleNamespace(free=controller.MIN_SNAPSHOT_FREE_BYTES)
        current = mock.Mock()
        current.exists.return_value = True
        with mock.patch.object(controller, "require_ready"), \
             mock.patch.object(controller, "CURRENT", current), \
             mock.patch.object(controller, "read_json", return_value=None), \
             mock.patch.object(controller, "quarantine_corrupt_current") as quarantine, \
             mock.patch.object(controller.shutil, "disk_usage", return_value=usage), \
             mock.patch.object(controller, "create_snapshot", return_value=61), \
             mock.patch.object(controller, "atomic_json") as write, \
             mock.patch.object(controller, "log_event"), \
             mock.patch.object(controller, "utc_now", return_value="2026-09-01T10:00:00Z"):
            controller.start_session.__wrapped__("settings")
        quarantine.assert_called_once_with()
        write.assert_called_once()
        self.assertEqual(61, write.call_args.args[1]["pre"])

    def test_valid_active_session_is_never_quarantined(self):
        current = mock.Mock()
        current.exists.return_value = True
        with mock.patch.object(controller, "require_ready"), \
             mock.patch.object(controller, "CURRENT", current), \
             mock.patch.object(controller, "read_json", return_value={"pre": 51}), \
             mock.patch.object(controller, "quarantine_corrupt_current") as quarantine, \
             mock.patch.object(controller, "require_snapshot_headroom") as headroom:
            with self.assertRaisesRegex(controller.RewindError, "Finish the current"):
                controller.start_session.__wrapped__("software")
        quarantine.assert_not_called()
        headroom.assert_not_called()


class FinishRecoveryTests(unittest.TestCase):
    def base_patches(self, *, owned=False):
        fake_current = mock.Mock()
        return (
            fake_current,
            mock.patch.object(controller, "require_ready"),
            mock.patch.object(controller, "CURRENT", fake_current),
            mock.patch.object(controller, "read_json", return_value={
                "preset": "software", "pre": 51, "startedAt": "2026-09-01T10:00:00Z"
            }),
            mock.patch.object(controller, "existing_post", return_value=52),
            mock.patch.object(controller, "pair_is_owned", return_value=owned),
            mock.patch.object(controller, "append_history"),
            mock.patch.object(controller, "create_snapshot"),
            mock.patch.object(controller, "log_event"),
            mock.patch.object(controller, "utc_now", return_value="2026-09-01T10:03:00Z"),
        )

    def test_retry_reuses_post_snapshot_created_before_a_crash(self):
        (current, ready, current_patch, read, existing, owned,
         append, create, log, now) = self.base_patches(owned=False)
        with ready, current_patch, read, existing, owned, \
             append as append_mock, create as create_mock, log, now:
            controller.finish_session.__wrapped__()
            create_mock.assert_not_called()
            append_mock.assert_called_once()
            record = append_mock.call_args.args[0]
            self.assertEqual((51, 52), (record["pre"], record["post"]))
            current.unlink.assert_called_once_with(missing_ok=True)

    def test_retry_does_not_duplicate_a_history_receipt(self):
        (current, ready, current_patch, read, existing, owned,
         append, create, log, now) = self.base_patches(owned=True)
        with ready, current_patch, read, existing, owned, \
             append as append_mock, create as create_mock, log, now:
            controller.finish_session.__wrapped__()
            create_mock.assert_not_called()
            append_mock.assert_not_called()
            current.unlink.assert_called_once_with(missing_ok=True)


class CombinedActionTests(unittest.TestCase):
    def test_start_export_mutates_and_returns_one_catalog(self):
        with mock.patch.object(controller, "start_session") as start, \
             mock.patch.object(controller, "export_state", return_value={"ready": True}) as export:
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(0, controller.main(["rewind-ctl", "start-export", "settings"]))
        start.assert_called_once_with("settings")
        export.assert_called_once_with()
        self.assertEqual({"ready": True}, __import__("json").loads(output.getvalue()))

    def test_finish_export_returns_the_completed_pair_review(self):
        with mock.patch.object(controller, "finish_session", return_value=(41, 42)) as finish, \
             mock.patch.object(controller, "export_state", return_value={"review": {"pre": 41, "post": 42}}) as export:
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(0, controller.main(["rewind-ctl", "finish-export"]))
        finish.assert_called_once_with()
        export.assert_called_once_with((41, 42))
        self.assertEqual(42, __import__("json").loads(output.getvalue())["review"]["post"])

if __name__ == "__main__":
    unittest.main()
