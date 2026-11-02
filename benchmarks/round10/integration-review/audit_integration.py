"""Read-only integration gate audit; writes only this review directory."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROUND = OUT.parent
SOURCE = Path(r'C:\Users\User\Work\mink-wt\integration')
BUILD_ROOT = Path(r'C:\Users\User\Work\mink-build')
EXPECTED = 'a67f671f4aa3a003751e3d06af85d2b9b8b459e5'
SUITES = {'cmake_source_filter', 'ab_compare_selftest', 'adaptive_tests',
          'adaptive_split_tests', 'adaptive_vs_uniform_bench_smoke',
          'gaussian_tests', 'core_tests', 'point_dataset_tests',
          'benchmark_memory_tests', 'ml_summary_tests',
          'modelnet_preprocessing_tests', 'ml_representations_smoke',
          'memory_growth_tests', 'test_framework_contract'}

def git(*args):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args])

def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()

def require(value, message):
    if not value:
        raise RuntimeError(message)

def engine_manifest():
    extensions = {'.c', '.cc', '.cpp', '.cu', '.cuh', '.h', '.hpp', '.hh', '.hxx', '.inl'}
    paths = [p for p in git('ls-tree', '-r', '--name-only', EXPECTED, '--',
                             'MinkowskiEngine').decode().splitlines() if Path(p).suffix in extensions]
    payload = ''.join(f'{EXPECTED}:{p}\n' for p in paths).encode()
    result = subprocess.check_output(['git', '-C', str(SOURCE), 'cat-file', '--batch'], input=payload)
    cursor, items = 0, []
    for path in paths:
        end = result.index(b'\n', cursor)
        header = result[cursor:end].decode().split()
        require(len(header) == 3 and header[1] == 'blob', 'Invalid canonical source blob')
        size = int(header[2])
        content = result[end + 1:end + 1 + size]
        require(len(content) == size, 'Truncated canonical source blob')
        cursor = end + 2 + size
        items.append(dict(path=path, sha256=hashlib.sha256(content).hexdigest()))
    require(cursor == len(result), 'Unexpected canonical source batch data')
    record = dict(source=EXPECTED, files=items)
    encoded = (json.dumps(record, indent=2) + '\n').encode()
    (OUT / 'engine-source-manifest.json').write_bytes(encoded)
    return dict(files=len(items), sha256=hashlib.sha256(encoded).hexdigest())

def audit():
    require(git('rev-parse', 'HEAD').decode().strip() == EXPECTED, 'Integration HEAD moved')
    require(not git('diff', '--name-only', 'HEAD').strip(), 'Tracked integration source is dirty')
    engine = engine_manifest()
    identity_files = {
        'MinkowskiEngine/adaptive/part_split.hpp': '95093e2',
        'MinkowskiEngine/gaussian/gaussian_raster_cuda.cu': 'b96db27',
        'benchmarks/ml_representations_summary.py': '7460c7e',
        'benchmarks/benchmark_memory.hpp': '2ceceea',
    }
    source_checks = []
    for path, candidate in identity_files.items():
        integrated = git('show', f'{EXPECTED}:{path}')
        require(integrated == git('show', f'{candidate}:{path}'), f'Integrated candidate differs: {path}')
        source_checks.append(dict(path=path, candidate=candidate,
                                  sha256=hashlib.sha256(integrated).hexdigest()))
    cmake = git('show', f'{EXPECTED}:CMakeLists.txt').decode().replace('\r\n', '\n')
    for test in ('test_gaussian_adaptive.cpp', 'test_gaussian_adam.cpp',
                 'test_gaussian_parallel_atomics.cpp'):
        require(cmake.count(test) == 1, f'Gaussian test lost/duplicated in merge: {test}')
    for suite in ('adaptive_split_tests', 'benchmark_memory_tests', 'ml_summary_tests'):
        require(f'add_test(NAME {suite} ' in cmake or f'add_test(NAME {suite}\n' in cmake,
                f'New suite registration absent: {suite}')
    ninja = (BUILD_ROOT / 'integration-cpu/build.ninja').read_text()
    objects = re.findall(r'^build (CMakeFiles[^:]+coordinate_manager\.(?:cpp|cu)\.obj):', ninja, re.M)
    require(len(objects) == 1 and objects[0].endswith('coordinate_manager.cu.obj'),
            'CPU target contains duplicate/legacy manager implementation')
    receipt_path = ROUND / 'integration-final/receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig'))
    require(receipt['source'] == EXPECTED, 'Native receipt source mismatch')
    original_failure = None
    if receipt['status'] == 'failed':
        root = ET.parse(ROUND / 'integration-final/ctest-cuda.xml').getroot()
        require(root.attrib['tests'] == '14' and root.attrib['failures'] == '1',
                'Original EAGER failure scope changed')
        failed = [c for c in root.findall('testcase') if c.find('failure') is not None]
        require(len(failed) == 1 and failed[0].attrib['name'] == 'gaussian_tests' and
                failed[0].find('failure').attrib['message'] == 'Timeout',
                'Original EAGER failure is not the recorded Gaussian timeout')
        original_failure = dict(status='failed', loading='EAGER', failed_suite='gaussian_tests',
                                reason='Timeout', seconds=float(failed[0].attrib['time']),
                                junit_sha256=sha(ROUND / 'integration-final/ctest-cuda.xml'))
    records = [(config, ROUND / 'integration-final', 'EAGER') for config in receipt['configurations']]
    lazy_dir = ROUND / 'integration-final/lazy-retry'
    lazy_receipt_path = lazy_dir / 'receipt.json'
    lazy_receipt = None
    if lazy_receipt_path.exists():
        lazy_receipt = json.loads(lazy_receipt_path.read_text(encoding='utf-8-sig'))
        require(lazy_receipt['source'] == EXPECTED and lazy_receipt['loading'] == 'LAZY' and
                lazy_receipt['timeout_seconds'] == 420, 'LAZY retry configuration changed')
        if lazy_receipt['status'] == 'passed':
            require(lazy_receipt['ctest_exit'] == 0, 'LAZY retry nonzero exit')
            require((lazy_dir / 'eager-ctest-cuda.xml').read_bytes() ==
                    (ROUND / 'integration-final/ctest-cuda.xml').read_bytes(),
                    'Original EAGER JUnit was not preserved exactly')
            before = json.loads((lazy_dir / 'binaries-before.json').read_text(encoding='utf-8-sig'))
            after = json.loads((lazy_dir / 'binaries-after.json').read_text(encoding='utf-8-sig'))
            require(before == after and len(before) == 7, 'LAZY retry binary cohort changed')
            require('mink-build: exit 0 ' in (ROUND / 'integration-final/build-cuda.log').read_text(encoding='utf-8-sig'),
                    'Original source CUDA build did not pass')
            records.append((dict(kind='cuda', build_exit=0, ctest_exit=0, binaries=before), lazy_dir, 'LAZY'))
    configurations = []
    for config, result_dir, loading in records:
        kind = config['kind']
        require(config['build_exit'] == 0 and config['ctest_exit'] == 0, f'{kind} native exit failure')
        junit = result_dir / f'ctest-{kind}.xml'
        root = ET.parse(junit).getroot()
        cases = root.findall('.//testcase')
        require(len(cases) == 14 and {c.attrib['name'] for c in cases} == SUITES,
                f'{kind} CTest coverage differs')
        require(root.attrib['failures'] == '0' and not root.findall('.//failure') and
                not root.findall('.//skipped'), f'{kind} CTest failure or skipped suite')
        binaries = []
        for binary in config['binaries']:
            path = BUILD_ROOT / f'integration-{kind}' / (binary['name'] + '.exe')
            digest = sha(path)
            require(digest == binary['sha256'].lower(), f'{kind} live binary differs: {binary["name"]}')
            binaries.append(dict(name=binary['name'], sha256=digest))
        log = (result_dir / f'ctest-{kind}.log').read_text(encoding='utf-8-sig')
        counts = re.findall(r'(?m)^\d+: (\d+) passed, (\d+) failed, (\d+) skipped', log)
        require(all(f == '0' for _, f, _ in counts), f'{kind} internal suite failure')
        archive = BUILD_ROOT / f'integration-{kind}' / 'minkowski_cpp.lib'
        configurations.append(dict(kind=kind, loading=loading, ctest_suites=len(cases), suite_counts=counts,
                                   junit_sha256=sha(junit), archive_sha256=sha(archive), binaries=binaries))
    complete = {c['kind'] for c in configurations} == {'cpu', 'cuda'}
    state = 'passed' if complete else 'pending'
    if lazy_receipt is not None and lazy_receipt['status'] == 'failed':
        state = 'failed'
    return dict(status=state, source=EXPECTED, original_eager_failure=original_failure,
                source_checks=source_checks, engine_manifest=engine, cpu_manager_objects=objects,
                configurations=configurations,
                limits=['Native CPU/CUDA only; Docker results audited separately',
                        'Historical ModelNet pilot belongs to source0a4b62a, not this integrated build',
                        'No sum of unrelated percentage gains or claim of real-training Gaussian speedup'])

try:
    result = audit()
except Exception as error:
    result = dict(status='failed', source=EXPECTED, error=str(error))
(OUT / 'gate-audit.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
raise SystemExit(1 if result['status'] == 'failed' else 0)
