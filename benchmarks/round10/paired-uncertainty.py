"""Exploratory uncertainty from existing paired trials; no new timed execution."""
import hashlib
import argparse
import json
import math
import os
from pathlib import Path
import random
import statistics

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=ROOT/'paired-reanalysis')
args=parser.parse_args()
assert not args.output_dir.exists() or not any(args.output_dir.iterdir()), 'Preserve previous derived outputs'
args.output_dir.mkdir(parents=True,exist_ok=True)
ADAPTIVE=ROOT/'adaptive' if (ROOT/'adaptive').is_dir() else ROOT.parent/'adaptive_part_split_results'
GAUSSIAN=ROOT/'gaussian-atomics' if (ROOT/'gaussian-atomics').is_dir() else ROOT.parent/'gaussian_parallel_atomics_results'
inputs=[]
def load(path):
    inputs.append(dict(path=os.path.relpath(path,ROOT),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return json.loads(path.read_text())

def sign_p(wins,losses):
    n=wins+losses
    return min(1.0,2*sum(math.comb(n,k) for k in range(min(wins,losses)+1))/2**n) if n else 1.0
assert sign_p(3,0)==.25 and sign_p(6,0)==.03125
assert sign_p(8,2)==.109375 and sign_p(9,1)==.021484375 and sign_p(5,5)==1

def quantile(values,p):
    position=(len(values)-1)*p
    i=int(position); fraction=position-i
    return values[i]*(1-fraction)+values[min(i+1,len(values)-1)]*fraction

rows=[]
def analyze(label,a,b):
    assert len(a)==len(b) and len(a) in (6,10)
    assert all(math.isfinite(v) and v>0 for v in a+b)
    n=len(a)
    wins=sum(y<x for x,y in zip(a,b)); losses=sum(y>x for x,y in zip(a,b))
    rng=random.Random(2026+len(rows))
    samples=[]
    for _ in range(20000):
        indexes=[rng.randrange(n) for _ in range(n)]
        samples.append(100*(statistics.median(b[i] for i in indexes)/statistics.median(a[i] for i in indexes)-1))
    samples.sort()
    rows.append(dict(workload=label,pairs=n,lower_pairs=wins,ties=n-wins-losses,
                     bootstrap_seed=2026+len(rows),
                     median_ratio_change_percent=100*(statistics.median(b)/statistics.median(a)-1),
                     exploratory_pair_bootstrap_95pct=[quantile(samples,.025),quantile(samples,.975)],
                     unadjusted_exact_two_sided_sign_p=sign_p(wins,losses)))

for device in ('cpu','cuda'):
    data=load(ADAPTIVE/('map-'+device)/'receipt.json')
    assert data['status']=='passed'
    assert len(data['runs'])==24 and {r['workload'] for r in data['runs']}=={'center','volume'}
    assert all(r['exit']==0 for r in data['runs'])
    for workload in ('center','volume'):
        selected=[r for r in data['runs'] if r['workload']==workload]
        indexed={(r['round'],r['arm']):r['metrics'] for r in selected}
        assert len(selected)==12 and set(indexed)=={(r,a) for r in range(1,7) for a in (0,1)}
        for metric in ('kmap_batch_first_epoch_ms','kmap_batch_later_epochs_ms'):
            analyze(f'adaptive/{device}/{workload}/{metric}',
                    [indexed[(r,0)][metric] for r in range(1,7)],
                    [indexed[(r,1)][metric] for r in range(1,7)])
gaussian=load(GAUSSIAN/'ab/summary.json')
for row in gaussian:
    if ((row['workload'] in ('row-groups','sparse','dense') and row['metric']=='gpu_ms') or
        (row['workload'] in ('512','1024') and row['metric'] in ('backward_median_ms','train_median_ms'))):
        analyze(f'gaussian/{row["workload"]}/{row["metric"]}',row['off'],row['on'])
assert len(rows)==15 and len({r['workload'] for r in rows})==15

limits='''Exploratory analysis of existing trials, not an additional timed benchmark.
Bootstrap resamples whole A/B pairs with replacement (20,000 draws, deterministic
seeds) and uses percentile intervals for median(B)/median(A)-1. Small cohorts,
fixed alternating order and nonstationary background load limit interpretation.
Bootstrap blocks are assumed approximately independent/representative; serial
load can violate that assumption. The sign test targets paired win probability
0.5, not the ratio of marginal medians used by the bootstrap interval.
The exact sign calculation discards ties and assumes independent exchangeable
signs under the null. P values are unadjusted across multiple workloads/metrics;
none is a confirmatory claim. Original reported point estimates and raw evidence
remain unchanged. Intervals/p values do not establish real-training benefit or
universal superiority.'''
record=dict(kind='exploratory_derived_analysis',inputs=inputs,bootstrap_draws=20000,
            seed_base=2026,limits=limits,rows=rows)
(args.output_dir/'paired-uncertainty.json').write_text(json.dumps(record,indent=2)+'\n')
lines=['# Exploratory paired-trial uncertainty','',limits,'',
       '| Workload | Pairs | Lower | Median change% | Paired bootstrap95% | Unadjusted sign p |',
       '|---|---:|---:|---:|---:|---:|']
for row in rows:
    lo,hi=row['exploratory_pair_bootstrap_95pct']
    lines.append(f'| {row["workload"]} | {row["pairs"]} | {row["lower_pairs"]} | '
                 f'{row["median_ratio_change_percent"]:+.2f} | [{lo:+.2f}, {hi:+.2f}] | '
                 f'{row["unadjusted_exact_two_sided_sign_p"]:.5f} |')
(args.output_dir/'PAIRED-UNCERTAINTY.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
