#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the actual setup hook and panel scripts against isolated fixtures."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
INC = ROOT / 'config/includes.chroot'


class Installer(unittest.TestCase):
    def test_yaml_dependency_is_explicit_in_both_editions(self):
        packages = (ROOT / 'config/package-lists/installer.list.chroot').read_text().splitlines()
        self.assertIn('python3-yaml', packages)

    def test_both_editions_share_entry_and_keep_account_confirmation(self):
        for edition in ('free', 'pro'):
            with self.subTest(edition=edition), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                entry, setup, config = (base / n for n in ('install.desktop', 'setup.desktop', 'settings.conf'))
                entry.write_text('old installer entry')
                setup.write_text((INC / 'usr/share/applications/dagric-firstrun.desktop').read_text())
                config.write_text(yaml.safe_dump({'sequence': [
                    {'show': ['welcome', 'partition', 'users', 'summary']},
                    {'exec': ['partition', 'users']}, {'show': ['finished']}],
                    'dont-chroot': False, 'prompt-install': False, 'branding': 'dagric'}))
                source = (ROOT / 'config/hooks/normal/0505-unified-setup.hook.chroot').read_text()
                for original, replacement in (
                    ('/usr/share/applications/calamares-install-debian.desktop', entry),
                    ('/usr/share/applications/dagric-firstrun.desktop', setup),
                    ('/etc/calamares/settings.conf', config)):
                    source = source.replace(original, str(replacement))
                result = subprocess.run(['sh', '-s'], input=source, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('Exec=dagric-firstrun\n', entry.read_text())
                self.assertIn('NoDisplay=true\n', entry.read_text())
                settings = yaml.safe_load(config.read_text())
                self.assertTrue(settings['prompt-install'])
                self.assertFalse(settings['dont-chroot'])
                self.assertEqual(settings['sequence'][0]['show'][-2:], ['users', 'summary'])


class Panels(unittest.TestCase):
    def test_packaged_layouts_build_before_removing_old_panels(self):
        source = (INC / 'usr/bin/dagric-firstrun').read_text()
        function = source[source.index('set_layout() {'):source.index('\nscale_factor() {')]
        prelude = '''
skey() { sed -n 's/^SCRIPT=//p' "$1"; }
wait_plasma() { return 0; }
plasma_script() { printf '%s' "$1"; }
'''
        for look in sorted((INC / 'usr/share/dagric/looks').glob('*.look')):
            script = subprocess.check_output(['sh', '-c', prelude + function + '\nset_layout "$1"', 'fixture', str(look)], text=True)
            for fail in (False, True):
                with self.subTest(layout=look.name, widget_failure=fail):
                    # Simulated Plasma API, not evidence of the actual compositor.
                    harness = '''
const assert=require('node:assert/strict');
let all=[], nextId=1, minimum=999, fail=FAIL;
const gridUnit=18;
function Panel(){this.id=nextId++;this.widgetIds=[];all.push(this);}
Panel.prototype.remove=function(){all=all.filter(p=>p!==this);minimum=Math.min(minimum,all.length);};
Panel.prototype.addWidget=function(type){if(fail)throw Error('missing widget');this.widgetIds.push(type);return {writeConfig(){}};};
function panels(){return all.slice();}
const old=new Panel();old.ownerSetting='keep-me';let threw=false;
try { SCRIPT } catch(e) { threw=true; }
assert.ok(all.length>0);assert.ok(minimum>0);
if(fail){assert.ok(threw);assert.deepEqual(all,[old]);assert.equal(old.ownerSetting,'keep-me');}
else{assert.ok(!threw);assert.ok(!all.includes(old));assert.ok(all.every(p=>p.widgetIds.length>0));}
'''.replace('FAIL', json.dumps(fail)).replace('SCRIPT', script)
                    result = subprocess.run(['node', '-e', harness], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
