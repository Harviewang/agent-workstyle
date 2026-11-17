import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_public', ROOT / 'scripts/check_public.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def release(extra=None):
    contents = {'README.md': b'Generic instructions only.\n'}
    if extra:
        contents.update(extra)
    names = sorted([*contents, 'PUBLIC_FILES.json', 'SHA256SUMS'])
    contents['PUBLIC_FILES.json'] = json.dumps({'files': names}).encode()
    contents['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                                    for name, data in sorted(contents.items())).encode()
    return contents


class PublicReleaseTests(unittest.TestCase):
    def test_valid_release(self):
        self.assertEqual(guard.validate_release(release())['status'], 'passed')

    def test_extra_unlisted_file_rejected(self):
        contents = release()
        contents['unlisted.txt'] = b'not approved'
        with self.assertRaises(ValueError):
            guard.validate_release(contents)

    def test_missing_file_rejected(self):
        contents = release()
        del contents['README.md']
        with self.assertRaises(ValueError):
            guard.validate_release(contents)

    def test_modified_content_rejected(self):
        contents = release()
        contents['README.md'] += b'changed after review'
        with self.assertRaises(ValueError):
            guard.validate_release(contents)

    def test_private_paths_and_traversal_rejected(self):
        for name in ['.codex/config.toml', '.dev-flow/task.md', '../outside', '/absolute', 'backups/original.toml']:
            with self.assertRaises(ValueError):
                guard.validate_names([name])

    def test_sensitive_patterns_detected_without_echoing_values(self):
        samples = [
            '/Us' + 'ers/alice/private',
            'C:' + '\\Us' + 'ers\\alice\\private',
            'gh' + 'p_' + 'X' * 36,
            '-----BEGIN' + ' PRIVATE KEY-----',
            'api' + '_key = "' + 'X' * 32 + '"',
        ]
        for sample in samples:
            findings = guard.scan_content('sample.txt', sample.encode())
            self.assertTrue(findings)
            self.assertNotIn(sample, json.dumps(findings))

    def test_vendor_neutral_names_and_new_files_are_listed(self):
        manifest = json.loads((ROOT / 'PUBLIC_FILES.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '2.0.0')
        for name in ['references/routing.md', 'references/failover.md',
                     'references/clients.md', 'profiles/example.toml']:
            self.assertIn(name, manifest['files'])
        self.assertIn('name: agent-workstyle', (ROOT / 'SKILL.md').read_text(encoding='utf-8'))

    def test_forbidden_terms_rejected_before_digest_validation(self):
        samples = ['Fa' + 'ble', 'Op' + 'us', 'Son' + 'net', 'Hai' + 'ku',
                   'gp' + 't-6-example', 'Ge' + 'mini 4-example',
                   'Ge' + 'mini 3.8-example', '/Us' + 'ers/x']
        for sample in samples:
            with self.subTest(sample=sample):
                with self.assertRaisesRegex(ValueError, '敏感模式'):
                    guard.validate_release(release({'example.txt': sample.encode()}))

    def test_private_terms_file_is_applied_without_echoing_terms(self):
        with tempfile.TemporaryDirectory() as temporary:
            terms = Path(temporary) / 'private-terms.txt'
            terms.write_text('# synthetic\nzebracorn-handle\n', encoding='utf-8')
            saved = dict(guard.PATTERNS)
            try:
                self.assertEqual(guard.load_private_terms(terms), 1)
                findings = guard.scan_content('example.txt', b'hello ZebraCorn-Handle')
                self.assertEqual([f['category'] for f in findings], ['private-term'])
                self.assertNotIn('zebracorn', json.dumps(findings).lower())
                self.assertEqual(guard.scan_content('example.txt', b'hello world'), [])
            finally:
                guard.PATTERNS.clear()
                guard.PATTERNS.update(saved)

    def test_temporary_copy_with_forbidden_content_fails_cli(self):
        names = json.loads((ROOT / 'PUBLIC_FILES.json').read_text(encoding='utf-8'))['files']
        for sample in ['Op' + 'us', '/Us' + 'ers/x']:
            with self.subTest(sample=sample), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                for name in names:
                    destination = target / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / name, destination)
                with (target / 'README.md').open('a', encoding='utf-8') as output:
                    output.write('\n' + sample + '\n')
                # Update digests so only the privacy violation causes rejection.
                (target / 'SHA256SUMS').write_text(''.join(
                    hashlib.sha256((target / name).read_bytes()).hexdigest() + '  ' + name + '\n'
                    for name in sorted(names) if name != 'SHA256SUMS'), encoding='utf-8')
                result = subprocess.run([sys.executable, str(target / 'scripts/check_public.py')],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn('Public-file check failed', result.stderr)
                self.assertRegex(result.stderr, 'model-name|private-home-path|private-user-home')
                findings = guard.scan_content('README.md', (target / 'README.md').read_bytes())
                self.assertTrue(findings)
                self.assertNotIn(sample, result.stderr)

    def test_vendor_names_and_private_profile_convention_are_allowed(self):
        sample = b'Claude Codex Gemini gemini skills install agy -p'
        self.assertFalse(guard.scan_content('sample.txt', sample))
        self.assertFalse(guard.scan_content('sample.txt',
                         b'~/.config/agent-workstyle/profile.toml'))

    def test_non_utf8_rejected(self):
        with self.assertRaises(ValueError):
            guard.validate_release(release({'binary.txt': bytes([255])}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
