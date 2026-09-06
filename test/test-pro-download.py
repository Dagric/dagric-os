#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the real optional-download shell fragment; no network or unpacking."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = (ROOT / 'config/hooks/normal/0600-pro-edition.hook.chroot').read_text()
PIN = '05ca56937dbe9aa5ea6b6a18b4cb530f4e508e61ce69afd58caba0414cadebbb'


class DownloadBoundaryTests(unittest.TestCase):
    def probe(self, exit_code, matching, ipv4=False):
        with tempfile.TemporaryDirectory(prefix='dagric-download-test-') as tmp:
            root = Path(tmp); binary = root / 'bin'; binary.mkdir()
            payload = root / 'payload'; payload.write_bytes(b'fixture archive bytes')
            arguments = root / 'arguments'
            curl = binary / 'curl'
            curl.write_text('#!/bin/sh\nset -eu\nprintf "%s\\n" "$@" > "$TEST_ARGS"\n'
                'while [ "$#" -gt 0 ]; do\n'
                '  if [ "$1" = -o ]; then shift; cp "$TEST_PAYLOAD" "$1"; break; fi\n'
                '  shift\ndone\nexit "$TEST_EXIT"\n')
            curl.chmod(0o700)
            start = HOOK.index('PG_VER=3.1\n')
            end = HOOK.index('    if command -v unzip', start)
            fragment = HOOK[start:end] + '\n    echo TEST_ACCEPTED\nfi\n'
            self.assertIn(PIN, fragment)
            fragment = fragment.replace('/tmp/photogimp.XXXXXXXX', str(root / 'photogimp.XXXXXXXX'))
            if matching: fragment = fragment.replace(PIN, hashlib.sha256(payload.read_bytes()).hexdigest())
            result = subprocess.run(['sh', '-eu'], input=fragment, capture_output=True, text=True,
                env={**os.environ, 'PATH': str(binary) + ':' + os.environ['PATH'],
                     'TEST_ARGS': str(arguments), 'TEST_PAYLOAD': str(payload), 'TEST_EXIT': str(exit_code),
                     'DAGRIC_BUILD_IPV4': '1' if ipv4 else '0'})
            self.assertEqual(result.returncode, 0, result.stderr)
            return 'TEST_ACCEPTED' in result.stdout, arguments.read_text().splitlines()

    def test_failed_transfer_with_a_complete_matching_file_is_rejected(self):
        accepted, _ = self.probe(28, True)
        self.assertFalse(accepted)

    def test_successful_transfer_with_wrong_hash_is_rejected(self):
        accepted, _ = self.probe(0, False)
        self.assertFalse(accepted)

    def test_only_successful_and_hash_verified_download_is_accepted(self):
        accepted, arguments = self.probe(0, True)
        self.assertTrue(accepted)
        self.assertIn('--connect-timeout', arguments)
        self.assertIn('--max-time', arguments)
        self.assertNotIn('-4', arguments)

    def test_ipv4_option_is_explicitly_build_only(self):
        accepted, arguments = self.probe(0, True, True)
        self.assertTrue(accepted)
        self.assertIn('-4', arguments)


if __name__ == '__main__':
    unittest.main()
