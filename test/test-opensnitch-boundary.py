#!/usr/bin/env python3
"""Managed OpenSnitch unit/source checks and isolated Linux DAC evidence.

Root-only cases create synthetic UID processes and sockets inside one private
test directory, not the installed service or its actual /tmp or /run endpoint.
These checks are NOT physical/installed multi-user approval.
"""
from __future__ import annotations

import errno
import grp
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
INC = ROOT / "config/includes.chroot"
LAUNCHER = INC / "usr/bin/opensnitch-ui"
loader = importlib.machinery.SourceFileLoader("managed_opensnitch", str(LAUNCHER))
spec = importlib.util.spec_from_loader(loader.name, loader)
managed = importlib.util.module_from_spec(spec)
loader.exec_module(managed)


def metadata(kind=stat.S_IFDIR, mode=0o2770, uid=0, gid=27):
    return types.SimpleNamespace(st_mode=kind | mode, st_uid=uid, st_gid=gid)


class BoundaryTests(unittest.TestCase):
    def test_directory_requires_exact_administrator_boundary(self):
        directory = Mock()
        directory.lstat.return_value = metadata()
        managed.validate_directory(directory, 27)
        for changed in (
            metadata(mode=0o2777), metadata(mode=0o770), metadata(uid=1001),
            metadata(gid=1001), metadata(kind=stat.S_IFLNK),
        ):
            with self.subTest(changed=changed):
                directory.lstat.return_value = changed
                with self.assertRaises(PermissionError):
                    managed.validate_directory(directory, 27)

    def test_missing_directory_fails_without_fallback(self):
        directory = Mock()
        directory.lstat.side_effect = FileNotFoundError()
        with self.assertRaises(FileNotFoundError):
            managed.validate_directory(directory, 27)

    def test_root_and_nonadministrators_cannot_run_gui(self):
        for uid, groups in ((0, [0, 27]), (1001, [1001])):
            with self.assertRaises(PermissionError):
                managed.validate_user(uid, groups, 27)
        managed.validate_user(1001, [1001, 27], 27)

    def test_nonadmin_autostart_has_no_modal(self):
        with patch.object(managed.grp, "getgrnam", return_value=types.SimpleNamespace(gr_gid=27)), \
             patch.object(managed.os, "geteuid", return_value=1001), \
             patch.object(managed.os, "getegid", return_value=1001), \
             patch.object(managed.os, "getgroups", return_value=[1001]), \
             patch.object(managed, "error", return_value=1) as error:
            self.assertEqual(managed.main([]), 1)
            self.assertFalse(error.call_args.args[1])

    def test_no_user_supplied_endpoint_or_auth_override(self):
        with patch.object(managed, "error", return_value=1):
            for args in (["--socket", "unix:///tmp/attacker"], ["--socket-auth", "tls"], ["--anything"]):
                self.assertEqual(managed.main(args), 1)

    def test_upstream_requires_trusted_leaf_and_all_ancestors(self):
        leaf = Mock()
        parent = Mock()
        leaf.parents = [parent]
        leaf.lstat.return_value = metadata(stat.S_IFREG, 0o755, gid=0)
        parent.lstat.return_value = metadata(mode=0o755, gid=0)
        managed.validate_upstream(leaf)
        for bad in (metadata(mode=0o777), metadata(uid=1001), metadata(stat.S_IFLNK, 0o755)):
            parent.lstat.return_value = bad
            with self.assertRaises(PermissionError):
                managed.validate_upstream(leaf)
        parent.lstat.return_value = metadata(mode=0o755)
        leaf.lstat.return_value = metadata(stat.S_IFREG, 0o775)
        with self.assertRaises(PermissionError):
            managed.validate_upstream(leaf)

    def test_defaults_are_written_as_user_only_when_absent(self):
        settings = Mock(NoError=0)
        settings.contains.return_value = False
        settings.status.return_value = 0
        managed.seed_defaults(settings)
        settings.setValue.assert_called_once_with("global/default_action", 1)
        settings.reset_mock()
        settings.contains.return_value = True
        managed.seed_defaults(settings)
        settings.setValue.assert_not_called()
        settings.contains.return_value = False
        settings.status.return_value = 1
        with self.assertRaises(OSError):
            managed.seed_defaults(settings)

    def test_admin_exec_uses_exact_fixed_supported_arguments(self):
        settings = Mock(NoError=0)
        settings.contains.return_value = True
        qt = types.ModuleType("PyQt5.QtCore")
        qt.QSettings = Mock(return_value=settings)
        with patch.dict("sys.modules", {"PyQt5": types.ModuleType("PyQt5"), "PyQt5.QtCore": qt}), \
             patch.object(managed.grp, "getgrnam", return_value=types.SimpleNamespace(gr_gid=27)), \
             patch.object(managed.os, "geteuid", return_value=1001), \
             patch.object(managed.os, "getegid", return_value=1001), \
             patch.object(managed.os, "getgroups", return_value=[1001, 27]), \
             patch.object(managed, "validate_directory") as directory, \
             patch.object(managed, "validate_upstream"), \
             patch.object(managed.os, "umask") as umask, \
             patch.object(managed.os, "execv") as execute:
            self.assertEqual(managed.main(["--background"]), 0)
            directory.assert_called_once_with(Path("/run/dagric-opensnitch"), 27)
            umask.assert_called_once_with(0o077)
            execute.assert_called_once_with(str(managed.UPSTREAM), [str(managed.UPSTREAM), "--socket", managed.SOCKET_ADDRESS, "--socket-auth", "simple", "--background"])

    def test_source_endpoints_package_and_locale_wiring(self):
        document = json.loads((INC / "etc/opensnitchd/default-config.json").read_text())
        self.assertEqual(document["Server"]["Address"], managed.SOCKET_ADDRESS)
        unit_path = "usr/lib/systemd/system/opensnitch.service.d/20-dagric-control-socket.conf"
        unit = (INC / unit_path).read_text()
        self.assertIn("ExecStartPre=/usr/bin/opensnitch-ui --check-directory", unit)
        self.assertIn("ExecStartPre=/usr/bin/opensnitch-ui --migrate-config", unit)
        self.assertIn("ExecStart=/usr/bin/opensnitchd -rules-path /etc/opensnitchd/rules -ui-socket " + managed.SOCKET_ADDRESS, unit)
        self.assertNotIn("/tmp/", unit)
        self.assertIn("d /run/dagric-opensnitch 02770 root sudo -", (INC / "usr/lib/tmpfiles.d/dagric-opensnitch.conf").read_text())
        self.assertNotIn("20-dagric-control-socket", (ROOT / "packages/dagric-tools/DEBIAN/conffiles").read_text())
        self.assertIn(unit_path, (ROOT / "packages/stage-packages.sh").read_text())
        upgrade = (INC / "usr/bin/dagric-upgrade-to-pro").read_text()
        self.assertNotIn('chown -R "$uid:$gid"', upgrade)
        self.assertNotIn('mkdir -p "$home/.config/opensnitch"', upgrade)
        self.assertIn('--language=Python', (ROOT / "tools/i18n-extract.sh").read_text())
        self.assertIn("OpenSnitch's control directory", (ROOT / "po/dagric.pot").read_text())


@unittest.skipUnless(os.geteuid() == 0 and Path("/run").is_dir(), "isolated Linux root DAC checks; run with sudo")
class RootFilesystemTests(unittest.TestCase):
    def setUp(self):
        # /run has trusted non-writable ancestors, unlike world-writable /tmp.
        self.temporary = tempfile.TemporaryDirectory(prefix="dagric-osni-test-", dir="/run")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o755)

    def config(self, value):
        path = self.root / "default-config.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        path.chmod(0o644)
        return path

    def test_legacy_configuration_migration_is_narrow_and_private(self):
        document = {"Server": {"Address": "unix:///tmp/osui.sock", "LogFile": "/custom/log", "Authentication": {"Type": "tls"}}, "DefaultAction": "deny", "custom": [1, 2]}
        path = self.config(document)
        managed.migrate_daemon_config(path)
        document["Server"]["Address"] = managed.SOCKET_ADDRESS
        self.assertEqual(json.loads(path.read_text()), document)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(path.stat().st_uid, 0)
        before = path.stat().st_ino
        managed.migrate_daemon_config(path)
        self.assertEqual(path.stat().st_ino, before)
        self.assertEqual(list(self.root.glob(".dagric-socket-*")), [])

    def test_custom_address_is_not_rewritten(self):
        path = self.config({"Server": {"Address": "unix:///custom/admin.sock"}})
        before = path.read_bytes()
        managed.migrate_daemon_config(path)
        self.assertEqual(path.read_bytes(), before)

    def test_missing_config_is_safe_for_free_edition(self):
        managed.migrate_daemon_config(self.root / "absent.json")

    def test_invalid_config_and_unsafe_types_fail_closed(self):
        for value in ([], {"Server": []}):
            path = self.config(value)
            with self.assertRaises(ValueError):
                managed.migrate_daemon_config(path)
        path.unlink()
        target = self.root / "target"
        target.write_text('{}')
        path.symlink_to(target)
        with self.assertRaises(PermissionError):
            managed.migrate_daemon_config(path)
        path.unlink()
        os.mkfifo(path)
        with self.assertRaises(PermissionError):
            managed.migrate_daemon_config(path)
        path.unlink()
        path = self.config({})
        path.chmod(0o666)
        with self.assertRaises(PermissionError):
            managed.migrate_daemon_config(path)
        path.chmod(0o644)
        self.root.chmod(0o777)
        with self.assertRaises(PermissionError):
            managed.migrate_daemon_config(path)

    def child_bind(self, path, uid, groups, expected_errno=None):
        pid = os.fork()
        if pid == 0:
            try:
                os.setgroups(groups)
                os.setgid(uid)
                os.setuid(uid)
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                    try:
                        listener.bind(str(path))
                    except OSError as exc:
                        os._exit(0 if exc.errno == expected_errno else 2)
                os._exit(0 if expected_errno is None else 3)
            except BaseException:
                os._exit(4)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(os.waitstatus_to_exitcode(status), 0)

    def test_attacker_can_precreate_tmp_but_not_managed_endpoint(self):
        admin_gid = grp.getgrnam("sudo").gr_gid
        public = self.root / "tmp"
        public.mkdir(mode=0o777)
        public.chmod(0o1777)
        protected = self.root / "run" / "dagric-opensnitch"
        protected.parent.mkdir(mode=0o755)
        protected.mkdir()
        os.chown(protected, 0, admin_gid)
        protected.chmod(0o2770)
        managed.validate_directory(protected, admin_gid)
        self.child_bind(public / "osui.sock", 65534, [], None)
        self.child_bind(protected / "osui.sock", 65534, [], errno.EACCES)
        self.child_bind(protected / "osui.sock", 60001, [admin_gid], None)
        self.assertTrue(stat.S_ISSOCK((public / "osui.sock").stat().st_mode))
        self.assertTrue(stat.S_ISSOCK((protected / "osui.sock").stat().st_mode))
        self.assertEqual((protected / "osui.sock").stat().st_gid, admin_gid)
        self.assertNotEqual(public / "osui.sock", protected / "osui.sock")


if __name__ == "__main__":
    unittest.main(verbosity=2)
