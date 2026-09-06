#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise real controller transactions with mocked compositor/service calls."""
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'config/includes.chroot/usr/lib/dagric'
sys.path.insert(0, str(LIB))
import desktop_controls as dc

VALUES = dict(height=48, location='bottom', alignment='center', floating=True,
              hiding='none', lengthMode='fill')


class Controls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.controller = dc.Controller(self.base / 'state', self.base / 'config')
        self.controller.config.mkdir(mode=0o700)
        self.calls = []
        self.panel = dict(id=7, screen=0, **VALUES)
        def write_panel(value):
            self.calls.append(value)
            self.panel.update(json.loads(re.search(r'var v=(\{.*?\});', value).group(1)))
            return 'ok'
        self.patches = [patch.object(dc, 'inventory', side_effect=lambda: [dict(self.panel)]),
                        patch.object(dc, 'plasma', side_effect=write_panel),
                        patch.object(self.controller, 'watchdog', side_effect=lambda token: self.calls.append('watchdog')),
                        patch.object(self.controller, 'service', side_effect=lambda action: self.calls.append(action))]
        for item in self.patches: item.start()

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def apply(self):
        return self.controller.dispatch('apply', {'id': 7, 'values': dict(VALUES, height=64, location='top')})

    def test_watchdog_precedes_apply_and_revert_restores_exact_values(self):
        self.assertTrue(self.apply()['pending'])
        self.assertEqual(self.calls[0], 'watchdog')
        self.assertIn('"height":64', self.calls[1])
        self.controller.dispatch('revert')
        self.assertEqual(self.calls[-1], dc.panel_script(7, VALUES))
        self.assertIsNone(self.controller.read('pending.json'))

    def test_keep_and_second_change(self):
        self.apply()
        with self.assertRaises(ValueError): self.apply()
        self.controller.dispatch('keep')
        self.assertIsNone(self.controller.read('pending.json'))
        self.apply()

    def test_expired_preview_recovers_when_ui_reopens(self):
        self.apply()
        pending = self.controller.read('pending.json'); pending['deadline'] = time.monotonic() - 1
        self.controller.write('pending.json', pending)
        self.assertFalse(self.controller.dispatch('query')['pending'])
        self.assertEqual(self.calls[-1], dc.panel_script(7, VALUES))

    def test_watchdog_failure_restores_without_apply(self):
        with patch.object(self.controller, 'watchdog', side_effect=RuntimeError('no watchdog')):
            with self.assertRaises(RuntimeError): self.apply()
        self.assertNotIn('"height":64', ''.join(self.calls))
        self.assertIsNone(self.controller.read('pending.json'))

    def test_partial_apply_failure_rolls_back(self):
        with patch.object(dc, 'plasma', side_effect=[RuntimeError('apply failed'), 'ok']) as plasma:
            with self.assertRaises(RuntimeError): self.apply()
            self.assertEqual(plasma.call_args_list[-1].args[0], dc.panel_script(7, VALUES))
        self.assertIsNone(self.controller.read('pending.json'))

    def test_reset_and_durable_undo_preserve_unrelated_files(self):
        config = self.controller.config
        original = '[Containments][3]\nwallpaperplugin=org.kde.image\n'
        (config / dc.LAYOUT_FILES[0]).write_text(original)
        (config / 'kdeglobals').write_text('owner colors and fonts')
        personal = self.base / 'photo.txt'; personal.write_text('keep my data')
        result = self.controller.dispatch('reset-layout')
        self.assertTrue(result['pending'])
        self.assertEqual(self.calls[:2], ['watchdog', 'stop'])
        self.assertFalse((config / dc.LAYOUT_FILES[0]).exists())
        self.controller.dispatch('keep')
        self.assertIsNotNone(self.controller.read('layout-undo.json'))
        self.controller.dispatch('undo-layout')
        self.assertEqual((config / dc.LAYOUT_FILES[0]).read_text(), original)
        self.controller.dispatch('keep')
        self.assertEqual((config / 'kdeglobals').read_text(), 'owner colors and fonts')
        self.assertEqual(personal.read_text(), 'keep my data')

    def test_reset_failure_restores_layout_and_starts_shell(self):
        (self.controller.config / dc.LAYOUT_FILES[0]).write_text('original')
        original = self.controller.layout_write
        with patch.object(self.controller, 'layout_write', side_effect=[OSError('disk full'), None]):
            with self.assertRaises(OSError): self.controller.dispatch('reset-layout')
        self.assertEqual(self.calls[-1], 'start')

    def test_new_session_cannot_revert_an_old_panel_id(self):
        self.apply()
        pending = self.controller.read('pending.json'); pending['session'] = 'another-session'
        self.controller.write('pending.json', pending)
        before = list(self.calls)
        self.controller.dispatch('revert')
        self.assertEqual(self.calls, before)
        self.assertIsNone(self.controller.read('pending.json'))
        archives = list(self.controller.state.glob('previous-session-*.json'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(json.loads(archives[0].read_text())['before'], VALUES)

    def test_allowlist_rejects_scripts_bools_unknown_fields(self):
        for payload in [dict(VALUES, height=True), dict(VALUES, height=121),
                        dict(VALUES, location='bottom; evil()'), dict(VALUES, extra='bad'),
                        dict(VALUES, floating='true')]:
            with self.subTest(payload=payload), self.assertRaises(ValueError): dc.validate(payload)
        for value in [True, -1, '7;evil()', 2**32]:
            with self.assertRaises(ValueError): dc.panel_id(value)

    def test_state_and_layout_links_rejected(self):
        target = self.base / 'target'; target.write_text('private')
        (self.controller.state / 'pending.json').symlink_to(target)
        with self.assertRaises(OSError): self.controller.read('pending.json')
        (self.controller.config / dc.LAYOUT_FILES[0]).symlink_to(target)
        with self.assertRaises(OSError): self.controller.layout_backup()
        self.assertEqual(target.read_text(), 'private')

    def test_generated_javascript_only_changes_selected_panel(self):
        script = dc.panel_script(7, dict(VALUES, height=64))
        harness = '''const assert=require('node:assert/strict');
const first={id:6,height:33,widgets:['mine']},second={id:7,widgets:['keep']};
function panelById(id){return id===7?second:first;} function print(){}
SCRIPT
assert.equal(first.height,33);assert.equal(second.height,64);
assert.deepEqual(first.widgets,['mine']);assert.deepEqual(second.widgets,['keep']);'''.replace('SCRIPT', script)
        subprocess.run(['node', '-e', harness], check=True)

    def test_shared_runner_sets_identity_before_loading(self):
        source = (LIB / 'ui_runner.py').read_text()
        self.assertLess(source.index('app.setDesktopFileName(identity)'), source.index('engine.load('))
        self.assertIn('python3-pyside6.qtquick', (ROOT / 'packages/dagric-tools/DEBIAN/control').read_text())
        hook = (ROOT / 'config/hooks/normal/0540-qml-identity.hook.chroot').read_text()
        self.assertNotIn('org.qt-project.qml.desktop', hook)

    def test_inventory_preserves_upstream_visibility_mode_three(self):
        harness = '''const assert=require('node:assert/strict'); let result;
function panels(){return [{id:7,screen:0,height:48,location:'bottom',alignment:'center',floating:true,hiding:'none',lengthMode:'fill'}];}
function ConfigFile(parent,group){this.readEntry=k=>k==='panelVisibility'?3:undefined;}
function print(value){result=JSON.parse(value);}
SCRIPT
assert.equal(result[0].hiding,'windowsgobelow');'''.replace('SCRIPT', dc.INVENTORY_SCRIPT)
        subprocess.run(['node', '-e', harness], check=True)

    def test_no_acknowledgment_is_a_failure(self):
        with patch.object(dc, 'plasma', return_value=''):
            with self.assertRaises(RuntimeError): dc.apply_panel(7, VALUES)

    def test_oversize_journal_cannot_be_written(self):
        with patch.object(dc, 'LIMIT', 100):
            with self.assertRaises(ValueError): self.controller.write('pending.json', {'data': 'x' * 101})
        self.assertFalse((self.controller.state / 'pending.json').exists())

    def test_readback_rejects_silent_unchanged_values(self):
        with patch.object(dc, 'plasma', return_value='ok'):
            with self.assertRaises(RuntimeError): dc.apply_panel(7, dict(VALUES, location='top'))

    def test_height_is_applied_after_location_restores_orientation_defaults(self):
        script = dc.panel_script(7, dict(VALUES, location='top', height=64))
        self.assertLess(script.index('p.location=v.location'), script.index('p.height=v.height'))
        dc.validate(dict(VALUES, height=200), existing=True)
        with self.assertRaises(ValueError): dc.validate(dict(VALUES, height=200))


if __name__ == '__main__': unittest.main()
