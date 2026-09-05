#!/usr/bin/env python3
"""Mutation tests for the actual embedded immutable-image security audit.

Fixtures contain text/listing data only. No image is mounted or executed.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
script = (ROOT / 'tools/check-artifacts.sh').read_text(encoding='utf-8')
code = script.split("<<'DAGRIC_SECURITY_ARTIFACT_PY'\n", 1)[1].split('\nDAGRIC_SECURITY_ARTIFACT_PY', 1)[0]
namespace = {'__name__': 'artifact_fixture'}
exec(compile(code, 'check-artifacts.sh:security', 'exec'), namespace)


class SecurityArtifactTests(unittest.TestCase):
    def setUp(self):
        self.files = {}
        self.listing = {}
        self.expected = {}
        for path, source in namespace['SOURCE_FILES'].items():
            content = (ROOT / source).read_bytes()
            self.files[path] = content
            self.expected[path] = content
            self.listing[path] = ('-rwxr-xr-x', 'root/root', '')
        for path in (namespace['DROPIN'], 'usr/lib/tmpfiles.d/dagric-opensnitch.conf', 'etc/opensnitchd/default-config.json'):
            self.files[path] = (ROOT / 'config/includes.chroot' / path).read_bytes()
            self.listing[path] = ('-rw-r--r--', 'root/root', '')
        self.files['var/lib/dpkg/info/dagric-tools.list'] = ('\n'.join('/' + path for path in self.files) + '\n').encode()
        self.files['var/lib/dpkg/diversions'] = b'/usr/bin/opensnitch-ui\n/usr/lib/dagric/opensnitch-ui-upstream\ndagric-tools\n'

    def audit(self, edition='free'):
        namespace['audit_security_payload'](self.files.__getitem__, self.listing, edition, self.expected)

    def add_pro(self):
        self.files['usr/lib/dagric/opensnitch-ui-upstream'] = b'parser.add_argument("--socket")'
        self.listing['usr/lib/dagric/opensnitch-ui-upstream'] = ('-rwxr-xr-x', 'root/root', '')
        desktop = 'usr/share/applications/opensnitch_ui.desktop'
        self.files[desktop] = b'[Desktop Entry]\nExec=opensnitch-ui\n'
        self.listing['etc/xdg/autostart/opensnitch_ui.desktop'] = ('lrwxrwxrwx', 'root/root', '/' + desktop)

    def test_free_guard_and_pro_menu_autostart_are_valid(self):
        self.audit()
        self.add_pro()
        self.audit('pro')

    def test_exact_path_not_pycache_prefix(self):
        path = 'usr/lib/dagric/private_files.py'
        self.listing[path + 'c'] = self.listing.pop(path)
        with self.assertRaisesRegex(ValueError, 'missing exact'):
            self.audit()

    def test_stale_security_code_rejected_against_recorded_commit(self):
        self.files['usr/bin/opensnitch-ui'] += b'\n# stale build\n'
        with self.assertRaisesRegex(ValueError, 'differs from recorded source'):
            self.audit()

    def test_crlf_build_normalization_is_allowed(self):
        self.files['usr/bin/opensnitch-ui'] = self.files['usr/bin/opensnitch-ui'].replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        self.audit()

    def test_unpackaged_helper_fails(self):
        self.files['var/lib/dpkg/info/dagric-tools.list'] = self.files['var/lib/dpkg/info/dagric-tools.list'].replace(b'/usr/lib/dagric/private_files.py\n', b'')
        with self.assertRaisesRegex(ValueError, 'not owned'):
            self.audit()

    def test_unsafe_launcher_permissions_fail(self):
        self.listing['usr/bin/opensnitch-ui'] = ('-rwxrwxrwx', 'root/root', '')
        with self.assertRaisesRegex(ValueError, 'writable'):
            self.audit()

    def test_old_tmp_endpoint_and_public_directory_fail(self):
        path = 'etc/opensnitchd/default-config.json'
        original = self.files[path]
        self.files[path] = original.replace(b'/run/dagric-opensnitch/', b'/tmp/')
        with self.assertRaisesRegex(ValueError, 'protected endpoint'):
            self.audit()
        self.files[path] = original
        self.files['usr/lib/tmpfiles.d/dagric-opensnitch.conf'] = b'd /run/dagric-opensnitch 02777 root sudo -\n'
        with self.assertRaisesRegex(ValueError, '2770'):
            self.audit()

    def test_wrong_diversion_and_surviving_conffile_fail(self):
        original = self.files['var/lib/dpkg/diversions']
        self.files['var/lib/dpkg/diversions'] = original.replace(b'dagric-tools', b'other-package')
        with self.assertRaisesRegex(ValueError, 'diversion'):
            self.audit()
        self.files['var/lib/dpkg/diversions'] = original
        self.listing['etc/systemd/system/opensnitch.service.d/20-dagric-control-socket.conf'] = ('-rw-r--r--', 'root/root', '')
        with self.assertRaisesRegex(ValueError, 'under /etc'):
            self.audit()

    def test_pro_needs_vendor_and_managed_autostart(self):
        with self.assertRaisesRegex(ValueError, 'missing exact'):
            self.audit('pro')
        self.add_pro()
        self.listing['etc/xdg/autostart/opensnitch_ui.desktop'] = ('lrwxrwxrwx', 'root/root', '/wrong.desktop')
        with self.assertRaisesRegex(ValueError, 'autostart'):
            self.audit('pro')

    def test_pro_enabled_daemon_dependencies_are_rejected(self):
        self.add_pro()
        for name in ('docker.service', 'docker.socket', 'containerd.service', 'ssh.service', 'sshd.service', 'ssh.socket'):
            for suffix in ('multi-user.target.wants', 'sockets.target.requires'):
                path = 'etc/systemd/system/' + suffix + '/' + name
                self.listing[path] = ('lrwxrwxrwx', 'root/root', '../' + name)
                with self.assertRaisesRegex(ValueError, 'unexpected enabled'):
                    self.audit('pro')
                del self.listing[path]

    def test_unsquashfs_listing_parser_preserves_exact_symlink_paths(self):
        entries = namespace['parse_listing']('lrwxrwxrwx root/root 56 2026-09-05 12:00 squashfs-root/etc/xdg/autostart/opensnitch_ui.desktop -> /usr/share/applications/opensnitch_ui.desktop\n')
        self.assertEqual(entries['etc/xdg/autostart/opensnitch_ui.desktop'][2], '/usr/share/applications/opensnitch_ui.desktop')


if __name__ == '__main__':
    unittest.main(verbosity=2)
