"""Small integrity and path-binding boundary tests; no material payload required."""
from pathlib import Path
import hashlib,importlib.util,json,tempfile,tomllib,unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('material_assets',ROOT/'scripts/install_material_assets.py')
assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)

class MaterialAssets(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.file=self.root/'Materials/GeS/GeS.chk';self.file.parent.mkdir(parents=True);self.file.write_bytes(b'fixture')
        self.requirements={'requirements':[{'logical_path':'Materials/GeS/GeS.chk','kind':'file','expected_bytes':7,'expected_sha256':hashlib.sha256(b'fixture').hexdigest()}],
            'binding_keys':['Materials/GeS/GeS.chk','Materials/GeS/GeS']}
    def tearDown(self):self.tmp.cleanup()
    def test_verified_binding_preserves_seed_prefix(self):
        self.assertEqual(assets.verify_assets(self.requirements,self.root)['verified_files'],1)
        out=self.root/'private/locations.toml';assets.write_bindings(self.requirements,self.root,out)
        paths=tomllib.loads(out.read_text())['paths']
        self.assertEqual((out.parent/paths['Materials/GeS/GeS']).resolve(),(self.root/'Materials/GeS/GeS').resolve())
        self.assertEqual((out.parent/paths['Materials/GeS/GeS.chk']).resolve(),self.file.resolve())
        with self.assertRaises(FileExistsError):assets.write_bindings(self.requirements,self.root,out)
    def test_wrong_bytes_rejected(self):
        self.file.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'SHA-256'):assets.verify_assets(self.requirements,self.root)
    def test_missing_file_rejected(self):
        self.file.unlink()
        with self.assertRaises(FileNotFoundError):assets.verify_assets(self.requirements,self.root)
    def test_escape_rejected(self):
        with self.assertRaises(ValueError):assets.material_path(self.root,'../outside')
    def test_binding_parent_symlink(self):
        target=self.root/'canonical/deeper';target.mkdir(parents=True)
        alias=self.root/'alias';alias.symlink_to(target,target_is_directory=True)
        out=alias/'locations.toml';assets.write_bindings(self.requirements,self.root,out)
        paths=tomllib.loads(out.read_text())['paths']
        self.assertEqual((out.parent/paths['Materials/GeS/GeS.chk']).resolve(),self.file.resolve())

if __name__=='__main__':unittest.main()
