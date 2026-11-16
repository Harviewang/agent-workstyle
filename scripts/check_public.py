"""Check the exact public file list, UTF-8 content, digests and selected sensitive patterns."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PARTS = {'.git', '.codex', '.claude', '.dev-flow', 'evidence', 'workstyle-state', 'backups'}
PATTERNS = {
    'private-home-path': re.compile(r'(?:/(?:Users|home)/[^/\\\s]+|[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/][^/\\\s]+)'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github-token': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
    'cloud-key': re.compile(r'\bAKIA[0-9A-Z]{16}\b|\bLTAI[0-9A-Za-z]{12,}\b'),
    'assigned-secret': re.compile(r'''(?i)\b(?:api[_-]?key|password|client_secret|access_token)\s*[:=]\s*["'][A-Za-z0-9_+=/-]{16,}["']'''),
}


def scan_content(name, data):
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return [{'file': name, 'category': 'non-utf8-content'}]
    findings = []
    for category, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append({'file': name, 'line': text.count('\n', 0, match.start()) + 1,
                             'category': category})  # Never print matching values.
    return findings


def validate_names(names):
    if not names or len(names) != len(set(names)):
        raise ValueError('公开清单为空或包含重复路径')
    for name in names:
        path = PurePosixPath(name)
        if (not re.fullmatch(r'[A-Za-z0-9_.\-/]+', name) or path.is_absolute()
                or '..' in path.parts or any(part in PRIVATE_PARTS for part in path.parts)):
            raise ValueError('公开清单含不允许的路径')


def validate_release(contents):
    expected = json.loads(contents['PUBLIC_FILES.json'].decode('utf-8'))['files']
    validate_names(expected)
    if set(contents) != set(expected):
        raise ValueError('实际 Git/文件集合与明确公开清单不一致')
    findings = [finding for name, data in contents.items() for finding in scan_content(name, data)]
    if findings:
        raise ValueError('发现敏感模式（仅文件/行号/类别）：' + json.dumps(findings, ensure_ascii=True))
    expected_digests = {}
    for line in contents['SHA256SUMS'].decode('utf-8').splitlines():
        digest, name = line.split('  ', 1)
        if name in expected_digests or not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError('摘要清单格式错误或重复')
        expected_digests[name] = digest
    if set(expected_digests) != set(expected) - {'SHA256SUMS'}:
        raise ValueError('摘要清单未精确覆盖公开文件')
    if any(hashlib.sha256(contents[name]).hexdigest() != digest for name, digest in expected_digests.items()):
        raise ValueError('公开文件摘要不一致')
    return {'status': 'passed', 'public_files': len(contents), 'digests_verified': len(expected_digests),
            'limit': 'selected patterns only; human review remains required'}


def from_index(root):
    actual_root = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], text=True).strip()
    if Path(actual_root).resolve() != root.resolve():
        raise ValueError('必须是独立仓库，不能读取或发布父仓库')
    names = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
    names = [name for name in names if name]
    validate_names(names)
    return {name: subprocess.check_output(['git', '-C', str(root), 'show', ':' + name]) for name in names}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', action='store_true', help='Check exact Git index blobs, not working-tree copies')
    args = parser.parse_args()
    try:
        if args.index:
            contents = from_index(ROOT)
        else:
            names = json.loads((ROOT / 'PUBLIC_FILES.json').read_text(encoding='utf-8'))['files']
            validate_names(names)
            contents = {}
            for name in names:
                path = ROOT / name
                if path.is_symlink():
                    raise ValueError('不发布符号链接')
                contents[name] = path.read_bytes()
        print(json.dumps(validate_release(contents), ensure_ascii=True, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError):
        # Detailed pattern findings are safe, but command errors may contain host data.
        print('Public-file check failed; inspect the allowlist, digests and selected sensitive patterns locally.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
