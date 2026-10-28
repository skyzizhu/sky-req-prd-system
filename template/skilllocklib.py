"""Project-local, content-addressed skill runtime. No network or package manager."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

BUILD_TOOLS = ('build.py', 'projectlib.py', 'outcomelib.py', 'prdlib.py', 'attachmentlib.py', 'materiallib.py', 'qualitylib.py', 'diagramlib.py', 'skilllocklib.py')
PARTS = ('SKILL.md', 'README.md', 'LICENSE', 'TESTS.md', 'config.md', 'agents', 'scripts', 'template', 'assets', 'references', 'examples', 'tests')


def inventory(source):
    source = Path(source)
    result = {}
    for part in PARTS:
        entry = source / part
        files = sorted(entry.rglob('*')) if entry.is_dir() else [entry]
        for file in files:
            rel = file.relative_to(source)
            if '__pycache__' in rel.parts or file.suffix == '.pyc' or file.name == '.DS_Store':
                continue
            if file.is_symlink():
                raise ValueError('技能运行副本不接受符号链接：' + str(rel))
            if file.is_file():
                result[rel.as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    return result


def digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def metadata(source):
    files = inventory(source)
    text = (Path(source) / 'SKILL.md').read_text(encoding='utf-8')
    match = re.search(r'^\s+version:\s*[\"\']?([^\"\'\s]+)', text, re.M)
    if not match:
        raise ValueError('技能缺少 metadata.version')
    return {'version': match.group(1), 'fingerprint': digest(files), 'files': files}


def load(root):
    file = Path(root) / '.skill-lock.json'
    if not file.exists():
        return None
    value = json.loads(file.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or not isinstance(value.get('files'), dict):
        raise ValueError('技能锁定记录格式错误，请恢复备份')
    return value


def verify(root, tools=True):
    root = Path(root).resolve()
    lock = load(root)
    if lock is None:
        return []  # Existing unlocked V2 projects remain readable; adoption is explicit.
    errors = []
    fp = lock.get('fingerprint', '')
    tool_names = lock.get('build_tools')
    valid_tools = isinstance(tool_names, list) and bool(tool_names) and all(isinstance(n, str) and re.fullmatch(r'[a-z][a-z0-9_]*\.py', n) for n in tool_names)
    if lock.get('schema_version') != 1 or not isinstance(fp, str) or not re.fullmatch(r'[a-f0-9]{64}', fp) or lock.get('runtime') != '.skill-runtime/' + fp or not valid_tools:
        return ['技能锁定记录无效']
    target = root / lock['runtime']
    if target.is_symlink() or (root / '.skill-runtime').is_symlink():
        return ['技能运行副本不能使用符号链接']
    project = json.loads((root / 'project.json').read_text(encoding='utf-8'))
    if lock.get('project_id') != project.get('id'):
        errors.append('技能锁与项目身份不一致')
    try:
        actual = metadata(target)
        if any(actual[key] != lock.get(key) for key in ('version', 'fingerprint', 'files')):
            errors.append('锁定技能副本缺失或已修改，请恢复源项目备份或显式升级')
        if tools:
            for name in tool_names:
                file = root / name
                if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != lock['files'].get('template/' + name):
                    errors.append('项目构建工具与锁定版本不一致：' + name)
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append('锁定技能副本不可用：' + str(error))
    return errors


def pin(root, source):
    root, source = Path(root).resolve(), Path(source).resolve()
    info = metadata(source)
    target = root / '.skill-runtime' / info['fingerprint']
    if target.is_symlink() or target.parent.is_symlink():
        raise ValueError('技能运行副本不能使用符号链接')
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.pin-', dir=target.parent) as temporary:
            stage = Path(temporary) / 'runtime'
            for rel in info['files']:
                dest = stage / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / rel, dest)
            if inventory(stage) != info['files']:
                raise ValueError('保存期间技能源发生变化，停止锁定')
            stage.rename(target)
    if inventory(target) != info['files']:
        raise ValueError('目标技能副本与来源不一致，停止锁定')
    project = json.loads((root / 'project.json').read_text(encoding='utf-8'))
    lock = dict(info, schema_version=1, skill='sky-req-prd-system', project_id=project['id'], build_tools=list(BUILD_TOOLS),
                runtime=target.relative_to(root).as_posix(), created_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root, prefix='.skill-lock-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(lock, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(root / '.skill-lock.json')
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return lock


def status(root, source):
    current, locked = metadata(source), load(root)
    before = locked.get('files', {}) if locked else {}
    return {'locked_version': locked.get('version') if locked else None,
            'candidate_version': current['version'], 'locked_fingerprint': locked.get('fingerprint') if locked else None,
            'candidate_fingerprint': current['fingerprint'], 'integrity_errors': verify(root),
            'changed_files': sorted(k for k in set(before) | set(current['files']) if before.get(k) != current['files'].get(k)),
            'runtime': str(Path(root) / locked['runtime']) if locked and not verify(root) else None}


def copy_to_stage(root, stage):
    """Preserve the exact compiler identity during transactional project edits."""
    root, stage = Path(root), Path(stage)
    lock = load(root)
    if not lock:
        return
    errors = verify(root)
    if errors:
        raise ValueError('\n'.join(errors))
    shutil.copy2(root / '.skill-lock.json', stage / '.skill-lock.json')
    shutil.copytree(root / lock['runtime'], stage / lock['runtime'], dirs_exist_ok=True)
    for name in lock['build_tools']:
        shutil.copy2(root / name, stage / name)
