"""Regression tests for scripts/install.py using isolated temporary directories."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / 'scripts' / 'install.py'
NAMES = ('pet.json', 'spritesheet.png', 'version.json')


def files_under(path):
    return {
        str(item.relative_to(path)): (item.read_bytes(), item.stat().st_mtime_ns)
        for item in sorted(path.rglob('*'))
        if item.is_file()
    }


class InstallScriptTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.script = self.root / 'scripts' / 'install.py'
        self.script.parent.mkdir()
        shutil.copy2(INSTALL_SCRIPT, self.script)
        self.pets = self.root / 'state' / 'pets'
        self.target = self.pets.resolve() / 'amu'
        self.backup_root = self.pets.resolve().parent / 'pet-backups'
        self.package = self.root / 'packages' / 'amu'
        self.write_package('1.0.0', b'amu sprite 1.0.0')

    def write_package(self, version, sprite):
        self.package.mkdir(parents=True, exist_ok=True)
        (self.package / 'pet.json').write_text(
            json.dumps({'spritesheetPath': 'spritesheet.png'}), encoding='utf-8')
        (self.package / 'spritesheet.png').write_bytes(sprite)
        (self.package / 'version.json').write_text(json.dumps({
            'version': version,
            'sha256': hashlib.sha256(sprite).hexdigest(),
        }), encoding='utf-8')

    def write_metadata(self, pet_text, version_text):
        (self.package / 'pet.json').write_text(pet_text, encoding='utf-8')
        (self.package / 'version.json').write_text(version_text, encoding='utf-8')

    def invalid_metadata_cases(self):
        """Return (label, pet.json text, version.json text, expected error fragment)."""
        digest = hashlib.sha256((self.package / 'spritesheet.png').read_bytes()).hexdigest()
        valid_pet = json.dumps({'spritesheetPath': 'spritesheet.png'})
        valid_version = json.dumps({'version': '1.0.0', 'sha256': digest})
        return [
            ('pet_json_syntax', '{not json', valid_version,
             'pet.json is not valid JSON'),
            ('pet_json_array', '[]', valid_version,
             'pet.json must contain a JSON object'),
            ('pet_missing_spritesheet_path', '{}', valid_version,
             'pet.json spritesheetPath'),
            ('pet_non_string_spritesheet_path', json.dumps({'spritesheetPath': 1}), valid_version,
             'pet.json spritesheetPath'),
            ('pet_absolute_spritesheet_path',
             json.dumps({'spritesheetPath': str(self.package / 'spritesheet.png')}), valid_version,
             'pet.json spritesheetPath'),
            ('pet_parent_spritesheet_path', json.dumps({'spritesheetPath': '../spritesheet.png'}),
             valid_version, 'pet.json spritesheetPath'),
            ('pet_other_spritesheet_path', json.dumps({'spritesheetPath': 'other.png'}),
             valid_version, 'pet.json spritesheetPath'),
            ('version_json_syntax', valid_pet, '{not json',
             'version.json is not valid JSON'),
            ('version_json_array', valid_pet, '[]',
             'version.json must contain a JSON object'),
            ('version_missing_version', valid_pet, json.dumps({'sha256': digest}),
             'version.json version must be a non-empty string'),
            ('version_empty_version', valid_pet,
             json.dumps({'version': '', 'sha256': digest}),
             'version.json version must be a non-empty string'),
            ('version_non_string_version', valid_pet,
             json.dumps({'version': 1.0, 'sha256': digest}),
             'version.json version must be a non-empty string'),
            ('version_missing_sha256', valid_pet, json.dumps({'version': '1.0.0'}),
             'version.json sha256 must be a 64-character hexadecimal string'),
            ('version_short_sha256', valid_pet,
             json.dumps({'version': '1.0.0', 'sha256': 'abc'}),
             'version.json sha256 must be a 64-character hexadecimal string'),
            ('version_non_hex_sha256', valid_pet,
             json.dumps({'version': '1.0.0', 'sha256': 'z' * 64}),
             'version.json sha256 must be a 64-character hexadecimal string'),
            ('version_non_string_sha256', valid_pet,
             json.dumps({'version': '1.0.0', 'sha256': 123}),
             'version.json sha256 must be a 64-character hexadecimal string'),
        ]

    def run_install(self, *args):
        env = os.environ.copy()
        env.pop('CODEX_HOME', None)
        return subprocess.run(
            [sys.executable, str(self.script), '--pets-dir', str(self.pets), *args],
            cwd=self.root, env=env, text=True, capture_output=True,
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_metadata_error(self, result, fragment):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertIn(fragment, result.stderr)

    def test_dry_run_first_install_reports_plan_without_writing(self):
        result = self.run_install('--dry-run')
        self.assert_success(result)
        self.assertIn('Version: 1.0.0', result.stdout)
        self.assertIn(f'Target: {self.target}', result.stdout)
        self.assertIn('first install', result.stdout)
        self.assertFalse(self.pets.exists())
        self.assertFalse(self.pets.parent.exists())
        self.assertFalse(self.backup_root.exists())

    def test_dry_run_already_installed_reports_plan_without_writing(self):
        self.assert_success(self.run_install())
        before = files_under(self.pets)
        result = self.run_install('--dry-run')
        self.assert_success(result)
        self.assertIn('already installed', result.stdout)
        self.assertEqual(files_under(self.pets), before)
        self.assertFalse(self.backup_root.exists())

    def test_dry_run_update_reports_plan_without_writing(self):
        self.assert_success(self.run_install())
        before = files_under(self.pets)
        self.write_package('2.0.0', b'amu sprite 2.0.0')
        result = self.run_install('--dry-run')
        self.assert_success(result)
        self.assertIn('Version: 2.0.0', result.stdout)
        self.assertIn(f'Target: {self.target}', result.stdout)
        self.assertIn('update', result.stdout)
        self.assertIn('pet-backups', result.stdout)
        self.assertEqual(files_under(self.pets), before)
        self.assertFalse(self.backup_root.exists())

    def test_json_dry_run_first_install_reports_plan_without_writing(self):
        result = self.run_install('--dry-run', '--json')
        self.assert_success(result)
        plan = json.loads(result.stdout)
        self.assertEqual(plan['version'], '1.0.0')
        self.assertEqual(plan['target'], str(self.target))
        self.assertEqual(plan['action'], 'first_install')
        self.assertIsNone(plan['backup_dir'])
        self.assertIs(plan['dry_run'], True)
        self.assertFalse(self.pets.exists())
        self.assertFalse(self.pets.parent.exists())
        self.assertFalse(self.backup_root.exists())

    def test_json_dry_run_already_installed_reports_plan_without_writing(self):
        self.assert_success(self.run_install())
        before = files_under(self.pets)
        result = self.run_install('--dry-run', '--json')
        self.assert_success(result)
        plan = json.loads(result.stdout)
        self.assertEqual(plan['version'], '1.0.0')
        self.assertEqual(plan['target'], str(self.target))
        self.assertEqual(plan['action'], 'up_to_date')
        self.assertIsNone(plan['backup_dir'])
        self.assertIs(plan['dry_run'], True)
        self.assertEqual(files_under(self.pets), before)
        self.assertFalse(self.backup_root.exists())

    def test_json_dry_run_update_reports_plan_without_writing(self):
        self.assert_success(self.run_install())
        before = files_under(self.pets)
        self.write_package('2.0.0', b'amu sprite 2.0.0')
        result = self.run_install('--dry-run', '--json')
        self.assert_success(result)
        plan = json.loads(result.stdout)
        self.assertEqual(plan['version'], '2.0.0')
        self.assertEqual(plan['target'], str(self.target))
        self.assertEqual(plan['action'], 'update')
        self.assertEqual(plan['backup_dir'], str(self.backup_root))
        self.assertIs(plan['dry_run'], True)
        self.assertEqual(files_under(self.pets), before)
        self.assertFalse(self.backup_root.exists())

    def test_json_without_dry_run_is_usage_error_and_installs_nothing(self):
        result = self.run_install('--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr)
        self.assertIn('--json', result.stderr)
        self.assertIn('--dry-run', result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertFalse(self.pets.exists())
        self.assertFalse(self.pets.parent.exists())
        self.assertFalse(self.backup_root.exists())

    def test_json_dry_run_rejects_invalid_metadata_without_output(self):
        self.write_metadata('{not json', json.dumps({'version': '1.0.0', 'sha256': '0' * 64}))
        result = self.run_install('--dry-run', '--json')
        self.assert_metadata_error(result, 'pet.json is not valid JSON')
        self.assertEqual(result.stdout, '')
        self.assertFalse(self.pets.parent.exists())
        self.assertFalse(self.backup_root.exists())

    def test_dry_run_rejects_corrupt_package_without_creating_target(self):
        (self.package / 'spritesheet.png').write_bytes(b'corrupt sprite')
        result = self.run_install('--dry-run')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum', result.stderr.lower())
        self.assertFalse(self.pets.parent.exists())

    def test_dry_run_rejects_corrupt_package_without_touching_install(self):
        self.assert_success(self.run_install())
        before = files_under(self.pets)
        (self.package / 'spritesheet.png').write_bytes(b'corrupt sprite')
        result = self.run_install('--dry-run')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum', result.stderr.lower())
        self.assertEqual(files_under(self.pets), before)
        self.assertFalse(self.backup_root.exists())

    def test_normal_install_and_repeat(self):
        result = self.run_install()
        self.assert_success(result)
        self.assertIn('Installed Amu 1.0.0:', result.stdout)
        for name in NAMES:
            self.assertEqual((self.target / name).read_bytes(), (self.package / name).read_bytes())
        before = files_under(self.target)
        repeat = self.run_install()
        self.assert_success(repeat)
        self.assertIn('already installed', repeat.stdout)
        self.assertEqual(files_under(self.target), before)
        self.assertFalse(self.backup_root.exists())

    def test_update_backs_up_previous_installation(self):
        self.assert_success(self.run_install())
        old_sprite = (self.package / 'spritesheet.png').read_bytes()
        self.write_package('2.0.0', b'amu sprite 2.0.0')
        result = self.run_install()
        self.assert_success(result)
        self.assertIn('Installed Amu 2.0.0:', result.stdout)
        self.assertIn('Previous installation backed up:', result.stdout)
        self.assertEqual((self.target / 'spritesheet.png').read_bytes(), b'amu sprite 2.0.0')
        self.assertEqual(
            json.loads((self.target / 'version.json').read_text(encoding='utf-8'))['version'],
            '2.0.0',
        )
        backups = list(self.backup_root.iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / 'spritesheet.png').read_bytes(), old_sprite)
        self.assertEqual(
            json.loads((backups[0] / 'version.json').read_text(encoding='utf-8'))['version'],
            '1.0.0',
        )

    def test_uppercase_sha256_metadata_installs(self):
        digest = hashlib.sha256((self.package / 'spritesheet.png').read_bytes()).hexdigest().upper()
        (self.package / 'version.json').write_text(json.dumps({
            'version': '1.0.0',
            'sha256': digest,
        }), encoding='utf-8')
        result = self.run_install()
        self.assert_success(result)
        self.assertIn('Installed Amu 1.0.0:', result.stdout)
        for name in NAMES:
            self.assertEqual((self.target / name).read_bytes(), (self.package / name).read_bytes())

    def test_invalid_metadata_dry_run_rejected_without_creating_target(self):
        for label, pet_text, version_text, fragment in self.invalid_metadata_cases():
            with self.subTest(case=label):
                self.write_metadata(pet_text, version_text)
                result = self.run_install('--dry-run')
                self.assert_metadata_error(result, fragment)
                self.assertFalse(self.pets.parent.exists())
                self.assertFalse(self.backup_root.exists())

    def test_invalid_metadata_normal_install_rejected_without_creating_target(self):
        for label, pet_text, version_text, fragment in self.invalid_metadata_cases():
            with self.subTest(case=label):
                self.write_metadata(pet_text, version_text)
                result = self.run_install()
                self.assert_metadata_error(result, fragment)
                self.assertFalse(self.pets.parent.exists())
                self.assertFalse(self.backup_root.exists())

    def test_invalid_metadata_dry_run_keeps_existing_install(self):
        self.assert_success(self.run_install())
        before = files_under(self.pets)
        for label, pet_text, version_text, fragment in self.invalid_metadata_cases():
            with self.subTest(case=label):
                self.write_metadata(pet_text, version_text)
                result = self.run_install('--dry-run')
                self.assert_metadata_error(result, fragment)
                self.assertEqual(files_under(self.pets), before)
                self.assertFalse(self.backup_root.exists())

    def test_invalid_metadata_normal_install_keeps_existing_install(self):
        self.assert_success(self.run_install())
        before = files_under(self.pets)
        for label, pet_text, version_text, fragment in self.invalid_metadata_cases():
            with self.subTest(case=label):
                self.write_metadata(pet_text, version_text)
                result = self.run_install()
                self.assert_metadata_error(result, fragment)
                self.assertEqual(files_under(self.pets), before)
                self.assertFalse(self.backup_root.exists())


if __name__ == '__main__':
    unittest.main()