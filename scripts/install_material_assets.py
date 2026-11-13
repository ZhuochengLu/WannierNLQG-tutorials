#!/usr/bin/env python3
"""Verify a local tutorial data set and create private path bindings; never download or run models."""
from pathlib import Path
import argparse,hashlib,json,os,re
ROOT=Path(__file__).resolve().parents[1]

def material_path(root,logical):
    rel=Path(logical)
    if rel.is_absolute()or'..'in rel.parts or not rel.parts or rel.parts[0]!='Materials':
        raise ValueError('Invalid logical material path: '+logical)
    path=root/rel
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Material path escapes the chosen asset root: '+logical)
    return path

def verify_assets(requirements,root):
    root=Path(root).expanduser().resolve()
    if not root.is_dir():raise FileNotFoundError(root)
    cache={};checked=[]
    for row in requirements['requirements']:
        if row['kind']!='file':continue
        logical=row['logical_path'];path=material_path(root,logical)
        if not path.is_file():raise FileNotFoundError('Missing required asset: '+logical)
        expected=row['expected_sha256'];size=row['expected_bytes']
        if not isinstance(expected,str)or not re.fullmatch('[0-9a-f]{64}',expected)or not isinstance(size,int):
            raise ValueError('Expected asset identity is not recorded: '+logical)
        stat=path.stat()
        if stat.st_size!=size:raise ValueError('Asset size mismatch: '+logical)
        key=(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns)
        if key not in cache:
            digest=hashlib.sha256()
            with path.open('rb')as stream:
                for block in iter(lambda:stream.read(4*1024**2),b''):digest.update(block)
            after=path.stat()
            if (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)!=key:
                raise ValueError('Asset changed during verification: '+logical)
            cache[key]=digest.hexdigest()
        if cache[key]!=expected:raise ValueError('Asset SHA-256 mismatch: '+logical)
        checked.append(logical)
    return {'qualification':'ASSET_INTEGRITY_ONLY','verified_files':len(checked),
        'distinct_files_read':len(cache),'model_or_response_executed':False,'asset_set':requirements.get('asset_set',{}).get('id')}

def write_bindings(requirements,asset_root,destination):
    root=Path(asset_root).expanduser().resolve();destination=Path(destination).expanduser().absolute()
    destination=destination.parent.resolve()/destination.name
    lines=['# Private material locations only; no numerical parameter changes.','[paths]']
    for logical in requirements['binding_keys']:
        path=material_path(root,logical)
        try:relative=os.path.relpath(path,destination.parent)
        except ValueError:relative=str(path)
        lines.append(json.dumps(logical)+' = '+json.dumps(relative))
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('x')as stream:stream.write('\n'.join(lines)+'\n')
    return destination

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets-root',type=Path)
    parser.add_argument('--write-bindings',type=Path)
    parser.add_argument('--list',action='store_true')
    args=parser.parse_args();requirements=json.loads((ROOT/'manifests/material_requirements.json').read_text())
    if args.list:
        print(json.dumps([{'path':r['logical_path'],'kind':r['kind'],'bytes':r.get('expected_bytes'),'sha256':r.get('expected_sha256')}for r in requirements['requirements']],indent=2));return
    if args.assets_root is None:parser.error('--assets-root is required for verification')
    report=verify_assets(requirements,args.assets_root)
    if args.write_bindings:report['private_bindings_written']=str(write_bindings(requirements,args.assets_root,args.write_bindings))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
