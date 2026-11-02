# Minkowski4CPP round 9 research report

Status: native validation and measurement audits complete, 2026-11-02. Three independent improvements are submitted as PRs #51–53. Container runtime validation remains unavailable on the measured host. [Complete PR index](pr-index.md).

## Scope and provenance

This continues the original lab at `C:\Users\User\Work\Minkowski4CPP`, baseline
`f93b7bc`, using the unfinished `ROUND9.md` handoff and the prior eight rounds of
experiments. Upstream main was rechecked as `f4ac612d063698f587357881e910328c057b9217`.
The combined round-9 runtime candidate is `f3f74919a64bede57fab7d5f303e94ca188c931a`.
Prior reports remain historical evidence with their original limitations; current
receipts identify freshly verified source, commands, executable hashes and outputs.

The extra Adam teammate finished the abandoned optimizer investigation; the adaptive
teammate implemented and measured device-cache limits; the Gaussian/CUDA teammate
implemented sorted attribute gathering and reviewed its gradient storage. The lead
integrated the branches, reran the complete suites and measured the combined stack.
Independent cross-reviews examined merge dispatch, cache lifetime and measurement
aggregation. Work survived session restarts through detached jobs and durable logs.

## Independent pull requests

| PR | Runtime source | Improvement | Branch validation |
|---|---|---|---|
| [#51](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/51) | `977bd71` | Fused CUDA Adam with corrected ATen rounding | CPU/CUDA CTest 4/4 each; five CUDA tests; memcheck, racecheck and initcheck |
| [#52](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/52) | `2623c56` | Optional budget for retained adaptive part uploads | CPU/CUDA CTest 4/4 each; five CUDA tests; lifetime/eviction sanitizer coverage |
| [#53](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/53) | `d45b911` | Fused sorted Gaussian attribute gather and backward scatter | Gaussian and adaptive executables passed on CPU and CUDA; six new CUDA tests; all three sanitizers |

Each PR contains its implementation, automated tests, measurements, reproduction
instructions, limitations and a technical-summary comment. Fork branches only were
pushed; no PR was merged. All nine Docker matrix builds passed (12.4/13.2/13.4 for
each PR). Exact-head receipts are `docker-ci/adam.json`, `docker-ci/adaptive.json`
and `docker-ci/gaussian.json`; all three PR bodies and CI comments were read back.
These are compilation checks, separate from native runtime validation.

## Correctness findings

The abandoned Adam comparison did not establish a tolerance problem. Its displayed
"ulp" denominator was scaled by learning rate, rather than true float spacing; the
worst cancellation case differed by about twelve actual float32 ULPs. The correction
matches ATen operation order, explicit multiplication rounding and version-dependent
reciprocal conversion. On measured LibTorch2.15/CUDA13.4, parameters and both moments
match exactly for 100,003 elements through six updates, including tiny/large gradients. Eight-step trainer comparisons
remain within the documented relative tolerance. A failed filtered initcheck was
retained; a full unfiltered run passed, distinguishing instrumentation from a kernel bug.

Gather backward originally allocated gradients for frozen inputs. A one-trainable-input
case reproduced 16,448 bytes of storage versus 2,056 required bytes. The retained
implementation allocates only requested gradient slices and tests each input category.
Other coverage includes empty and noncontiguous inputs, unique permutation subsets,
112 finite-difference components, exact render images, retained means2d gradients and
nondefault stream lifetime. The operation retains the renderer's first-order autograd
scope; no new higher-order derivative support is claimed.

The adaptive cache budget accounts for complete shared upload groups and evicts them
together, preserving asynchronous consumers with stream lifetime tracking. The default
remains unlimited; zero disables retention. Accounting is deliberately conservative
if only part of a shared slab expires. The budget excludes active batch maps, in-flight
consumers, temporary storage and allocator reservations, so it is not a cap on total VRAM.
Tests cover gradients, duplicate parts, mixed index widths, eviction and stream reuse.
Adaptive and gather sanitizer runs exclude the `indexing_backward_kernel` family
because of LibTorch's previously reproduced small-stride issue; this is a coverage
limitation, not a claim that excluded code is clean. Adam's final initcheck is unfiltered.

## Standalone measurements

Gaussian measurements use ten balanced paired rounds, synchronized GPU timings, fixed input and executable,
three warmups and ten timed iterations per process. The host was contended; small
changes are workload observations, not guaranteed deployment speedups. Full ranges,
raw records and unchanged-path controls are in each PR's committed benchmark report.

| Change | Workload | Before | After | Latency change | Faster paired rounds |
|---|---|---|---|---|---|
| Adam | 512-pixel Gaussian training step | 25.787 ms | 24.268 ms | -5.89% | 9/10 |
| Adam | 1024-pixel training step | 43.438 ms | 43.079 ms | -0.83% | 5/10; inconclusive |
| Gather | 512-pixel training step | 10.37 ms | 9.95 ms | -4.1% | 9/10 |
| Gather | 1024-pixel training step | 23.78 ms | 23.28 ms | -2.1% | 10/10 |

These branches have different bases; do not compare their absolute times or multiply
their percentage improvements. Adam training allocated memory increased about 0.01%
and 0.08% at 512/1024; reserved memory changed -1.96% and +1.99%. Gather render
backward peak allocation changed +0.7% at 512 and -0.5% at 1024. These regressions are retained.

The gather five-step Kineto sample reduced GPU operations per step from 283 to 244
(-13.8%) and memsets from 38 to 25. Summed recorded GPU duration was 9.935 to 9.276ms;
the new gather/scatter kernels took 0.204/0.287ms per step. This single instrumented
sample explains launch reduction; it is not an independent throughput benchmark.

The 16MiB adaptive budget is an explicit tradeoff, measured in six balanced rounds:

| Batch-map workload | Retained group charge, unlimited to bounded | Warm latency change | Process CUDA allocation change |
|---|---|---|---|
| CenterSampled | 20.058 to 15.376 MiB (-23.3%) | 10.267 to 11.5365 ms (+12.36%) | -0.47% |
| VolumeWeighted | 60.175 to 6.942 MiB (-88.5%) | 11.2235 to 29.9645 ms (+166.98%) | -3.96% |

These timings cover a synchronized batch-map phase, potentially including preceding
asynchronous preparation; they are not isolated kernel durations. Whole-process peaks
include other allocations. New unlimited versus old unlimited showed mixed results
(CenterSampled +5.61% warm latency, VolumeWeighted -5.86%), so no default speedup is claimed.
VolumeWeighted process peak working set also increased from 1121.799 to 1151.153MiB
(+2.62%); a device-cache cap does not imply lower CPU memory.

## Combined stack and machine learning

Both combined Release builds completed, and all nine registered CTest suites passed
in each configuration at the frozen source hash. The native suite details are:

| Configuration | Adaptive passed/failed/skipped | Gaussian | Core | Memory growth | CTest |
|---|---|---|---|---|---|
| CPU | 175/0/21 | 78/0/11 | 37/0/15 | 6/0/6 | 9/9 |
| CUDA | 199/0/0 | 114/0/0 | 51/0/1 | 12/0/0 | 9/9 |

The CUDA core skip is retained and is not counted as a pass. Receipts, complete
logs and JUnit are in `integration-final/`; source and executable SHA256 checks bind
the subsequent measurements to these builds. All three Gaussian comparisons passed
20/20 process runs and independent raw-data audits. The 18 ML timing runs and three deterministic correctness runs also completed successfully.

Root SSIM follow-up on recovered round8b already completed:
512 training 11.26 to 8.75ms (-22.3%,9/10),1024 25.10 to 15.77ms (-37.2%,10/10).
This was posted to PR50 with host contention and pre-trainer memory-field caveats.

The round9 comparisons separately toggle Adam, gather, and all five Gaussian fusions
(projection, tile construction, SSIM, Adam, gather) in one binary. The all-fusions
baseline is this binary with those switches disabled, not original upstream f93b7bc.
Within a Gaussian process, sizes execute in order; 1024-pixel reserved memory can
retain prior 512-pixel training allocator state. Process peak working set is cumulative.
Training allocation is a phase-level process measurement, not optimizer-only storage.

| Combined binary comparison | Pixels | Training latency off to on | Change | Faster pairs | Training allocated MiB off to on | Training reserved MiB off to on |
|---|---|---|---|---|---|---|
| Adam alone | 512 | 20.807 to 17.685ms | -15.01% | 10/10 | 230.368 to 218.286 (-5.24%) | 292 to 268 (-8.22%) |
| Adam alone | 1024 | 42.273 to 37.869ms | -10.42% | 10/10 | 313.015 to 313.527 (+0.16%) | 364 to 372 (+2.20%) |
| Gather alone | 512 | 19.069 to 18.364ms | -3.70% | 7/10 | 218.596 to 218.286 (-0.14%) | 268 to 268 (flat) |
| Gather alone | 1024 | 42.100 to 41.864ms | -0.56% | 7/10 | 312.863 to 313.527 (+0.21%) | 396 to 372 (-6.06%) |
| All five fusions | 512 | 56.553 to 17.489ms | -69.07% | 10/10 | 295.282 to 218.286 (-26.08%) | 338 to 268 (-20.71%) |
| All five fusions | 1024 | 97.517 to 37.736ms | -61.30% | 10/10 | 569.003 to 313.527 (-44.90%) | 662 to 372 (-43.81%) |

Complete median/minimum/maximum tables, throughput and controls:
[Adam](adam-stack/summary.md), [gather](gather-stack/summary.md),
[all fusions](all-fusions/summary.md). For all five fusions, derived training
throughput increased 17.682 to 57.178 steps/s at 512 and 10.255 to 26.500 at 1024;
whole-process peak working set fell 28.38% and 28.12%.

CPU boundary load was 47.5–100% for Adam, 69.9–96.5% for gather and 38.3–95.3% for
all fusions. The unmodified render controls in the Adam experiment shifted up to
-4.91%; these comparisons do not isolate kernel time. Gather's 1024 training result
is inconclusive, and its 1024 render forward/backward median regressed 0.76% (5/10
faster), with backward allocation +0.31%. Strong combined improvements do not erase
these smaller regressions. Do not compare absolute times across different blocks.

The ML experiment compares unlimited, 32MiB and zero retained device uploads in the
combined adaptive classifier: six order permutations, seed1, data seed2026, 300 training
and 200 test shapes, 2048 points, three epochs and batch16. Deterministic mode is off
to exercise default fused CUDA apply; seeds are fixed but atomic sums may vary. This
is one-seed performance/compatibility evidence, not a multi-seed generalization study.
Legacy *_train allocator peaks include per-epoch evaluation; training time excludes it.

| ML measure | Unlimited retention | 32 MiB budget | Zero retention |
|---|---|---|---|
| Epoch-loop peak CUDA allocation | 335.354 MiB | 295.638 MiB (-11.84%) | 252.638 MiB (-24.67%) |
| Epoch-loop peak CUDA reservation | 388 MiB | 340 MiB (-12.37%) | 292 MiB (-24.74%) |
| Retained upload charge at experiment end | 70.279 MiB | 31.894 MiB (-54.62%) | 0 MiB (-100%) |
| Whole training median | 6.476 s | 5.385 s (-16.85%; 4/6 faster pairs) | 5.754 s (-11.14%; 2/6 faster pairs) |
| Mean epochs 2–3, change from unlimited | — | +2.63% | +13.97% |
| Batch-one inference median | 12.669 ms | 11.626 ms (-8.23%) | 13.453 ms (+6.19%) |
| Evaluation throughput | 633.676 samples/s | 771.406 samples/s (+21.74%) | 626.670 samples/s (-1.11%) |
| Process peak working set | 4440.322 MiB | 4464.453 MiB (+0.54%) | 4464.580 MiB (+0.55%) |
| Three-epoch test accuracy median | 25.25% | 28.50% | 28.00% |
| Macro F1 median | 21.967% | 25.010% | 25.041% |

Allocation reductions occur in every repeat, but whole-run latency is dominated by
first-epoch variability on a host with 59.5–86.2% boundary CPU load. The apparent
whole-run speedups coexist with slower warm epochs and do not establish a general
training speedup. The zero-retention configuration also regresses inference latency.
Fixed-seed fused runs have overlapping quality ranges and varying atomic sums; these
short, undertrained models provide no evidence that cache policy improves accuracy.
Precision, recall, F1, complete convergence curves, ranges and paired counts appear in
the [ML tables](ml-budgets/summary.md) and [interpretation](ml-budgets/interpretation.md).

A separate [deterministic fallback check](ml-deterministic-check/summary.md) ran one
process per budget with the same seed and compared 163 numerical/categorical fields.
Loss, per-epoch accuracy, final confusion matrix, precision/recall/F1 and class metrics
all matched exactly; final accuracy was 29% and macro F1 0.25504948. This mode bypasses
fused apply, requests deterministic algorithms in warn-only mode, and emitted no
captured warnings. It supports cache-policy correctness for this workload, not universal
CUDA determinism or a timing comparison. Raw outputs and the comparison are retained.


## Earlier research retained with its limitations

The [original-versus-optimized report](historical-original-vs-optimized.md) compares
f93b7bc with round3 e1af851, not round9. It recorded 2.96x adaptive CUDA forward/backward,
80.5x cold OverlapWeighted map construction and 67.5x interpolation speedups, but used
unswapped order on a contended host. Small differences are not reliable, and original
CPU convolution produced incorrect results. Later rounds corrected the initial CUDA
memory regression using fused adaptive apply; the cumulative report preserves that history.

The prior three-seed synthetic classification study (#31, twelve epochs) reported
79.0% uniform, 72.3% adaptive, 81.2% Gaussian and 80.8% combined adaptive/Gaussian
accuracy. Architectures have different parameter counts and these are synthetic
objects, not real-world segmentation or reconstruction quality results. The Gaussian/uniform
accuracy gap is not proof of a statistically significant advantage. Adaptive voxelization
improved interpolation accuracy per voxel on clustered inputs but lost
to uniform resolution on near-uniform density. Those comparisons are not rerun or
silently relabeled as round9 results.

## Environment, reproduction and limits

Measured host: Ryzen5600X (6C/12T), 16GiB RAM, RTX2080SUPER 8GiB SM75, driver610.88,
Windows11, MSVC19.44, CMake4.2.3, CUDA13.4.3 distribution (nvcc13.4.92), LibTorch2.15.0.
The existing native toolchain was reused. Docker is absent on this host; no local
container GPU execution is claimed. PR CI builds the Dockerfile under CUDA12.4/13.2/13.4;
this proves compilation only. Hardware/runtime compatibility on other GPUs and older
LibTorch releases remains limited by the actual tests performed.

Native scripts: `run-integration.ps1`, `run-gaussian-ab.ps1`, `run-ml-budgets.ps1` and
`summarize-final.py` in this directory. Build and GPU locks serialize measurements.
Receipts record commands, source hashes, input hash, executable SHA256 and status.
Complete raw measurements and failed attempts are retained alongside summaries. The original PowerShell runners use lab-specific absolute paths; their helper snapshots and a portable command recipe are provided in [REPRODUCTION.md](REPRODUCTION.md). Fresh output directories and receipts must be used for reruns, preserving the archived data.
No automatic service shutdown or restart was performed to obtain quieter measurements.

Container reproduction below is a prepared recipe, not an executed result from this host.
Use the existing image first, record its immutable image ID/digest, and build the mounted
modified source into a separate build volume so the installed library cannot mask it:

```bash
git clone https://github.com/itsSio/Minkowski4CPP.git
cd Minkowski4CPP
git checkout f3f74919a64bede57fab7d5f303e94ca188c931a
docker pull acaicia/minkowski4cpp:latest
docker image inspect acaicia/minkowski4cpp:latest --format '{{.Id}} {{json .RepoDigests}}'
docker run --rm --gpus all -v "$PWD:/workspace/src:ro" \
  -v mink-round9-build:/workspace/build -w /workspace/src \
  acaicia/minkowski4cpp:latest bash -lc '
    export TORCH_CUDA_ARCH_LIST=7.5
    cmake -S . -B /workspace/build -GNinja -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_PREFIX_PATH=/opt/libtorch -DCMAKE_CUDA_ARCHITECTURES=75 \
      -DMINK_BUILD_TESTS=ON -DMINK_BUILD_GAUSSIAN_BENCHMARKS=ON \
      -DMINK_BUILD_ML_EXPERIMENTS=ON &&
    cmake --build /workspace/build --parallel 2 &&
    ctest --test-dir /workspace/build --output-on-failure'
```

SM75 is the measured GPU; select the target GPU's architecture for another machine.
If the published image differs from the checked-in profile, preserve its receipt and
build `docker/Dockerfile` with `--build-arg CUDA_VERSION=134 --build-arg CUDA_ARCHITECTURES=75`
instead of modifying the host environment. No image digest is invented here.

## Remaining work and stopping criterion

Rasterizer backward, host synchronization in nonzero/pair counts, and variable tile
work remain optimization targets. Real scene segmentation, reconstruction quality,
multi-GPU portability and container GPU execution require further experiments.
The current small Adam/gather end-to-end gains and severe cache-cap latency costs
show diminishing returns for further unprofiled changes on this contended machine.
The validated changes remain reviewable as separate PRs, with optional memory controls
and explicit regressions instead of a blanket claim that adaptive resolution is faster.


## Recovery audit and publication scope

After the restart, the testing teammate checked both JUnit suites, all 12 current
executable hashes and the 78 measured process receipts. The Gaussian/CUDA teammate
independently recomputed every Gaussian aggregate; the adaptive teammate checked all
17 ML summary measures, cache implementation and deterministic follow-up. Their records
are [testing](restart-audit-testing.md), [Gaussian](restart-audit-gaussian.md) and
[adaptive](restart-audit-adaptive.md). No new native builds or timed experiments were
needed because the surviving source, binaries and receipts matched.

The final PR heads add only documentation, raw evidence and a benchmark helper to
the measured runtime commits. They are merged locally into the fork's integration
support branch. The native C++ and CMake trees remain identical to measured f3f74919;
the [source provenance receipt](source-provenance.json) records that distinction.
The support branch is for reproduction; upstream PRs remain independent and unmerged.

The [PR index](pr-index.md) covers all 49 PRs from this research effort: 36 open and
13 merged by the maintainer at the recorded snapshot. Earlier PR tests and benchmarks
are attributed reports unless checked in the round receipts. Historical summaries
and raw evidence are preserved; the new combined-stack measurements supplement the
original PR findings. No Samaritan source or live service was changed.
