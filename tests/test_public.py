import hashlib
import importlib.util
import json
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

    def test_non_utf8_rejected(self):
        with self.assertRaises(ValueError):
            guard.validate_release(release({'binary.txt': bytes([255])}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
