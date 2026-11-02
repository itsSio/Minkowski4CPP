"""Verify frozen round10 evidence without compiling or running models."""
import hashlib
import json
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())['files']
for item in manifest:
    path=root/item['path']
    assert path.is_file() and path.is_relative_to(root)
    assert path.stat().st_size==item['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'],item['path']
native=json.loads((root/'integration-review/gate-audit.json').read_text())
assert native['status']=='passed' and native['original_eager_failure']['status']=='failed'
corrected=root/'container-runtime/run-41514149790'
certificate=json.loads((corrected/'independent-stage-certificate.json').read_text())
assert certificate['audit']=='passed' and len(certificate['jobs'])==3
assert all(j['overall_ci']=='success' and j['ctest_suites']==14 and j['ctest_failures']==0
           and j['sanitizer_build']=='passed' for j in certificate['jobs'])
members=0
for path in root.glob('container-runtime/run-*/decoded-evidence.zip'):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None,path
        members+=len(archive.namelist())
        for name in archive.namelist():
            if name.endswith('/evidence-manifest.json'):
                evidence=json.loads(archive.read(name))
                prefix=name.rsplit('/',1)[0]+'/'
                for item in evidence:
                    payload=archive.read(prefix+item['path'])
                    assert len(payload)==item['bytes']
                    assert hashlib.sha256(payload).hexdigest()==item['sha256']
print(f'Verified {len(manifest)} evidence files, {members} archived members, native and three-job Docker gates')
