"""Independent audit of decoded CPU runtime stages, without promoting failed CI."""
import csv
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
REPO = Path(r'C:\Users\User\Work\mink-wt\docker-runtime')
parser = argparse.ArgumentParser()
parser.add_argument('--run', default='41512323659')
parser.add_argument('--require-passed', action='store_true')
args = parser.parse_args()
RUN = args.run
EXPECTED_SUITES = {'ab_compare_selftest', 'adaptive_split_tests', 'adaptive_tests',
    'adaptive_vs_uniform_bench_smoke', 'benchmark_memory_tests', 'cmake_source_filter',
    'core_tests', 'gaussian_tests', 'memory_growth_tests', 'ml_representations_smoke',
    'ml_summary_tests', 'modelnet_preprocessing_tests', 'point_dataset_tests', 'test_framework_contract'}
EXPECTED_ARTIFACTS = {'minkowski_cpp', 'adaptive_tests', 'gaussian_tests', 'core_tests',
    'memory_growth_tests', 'adaptive_vs_uniform_bench', 'ml_representations',
    'test_framework_contract', 'adaptive_split_tests', 'point_dataset_tests', 'benchmark_memory_tests'}
EXPECTED_LINKED = {'adaptive_tests', 'gaussian_tests', 'core_tests', 'memory_growth_tests',
    'adaptive_vs_uniform_bench', 'ml_representations'}
IMAGE = 'sha256:a4bf4c4e91ef5f4e50089f435005ca07f1a0a48deeeb9814ca4b526974de79ba'

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check(condition, reason):
    if not condition:
        raise RuntimeError(reason)

def check_git_blobs(manifest):
    commit = manifest['source_base_commit']
    specs = [commit + ':' + row['path'] for row in manifest['files']]
    data = subprocess.check_output(['git', '-C', str(REPO), 'cat-file', '--batch'],
                                   input=('\n'.join(specs) + '\n').encode())
    stream = io.BytesIO(data)
    seen = set()
    for row in manifest['files']:
        check(row['path'] not in seen, 'Duplicate canonical source path')
        seen.add(row['path'])
        head = stream.readline().split()
        check(len(head) == 3 and head[1] == b'blob', 'Missing canonical Git blob: ' + row['path'])
        blob = stream.read(int(head[2]))
        check(stream.read(1) == b'\n', 'Git batch delimiter mismatch')
        check(len(blob) == row['bytes'] and hashlib.sha256(blob).hexdigest() == row['sha256'],
              'Canonical source hash differs: ' + row['path'])
    check(not stream.read(), 'Unconsumed canonical source output')
    return len(seen)

root = ROOT / ('run-' + RUN)
summary = load(root / 'download-summary.json')
check(len(summary) == 3 and all(r['extract_exit'] == 0 for r in summary), 'Expected three decoded CI jobs')
overall = {r['conclusion'] for r in summary}
check(overall in ({'failure'}, {'success'}), 'Mixed/unknown CI outcomes need explicit investigation')
passed = overall == {'success'}
check(passed or not args.require_passed, 'Passed CI was required')
results = []
csv_rows = []
canonical = None
for item in summary:
    job = str(item['job'])
    directory = root / ('job-' + job)
    manifest = load(directory / 'evidence-manifest.json')
    for entry in manifest:
        path = directory / entry['path']
        check(path.resolve().is_relative_to(directory.resolve()), 'Evidence path escaped output')
        check(path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'],
              'Decoded evidence hash differs: ' + entry['path'])
    receipt = load(directory / 'receipt.json')
    check(receipt['status'] == ('passed' if passed else 'failed'), 'Unexpected overall runtime outcome')
    if not passed:
        check(receipt['error'] == 'split-sanitizer-build failed with exit 1', 'Unexpected failed stage')
    check(receipt['image_digest'] == IMAGE and receipt['image_cuda_profile'] in {'124', '132', '134'},
          'Unexpected existing image identity')
    check(receipt['mode'].startswith('CPU_ONLY'), 'Unexpected claimed execution mode')
    stages = {s['name']: s for s in receipt['stages']}
    expected = {'versions', 'configure', 'build', 'ctest-list', 'ctest', 'split-sanitizer-build'}
    if passed:
        expected.add('split-sanitizer-test')
    check(set(stages) == expected, 'Unexpected stage coverage')
    check(all(stages[name]['exit_code'] == 0 for name in expected - {'split-sanitizer-build'}),
          'A required runtime stage did not pass')
    check(stages['split-sanitizer-build']['exit_code'] == (0 if passed else 1), 'Unexpected sanitizer build outcome')
    if passed:
        check('-std=c++20' in stages['split-sanitizer-build']['command'], 'Wrong sanitizer compiler standard')
        sanitized_log = (directory / 'split-sanitizer-test.log').read_text()
        check('6 passed, 0 failed, 0 skipped' in sanitized_log, 'Incomplete sanitizer differential suite')
        check(not re.search(r'ERROR: AddressSanitizer|runtime error:|LeakSanitizer|SUMMARY:.*Sanitizer', sanitized_log),
              'Sanitizer diagnostic detected')
        check(re.fullmatch('[0-9a-f]{64}', receipt['split_sanitizer_sha256']), 'Missing sanitizer binary identity')
    else:
        failure = (directory / 'split-sanitizer-build.log').read_text()
        check('only available with' in failure and 'std=c++20' in failure and 'operator==' in failure,
              'Sanitizer failure differs from known C++17 harness error')
        check('-std=c++17' in stages['split-sanitizer-build']['command'], 'Unexpected failed compiler standard')
    source = load(directory / 'source-manifest.json')
    if canonical is None:
        canonical = source
        canonical_count = check_git_blobs(source)
    check(source == canonical and canonical_count == receipt['verified_source_files'] == 471,
          'Source manifest differs between jobs or canonical inputs')
    check(receipt['source_base_commit'] == source['source_base_commit'], 'Receipt source identity differs')
    junit = ET.parse(directory / 'ctest.xml').getroot()
    cases = junit.findall('.//testcase')
    check(len(cases) == int(junit.attrib['tests']) == 14 and int(junit.attrib['failures']) == 0,
          'JUnit suite count/failures differ')
    check(not junit.findall('.//failure') and not junit.findall('.//error') and not junit.findall('.//skipped'),
          'JUnit contains a failed/skipped suite')
    check({c.attrib['name'] for c in cases} == EXPECTED_SUITES, 'JUnit named suite coverage differs')
    check(set(receipt['junit']['suites']) == EXPECTED_SUITES, 'Receipt JUnit identity differs')
    discovery = load(directory / 'ctest-list.log')
    check({c['name'] for c in discovery['tests']} == EXPECTED_SUITES, 'Discovered suite coverage differs')
    artifacts = receipt['artifacts']
    check({a['target'] for a in artifacts} == EXPECTED_ARTIFACTS, 'Built target coverage differs')
    for artifact in artifacts:
        check(re.fullmatch('[0-9a-f]{64}', artifact['sha256']) and artifact['bytes'] > 0,
              'Invalid pre-test artifact identity')
        check(PurePosixPath(artifact['path']).is_relative_to('/opt/minkowski-runtime/build'),
              'Artifact path is outside rebuilt directory')
    linkage = load(directory / 'linkage.json')
    check(linkage['archive'] == '/opt/minkowski-runtime/build/libminkowski_cpp.a', 'Unexpected rebuilt archive')
    check(set(linkage['targets']) == EXPECTED_LINKED, 'Library-linked target coverage differs')
    for target in linkage['targets'].values():
        check(target['dependency'].startswith('minkowski_cpp::') and 'libminkowski_cpp.a' in target['fragments'],
              'Rebuilt library dependency missing')
        check(not any('/usr/local/lib/libminkowski_cpp' in f for f in target['fragments']), 'Stale installed library')
    commands = load(directory / 'compile_commands.json')
    manager = [c for c in commands if PurePosixPath(c['file']).stem == 'coordinate_manager']
    check(len(manager) == 1 and manager[0]['file'].endswith('/coordinate_manager.cu'),
          'Wrong/multiple coordinate manager compilation inputs')
    check('-DCPU_ONLY' in manager[0]['command'], 'Canonical manager was not CPU-only')
    ctest = (directory / 'ctest.log').read_text()
    match = re.search(r'peak RSS MiB before=([0-9.]+) allocated=([0-9.]+) after_free=([0-9.]+) '
                      r'source=getrusage\(RUSAGE_SELF\).ru_maxrss; lifetime high-water and unit checks passed', ctest)
    check(match is not None, 'Missing actual Linux memory regression output')
    before, allocated, after_free = map(float, match.groups())
    check(0 < before < 8192 and 32 < allocated - before < 128 and after_free >= allocated,
          'Implausible Linux high-water memory result')
    versions = (directory / 'versions.log').read_text()
    memory = re.search(r'^MemTotal:\s+(\d+) kB$', versions, re.M)
    record = dict(job=job, label=item['name'], overall_ci='success' if passed else 'failure', library_build='passed',
        ctest_suites=14, ctest_failures=0, sanitizer_build='passed' if passed else 'failed: harness requested C++17, project requires C++20',
        sanitizer_test='6 passed; zero ASan/UBSan findings' if passed else 'not executed',
        source_base_commit=source['source_base_commit'], canonical_git_blobs_verified=canonical_count,
        decoded_evidence_hashes_verified=len(manifest), linkage='rebuilt archive; installed Minkowski archive excluded',
        manager_source='coordinate_manager.cu only; CPU_ONLY',
        binary_hash_scope=('pre-test identities recorded; successful runner also verified post-test binary/source hashes'
                           if passed else 'pre-test hashes recorded in receipt; failed sanitizer prevented final post-test hash check'),
        rss_before_mib=before, rss_allocated_mib=allocated, rss_after_free_mib=after_free,
        rss_delta_mib=allocated-before, cpu_count=receipt['cpu_count'],
        mem_total_kib=int(memory.group(1)) if memory else None, cpu_model='not recorded; not inferred',
        platform=receipt['platform'], image_digest=receipt['image_digest'],
        compiler='GCC 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04.1)', cmake='4.2.3', libtorch='2.15.0+cu134',
        gpu='no GPU execution; CPU_ONLY against CUDA-enabled LibTorch',
        stages=[dict(name=s['name'], exit_code=s['exit_code'], seconds=s['wall_seconds']) for s in receipt['stages']])
    results.append(record)
    csv_rows.append({k: v for k, v in record.items() if k != 'stages'})
out = dict(audit='passed', claim=('full CPU runtime and ASan/UBSan split stages passed; overall CI succeeded' if passed else
           'full CPU runtime stages passed; overall CI failed at standalone sanitizer compilation'),
           run=RUN, runtime_head=load(root / 'run.json')['headSha'], jobs=results)
(root / 'independent-stage-certificate.json').write_text(json.dumps(out, indent=2) + '\n')
with (root / 'runtime-stage-certificate.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(csv_rows[0]))
    writer.writeheader(); writer.writerows(csv_rows)
print(json.dumps(out, indent=2))
