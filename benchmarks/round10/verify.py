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
ci=json.loads((root/'ci-final/CERTIFICATE.json').read_text())
assert ci['status']=='passed' and len(ci['checks'])==len(ci['completed_production_logs'])==12
assert all(c['conclusion']=='SUCCESS' and c['status']=='COMPLETED' for c in ci['checks'])
with zipfile.ZipFile(root/'ci-final/production-logs.zip') as archive:
    assert archive.testzip() is None and len(archive.namelist())==12
    for row in ci['completed_production_logs']:
        assert hashlib.sha256(archive.read(row['log'])).hexdigest()==row['log_sha256']
        assert row['status']=='success' and not row['cpu_only'] and row['install_completed']
        assert row['cuda_object_build_lines']>0
with zipfile.ZipFile(root/'negative-warp-bounds.zip') as archive:
    assert archive.testzip() is None
    negative_members=len(archive.namelist())
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
print(f'Verified {len(manifest)} evidence files, {members} container members, '
      f'{negative_members} negative-experiment files, native/Docker gates and12production CUDA builds')
