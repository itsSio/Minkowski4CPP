"""Independently inspect completed first-candidate container evidence, preserving failure."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent / 'docker-runtime/run-41511100024'
EXPECTED = {'cmake_source_filter', 'ab_compare_selftest', 'adaptive_tests',
            'adaptive_split_tests', 'adaptive_vs_uniform_bench_smoke',
            'gaussian_tests', 'core_tests', 'point_dataset_tests',
            'ml_summary_tests', 'modelnet_preprocessing_tests',
            'ml_representations_smoke', 'memory_growth_tests', 'test_framework_contract'}
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def require(value, message):
    if not value:
        raise RuntimeError(message)
jobs = []
for job in read(ROOT / 'download-summary.json'):
    require(job['extract_exit'] == 0, 'Evidence bundle extraction failed')
    directory = ROOT / ('job-' + job['job'])
    manifests = read(directory / 'evidence-manifest.json')
    for item in manifests:
        data = (directory / item['path']).read_bytes()
        require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'],
                'Evidence file checksum mismatch: ' + item['path'])
    receipt = read(directory / 'receipt.json')
    stages = {row['name']: row for row in receipt['stages']}
    require(receipt['status'] == 'failed' and receipt['error'] == 'split-sanitizer-build failed with exit 1',
            'Do not turn the failed overall run into a pass')
    require(all(stages[name]['exit_code'] == 0 for name in
                ('versions', 'configure', 'build', 'ctest-list', 'ctest')),
            'Earlier source rebuild/runtime stage failed')
    root = ET.parse(directory / 'ctest.xml').getroot()
    require(root.attrib['tests'] == '13' and root.attrib['failures'] == '0' and
            not root.findall('.//skipped') and {c.attrib['name'] for c in root.findall('testcase')} == EXPECTED,
            'Incomplete or failed container CPU CTest coverage')
    commands = read(directory / 'compile_commands.json')
    manager = [row for row in commands if Path(row['file']).stem == 'coordinate_manager']
    require(len(manager) == 1 and manager[0]['file'].endswith('/coordinate_manager.cu'),
            'Container CPU build compiled legacy/duplicate manager source')
    linkage = read(directory / 'linkage.json')
    require(linkage['archive'] == '/opt/minkowski-runtime/build/libminkowski_cpp.a', 'Wrong archive path')
    for name, target in linkage['targets'].items():
        require(target['dependency'].startswith('minkowski_cpp::') and
                'libminkowski_cpp.a' in target['fragments'], 'Wrong library dependency: ' + name)
    source_manifest = read(directory / 'source-manifest.json')
    source_hashes = {r['path']: r['sha256'] for r in source_manifest['files']}
    require(source_hashes['MinkowskiEngine/adaptive/part_split.hpp'] ==
            '1bcb3d2fe6f47bfceccde67afd6088b289942c021f8d776f5ddcd23256d69c41', 'Changed split helper identity')
    require(source_hashes['benchmarks/ml_representations_summary.py'] ==
            '0af2c5ec13b81ab7148f8d6b26a2cf6b94e9b406825149700c2fbdc4dfc134a2', 'Changed summary guard identity')
    jobs.append(dict(job=job['job'], checked_evidence_files=len(manifests), ctest_suites=13,
                     ctest_failures=0, canonical_manager=manager[0]['file'],
                     archive=linkage['archive'], source_manifest_base=source_manifest['source_base_commit'],
                     overall_status='failed', failed_stage='split-sanitizer-build'))
require(len(jobs) == 3, 'Expected three repeated CPU image jobs')
record = dict(status='partial_runtime_verified_overall_failed', run=41511100024,
              workflow_head='e7b0810de398ce5a7f25815789c139f0362b07de', jobs=jobs,
              limits=['This is source-built container CPU execution, not container GPU validation',
                      'All three matrix labels use one identical pinned image',
                      'RSS and Gaussian atomics are absent from this first candidate; await final candidate',
                      'Standalone split ASan/UBSan was not built or executed'])
(OUT / 'partial-docker-audit.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps(record, indent=2))
