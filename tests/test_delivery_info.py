import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from delivery_info import delivery_info
from projectlib import hashes


class DeliveryLocationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)/'project with spaces'
        subprocess.run([sys.executable,str(ROOT/'scripts/create_static_demo.py'),str(cls.root)],check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_locations_and_package_scope_are_read_only(self):
        before=hashes(self.root)
        info=delivery_info(self.root,'http://localhost:8795','create-order')
        self.assertEqual(info['local_web_entry'],str(self.root.resolve()/'site/index.html'))
        self.assertEqual(info['package_root'],str(self.root.resolve()))
        self.assertEqual(info['localhost_url'],'http://localhost:8795/site/index.html#/v/v0.1/prototype/create-order')
        self.assertIn('versions',info['package_note']);self.assertEqual(before,hashes(self.root))

    def test_rejects_foreign_host_tokens_and_invalid_page(self):
        for url in ['https://example.com','http://localhost:8795/#token=secret','http://localhost:8795/site/index.html','http://user:pass@localhost:8795']:
            with self.subTest(url=url),self.assertRaises(ValueError):delivery_info(self.root,url)
        with self.assertRaises(ValueError):delivery_info(self.root,'http://localhost:8795','missing')

    def test_modified_source_is_not_reported_as_fresh_delivery(self):
        file=self.root/'versions/v0.1/content/spec.json';before=file.read_bytes()
        try:
            file.write_bytes(before+b'\n')
            with self.assertRaises(ValueError):delivery_info(self.root,'http://localhost:8795')
        finally:file.write_bytes(before)
