import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class Scripts(HTMLParser):
    def __init__(self):super().__init__();self.scripts=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script':self.scripts.append(dict(attrs))


class BundledAssetsTests(unittest.TestCase):
    def test_new_project_contains_verified_local_diagram_dependency(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'project'
            subprocess.run([sys.executable,str(ROOT/'scripts/project.py'),'init',str(root),'--name','offline','--form','web','--version','v0.1'],check=True,capture_output=True)
            vendor=root/'site/js/vendor'
            metadata=json.loads((vendor/'mermaid.json').read_text())
            self.assertEqual(hashlib.sha256((vendor/metadata['file']).read_bytes()).hexdigest(),metadata['sha256'])
            self.assertIn('Permission is hereby granted',(vendor/metadata['license_file']).read_text())
            parser=Scripts();parser.feed((root/'site/index.html').read_text())
            self.assertFalse(any(s.get('src','').startswith(('https:','http:')) for s in parser.scripts))
            graph=next(i for i,s in enumerate(parser.scripts) if s.get('src')=='js/vendor/'+metadata['file'])
            boot=next(i for i,s in enumerate(parser.scripts) if s.get('src')=='js/main.js')
            self.assertLess(graph,boot)
            self.assertIn('defer',parser.scripts[graph]);self.assertNotIn('async',parser.scripts[graph])


if __name__=='__main__':unittest.main()
