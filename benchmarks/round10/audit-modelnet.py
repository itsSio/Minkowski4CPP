"""Audit frozen ModelNet trials, recompute metrics, and collect a reproducible cohort."""
import hashlib
import argparse
import importlib.util
import json
import math
from pathlib import Path
import shutil
import statistics

ROOT = Path(__file__).resolve().parent
LAB = ROOT.parents[1]
SOURCE = Path(r'C:\Users\User\Work\mink-wt\gaussian-adaptive-bridge')
DATA = LAB / 'datasets/modelnet10/subset40-20-p1024-s2026'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=ROOT/'modelnet-three-seed')
parser.add_argument('--pilot-executable', type=Path, default=Path(
    r'C:\Users\User\Work\mink-build\integration-cuda\ml_representations.modelnet-pilot.exe'))
args = parser.parse_args()
OUT = args.output
METHODS = ('uniform', 'adaptive', 'gaussian', 'adaptive_gaussian')

def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()

def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12), (a, b)

spec = importlib.util.spec_from_file_location('summary', SOURCE / 'benchmarks/ml_representations_summary.py')
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)
assert not OUT.exists(), 'Preserve previous evidence; choose a fresh output directory'
receipts, rows, copies = [], [], []
for seed in (1, 2, 3):
    directory = ROOT / f'modelnet-seed{seed}'
    receipt = json.loads((directory / 'receipt.json').read_text(encoding='utf-8-sig'))
    assert receipt['status'] == 'passed' and receipt['seed'] == seed and receipt['epochs'] == 6
    assert len(receipt['runs']) == 4 and {r['method'] for r in receipt['runs']} == set(METHODS)
    assert all(r['exit'] == 0 for r in receipt['runs'])
    assert receipt['dataset_manifest_sha256'].lower() == sha(DATA / 'manifest.json')
    assert receipt['executable_sha256'].lower() == sha(args.pilot_executable)
    for split in receipt['data']:
        assert split['sha256'].lower() == sha(DATA / (split['split'] + '.bin'))
    receipts.append(receipt)
    for method in METHODS:
        path = directory / (method + '.json')
        row = json.loads(path.read_text(encoding='utf-8'))
        summary.validate_run(row)
        assert row['seed'] == seed and row['method'] == method
        assert row['dataset'] == 'ModelNet10' and row['device'] == 'cuda'
        assert row['train_samples'] == 400 and row['test_samples'] == 200
        assert row['dataset_manifest'] == json.loads((DATA / 'manifest.json').read_text())
        cm = row['confusion']
        assert len(cm) == 10 and all(len(r) == 10 and all(type(v) is int and v >= 0 for v in r) for r in cm)
        assert all(sum(r) == 20 for r in cm)
        close(row['accuracy'], sum(cm[c][c] for c in range(10)) / 200)
        ps, rs, fs = [], [], []
        for c in range(10):
            tp = cm[c][c]
            predicted = sum(cm[k][c] for k in range(10))
            p = tp / predicted if predicted else 0
            r = tp / sum(cm[c])
            f = 2*p*r/(p+r) if p+r else 0
            for key, value in (('precision', p), ('recall', r), ('f1', f)):
                close(row['per_class'][c][key], value)
            ps.append(p); rs.append(r); fs.append(f)
        close(row['macro_precision'], statistics.fmean(ps))
        close(row['macro_recall'], statistics.fmean(rs))
        close(row['macro_f1'], statistics.fmean(fs))
        close(row['train_time_s'], sum(e['epoch_train_s'] for e in row['curve']))
        rows.append(row)
        copies.append((path, f'{method}-seed{seed}.json'))
assert len({r['source'] for r in receipts}) == len({r['executable_sha256'] for r in receipts}) == 1
OUT.mkdir()
for path, name in copies:
    shutil.copyfile(path, OUT / name)
runs = summary.load_runs(OUT, set(METHODS), {1, 2, 3})
table = summary.render(runs)
(OUT / 'SUMMARY.md').write_text(table + '\n', encoding='utf-8')
record = dict(status='passed', source=receipts[0]['source'], receipts=receipts,
              independent_checks=['SHA256 data/manifest/executable', 'exact four-mode three-seed cohort',
                                  'identical complete dataset manifests', 'all confusion/per-class/macro metrics',
                                  'completed curve and training-time sums', 'architecture stability across seeds'],
              files=[dict(file=name, sha256=sha(OUT / name)) for _, name in copies])
(OUT / 'audit.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(table)
