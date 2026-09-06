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
                    {'exec': ['partition', 'unpackfs', 'users', 'umount']}, {'show': ['finished']}],
                    'dont-chroot': False, 'prompt-install': False, 'branding': 'dagric'}))
                source = (ROOT / 'config/hooks/normal/0505-unified-setup.hook.chroot').read_text()
                for original, replacement in (
                    ('/usr/share/applications/calamares-install-debian.desktop', entry),
                    ('/usr/share/applications/dagric-firstrun.desktop', setup),
                    ('/etc/calamares/settings.conf', config),
                    ('/usr/lib/dagric', INC / 'usr/lib/dagric'),
                    ('/etc/calamares/modules/dagricdesktop.conf', base / 'dagricdesktop.conf'),
                    ('/usr/lib/x86_64-linux-gnu/calamares/modules/packagechooserq/module.desc', entry),
                    ('/usr/lib/calamares/modules/dagricpersonalize/module.desc', INC / 'usr/lib/calamares/modules/dagricpersonalize/module.desc')):
                    source = source.replace(original, str(replacement))
                result = subprocess.run(['sh', '-s'], input=source, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('Exec=dagric-firstrun\n', entry.read_text())
                self.assertIn('NoDisplay=true\n', entry.read_text())
                settings = yaml.safe_load(config.read_text())
                self.assertTrue(settings['prompt-install'])
                self.assertFalse(settings['dont-chroot'])
                self.assertEqual(settings['sequence'][0]['show'][-2:], ['users', 'summary'])
                self.assertEqual(settings['sequence'][0]['show'][-3], 'packagechooserq@dagricdesktop')
                jobs = settings['sequence'][1]['exec']
                self.assertEqual(jobs[0], 'dagricpersonalize@dagricprofilecheck')
                self.assertEqual(jobs[jobs.index('users') + 1], 'dagricpersonalize@dagricprofileapply')
                self.assertLess(jobs.index('dagricpersonalize@dagricprofileapply'), jobs.index('umount'))
                choices = yaml.safe_load((base / 'dagricdesktop.conf').read_text())
                self.assertEqual(choices['method'], 'legacy')
                self.assertNotIn('items', choices)
                self.assertIn('Centered', choices['packageChoice'])
                again = subprocess.run(['sh', '-s'], input=source, text=True, capture_output=True)
                self.assertEqual(again.returncode, 0, again.stderr)
                self.assertEqual(yaml.safe_load(config.read_text()), settings)


class Panels(unittest.TestCase):
    def test_settings_window_uses_its_own_x11_identity(self):
        launcher = (INC / 'usr/bin/dagric-desktop-settings').read_text()
        hook = (ROOT / 'config/hooks/normal/0540-qml-identity.hook.chroot').read_text()
        self.assertIn('QML=/usr/lib/dagric/wm/dagric-desktop-settings', launcher)
        self.assertEqual(hook.count('dagric-rewind dagric-desktop-settings; do'), 2)

    def test_missing_icon_fill_preserves_upstream_icons_and_actions(self):
        source = (ROOT / 'config/hooks/normal/0555-launcher-icons.hook.chroot').read_text()
        for icon in ('', 'Icon=\n', 'Icon=upstream-lynis\n'):
            with self.subTest(icon=icon), tempfile.TemporaryDirectory() as tmp:
                entry = Path(tmp) / 'lynis.desktop'
                action = '[Desktop Action Inspect]\nIcon=original-action\n'
                entry.write_text('[Desktop Entry]\nName=Lynis\n' + icon + 'Exec=unchanged\n' + action)
                script = source.replace('/usr/share/applications/lynis.desktop', str(entry))
                subprocess.run(['sh', '-s'], input=script, text=True, check=True, capture_output=True)
                first = entry.read_text()
                self.assertIn('Icon=upstream-lynis\n' if icon.startswith('Icon=upstream') else 'Icon=security-high\n', first)
                self.assertIn('Exec=unchanged\n', first)
                self.assertTrue(first.endswith(action))
                subprocess.run(['sh', '-s'], input=script, text=True, check=True, capture_output=True)
                self.assertEqual(first, entry.read_text())

    def test_first_desktop_consumes_profile_without_resetting_existing_panels(self):
        script = (INC / 'usr/share/plasma/look-and-feel/org.dagric.desktop/contents/layouts/org.kde.plasma.desktop-layout.js').read_text()
        for layout in ('classic', 'eleven'):
            for existing in (True, False):
                harness = '''
const assert=require('node:assert/strict');
let all=[], writes=[], desktop={writeConfig(k,v){writes.push([k,v]);}};
function ConfigFile(name,group){assert.equal(name,'dagric/installed-desktoprc');this.readEntry=k=>k==='Layout'?LAYOUT:'DagricArcticClean';}
function Panel(){this.widgets=[];all.push(this);}
Panel.prototype.addWidget=function(type){this.widgets.push(type);return {writeConfig(){}};};
function panels(){return all;}
function desktops(){return [desktop];}
if(EXISTING) new Panel();
SCRIPT
assert.equal(all.length,1);
if(EXISTING){assert.equal(all[0].widgets.length,0);assert.equal(writes.length,0);}
else {assert.equal(all[0].height,48);assert.equal(all[0].floating,true);assert.ok(all[0].widgets.includes(LAYOUT==='classic'?'org.kde.plasma.taskmanager':'org.kde.plasma.icontasks'));assert.ok(writes[0][1].includes('/DagricArcticClean/'));}
'''.replace('SCRIPT', script).replace('LAYOUT', json.dumps(layout)).replace('EXISTING', json.dumps(existing))
                result = subprocess.run(['node','-e',harness],text=True,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)

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
