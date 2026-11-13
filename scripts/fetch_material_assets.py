#!/usr/bin/env python3
"""Fetch/check versioned data archives or install them into a new directory.

Only Python's standard library is required. A manifest with unpublished URLs
can be exercised using --source-dir; that does not test a public download.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import urllib.request

from install_material_assets import verify_assets, write_bindings

ROOT = Path(__file__).resolve().parents[1]
BLOCK = 4 * 1024**2


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(BLOCK), b''):
            h.update(b)
    return h.hexdigest()


def check_file(path, row):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Not a regular local asset: ' + path.name)
    if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
        raise ValueError('Size/SHA-256 mismatch: ' + path.name)


def load_manifest(path):
    d = json.loads(Path(path).read_text())
    if d['schema'] != 'tutorial-material-distribution/1':
        raise ValueError('Unsupported distribution schema')
    seen, files = set(), set()
    for a in d['archives']:
        for r in [a, *a['parts']]:
            name = r['name']
            if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
                raise ValueError('Unsafe archive/part name')
            if not isinstance(r['bytes'], int) or isinstance(r['bytes'], bool) or r['bytes'] <= 0:
                raise ValueError('Invalid byte length')
            if not re.fullmatch('[0-9a-f]{64}', r['sha256']):
                raise ValueError('Invalid SHA-256')
        if a['name'] in seen or not a['parts']:
            raise ValueError('Duplicate archive or empty part list')
        seen.add(a['name'])
        if sum(p['bytes'] for p in a['parts']) != a['bytes']:
            raise ValueError('Part lengths do not sum to archive length')
        part_names = [p['name'] for p in a['parts']]
        if len(set(part_names)) != len(part_names):
            raise ValueError('Duplicate part')
        for f in a['files']:
            p = PurePosixPath(f['logical_path'])
            if p.is_absolute() or '..' in p.parts or str(p) != f['logical_path'] or p.parts[0] != 'Materials':
                raise ValueError('Unsafe member path')
            if f['logical_path'] in files:
                raise ValueError('Duplicate logical file')
            files.add(f['logical_path'])
            if not isinstance(f['bytes'], int) or isinstance(f['bytes'], bool) or f['bytes'] <= 0 or not re.fullmatch('[0-9a-f]{64}', f['sha256']):
                raise ValueError('Invalid member identity')
    return d


def fetch(d, downloads, source_dir=None):
    downloads = Path(downloads)
    downloads.mkdir(parents=True, exist_ok=True)
    source_dir = Path(source_dir) if source_dir is not None else None
    for a in d['archives']:
        for p in a['parts']:
            dest = downloads / p['name']
            if dest.exists() or dest.is_symlink():
                check_file(dest, p)
                continue
            url = p.get('url')
            if source_dir is None and (not isinstance(url, str) or not url.startswith('https://')):
                raise ValueError('NOT_PUBLISHED: no pinned HTTPS URL for ' + p['name'])
            fd, temporary = tempfile.mkstemp(prefix='.fetch-', dir=downloads)
            tmp = Path(temporary)
            try:
                with os.fdopen(fd, 'wb') as out:
                    if source_dir is not None:
                        source = source_dir / p['name']
                        check_file(source, p)
                        with source.open('rb') as inp:
                            shutil.copyfileobj(inp, out, BLOCK)
                    else:
                        with urllib.request.urlopen(url, timeout=60) as inp:
                            if not inp.geturl().startswith('https://'):
                                raise ValueError('Refuse non-HTTPS redirect')
                            remaining = p['bytes']
                            while remaining:
                                b = inp.read(min(BLOCK, remaining))
                                if not b:
                                    raise ValueError('Truncated download')
                                out.write(b)
                                remaining -= len(b)
                            if inp.read(1):
                                raise ValueError('Download exceeds declared size')
                check_file(tmp, p)
                os.link(tmp, dest)  # exclusive publication, never overwrite a race
            finally:
                tmp.unlink(missing_ok=True)
    return {'status': 'PARTS_VERIFIED', 'source': 'LOCAL_EQUIVALENT' if source_dir else 'PINNED_HTTPS'}


def install(d, downloads, destination, requirements):
    downloads, destination = Path(downloads), Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Destination must be absent; use the ordinary verifier for existing data')
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.materials-', dir=destination.parent))
    try:
        for a in d['archives']:
            fd, name = tempfile.mkstemp(prefix='.archive-', dir=destination.parent)
            archive = Path(name)
            try:
                with os.fdopen(fd, 'wb') as out:
                    for p in a['parts']:
                        part = downloads / p['name']
                        check_file(part, p)
                        with part.open('rb') as inp:
                            shutil.copyfileobj(inp, out, BLOCK)
                check_file(archive, a)
                expected = {f['logical_path']: f for f in a['files']}
                seen = set()
                with tarfile.open(archive, 'r|gz') as tar:
                    for member in tar:
                        if member.name not in expected or member.name in seen or not member.isfile() or member.size != expected[member.name]['bytes']:
                            raise ValueError('Unexpected, duplicate, linked, or wrong-size archive member')
                        seen.add(member.name)
                        dest = stage / member.name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        h = hashlib.sha256()
                        with tar.extractfile(member) as inp, dest.open('xb') as out:
                            for b in iter(lambda: inp.read(BLOCK), b''):
                                out.write(b)
                                h.update(b)
                        if h.hexdigest() != expected[member.name]['sha256']:
                            raise ValueError('Extracted member SHA-256 mismatch')
                if seen != set(expected):
                    raise ValueError('Missing archive member')
            finally:
                archive.unlink(missing_ok=True)
        result = verify_assets(requirements, stage)
        # mkdir is an exclusive reservation. Never replace an existing destination,
        # even if another process creates it while verification is running.
        destination.mkdir()
        try:
            os.rename(stage / 'Materials', destination / 'Materials')
        except BaseException:
            destination.rmdir()
            raise
        result['status'] = 'INSTALLED_AND_RAW_SHA256_VERIFIED'
        return result
    finally:
        shutil.rmtree(stage)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['fetch', 'install'])
    p.add_argument('--manifest', type=Path, default=ROOT / 'manifests/material_distribution.json')
    p.add_argument('--downloads', type=Path, required=True)
    p.add_argument('--source-dir', type=Path)
    p.add_argument('--destination', type=Path)
    p.add_argument('--write-bindings', type=Path)
    a = p.parse_args()
    d = load_manifest(a.manifest)
    if a.action == 'fetch':
        result = fetch(d, a.downloads, a.source_dir)
    else:
        if a.destination is None or a.source_dir is not None:
            p.error('install requires --destination; --source-dir is only for fetch')
        requirements = json.loads((ROOT / 'manifests/material_requirements.json').read_text())
        result = install(d, a.downloads, a.destination, requirements)
        if a.write_bindings:
            result['private_bindings_written'] = str(write_bindings(requirements, a.destination, a.write_bindings))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
