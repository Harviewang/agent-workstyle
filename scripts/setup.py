"""Python 3.11+ standard-library installer. Default action is a read-only plan."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import tomllib
import uuid

NAME = 'codex-workstyle'
VERSION = '1.0.1'
START, END = '[codex-workstyle:start]', '[codex-workstyle:end]'
PAYLOAD = ('SKILL.md', 'agents/openai.yaml', 'references/workflow.md',
           'references/records.md', 'scripts/setup.py', 'README.zh-CN.md', 'LICENSE')
SOURCE = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse(data):
    return tomllib.loads(data.decode('utf-8'))


def string_end(text, start):
    quote = text[start]
    if quote not in ('"', "'"):
        raise ValueError('developer_instructions 必须是 TOML 字符串')
    triple = text.startswith(quote * 3, start)
    token = quote * (3 if triple else 1)
    i = start + len(token)
    while i < len(text):
        if quote == '"' and text[i] == '\\':
            i += 2
        elif text.startswith(token, i):
            i += len(token)
            # A multiline TOML string may end in four or five quotes.
            if triple:
                while i < len(text) and text[i] == quote:
                    i += 1
            return i
        else:
            i += 1
    raise ValueError('无法安全定位字符串结尾')


def instruction_span(text):
    """Find the root field, skipping strings, comments and array contents."""
    i, depth, line_start = 0, 0, True
    while i < len(text):
        if line_start and depth == 0:
            j = i
            while j < len(text) and text[j] in ' \t':
                j += 1
            if text[j:j + 1] == '[':
                break  # A root field cannot be declared inside a TOML table.
            match = re.match(r'''(?:developer_instructions|"developer_instructions"|'developer_instructions')[ \t]*=[ \t]*''', text[j:])
            if match:
                value = j + match.end()
                return j, value, string_end(text, value)
        char = text[i]
        if char == '#':
            end = text.find('\n', i)
            i = len(text) if end < 0 else end
            continue
        if char in ('"', "'"):
            i = string_end(text, i)
            line_start = False
            continue
        if char in '[{':
            depth += 1
        elif char in ']}':
            depth -= 1
        line_start = char == '\n'
        i += 1
    return None


def set_instruction(data, value):
    original = parse(data)
    if 'developer_instructions' in original and not isinstance(original['developer_instructions'], str):
        raise ValueError('现有 developer_instructions 不是字符串，不修改')
    text = data.decode('utf-8')
    span = instruction_span(text)
    newline = '\r\n' if '\r\n' in text else '\n'
    encoded = json.dumps(value, ensure_ascii=False)
    if 'developer_instructions' in original:
        if span is None:
            raise ValueError('不能安全定位现有指令，不修改')
        _, start, end = span
        result = text[:start] + encoded + text[end:]
    else:
        result = 'developer_instructions = ' + encoded + newline + text
    expected = dict(original, developer_instructions=value)
    output = result.encode('utf-8')
    if parse(output) != expected:
        raise ValueError('检测到其他配置变化，停止')
    return output


def remove_instruction(data):
    original = parse(data)
    text = data.decode('utf-8')
    span = instruction_span(text)
    if span is None:
        raise ValueError('无法安全移除本包新增的指令字段')
    start, _, end = span
    output = (text[:start] + text[end:]).encode('utf-8')
    expected = dict(original)
    expected.pop('developer_instructions')
    if parse(output) != expected:
        raise ValueError('移除字段将影响其他配置')
    return output


def read(path):
    return path.read_bytes() if path.exists() else None


def safe(home, path):
    if not path.is_relative_to(home):
        raise ValueError('目标超出 Codex 目录')
    current = path
    while current != home:
        if current.is_symlink():
            raise ValueError('目标存在符号链接，不自动写入：' + str(current))
        current = current.parent


def locations(home):
    home = Path(home).expanduser().resolve()
    skill = home / 'skills' / NAME
    state = home / 'workstyle-state'
    for path in (skill, state, state / 'current.json', home / 'config.toml'):
        safe(home, path)
    return home, skill, state


def atomic(path, data, expected, mode=0o600):
    if read(path) != expected:
        raise ValueError('文件在操作期间改变，停止：' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.workstyle-', dir=path.parent)
    temporary = Path(name)
    try:
        os.chmod(temporary, mode)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        if read(path) != expected:
            raise ValueError('检测到并发改动，停止')
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def lock(state):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = state / 'operation.lock'
    path.mkdir()  # Never silently remove an unknown/stale lock.
    try:
        yield
    finally:
        path.rmdir()


def payload():
    result = {}
    for name in PAYLOAD:
        path = SOURCE / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('发布包文件缺失或为符号链接：' + name)
        result[name] = path.read_bytes()
    return result


def manifest(state):
    path = state / 'current.json'
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    if set(data['files']) != set(PAYLOAD) or not re.fullmatch('[0-9a-f]{32}', data['backup_id']):
        raise ValueError('安装记录结构不匹配，不自动处理')
    return data


def check(home):
    home, skill, state = locations(home)
    safe(home, state / 'current.json')
    record = manifest(state)
    if record is None:
        raise ValueError('此 Codex 目录没有本包的有效安装记录')
    for name, digest in record['files'].items():
        path = skill / name
        safe(home, path)
        if not path.is_file() or sha(path.read_bytes()) != digest:
            raise ValueError('已安装文件被修改或缺失，不覆盖：' + name)
    config = read(home / 'config.toml')
    value = parse(config or b'').get('developer_instructions', '')
    if not isinstance(value, str) or value.count(record['suffix']) != 1:
        raise ValueError('本包指令段被修改或缺失，不自动处理')
    backup = state / 'backups' / record['backup_id'] / 'config.before.toml'
    safe(home, backup)
    if not backup.is_file() or sha(backup.read_bytes()) != record['before_sha256']:
        raise ValueError('私有备份缺失或改变')
    return {'status': 'ok', 'version': record['version'], 'files_verified': len(PAYLOAD),
            'codex_home': str(home), 'scope': '安装完整性；不代表模型行为保证'}


def prepare(home):
    home, skill, state = locations(home)
    files = payload()
    if manifest(state) is not None:
        check(home)
        record = manifest(state)
        if record['files'] != {name: sha(data) for name, data in files.items()}:
            raise ValueError('已安装另一版本；先检查并显式撤销，再安装新版本')
        return home, skill, state, files, None
    if skill.exists():
        raise ValueError('未知同名 skill 已存在，不覆盖：' + str(skill))
    before = read(home / 'config.toml')
    value = parse(before or b'').get('developer_instructions', '')
    if not isinstance(value, str) or START in value or END in value:
        raise ValueError('已有指令不兼容或管理段冲突，不覆盖')
    suffix = ('\n\n' + START + '\n'
              '用用户能理解的语言讲清目标、进展、结果、下一步与确需决策的事项；技术依据放附录。'
              '已明确授权的小步内连续完成，不因内部阶段切换反复确认或只报计划就停下。'
              '涉及项目工作时先读取 ' + (skill / 'SKILL.md').as_posix() +
              ' 接入既有要求与流程；普通独立问答无需预读。\n' + END)
    after = set_instruction(before or b'', value + suffix)
    return home, skill, state, files, (before, after, suffix)


def install(home, apply=False):
    home, skill, state, files, change = prepare(home)
    if change is None:
        return {'status': 'already-installed', 'changed': False}
    if not apply:
        return {'status': 'preview', 'writes': [str(skill), str(home / 'config.toml'), str(state)],
                'preserves': '现有指令与其他配置；不写 AGENTS.md/CLAUDE.md 或任何 Claude 文件'}
    with lock(state):
        home, skill, state, files, change = prepare(home)
        if change is None:
            return {'status': 'already-installed', 'changed': False}
        before, after, suffix = change
        token = uuid.uuid4().hex
        backup_dir = state / 'backups' / token
        safe(home, backup_dir)
        backup_dir.mkdir(parents=True, mode=0o700)
        atomic(backup_dir / 'config.before.toml', before or b'', None)
        config = home / 'config.toml'
        mode = stat.S_IMODE(config.stat().st_mode) if config.exists() else 0o600
        written = []
        config_written = False
        try:
            for name, content in files.items():
                path = skill / name
                safe(home, path)
                atomic(path, content, None)
                written.append(path)
            atomic(config, after, before, mode)
            config_written = True
            record = {'version': VERSION, 'backup_id': token, 'before_existed': before is not None,
                      'before_sha256': sha(before or b''), 'after_sha256': sha(after), 'suffix': suffix,
                      'files': {name: sha(data) for name, data in files.items()}}
            atomic(state / 'current.json', json.dumps(record, ensure_ascii=False, indent=2).encode(), None)
        except Exception:
            if config_written and read(config) == after:
                if before is None:
                    config.unlink()
                else:
                    atomic(config, before, after, mode)
            for path in reversed(written):
                if read(path) == files[path.relative_to(skill).as_posix()]:
                    path.unlink()
            prune_empty(skill)
            raise
    return dict(check(home), status='installed', changed=True)


def prune_empty(skill):
    for directory in (skill / 'scripts', skill / 'references', skill / 'agents', skill):
        if directory.is_dir() and not directory.is_symlink():
            try:
                directory.rmdir()
            except OSError:
                pass  # Preserve unknown files; never recursively delete user content.


def uninstall(home, apply=False):
    home, skill, state = locations(home)
    check(home)
    record = manifest(state)
    config = home / 'config.toml'
    before = read(config)
    backup = (state / 'backups' / record['backup_id'] / 'config.before.toml').read_bytes()
    if sha(before) == record['after_sha256']:
        after = backup if record['before_existed'] else None
    else:
        current = parse(before)
        value = current['developer_instructions'].replace(record['suffix'], '', 1)
        original = parse(backup)
        after = (remove_instruction(before) if not value and 'developer_instructions' not in original
                 else set_instruction(before, value))
    if not apply:
        return {'status': 'preview-uninstall', 'preserves': '其他配置、用户新增文件和私有原件备份'}
    with lock(state):
        check(home)
        if read(config) != before:
            raise ValueError('配置并发变化，停止撤销')
        history = state / 'history'
        safe(home, history)
        history.mkdir(exist_ok=True)
        stage = state / 'backups' / record['backup_id'] / ('uninstall-' + uuid.uuid4().hex)
        safe(home, stage)
        stage.mkdir(mode=0o700)
        moved, config_changed = [], False
        mode = stat.S_IMODE(config.stat().st_mode)
        try:
            # Move managed files into private recovery storage; do not delete them.
            for name in PAYLOAD:
                path = skill / name
                safe(home, path)
                if sha(path.read_bytes()) != record['files'][name]:
                    raise ValueError('文件并发变化，保留现场：' + name)
                saved = stage / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                os.replace(path, saved)
                moved.append((path, saved))
            if read(config) != before:
                raise ValueError('配置并发变化，撤销未应用')
            if after is None:
                os.replace(config, stage / 'config.installed.toml')
            else:
                atomic(config, after, before, mode)
            config_changed = True
            os.replace(state / 'current.json', history / (record['backup_id'] + '.json'))
        except Exception as error:
            recovery = []
            if config_changed:
                try:
                    if after is None and not config.exists():
                        os.replace(stage / 'config.installed.toml', config)
                    elif after is not None and read(config) == after:
                        atomic(config, before, after, mode)
                    else:
                        recovery.append('配置已被其他进程修改')
                except OSError:
                    recovery.append('配置恢复受阻')
            for path, saved in reversed(moved):
                try:
                    safe(home, path)
                    if not path.exists() and sha(saved.read_bytes()) == record['files'][path.relative_to(skill).as_posix()]:
                        os.replace(saved, path)
                    else:
                        recovery.append(path.relative_to(skill).as_posix())
                except (OSError, ValueError):
                    recovery.append(path.relative_to(skill).as_posix())
            if recovery:
                raise ValueError('撤销受阻；未覆盖外部变化。恢复资料保留于 ' + str(stage) + '；' + ', '.join(recovery)) from error
            raise
        prune_empty(skill)
    return {'status': 'uninstalled', 'backup_retained': True, 'other_files_preserved': True,
            'recovery_directory': str(stage)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=('plan', 'install', 'check', 'uninstall'), default='plan')
    parser.add_argument('--codex-home', default=os.environ.get('CODEX_HOME') or str(Path.home() / '.codex'))
    parser.add_argument('--apply', action='store_true', help='Explicitly apply uninstall; install is already explicit')
    args = parser.parse_args(argv)
    try:
        if args.action == 'check':
            result = check(args.codex_home)
        elif args.action == 'uninstall':
            result = uninstall(args.codex_home, args.apply)
        else:
            result = install(args.codex_home, args.action == 'install')
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'stopped', 'reason': str(error)}, ensure_ascii=True), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
