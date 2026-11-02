# Adaptive recovery and independent evidence audit

Auditor: the resumed adaptive_engineer teammate. No runtime source, executable,
benchmark measurement or existing raw result was changed during this audit.

## Recovered implementation

PR52, `feat/adaptive-device-cache-budget`, is already implemented. The runtime
commit is `2623c56`; the documentation head is
`647450b00e4c16c7b6b60e95f8823231ebc35214`. The device-compose worktree has only
the pre-existing untracked `benchmarks/__pycache__/` directory. Its CPU and CUDA
CTest logs each record four passing registered tests. The frozen combined runtime
is `f3f74919a64bede57fab7d5f303e94ca188c931a`.

Focused source review covered `PartDeviceStore`, `parts_on_device`,
`compose_parts_device`, cache setters/stats, and the five budget regressions in
`tests/adaptive/test_part_reuse.cpp`. Upload backing groups are charged and evicted
together; weak part owners avoid retaining host parts. Per-device handles remain
owned by an in-flight composition, and `recordStream` protects allocation reuse
after a launch on another stream. Device-copy mutation and accounting use the
device mutex; paths needing both locks take the outer cache lock first. Trimming
reserves upload bytes only after confirming the upload fits the budget, avoiding
unsigned budget subtraction underflow. Zero disables retention; the default stays
unlimited. Partial expiry intentionally conservatively charges the whole group.
The tests cover tiny/zero limits with forward/backward checks, whole-group eviction,
LRU/duplicate parts, cross-stream eviction and mixed-width partial host expiry.
No blocking defect was identified in this focused review. It is not a proof of
arbitrary concurrent usage, multi-GPU portability or sanitizer coverage of excluded
LibTorch kernels.

## Raw measurement audit

The `ml-budgets/receipt.json` records 18 successful runs, all six permutations of
three arms, source `f3f74919...`, fixed model seed1/data seed2026, 300 training and
200 test shapes, 2048 points each, three epochs, batch16 and 512 MiB host cache.
Its executable SHA256 matches the actual `integration-cuda/ml_representations.exe`
read after restart and the integration validation receipt:
`F66BB23A370DA9C7F4AF3BB5647C34337AE49A2BF7A093765B482280020DB35A`.

The pre-restart independent `adaptive/audit-ml.py` and its completed receipt validate
all18 rows, receipt argument controls, geometry, retained and peak budget limits,
confusion-derived accuracy/precision/recall/F1, finite metrics and summed epoch
training time. This restart audit independently recomputed central memory/timing
metrics and paired counts from the raw JSON. `summarize-final.py` matches the raw
data and was left unchanged. The independent summary uses relative percentages
for quality changes; the main summary uses percentage points. Both calculations
are numerically valid, but neither establishes an accuracy advantage.

Key verified results:

| Metric | Unlimited | 32 MiB | 0 MiB |
|---|---|---|---|
| Epoch-loop allocated CUDA peak, MiB | 335.354 | 295.638 (-11.84%) | 252.638 (-24.67%) |
| Epoch-loop reserved CUDA peak, MiB | 388 | 340 (-12.37%) | 292 (-24.74%) |
| End retained-group charge, MiB | 70.279 | 31.894 (-54.62%) | 0 |
| Training time median, seconds | 6.476 | 5.385 (-16.85%, 4/6 faster) | 5.754 (-11.14%, 2/6 faster) |
| Mean epochs2–3 median, seconds | 0.786 | 0.807 (+2.63%, 2/6 faster) | 0.896 (+13.97%, 2/6 faster) |
| Inference median, milliseconds | 12.669 | 11.626 (-8.23%) | 13.453 (+6.19%) |
| CPU peak working-set median, MiB | 4440.322 | 4464.453 (+0.54%) | 4464.580 (+0.55%) |

CPU boundary samples range59.5–86.2%, so total-training timing is substantially
contended. Memory figures repeat identically within arms. The cap is a retained-cache
bound, not a VRAM bound. Warm training/inference regressions and CPU working-set
increases must remain disclosed. No kernel-time or GPU utilization improvement is
inferred. Accuracy differences under default fused atomic sums are descriptive,
not model-quality gains.

## Completed deterministic follow-up analysis

The existing `ml-deterministic-check/receipt.json` had all three successful runs;
only its numerical analysis remained unfinished after restart. Executed:

```powershell
python -I -X utf8 C:\Users\User\Work\mink-lab\results\round9\adaptive\compare-deterministic.py
```

It generated `ml-deterministic-check/numerical-comparison.json` and `summary.md`.
All163 compared values agree exactly across budgets, including all epoch losses
and train/test accuracies, confusion/per-class/final metrics and geometry. Accuracy
is29.0%, macro-F1 is0.25504947752625773 and final loss is0.6798359594847027.
Captured warning lists are empty. Source dispatch in `adaptive/ops.cpp` explicitly
bypasses fused apply when deterministic algorithms are requested. The request was
warn-only; one process per budget validates this path/workload, not universal GPU
determinism. No timings from these correctness runs are used as performance evidence.

## Output and remaining integration work

New artifacts from this audit are `ml-budgets/interpretation.md`, this audit, and
the two deterministic comparison outputs above. Existing benchmark data and main
summary script remain unchanged. The root owns final report integration, evidence
packaging, branch publication and PR52 stacked-result comment/body updates. The
package must include the deterministic raw outputs, receipt, comparison and script
before citing them. No additional expensive benchmark run is justified by the
recovered evidence.
