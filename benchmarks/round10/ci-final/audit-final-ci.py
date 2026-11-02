"""Read-only exact-head audit of production CUDA compilation checks for PR54-57."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent
REPO = 'QuiteLiterallyConnor/Minkowski4CPP'
EXPECTED = {54: '4ac4292e40fd78c4d3b81cdc3e775898737647f8',
            55: 'd46eea3e23890e46da7c9b77a42a14f287620aed',
            56: '348e6b83da8bb068274ac02288f01defdbeaf5a3',
            57: 'b5c4bd8ab8b0f3557f04ff1cca09feea8e95922b'}
PROFILES = {'build-and-publish (124)', 'build-and-publish (132)', 'build-and-publish (134)'}
parser = argparse.ArgumentParser()
parser.add_argument('--watch', action='store_true')
args = parser.parse_args()

def command(command_args):
    result = subprocess.run(['gh', *command_args], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[:500])
    return result.stdout

def pr_state(number):
    return json.loads(command(['pr', 'view', str(number), '--repo', REPO,
                              '--json', 'number,headRefOid,statusCheckRollup,url']))

def actual_log(number, check):
    run, job = re.search(r'/runs/(\d+)/job/(\d+)', check['detailsUrl']).groups()
    path = ROOT / f'pr{number}-job-{job}.log'
    if not path.exists() or path.stat().st_size == 0:
        data = command(['api', '--allow-escape-sequences', f'repos/{REPO}/actions/jobs/{job}/logs'])
        path.write_bytes(data)
    data = path.read_bytes()
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', data.decode(errors='replace'))
    if check['conclusion'] != 'SUCCESS':
        raise RuntimeError(f'PR{number} job{job} failed; raw log {path}')
    # Read actual production CMake summary, not mocked version messages emitted
    # by tests/builders or versions appearing in the PR body at the log's end.
    def unique(pattern, name):
        values = set(re.findall(pattern, text))
        if len(values) != 1:
            raise RuntimeError(f'PR{number} job{job} needs review: {name} values {values}')
        return values.pop()
    cuda = unique(r'#\d+\s+[\d.]+ -- CUDA:\s+([0-9.]+)', 'actual CUDA')
    torch = unique(r'#\d+\s+[\d.]+ -- Torch:\s+([^\s]+)', 'actual LibTorch')
    cpu_only = unique(r'#\d+\s+[\d.]+ -- CPU only:\s+(ON|OFF)', 'CPU_ONLY')
    if cpu_only != 'OFF':
        raise RuntimeError('Production CUDA profile unexpectedly CPU_ONLY')
    merge = re.search(r'git log -1 --format=%H\r?\n[^\r\n]*? ([0-9a-f]{40})\r?\n', text)
    if not merge:
        raise RuntimeError('Missing actual checked-out merge identity')
    merge_line = re.search(r'HEAD is now at [0-9a-f]+ Merge ([0-9a-f]{40}) into ([0-9a-f]{40})', text)
    if not merge_line or merge_line.group(1) != EXPECTED[number]:
        raise RuntimeError('Production checkout did not merge expected PR head')
    cuda_objects = len(re.findall(r'Building CUDA object ', text))
    if cuda_objects == 0 or '-- Installing: /usr/local/' not in text:
        raise RuntimeError('Missing CUDA object compilation or completed install evidence')
    return dict(pr=number, pr_head=EXPECTED[number], profile=check['name'], run=run, job=job,
                status='success', checked_out_merge=merge.group(1), merge_base=merge_line.group(2),
                actual_cuda=cuda, actual_libtorch=torch, cpu_only=False,
                cuda_object_build_lines=cuda_objects, install_completed=True,
                execution_scope='production CUDA compilation and installation; no test execution claimed',
                log=path.name, log_sha256=hashlib.sha256(data).hexdigest())

while True:
    with ThreadPoolExecutor(max_workers=4) as pool:
        states = list(pool.map(pr_state, EXPECTED))
    checks = []
    completed = []
    for state in states:
        number = state['number']
        if state['headRefOid'] != EXPECTED[number]:
            raise RuntimeError(f'PR{number} head changed; update audit with explicit new identity')
        selected = [c for c in state['statusCheckRollup'] if c.get('workflowName') == 'CI']
        if len(selected) != 3 or {c['name'] for c in selected} != PROFILES:
            raise RuntimeError(f'PR{number} lacks exact three production CI jobs')
        for check in selected:
            checks.append(dict(pr=number, head=state['headRefOid'], name=check['name'],
                               status=check['status'], conclusion=check['conclusion'], url=check['detailsUrl']))
            if check['status'] == 'COMPLETED':
                completed.append((number, check))
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(lambda pair: actual_log(*pair), completed))
    complete = len(records) == 12
    result = dict(status='passed' if complete else 'pending',
                  checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  expected_heads=EXPECTED, checks=checks, completed_production_logs=records,
                  claim='production CUDA compilation is separate from repeated CPU_ONLY runtime validation',
                  cpu_runtime_run='41514149790', cpu_runtime_head='aa74d97229e899adfb5ec7c8c0037d1d06d1245e')
    (ROOT / 'current-state.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['checked_at'], result['status'], f'{len(records)}/12 production checks verified', flush=True)
    if complete:
        (ROOT / 'CERTIFICATE.json').write_text(json.dumps(result, indent=2) + '\n')
        break
    if not args.watch:
        break
    time.sleep(45)
