import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'template'))
from projectlib import read, write, hashes, validate, check_build


class HandoffTests(unittest.TestCase):
    def test_revisions_keep_draft_and_old_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / 'project'
            subprocess.run([sys.executable, str(ROOT / 'scripts/create_demo.py'), str(root)], check=True, capture_output=True)
            def handoff(r):
                return subprocess.run([sys.executable, str(ROOT / 'scripts/project.py'), 'handoff', str(root), '--version', 'v1.1', '--revision', r], capture_output=True, text=True)
            result = handoff('r1')
            self.assertEqual(result.returncode, 0, result.stderr)
            old = hashes(root / 'versions/v1.1.r1')
            specfile = root / 'versions/v1.1/content/spec.json'
            spec = read(specfile); spec['requirements'][0]['title'] = '第二次交接需求'
            write(specfile, spec)
            result = handoff('r2')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(old, hashes(root / 'versions/v1.1.r1'))
            project = read(root / 'project.json')
            self.assertEqual(project['current_version'], 'v1.1')
            self.assertEqual(project['versions'][0]['status'], 'planning')
            self.assertEqual(project['versions'][0]['current_handoff'], 'v1.1.r2')
            self.assertEqual(project['versions'][-1]['base'], 'v1.1.r1')
            self.assertNotEqual(handoff('r1').returncode, 0)
            self.assertEqual(validate(root)[0], [])
            self.assertEqual(check_build(root), [])
            (root / 'versions/v1.1.r1/content/prototype/assets/demo.js').write_text('tampered')
            self.assertTrue(validate(root)[0])

    def test_blocking_rule_prevents_handoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / 'project'
            subprocess.run([sys.executable, str(ROOT / 'scripts/create_demo.py'), str(root)], check=True, capture_output=True)
            file = root / 'versions/v1.1/content/spec.json'
            spec = read(file); spec['requirements'][0]['blocking'] = True
            write(file, spec)
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/project.py'), 'handoff', str(root), '--revision', 'r1'], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'versions/v1.1.r1').exists())
