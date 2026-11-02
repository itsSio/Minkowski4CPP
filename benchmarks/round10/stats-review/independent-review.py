"""Independent read-only check of the frozen exploratory statistics artifact."""
import ast
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
record = json.loads((ROOT / 'paired-uncertainty.json').read_text())
tree = ast.parse((ROOT / 'paired-uncertainty.py').read_text())
definition = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'sign_p')
namespace = {'math': math}
exec(compile(ast.Module(body=[definition], type_ignores=[]), '<reviewed-sign-function>', 'exec'), namespace)
for effective in range(13):
    for wins in range(effective+1):
        losses = effective-wins
        extreme = sum(min(assignment.count(1), assignment.count(0)) <= min(wins, losses)
                      for assignment in itertools.product((0, 1), repeat=effective))
        expected = extreme / 2**effective if effective else 1.0
        assert namespace['sign_p'](wins, losses) == expected
inputs = {}
for entry in record['inputs']:
    path = ROOT.joinpath(*entry['path'].replace('\\', '/').split('/'))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
    inputs[entry['path'].replace('\\', '/')] = json.loads(path.read_text())

cohorts = {}
for device in ('cpu', 'cuda'):
    receipt = inputs[f'adaptive/map-{device}/receipt.json']
    for workload in ('center', 'volume'):
        runs = [row for row in receipt['runs'] if row['workload'] == workload]
        assert len(runs) == 12
        index = {(row['round'], row['arm']): row['metrics'] for row in runs}
        assert set(index) == set(itertools.product(range(1, 7), (0, 1)))
        for metric in ('kmap_batch_first_epoch_ms', 'kmap_batch_later_epochs_ms'):
            cohorts[f'adaptive/{device}/{workload}/{metric}'] = (
                [index[(r, 0)][metric] for r in range(1, 7)],
                [index[(r, 1)][metric] for r in range(1, 7)])

for row in inputs['gaussian-atomics/ab/summary.json']:
    if (row['workload'] in ('row-groups', 'sparse', 'dense') and row['metric'] == 'gpu_ms') or (
            row['workload'] in ('512', '1024') and row['metric'] in ('backward_median_ms', 'train_median_ms')):
        key = f'gaussian/{row["workload"]}/{row["metric"]}'
        assert key not in cohorts
        cohorts[key] = (row['off'], row['on'])

assert len(record['rows']) == len(cohorts) == 15
assert len({row['workload'] for row in record['rows']}) == 15
results = []
for row in record['rows']:
    a, b = cohorts[row['workload']]
    n = len(a)
    assert n == len(b) == row['pairs']
    signs = [1 if y < x else -1 if y > x else 0 for x, y in zip(a, b)]
    wins, losses, ties = signs.count(1), signs.count(-1), signs.count(0)
    assert (wins, ties) == (row['lower_pairs'], row['ties'])
    # Enumerate all equally likely sign assignments instead of using the formula.
    effective = wins + losses
    extreme = sum(min(assignment.count(1), assignment.count(0)) <= min(wins, losses)
                  for assignment in itertools.product((0, 1), repeat=effective))
    pvalue = extreme / 2**effective if effective else 1.0
    assert pvalue == row['unadjusted_exact_two_sided_sign_p']
    estimate = 100 * (statistics.median(b) / statistics.median(a) - 1)
    assert estimate == row['median_ratio_change_percent']
    rng = random.Random(row['bootstrap_seed'])
    draws = []
    for _ in range(record['bootstrap_draws']):
        paired = [(a[i], b[i]) for i in (rng.randrange(n) for _ in range(n))]
        aa, bb = zip(*paired)
        draws.append(100 * (statistics.median(bb) / statistics.median(aa) - 1))
    draws.sort()
    bounds = []
    for probability in (.025, .975):
        position = probability * (len(draws) - 1)
        lower = math.floor(position)
        fraction = position - lower
        bounds.append(draws[lower] * (1-fraction) + draws[min(lower+1, len(draws)-1)] * fraction)
    assert bounds == row['exploratory_pair_bootstrap_95pct']
    results.append(dict(workload=row['workload'], pair_cardinality='passed',
                        exact_sign_enumeration='passed', deterministic_bootstrap='passed'))

result = dict(status='passed', rows=results,
              checks=['sign function exhaustively checked for effective n0through12',
                      'all3 input SHA256 identities', 'exact15workload cohort',
                      'pair cardinality and tie counts', 'all sign assignments enumerated',
                      'ratio-of-medians estimands', 'all20k-draw intervals independently reproduced'])
(OUT / 'independent-review.json').write_text(json.dumps(result, indent=2) + '\n')
print('All 15 rows independently reproduce; exact sign tests and paired bootstrap verified')
