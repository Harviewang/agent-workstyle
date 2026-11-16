import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workstyle_setup', ROOT / 'scripts/setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workstyle-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / '中文 user space' / '.codex'

    def config(self, data):
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / 'config.toml').write_bytes(data)

    def test_preview_is_read_only(self):
        self.assertEqual(setup.install(self.home)['status'], 'preview')
        self.assertFalse(self.home.exists())

    def test_empty_install_check_idempotence_and_uninstall(self):
        setup.install(self.home, True)
        self.assertEqual(setup.check(self.home)['files_verified'], len(setup.PAYLOAD))
        before = (self.home / 'config.toml').read_bytes()
        self.assertFalse(setup.install(self.home, True)['changed'])
        self.assertEqual(before, (self.home / 'config.toml').read_bytes())
        self.assertEqual(setup.uninstall(self.home)['status'], 'preview-uninstall')
        self.assertTrue((self.home / 'config.toml').exists())
        setup.uninstall(self.home, True)
        self.assertFalse((self.home / 'config.toml').exists())
        self.assertFalse((self.home / 'skills' / setup.NAME).exists())

    def test_existing_crlf_config_restored_byte_for_byte(self):
        original = '# 保留\r\nmodel = "existing"\r\ndeveloper_instructions = "我的原要求" # keep\r\n[features]\r\nmulti_agent = true\r\n'.encode()
        self.config(original)
        setup.install(self.home, True)
        updated = (self.home / 'config.toml').read_bytes()
        self.assertIn(b'# keep\r\n[features]', updated)
        self.assertEqual(tomllib.loads(updated.decode())['model'], 'existing')
        self.assertTrue(tomllib.loads(updated.decode())['developer_instructions'].startswith('我的原要求'))
        setup.uninstall(self.home, True)
        self.assertEqual((self.home / 'config.toml').read_bytes(), original)

    def test_string_forms_and_fake_field_inside_literal(self):
        for value in ['"plain"', "'literal'", '"""first\nsecond"""', "'''first\nsecond'''", '"""quoted end""""']:
            original = ('other = """fake\ndeveloper_instructions = nope\n[not_table]\n"""\n"developer_instructions" = ' + value + ' # retain\n[x]\nvalue = 1\n').encode()
            changed = setup.set_instruction(original, '新值 "quote" \\path\nline')
            original_data = setup.parse(original)
            self.assertEqual(setup.parse(changed), dict(original_data, developer_instructions='新值 "quote" \\path\nline'))
            self.assertIn(b'# retain', changed)

    def test_absent_root_and_same_named_nested_field(self):
        original = b'[x]\ndeveloper_instructions = "nested"\n'
        self.config(original)
        setup.install(self.home, True)
        updated = setup.parse((self.home / 'config.toml').read_bytes())
        self.assertEqual(updated['x']['developer_instructions'], 'nested')
        setup.uninstall(self.home, True)
        self.assertEqual((self.home / 'config.toml').read_bytes(), original)

    def test_unknown_skill_refused(self):
        target = self.home / 'skills' / setup.NAME
        target.mkdir(parents=True)
        (target / 'mine.txt').write_text('keep')
        with self.assertRaises(ValueError):
            setup.install(self.home, True)
        self.assertEqual((target / 'mine.txt').read_text(), 'keep')
        self.assertFalse((self.home / 'config.toml').exists())

    def test_modified_managed_file_refused_without_config_change(self):
        setup.install(self.home, True)
        target = self.home / 'skills' / setup.NAME / 'SKILL.md'
        target.write_text('user modification')
        before = (self.home / 'config.toml').read_bytes()
        for action in [setup.install, setup.uninstall]:
            with self.assertRaises(ValueError):
                action(self.home, True)
        self.assertEqual((self.home / 'config.toml').read_bytes(), before)
        self.assertEqual(target.read_text(), 'user modification')

    def test_later_config_changes_and_extra_files_preserved(self):
        self.config(b'developer_instructions = "original"\nmodel = "one"\n')
        setup.install(self.home, True)
        config = self.home / 'config.toml'
        current = config.read_bytes().replace(b'model = "one"', b'model = "two"')
        value = setup.parse(current)['developer_instructions'] + '\nmy later note'
        config.write_bytes(setup.set_instruction(current, value))
        extra = self.home / 'skills' / setup.NAME / 'my-notes.txt'
        extra.write_text('keep my notes')
        setup.uninstall(self.home, True)
        actual = setup.parse(config.read_bytes())
        self.assertEqual(actual, {'developer_instructions': 'original\nmy later note', 'model': 'two'})
        self.assertEqual(extra.read_text(), 'keep my notes')

    def test_added_field_removed_while_later_settings_preserved(self):
        self.config(b'model = "one"\n')
        setup.install(self.home, True)
        config = self.home / 'config.toml'
        config.write_bytes(config.read_bytes().replace(b'model = "one"', b'model = "two"'))
        setup.uninstall(self.home, True)
        self.assertEqual(setup.parse(config.read_bytes()), {'model': 'two'})

    def test_invalid_config_and_conflicting_marker_are_read_only(self):
        for source in [b'broken = [', b'developer_instructions = 4', ('developer_instructions = "' + setup.START + '"').encode()]:
            self.config(source)
            with self.assertRaises(ValueError):
                setup.install(self.home, True)
            self.assertEqual((self.home / 'config.toml').read_bytes(), source)
            self.assertFalse((self.home / 'skills' / setup.NAME).exists())

    def test_modified_instruction_segment_refused(self):
        setup.install(self.home, True)
        config = self.home / 'config.toml'
        config.write_bytes(config.read_bytes().replace(setup.START.encode(), b'[changed]'))
        with self.assertRaises(ValueError):
            setup.uninstall(self.home, True)

    def test_codex_home_environment_and_cli_preview(self):
        env = dict(os.environ, CODEX_HOME=str(self.home), PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/setup.py')], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'preview')
        self.assertFalse(self.home.exists())

    def test_cli_install_check_uninstall_and_error(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='ascii')
        def invoke(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/setup.py'), *args,
                                   '--codex-home', str(self.home)], env=env, capture_output=True, text=True)
        for action, expected in [('install', 'installed'), ('check', 'ok'), ('uninstall', 'preview-uninstall')]:
            result = invoke(action)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], expected)
        result = invoke('uninstall', '--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'uninstalled')
        result = invoke('check')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)['status'], 'stopped')

    def test_uninstall_move_failure_restores_complete_installation(self):
        setup.install(self.home, True)
        original = (self.home / 'config.toml').read_bytes()
        real_replace = setup.os.replace
        def fail_managed_move(source, target):
            if Path(source) == self.home.resolve() / 'skills' / setup.NAME / 'references/workflow.md':
                raise PermissionError('simulated locked file')
            return real_replace(source, target)
        with mock.patch.object(setup.os, 'replace', side_effect=fail_managed_move):
            with self.assertRaises(PermissionError):
                setup.uninstall(self.home, True)
        self.assertEqual((self.home / 'config.toml').read_bytes(), original)
        self.assertEqual(setup.check(self.home)['status'], 'ok')

    def test_uninstall_commit_failure_restores_config_and_files(self):
        setup.install(self.home, True)
        original = (self.home / 'config.toml').read_bytes()
        real_replace = setup.os.replace
        def fail_history_move(source, target):
            if Path(source) == self.home.resolve() / 'workstyle-state/current.json':
                raise PermissionError('simulated metadata commit failure')
            return real_replace(source, target)
        with mock.patch.object(setup.os, 'replace', side_effect=fail_history_move):
            with self.assertRaises(PermissionError):
                setup.uninstall(self.home, True)
        self.assertEqual((self.home / 'config.toml').read_bytes(), original)
        self.assertEqual(setup.check(self.home)['status'], 'ok')

    def test_failed_install_restores_original_and_removes_only_own_files(self):
        original = b'model = "preserve"\n'
        self.config(original)
        real_atomic = setup.atomic
        def fail_manifest(path, *args, **kwargs):
            if path.name == 'current.json':
                raise OSError('simulated manifest write failure')
            return real_atomic(path, *args, **kwargs)
        with mock.patch.object(setup, 'atomic', side_effect=fail_manifest):
            with self.assertRaises(OSError):
                setup.install(self.home, True)
        self.assertEqual((self.home / 'config.toml').read_bytes(), original)
        self.assertFalse((self.home / 'skills' / setup.NAME).exists())

    def test_existing_operation_lock_is_not_removed(self):
        lock = self.home / 'workstyle-state' / 'operation.lock'
        lock.mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            setup.install(self.home, True)
        self.assertTrue(lock.is_dir())
        self.assertFalse((self.home / 'config.toml').exists())

    def test_changed_bundle_refused_without_rewriting_installation(self):
        setup.install(self.home, True)
        before = (self.home / 'config.toml').read_bytes()
        altered = dict(setup.payload())
        altered['SKILL.md'] += b'\nchanged version\n'
        with mock.patch.object(setup, 'payload', return_value=altered):
            with self.assertRaises(ValueError):
                setup.install(self.home, True)
        self.assertEqual((self.home / 'config.toml').read_bytes(), before)

    @unittest.skipIf(os.name == 'nt', 'POSIX permission bits only')
    def test_private_backup_permissions(self):
        self.config(b'developer_instructions = "private note"\n')
        setup.install(self.home, True)
        state = self.home / 'workstyle-state'
        record = json.loads((state / 'current.json').read_text(encoding='utf-8'))
        backup = state / 'backups' / record['backup_id'] / 'config.before.toml'
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(backup.parent.stat().st_mode), 0o700)

    def test_symlink_destination_is_refused(self):
        self.home.mkdir(parents=True)
        target = Path(self.temp.name) / 'unrelated'
        target.mkdir()
        try:
            (self.home / 'skills').symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with self.assertRaises(ValueError):
            setup.install(self.home, True)
        self.assertEqual(list(target.iterdir()), [])

    def test_symlink_backup_directory_is_refused(self):
        state = self.home / 'workstyle-state'
        state.mkdir(parents=True)
        target = Path(self.temp.name) / 'unrelated'
        target.mkdir()
        try:
            (state / 'backups').symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with self.assertRaises(ValueError):
            setup.install(self.home, True)
        self.assertEqual(list(target.iterdir()), [])

    def test_reinstall_after_uninstall_keeps_old_backup(self):
        setup.install(self.home, True)
        setup.uninstall(self.home, True)
        setup.install(self.home, True)
        state = self.home / 'workstyle-state'
        self.assertEqual(len(list((state / 'backups').iterdir())), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
