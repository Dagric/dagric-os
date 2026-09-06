#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise actual target-home writes without partitioning or creating OS accounts."""
import configparser
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INC = ROOT / 'config/includes.chroot'
spec = importlib.util.spec_from_file_location('install_profile', INC / 'usr/lib/dagric/install_profile.py')
profile = importlib.util.module_from_spec(spec); spec.loader.exec_module(profile)


class InstalledProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dagric-profile-test-')
        self.root = Path(self.tmp.name)
        (self.root / 'etc').mkdir()
        (self.root / 'etc/passwd').write_text('sample:x:1000:1000:Sample:/home/sample:/bin/bash\n')
        shutil.copytree(INC / 'usr/share/color-schemes', self.root / 'usr/share/color-schemes')
        self.home = self.root / 'home/sample'

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_profiles_round_trip_and_no_second_wizard(self):
        self.assertEqual(len(profile.profiles()), 108)
        for choice in profile.profiles():
            with self.subTest(choice=choice):
                prefs = profile.parse_profile(choice)
                profile.apply_to_target(str(self.root), 'sample', choice)
                config = configparser.ConfigParser(); config.read(self.home / '.config/kdeglobals')
                self.assertEqual(config['Icons']['Theme'], profile.ICONS[prefs['icons']])
                self.assertIn('Dagric', config['General']['ColorScheme'])
                layout = (self.home / '.config/dagric/installed-desktoprc').read_text()
                self.assertIn('Layout=' + prefs['layout'], layout)
                self.assertIn('Wallpaper=' + profile.WALLPAPERS[prefs['wallpaper']], layout)
                marker = self.home / '.config/dagric/firstrun-done'
                self.assertTrue(marker.is_file())
                self.assertEqual(marker.stat().st_uid, 1000)
                self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
                self.assertNotIn('password', (self.home / '.config/dagric/installed-personalization.json').read_text())

    def test_invalid_profiles_do_not_write(self):
        for choice in (None, '', '../../escape', 'dark:eleven:modern:normal:../../escape', 'x' * 101):
            with self.assertRaises((ValueError, TypeError)):
                profile.apply_to_target(str(self.root), 'sample', choice)
        self.assertFalse(self.home.exists())

    def test_refuses_host_root_missing_and_privileged_accounts(self):
        for root, user in (('/', 'sample'), (str(self.root), 'root'), (str(self.root), '../sample')):
            with self.assertRaises(ValueError):
                profile.apply_to_target(root, user, profile.DEFAULT)
        (self.root / 'etc/passwd').write_text('sample:x:0:0:Sample:/home/sample:/bin/bash\n')
        with self.assertRaises(ValueError): profile.apply_to_target(str(self.root), 'sample', profile.DEFAULT)

    def test_symlink_home_is_rejected(self):
        (self.root / 'home').mkdir(); self.home.symlink_to(self.root / 'etc')
        with self.assertRaises(OSError): profile.apply_to_target(str(self.root), 'sample', profile.DEFAULT)
        self.assertFalse((self.root / 'etc/.config').exists())

    def test_existing_wrong_owner_is_rejected(self):
        self.home.mkdir(parents=True)
        with self.assertRaises(ValueError): profile.apply_to_target(str(self.root), 'sample', profile.DEFAULT)

    def test_failure_does_not_mark_setup_done(self):
        original = profile.write_private
        def fail(parent, name, content, uid, gid):
            if name == 'installed-desktoprc': raise OSError('simulated full disk')
            return original(parent, name, content, uid, gid)
        with patch.object(profile, 'write_private', fail), self.assertRaises(OSError):
            profile.apply_to_target(str(self.root), 'sample', profile.DEFAULT)
        self.assertFalse((self.home / '.config/dagric/firstrun-done').exists())


if __name__ == '__main__':
    if os.geteuid() != 0: raise SystemExit('Run in isolated WSL test environment as root; verifies uid 1000 ownership.')
    unittest.main()
