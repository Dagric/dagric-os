#!/usr/bin/env python3
"""Boot presentation regression checks, including actual hook execution.

Fixtures are not boot/installation or accessibility acceptance evidence.
"""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'config/includes.chroot/usr/share/dagric/boot'
HOOK = ROOT / 'config/hooks/normal/0950-boot-branding.hook.binary'

class BootPresentation(unittest.TestCase):
    def test_selection_contrast_and_asset_encoding(self):
        def luminance(rgb):
            c = [v / 255 for v in rgb]
            c = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c]
            return sum(v * w for v, w in zip(c, (.2126, .7152, .0722)))
        self.assertGreater((1.05) / (luminance((184, 32, 54)) + .05), 4.5)
        for path in ART.rglob('*.png'):
            with self.subTest(path=path.name):
                header = struct.unpack('>IIBBBBB', path.read_bytes()[16:29])
                self.assertEqual((header[2], header[3], header[6]), (8, 6, 0))
        theme = (ART / 'grub-theme/theme.txt').read_text()
        self.assertIn('selected_item_color = "#ffffff"', theme)
        self.assertIn("fill '#b82036'", (ROOT / 'config/bootloaders/make-boot-art.sh').read_text())
        bios = (ROOT / 'config/bootloaders/isolinux/stdmenu.cfg').read_text()
        self.assertIn('#ffffffff #ffb82036', bios)
        self.assertIn('menu rows 8', bios)

    def test_layout_keeps_countdown_above_hint(self):
        theme = (ART / 'grub-theme/theme.txt').read_text()
        self.assertIn('top = 36%', theme)
        self.assertIn('top = 36%+372', theme)
        for height in (720, 768, 800, 1080):
            self.assertLess(height * .36 + 372 + 20, height - 52)
        self.assertIn('Starting selected option in %ds', theme)

    def test_actual_hook_keeps_boot_paths_and_accessibility(self):
        for edition in ('free', 'pro'):
            with self.subTest(edition=edition), tempfile.TemporaryDirectory(prefix='dagric-boot-fixture-') as tmp:
                base = Path(tmp)
                shutil.copytree(ART, base / 'chroot/usr/share/dagric/boot')
                binary = base / 'binary'
                (binary / 'boot/grub').mkdir(parents=True)
                (binary / 'isolinux').mkdir()
                grub = '''menuentry "Live system (amd64)" --hotkey=l {
 linux /live/vmlinuz boot=live quiet splash
 initrd /live/initrd.img
}
menuentry "Live system (amd64 fail-safe mode)" {
 linux /live/vmlinuz boot=live nomodeset
 initrd /live/initrd.img
}
submenu "Utilities" {
 menuentry "Firmware settings" { fwsetup }
}
'''
                (binary / 'boot/grub/grub.cfg').write_text(grub)
                (binary / 'boot/grub/config.cfg').write_text('set gfxmode=800x600\n')
                (binary / 'isolinux/live.cfg').write_text('''label live-amd64
 menu label ^Live system (amd64)
 menu default
 linux /live/vmlinuz
 initrd /live/initrd.img
 append boot=live quiet splash
label live-amd64-failsafe
 menu label ^Live system (amd64 fail-safe mode)
 linux /live/vmlinuz
 initrd /live/initrd.img
 append boot=live nomodeset
''')
                (binary / 'isolinux/isolinux.cfg').write_text('timeout 0\n')
                (binary / 'isolinux/menu.cfg').write_text('menu title Boot menu\n')
                shutil.copyfile(ROOT / 'config/bootloaders/isolinux/stdmenu.cfg', binary / 'isolinux/stdmenu.cfg')
                run = subprocess.run(['sh', str(HOOK)], cwd=binary,
                    env={**os.environ, 'DAGRIC_EDITION': edition}, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertNotIn('WARNING:', run.stdout + run.stderr)
                result = (binary / 'boot/grub/grub.cfg').read_text()
                bios = (binary / 'isolinux/live.cfg').read_text()
                product = 'Dagric OS Pro' if edition == 'pro' else 'Dagric OS Free'
                self.assertIn('Start ' + product, result)
                self.assertIn('Start ^' + product, bios)
                self.assertNotIn('menu label ^Start', bios)
                self.assertIn(product + ' - safe graphics', result)
                self.assertIn(product + ' - safe ^graphics', bios)
                self.assertIn(product + ' - screen reader" --hotkey=s', result)
                self.assertIn(product + ' - ^screen reader', bios)
                self.assertEqual(result.count('dagric.a11y=1'), 1)
                self.assertEqual(bios.count('dagric.a11y=1'), 1)
                self.assertIn('nomodeset', result)
                self.assertIn('Firmware settings', result)
                self.assertIn('locales=pt_BR.UTF-8', result)
                self.assertIn('menu label ^Back', bios)
                self.assertIn('set timeout=10', result)
                self.assertEqual((binary/'boot/grub/themes/dagric/background.png').read_bytes(),
                                 (ART/'grub-theme/background.png').read_bytes())

if __name__ == '__main__':
    unittest.main()
