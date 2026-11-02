# Deterministic fallback cache-policy check

Source `f3f74919a64bede57fab7d5f303e94ca188c931a`, executable SHA256 `F66BB23A370DA9C7F4AF3BB5647C34337AE49A2BF7A093765B482280020DB35A`; one process per budget, same seed and controls. This is a correctness follow-up and makes no timing claim.

Compared 163 numerical and categorical output fields, excluding timings/cache accounting. All budgets exactly equal: **True**.

| Budget | Accuracy | Final training loss | Detected warning lines |
|---|---|---|---|
| -1 MiB | 0.29 | 0.679835959485 | 0 |
| 32 MiB | 0.29 | 0.679835959485 | 0 |
| 0 MiB | 0.29 | 0.679835959485 | 0 |

One process per budget; deterministic algorithms requested in warn-only mode. Equality is evidence for this workload, not universal CUDA determinism.

All output differences and warning lines are retained in `numerical-comparison.json`.
