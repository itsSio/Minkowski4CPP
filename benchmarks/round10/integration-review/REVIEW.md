# Round 10 independent integration review

Reviewed source: `a67f671f4aa3a003751e3d06af85d2b9b8b459e5`.
The fresh native validation receipt identifies this commit; later evidence,
documentation or test-registration commits must be named separately.

## Source integration

The resolved Gaussian test list retains the adaptive bridge, Adam and new parallel
atomics cases exactly once each. The adaptive split, Linux RSS and ML summary
tests are registered. The native CPU target's actual Ninja object list contains
`coordinate_manager.cu.obj` and excludes the duplicate legacy `.cpp` object.
No blocking integration defect was found in the reviewed changes.

The integrated split helper, Gaussian raster CUDA implementation, summary guard
and RSS helper are byte-identical to their measured or validated candidates.
`kernel_map.cpp` additionally contains earlier integrated CenterAveraged and fused
apply-map support; whole-file identity to the standalone split branch would be
an incorrect claim. Full integrated tests cover that composition.

## Verified and pending gates

| Gate | Independently checked state |
|---|---|
| Fresh integrated CPU build | Passed |
| Fresh integrated CPU CTest | 14/14 passed; exact expected suite names; no skipped suites |
| CPU internal cases | Adaptive 175 passed/21 skipped; split 6/0; Gaussian 78/14; core 37/15; memory 6/6; zero failures |
| Fresh integrated CUDA build/CTest | Build passed; complete LAZY retry passed 14/14; exact expected suite names and seven binary hashes verified |
| CUDA internal cases | Adaptive 199/0/0; split 6/0/0; Gaussian 117/0/0; core 51/0/1; memory 12/0/0; zero failures |
| Candidate native Gaussian | Separate completed audit reports CPU/CUDA CTest 4/4 each and zero memcheck/initcheck errors or racecheck hazards |
| Adaptive evidence packaging | Independently rehashed all 134 manifest entries |
| ModelNet evidence packaging | Independently rehashed 12 raw runs and verified the preserved pilot executable hash against all three receipts |
| Adaptive portable-runner tests | Six manual regression checks reported passed; CTest registration follow-up planned by root |
| Genuine Docker runtime | Runs 41511100024 and 41512323659 pending; Documentation runs excluded |
| Docker GPU execution | Unavailable on these runners; do not describe native CUDA as container GPU validation |

CPU case skips are CUDA-only cases inside otherwise passing suites. They must not
be silently omitted or counted as executed GPU coverage.

Update: the original integrated CUDA EAGER run completed 13 passing suites and
one Gaussian timeout at 420.288 seconds. Its full failed receipt, JUnit and log
remain preserved. Read-only diagnostics saw 100% GPU utilization and only
125–135 MiB free VRAM; loaded Torch DLL file IDs match the installed LibTorch
2.15 CUDA13.4 files. The launcher sets EAGER and does not define OMP/MKL caps.
A controlled full-suite retry used LAZY loading, the same source/binaries and
420-second timeout, without filters, exclusions or tolerance changes. It passed
all 14 suites in 116.41 seconds; Gaussian passed 117 cases in 20.4991 seconds.
The existing skipped core case is `manager_lifetime_cuda_interpolation`.
Before/after hashes of all seven binaries match, and the failed original JUnit
is preserved byte-for-byte. These observations do not by themselves isolate the cause of the
timeout; unrelated GPU activity can vary between runs.

The final native certificate in `gate-audit.json` identifies source `a67f671`,
all 14 live binary hashes across the two configurations, both built archive
hashes and a manifest of 188 canonical engine source files. That manifest's
SHA256 is `e2bd12de6031b2b3c7fea74127d283c21fe527c72aa5c00422f70dc094b67e1f`.
Root may now advance to evidence/test-only heads, with explicit runtime source
equivalence and targeted new-test receipts; this certificate does not relabel
such later heads as the source of the original full suites.

The first actual container run 41511100024 passed source rebuild and all 13 CPU
CTest suites in all three jobs, then failed to compile the standalone split
sanitizer. `partial-docker-audit.json` independently verifies the 36 evidence-file
hashes, exact JUnit suite sets, canonical manager compilation, rebuilt-library
linkage and split/summary helper identities while retaining the overall failed
status. It does not cover the later RSS or Gaussian atomics changes.

## Publication structure and report index inputs

| Change | Branch/candidate | Relationship | Main result to report |
|---|---|---|---|
| CPU coordinate-manager duplicate | `fix/cpu-coordinate-manager-link`, original `21774d4`; root adds regression test commit `66d087a` | Independent from upstream `f4ac612` | Linux static-link failure repaired; no latency or memory speedup claim |
| Compact adaptive part splitting | `perf/adaptive-compact-part-split`, measured `95093e2`, evidence `acbf9d0` | Stacked on existing PR #52, baseline `647450b` | Warm CenterSampled CPU -19.16%, CUDA -10.93%; first-epoch CUDA +1.45%; no material memory reduction |
| Parallel Gaussian backward atomics | `perf/gaussian-backward-parallel-atomics`, measured `b96db27` | Stacked on existing PR #53, baseline benchmark parent `dbead49` | Isolated synthetic kernel -3.18% to -29.27%; real training effectively flat (-0.07% / +0.76%) |
| ModelNet input and measurement safeguards | `test/ml-modelnet10`, loader `0e5c4fe`, guards `7460c7e`, RSS `2ceceea` | Extends existing ML PR #31 and allocator compatibility PR #32 | Twelve fixed-budget pilot trials; accuracy 74.5/78.0/79.5/80.8%; measurement portability and dataset comparability corrected |

The pilot ran integrated source `0a4b62a`, not the later ModelNet documentation
head or fresh final integration build. The preserved executable is
`integration-cuda/ml_representations.modelnet-pilot.exe`, SHA256
`ec62ba12f3e29c4b4c23f53c0bbd51296c2e77e805d970c69f990eeef0c6c095`.

For each new PR, record its actual URL/title/review state after publication and
link its technical-summary comment. Existing PRs #51, #52 and #53 already exist;
do not create replacements. Use dedicated new branches and do not merge upstream.

## Scientific limits to preserve

- Adaptive results are contended native observations with six balanced pairs.
  Preserve the first-epoch regressions and do not add gains across unrelated
  baselines. Reciprocals of map-phase latency are map-phase calls/s, not training
  throughput.
- Gaussian serial/parallel reductions preserve the same intra-warp tree, but
  inter-warp atomics remain nondeterministic. The measurements do not establish
  a real-scene training gain or lower memory. Static register/instruction counts
  are not dynamic occupancy measurements.
- ModelNet methods differ in architecture, parameter count and input features.
  This is a practical systems comparison, not a capacity-matched representation
  ablation. The three seeds do not establish statistical superiority.
- ModelNet timings are fixed-order, contended observations. Cached-representation
  inference excludes conversion; report conversion separately rather than label
  a sum of medians as an end-to-end measurement. Legacy train VRAM includes the
  per-epoch evaluation loop; process RSS is a lifetime high-water mark.
- Fixed six-epoch final results use no tuned validation selection. Future tuning
  requires a deterministic validation split and matched-information/capacity
  ablations before claims about representation quality.
- All three inherited Docker matrix labels execute the same pinned image in
  CPU_ONLY mode. They are repetitions, not three CUDA-version compatibility
  demonstrations. Rebuilt archive linkage and source/binary hashes must be
  recovered before claiming a container pass.

## Publication checklist

1. Complete and independently parse fresh native CPU/CUDA receipts and JUnit;
   verify all recorded live binary hashes before any overwrite.
2. Recover actual Docker CI evidence bundles, verify checksums, exact required
   suites, source manifest, rebuilt static-library linkage and sanitizer stages.
3. Keep tested runtime identities separate from later docs/test-only heads;
   establish engine hash equivalence and run newly registered tests explicitly.
4. Include SUMMARY, TECHNICAL DETAILS, TESTING, BENCHMARKS, MACHINE LEARNING RESULTS,
   TRADEOFFS and REPRODUCTION in every PR; mark unavailable metrics with reasons.
5. Push only dedicated fork branches; open PRs and technical-summary comments,
   then read back remote heads/descriptions/comments. Never merge automatically.
6. Update the cumulative report and index with actual PR URLs, tests, measured
   improvements and review state. Preserve negative and interrupted experiments.
