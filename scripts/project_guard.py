"""Dispatch existing-project CLI work to its verified pinned runtime."""
from pathlib import Path
import os
import sys
from urllib.parse import urlsplit, unquote

VALUE_OPTIONS = {'--version', '--name', '--form', '--from-version', '--state', '--revision',
                 '--query', '--key', '--patch', '--page', '--id', '--field', '--value', '--port',
                 '--action', '--payload', '--report', '--input', '--evidence', '--rubric', '--url', '--out'}
FLAG_OPTIONS = {'--apply', '--save', '--read', '--summary', '--strict', '--draft', '--structure-only'}


def arguments(args):
    """Locate positionals even when flags precede them; leave full validation to the tool."""
    positionals, options = [], {}
    i = 0
    while i < len(args):
        token = args[i]
        if token == '--':
            positionals += args[i + 1:]; break
        if token.startswith('-'):
            key, sep, value = token.partition('=')
            if key in VALUE_OPTIONS:
                if not sep:
                    i += 1
                    value = args[i] if i < len(args) else None
                options[key] = value
            elif key in FLAG_OPTIONS:
                options[key] = True
            else:
                raise ValueError('请使用完整的命令选项：' + key)
        else:
            positionals.append(token)
        i += 1
    return positionals, options


def dispatch(script):
    try:
        _dispatch(script)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit('项目版本检查失败：' + str(error))


def _dispatch(script):
    args = sys.argv[1:]
    name = Path(script).name
    if not args or '--help' in args or '-h' in args:
        return
    positionals, options = arguments(args)
    command = positionals[0] if positionals else None
    if name == 'project.py':
        if command in ('init', 'discover', 'pin-status', 'upgrade-shell') or len(positionals) < 2:
            return
        location = positionals[1]
    else:
        if not positionals:
            return
        location = positionals[0]
    parsed = urlsplit(location)
    if parsed.scheme not in ('', 'file'):
        return
    path = Path(unquote(parsed.path)).expanduser().resolve()
    root = next((p for p in (path, *path.parents) if (p / 'project.json').is_file()), None)
    if root is None:
        return
    sys.path.insert(0, str(Path(script).resolve().parents[1] / 'template'))
    import skilllocklib
    lock = skilllocklib.load(root)
    if not lock:
        # Read-only inspection still works on existing V2; do not invent their origin.
        readonly = (name in ('validate.py', 'audit_quality.py', 'review_delivery.py', 'delivery_info.py')
                    or (name == 'project.py' and command in ('check', 'impact'))
                    or (name == 'edit_project.py' and options.get('--action') in ('state', 'preview'))
                    or (name in ('maintain.py', 'revise_item.py') and '--save' not in options))
        if not readonly:
            raise ValueError('项目尚未锁定技能。先运行 project.py upgrade-shell <项目> 查看差异，再在明确采用此版本后加 --apply；不会自动认定旧项目的生成版本。')
        print('提示：项目尚未锁定技能；本次仅检查。', file=sys.stderr)
        return
    errors = skilllocklib.verify(root)
    if errors:
        raise ValueError('\n'.join(errors))
    target = root / lock['runtime'] / 'scripts' / name
    if not target.is_file():
        raise ValueError('锁定版本不包含此工具；请使用该版本已有维护入口，或先预览并显式升级技能。')
    if target.resolve() != Path(script).resolve():
        print('使用项目锁定技能 ' + lock['version'] + '：' + str(target), file=sys.stderr)
        os.execv(sys.executable, [sys.executable, str(target), *args])
