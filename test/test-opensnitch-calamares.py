#!/usr/bin/env python3
"""Regression checks for the actual Pro hook's parsed installer owner policy."""
import ast
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'config/hooks/normal/0600-pro-edition.hook.chroot'
source = HOOK.read_text(encoding='utf-8').split("python3 - <<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
module = ast.parse(source)
function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'validate_admin_owner_yaml')
namespace = {'yaml': yaml}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(HOOK), 'exec'), namespace)
validate = namespace['validate_admin_owner_yaml']


class CalamaresOwnerTests(unittest.TestCase):
    def test_actual_upstream_block_list_and_aligned_spacing(self):
        validate('''---
userGroup:       users
defaultGroups:
    - cdrom
    - floppy
    - sudo
    - audio
sudoersGroup:    sudo
setRootPassword: false
''')

    def test_flow_list_and_quoted_values_are_equivalent(self):
        validate('defaultGroups: [audio, "sudo", video]\nsudoersGroup: "sudo"\n')

    def test_wrong_sudoers_group_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'sudoersGroup'):
            validate('defaultGroups: [sudo]\nsudoersGroup: wheel\n')

    def test_missing_admin_membership_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'defaultGroups'):
            validate('defaultGroups: [users, audio]\nsudoersGroup: sudo\n')

    def test_substring_or_comment_does_not_grant_admin_membership(self):
        for groups in ('[not-sudo]', '[users] # sudo', 'sudo', '{sudo: true}'):
            with self.subTest(groups=groups), self.assertRaisesRegex(ValueError, 'defaultGroups'):
                validate('defaultGroups: ' + groups + '\nsudoersGroup: sudo\n')

    def test_empty_or_nonmapping_policy_is_rejected(self):
        for source in ('', '[]', 'sudoersGroup: sudo\n', 'defaultGroups: [sudo]\n'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                validate(source)

    def test_hook_calls_validator_on_installed_configuration(self):
        self.assertIn("validate_admin_owner_yaml(Path('/etc/calamares/modules/users.conf').read_text())", source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
