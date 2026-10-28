"""Regression for pinned maintenance, explicit upgrades and restorable delivery archives."""
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'template'))
import skilllocklib
import prepare_delivery
from projectlib import read, hashes, compile_project, check_build
from review_delivery import review


def cli(source, *args):
    return subprocess.run([sys.executable, str(source / 'scripts/project.py'), *map(str, args)], capture_output=True, text=True)


class PinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name) / 'base'
        run = cli(ROOT, 'init', cls.base, '--name', '锁定回归', '--form', 'web')
        assert run.returncode == 0, run.stderr

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'
        shutil.copytree(self.base, self.root)

    def candidate(self):
        candidate = Path(self.tmp.name) / 'candidate'
        shutil.copytree(self.root / skilllocklib.load(self.root)['runtime'], candidate)
        doc = candidate / 'references/maintenance.md'
        doc.write_text(doc.read_text() + '\nCandidate instructions.\n')
        return candidate

    def test_init_keeps_self_contained_snapshot_and_pin_status_is_readonly(self):
        self.assertEqual(skilllocklib.verify(self.root), [])
        lock = skilllocklib.load(self.root)
        self.assertTrue((self.root / lock['runtime'] / 'scripts/project_guard.py').is_file())
        before = hashes(self.root)
        report = cli(ROOT, 'pin-status', self.root)
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(json.loads(report.stdout)['changed_files'], [])
        self.assertEqual(before, hashes(self.root))

    def test_same_version_different_contents_do_not_replace_pinned_maintenance(self):
        candidate = self.candidate(); before = skilllocklib.load(self.root)
        run = cli(candidate, 'build', self.root)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('使用项目锁定技能', run.stderr)
        self.assertEqual(skilllocklib.load(self.root), before)
        self.assertIn('references/maintenance.md', skilllocklib.status(self.root, candidate)['changed_files'])

    def test_future_compiler_inventory_does_not_break_old_pinned_project(self):
        candidate = self.candidate()
        library = candidate / 'template/skilllocklib.py'
        library.write_text(library.read_text().replace("'diagramlib.py', 'skilllocklib.py')", "'diagramlib.py', 'skilllocklib.py', 'futurelib.py')"))
        (candidate / 'template/futurelib.py').write_text('# future compiler dependency')
        result = cli(candidate, 'build', self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('使用项目锁定技能', result.stderr)
        self.assertFalse((self.root / 'futurelib.py').exists())

    def test_pinned_dispatch_accepts_reordered_and_equals_options(self):
        candidate = self.candidate()
        for args in [('build', '--version=v1.0', self.root), ('--version', 'v1.0', 'build', self.root)]:
            result = cli(candidate, *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('使用项目锁定技能', result.stderr)

    def test_tampered_runtime_and_compiler_stop_writes(self):
        lock = skilllocklib.load(self.root)
        target = self.root / lock['runtime'] / 'references/maintenance.md'
        target.write_text('tampered')
        self.assertTrue(skilllocklib.verify(self.root))
        before = hashes(self.root)
        result = cli(ROOT, 'build', self.root)
        self.assertNotEqual(result.returncode, 0); self.assertEqual(before, hashes(self.root))
        with self.assertRaises(ValueError): compile_project(self.root)

    def test_compiler_mismatch_not_silently_accepted(self):
        (self.root / 'prdlib.py').write_text('# changed')
        self.assertTrue(any('prdlib.py' in e for e in skilllocklib.verify(self.root)))
        self.assertNotEqual(cli(ROOT, 'check', self.root).returncode, 0)

    def test_explicit_upgrade_previews_then_validates_and_preserves_old_snapshot(self):
        candidate = self.candidate(); old = skilllocklib.load(self.root); before = hashes(self.root)
        result = cli(candidate, 'upgrade-shell', self.root)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertEqual(before, hashes(self.root))
        result = cli(candidate, 'upgrade-shell', self.root, '--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        new = skilllocklib.load(self.root)
        self.assertNotEqual(old['fingerprint'], new['fingerprint'])
        self.assertTrue((self.root / old['runtime']).is_dir())
        self.assertTrue(list((self.root / '.upgrade-backup').rglob('.skill-lock.json')))
        self.assertEqual(skilllocklib.verify(self.root), []); self.assertEqual(check_build(self.root), [])

    def test_failed_candidate_is_rejected_before_live_mutation(self):
        candidate = self.candidate()
        tool = candidate / 'template/projectlib.py'
        tool.write_text(tool.read_text().replace('def compile_project(root):', "def compile_project(root):\n    raise ValueError('candidate failure')"))
        before = hashes(self.root)
        run = cli(candidate, 'upgrade-shell', self.root, '--apply')
        self.assertNotEqual(run.returncode, 0); self.assertEqual(before, hashes(self.root))
        self.assertIn('candidate failure', run.stderr)

    def test_unlocked_v2_requires_explicit_adoption(self):
        (self.root / '.skill-lock.json').unlink(); compile_project(self.root)
        before = hashes(self.root)
        result = cli(ROOT, 'build', self.root)
        self.assertNotEqual(result.returncode, 0); self.assertIn('尚未锁定', result.stderr)
        self.assertEqual(before, hashes(self.root))
        self.assertEqual(cli(ROOT, 'check', self.root).returncode, 0)
        result = cli(ROOT, 'upgrade-shell', self.root, '--apply')
        self.assertEqual(result.returncode, 0, result.stderr); self.assertEqual(skilllocklib.verify(self.root), [])

    def test_upgrade_changes_planning_resources_but_preserves_frozen_content(self):
        project = Path(self.tmp.name) / 'versioned'
        result = subprocess.run([sys.executable, str(ROOT / 'tests/fixtures/versioned_project.py'), str(project)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        frozen = hashes(project / 'versions/v1.0')
        candidate = self.candidate()
        asset = candidate / 'assets/prototype-runtime.css'
        asset.write_text(asset.read_text() + '\n/* candidate runtime */\n')
        result = cli(candidate, 'upgrade-shell', project, '--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(frozen, hashes(project / 'versions/v1.0'))
        self.assertTrue((project / 'versions/v1.1/content/prototype/assets/prototype-runtime.css').read_text().endswith('/* candidate runtime */\n'))
        self.assertEqual(skilllocklib.verify(project), [])

    def test_malformed_lock_fails_with_clear_error(self):
        (self.root / '.skill-lock.json').write_text('[]')
        result = cli(ROOT, 'build', self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('技能锁定记录格式错误', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_new_product_version_inherits_pin(self):
        previous = skilllocklib.load(self.root)
        result = cli(ROOT, 'new-version', self.root, '--version', 'v2.0', '--from-version', 'v1.0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(previous, skilllocklib.load(self.root))


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.root = Path(cls.tmp.name) / 'project'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/create_static_demo.py'), str(cls.root)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        cls.input = Path(cls.tmp.name) / 'original-plan.md'; cls.input.write_text('Synthetic plan for packaging regression only.')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(cls.root)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.tmp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / 'delivery'

    def test_blocking_business_questions_stay_business_and_missing_content_is_agent_work(self):
        report = {'structure': {'errors': []}, 'quality': {'issues': [
            {'code': 'feature_decision', 'severity': 'error', 'path': 'FR/review/recovery', 'message': '失败后能否重试？'},
            {'code': 'prd_pending', 'severity': 'decision', 'path': 'prd/data.md', 'message': '数据章节待补充'},
            {'code': 'diagram_paths_unreviewed', 'severity': 'decision', 'path': 'FLOW', 'message': '场景路径未复核'}]},
            'controls': {'findings': []}, 'semantic': []}
        agent, business = prepare_delivery.split_work(report)
        self.assertEqual([i['code'] for i in business], ['feature_decision'])
        self.assertEqual(business[0]['severity'], 'error')
        self.assertEqual({i['code'] for i in agent}, {'prd_pending', 'diagram_paths_unreviewed'})

    def test_missing_review_is_agent_work_and_does_not_emit_ready_package(self):
        before = hashes(self.root)
        result = prepare_delivery.prepare(self.root, self.url, self.out, [self.input])
        self.assertEqual(result['status'], 'review_draft'); self.assertFalse(result['packages'])
        self.assertTrue(result['agent_todo']); self.assertTrue(result['business_decisions'])
        self.assertEqual(before, hashes(self.root))
        self.assertTrue((self.out / 'delivery-review.json').is_file())

    def test_draft_archives_are_integral_and_source_is_self_contained(self):
        result = prepare_delivery.prepare(self.root, self.url, self.out, [self.input], draft=True)
        self.assertEqual(result['status'], 'review_draft')
        for kind, file in result['packages'].items():
            self.assertIn('review-draft', file)
            with zipfile.ZipFile(file) as archive:
                manifest = json.loads(archive.read('delivery-manifest.json'))
                for key, digest in manifest['files'].items():
                    self.assertEqual(hashlib.sha256(archive.read(key)).hexdigest(), digest)
                if kind == 'static':
                    self.assertFalse(any(n.endswith('.py') for n in archive.namelist()))
                    self.assertIn('site/index.html', archive.namelist())
                else:
                    restored = Path(self.tmp.name) / 'restored'; archive.extractall(restored)
        self.assertEqual(skilllocklib.verify(restored), [])
        self.assertTrue((restored / 'delivery-sources/1-original-plan.md').is_file())
        result = subprocess.run([sys.executable, str(restored / 'build.py')], cwd=self.tmp.name, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        lock = skilllocklib.load(restored)
        result = cli(restored / lock['runtime'], 'check', restored)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ready_branch_packages_only_on_review_recorded(self):
        # Exercise packaging gate only: do not manufacture business confirmation in a real project.
        recorded = review(self.root, inputs=[self.input]); recorded['status'] = 'review_recorded'
        with patch.object(prepare_delivery, 'review', return_value=recorded):
            result = prepare_delivery.prepare(self.root, self.url, self.out, [self.input])
        self.assertEqual(result['status'], 'ready'); self.assertTrue(result['packages']['static'].endswith('static-ready.zip'))

    def test_reports_and_inputs_cannot_be_overwritten_and_service_must_match(self):
        with self.assertRaises(ValueError): prepare_delivery.prepare(self.root, self.url, self.root / 'delivery')
        self.out.mkdir(); (self.out / 'keep').write_text('unchanged')
        with self.assertRaises(ValueError): prepare_delivery.prepare(self.root, self.url, self.out)
        bad = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=self.tmp.name))
        thread = threading.Thread(target=bad.serve_forever, daemon=True); thread.start()
        try:
            with self.assertRaises(OSError):
                prepare_delivery.prepare(self.root, 'http://127.0.0.1:' + str(bad.server_port), Path(self.tmp.name) / 'wrong')
        finally: bad.shutdown(); bad.server_close(); thread.join()

    def test_concurrent_change_during_review_does_not_package_stale_content(self):
        file = self.root / 'input-race.md'
        def changing_review(*args, **kwargs):
            result = review(*args, **kwargs)
            file.write_text('new source while reviewing')
            return result
        try:
            with patch.object(prepare_delivery, 'review', side_effect=changing_review):
                with self.assertRaisesRegex(ValueError, '发生变化'):
                    prepare_delivery.prepare(self.root, self.url, self.out, [self.input], draft=True)
            self.assertFalse(self.out.exists())
        finally:
            file.unlink(missing_ok=True)

    def test_stale_evidence_is_rejected(self):
        evidence = Path(self.tmp.name) / 'evidence.json'; evidence.write_text(json.dumps({'fingerprint': 'old', 'checks': {}}))
        with self.assertRaisesRegex(ValueError, '过期'):
            prepare_delivery.prepare(self.root, self.url, self.out, [self.input], evidence_file=evidence, draft=True)
        self.assertFalse(self.out.exists())
