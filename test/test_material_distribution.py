"""Archive boundary controls, using tiny synthetic bytes only."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_material_assets as tool


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = b'unchanged scientific payload\x00\xff'
        self.logical = 'Materials/GeS/model_tb.dat'
        self.raw = dict(logical_path=self.logical, bytes=len(self.data), sha256=hashlib.sha256(self.data).hexdigest())
        self.requirements = dict(requirements=[dict(kind='file', logical_path=self.logical, expected_bytes=self.raw['bytes'], expected_sha256=self.raw['sha256'])])

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, malicious=None):
        archive = self.root / 'test.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            names = [self.logical] if malicious is None else malicious
            for name in names:
                i = tarfile.TarInfo(name)
                i.size = len(self.data)
                if name == 'symbolic':
                    i.type, i.linkname, i.size = tarfile.SYMTYPE, '/tmp/elsewhere', 0
                tar.addfile(i, io.BytesIO(self.data))
        content = archive.read_bytes()
        parts = []
        for n, offset in enumerate(range(0, len(content), 37)):
            p = self.root / ('part%03d' % n)
            b = content[offset:offset+37]
            p.write_bytes(b)
            parts.append(dict(name=p.name, bytes=len(b), sha256=tool.digest(p), url=None))
        d = dict(schema='tutorial-material-distribution/1', archives=[dict(name='test.tar.gz', bytes=len(content), sha256=tool.digest(archive), parts=parts, files=[self.raw])])
        manifest = self.root / 'manifest.json'
        manifest.write_text(json.dumps(d))
        return tool.load_manifest(manifest)

    def test_split_fetch_reassembly_and_exact_install(self):
        d = self.fixture()
        self.assertGreater(len(d['archives'][0]['parts']), 1)
        result = tool.fetch(d, self.root / 'download', self.root)
        self.assertEqual(result['source'], 'LOCAL_EQUIVALENT')
        result = tool.install(d, self.root / 'download', self.root / 'installed', self.requirements)
        self.assertEqual(result['verified_files'], 1)
        self.assertEqual((self.root / 'installed' / self.logical).read_bytes(), self.data)

    def test_existing_destination_and_bad_cached_part_protected(self):
        d = self.fixture()
        (self.root / 'installed').mkdir()
        (self.root / 'installed/sentinel').write_text('keep')
        with self.assertRaises(FileExistsError):
            tool.install(d, self.root, self.root / 'installed', self.requirements)
        self.assertEqual((self.root / 'installed/sentinel').read_text(), 'keep')
        part = self.root / d['archives'][0]['parts'][0]['name']
        part.write_bytes(b'bad')
        with self.assertRaises(ValueError):
            tool.fetch(d, self.root)

    def test_bad_archive_and_raw_sha_rejected(self):
        d = self.fixture()
        d['archives'][0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            tool.install(d, self.root, self.root / 'installed', self.requirements)
        self.assertFalse((self.root / 'installed').exists())
        d['archives'][0]['sha256'] = tool.digest(self.root / 'test.tar.gz')
        d['archives'][0]['files'][0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            tool.install(d, self.root, self.root / 'installed', self.requirements)
        self.assertFalse((self.root / 'installed').exists())

    def test_traversal_link_duplicate_or_extra_rejected(self):
        for names in [['../outside'], ['symbolic'], [self.logical, self.logical], [self.logical, 'POTCAR']]:
            d = self.fixture(names)
            with self.assertRaises(ValueError):
                tool.install(d, self.root, self.root / 'installed', self.requirements)
            self.assertFalse((self.root / 'installed').exists())

    def test_unpublished_download_and_unsafe_manifest_rejected(self):
        d = self.fixture()
        with self.assertRaisesRegex(ValueError, 'NOT_PUBLISHED'):
            tool.fetch(d, self.root / 'download')
        d['archives'][0]['parts'][0]['name'] = '../outside'
        p = self.root / 'manifest.json'
        p.write_text(json.dumps(d))
        with self.assertRaises(ValueError):
            tool.load_manifest(p)


if __name__ == '__main__':
    unittest.main()
