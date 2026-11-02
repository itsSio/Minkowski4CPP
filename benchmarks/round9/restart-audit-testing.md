# Restart evidence audit: testing and benchmark recovery

Audited on 2026-11-02 by the recovery/testing teammate. This is an independent
inspection of retained raw evidence and current binary hashes; it is not a new
execution of the C++ suites or benchmarks.

## Verified evidence

- Runtime source: `f3f74919a64bede57fab7d5f303e94ca188c931a`.
- `integration-final/receipt.json` records successful Release builds and zero test
  exit codes for CPU and CUDA. Both JUnit files contain nine tests and zero
  failures. The corresponding complete logs end with 9/9 passing suites.
- SHA256 was freshly recomputed for all six recorded executables in each build
  directory: adaptive, Gaussian, core, memory-growth, Gaussian benchmark and ML
  executables. All twelve current hashes match the receipt. No rebuild is needed
  for the already tested runtime source.
- `adam-stack`, `gather-stack` and `all-fusions` each contain twenty successful
  process runs and ten pairs with alternating execution order. Each receipt uses
  the same runtime source and Gaussian executable hash. The PLY dataset hash was
  freshly recomputed and matches each receipt.
- The serialized per-process training medians agree with medians recalculated
  from individual timing samples within their JSON decimal precision (relative
  tolerance 1e-5). Independently recalculated medians, percentage changes and
  faster-pair counts agree with the strict summary and draft report:

| Comparison | Pixels | Off median (ms) | On median (ms) | Change | Faster pairs |
|---|---:|---:|---:|---:|---:|
| Adam | 512 | 20.80690 | 17.68460 | -15.006% | 10/10 |
| Adam | 1024 | 42.27260 | 37.86900 | -10.417% | 10/10 |
| Gather | 512 | 19.06860 | 18.36370 | -3.697% | 7/10 |
| Gather | 1024 | 42.09955 | 41.86375 | -0.560% | 7/10 |
| Five Gaussian fusions | 512 | 56.55325 | 17.48945 | -69.074% | 10/10 |
| Five Gaussian fusions | 1024 | 97.51700 | 37.73595 | -61.303% | 10/10 |

- The ML receipt contains eighteen successful processes at the same source and
  recorded ML executable hash. Six balanced order permutations compare unlimited,
  32 MiB and zero retained device uploads. The strict summarizer verifies fixed
  seeds and dataset size, three epochs, requested budget and retained-cache bounds.
  A separate adaptive teammate reviews the ML interpretation and deterministic
  cross-check.
- The retained scripts verify source and executable identities before and after
  measurements. Gaussian runs use three warmups and ten synchronized samples.
  `locks.log` shows the final suite and benchmark stages running serially under
  their declared GPU/benchmark locks; completed work should not be rerun solely
  because the session restarted.

## Limits that must remain visible

The successful nine-suite CTest results include individual skipped cases inside
executables. CPU/CUDA pass-fail-skip counts in the draft are not equivalent to
claiming every individual case ran. The CUDA core suite retains one skipped case.

Benchmark CPU load was high and variable. Alternating order helps comparison but
does not remove external contention. The 1024-pixel gather timing remains
inconclusive. Peak working set is cumulative for a process; the 1024-pixel CUDA
reservation may retain state from the earlier 512-pixel case. Training allocation
metrics include more than optimizer storage. The all-fusions comparison toggles
features in one combined binary; its off arm is not original upstream `f93b7bc`.

Docker is unavailable on this native host. The checked workflow runs builder-script
tests and Docker image compilation/installation for CUDA 12.4, 13.2 and 13.4; neither
the workflow nor Dockerfile runs library CTest inside a container. The three PR
CI receipts report successful matrix builds, not container runtime verification.

## Packaging checks sent to the lead

- Preserve the deterministic ML check receipt and raw JSON if the final report
  cites that result; the initial packaging script did not include that directory.
- Include this audit when useful and preserve build logs alongside JUnit/test logs
  if the artifact promises complete build provenance.
- The runner scripts use this lab's absolute Windows paths and external helper
  scripts. Reproduction instructions must identify those prerequisites or include
  the helpers; copying the runners alone does not make them portable.
- Replace the report's stale "ML pending" and "measurements in progress" wording
  after incorporating the completed ML results. Refresh the PR index after final
  technical updates, preserving previous snapshots.

No source, worktree, build or running service was modified during this audit.
