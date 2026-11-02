# Round 10 research and optimization

Status: native integrated CPU and CUDA validation passed, 14/14 suites each.
Corrected Docker CI passed all three repeated jobs: rebuilt modified library,
CTest 14/14 and standalone GCC ASan/UBSan 6/6 with zero findings. Four independent
pull requests and their comprehensive technical-summary comments are submitted.
All12 current-head upstream CUDA-profile compilation/install checks also pass;
their actual logged versions and source identities are independently certified.
Earlier round 9 PRs51–53 remain open and are not recreated.

## Source and environment

This continues the existing lab and worktrees, without a fresh clone or host
dependency installation. Upstream main was checked as `f4ac612`. Pilot ML runtime
is `0a4b62a`; adaptive runtime is `95093e2`; Gaussian runtime is `b96db27`.
Frozen integrated runtime and documentation are `a67f671`.
The later evidence/test-only head `e5bf8d0` has the identical engine tree
`4686fb69c4ab658f216949729e695985084ef8aa`. Newly registered tests passed
CPU 2/2 and CUDA 1/1; the certified native binaries remain unchanged.

The existing image is pinned to
`acaicia/minkowski4cpp@sha256:a4bf4c4e91ef5f4e50089f435005ca07f1a0a48deeeb9814ca4b526974de79ba`.
Remote CI rebuilds source in that image and checks the CMake codemodel, source
manifest, rebuilt archive linkage, binary hashes, exact suite set and JUnit.
All inherited matrix labels use the same image with CPU_ONLY; there is no claim
of three CUDA runtime versions or container GPU execution. Native CUDA results
are supplementary. No Samaritan source or live service was changed.

Native hardware: Ryzen5 5600X, 6cores/12threads, 16GiB RAM, RTX2080SUPER8GiB/SM75,
Windows11, MSVC19.44, CMake4.2.3, CUDA13.4.3/nvcc13.4.92, LibTorch2.15.0,
driver610.88. The Linux image reports GCC13.3.0, CMake4.2.3 and nvcc13.4.92.

## Adaptive part splitting

Compact equal level-zero x runs before sorting, then assign leaves with a
monotonic cursor inside each level. Part boundaries, canonical ordering, map
weights, cache metrics and gradients remain unchanged. Six differential tests
include250 randomized cases and coordinates near +/-2^52.

The independent audit reparses108 raw processes and26 summary rows, verifies
paired order, source/binary identities and all workload/cache invariants.

| Complete map phase, median ms | Original | Candidate | Change |
|---|---:|---:|---:|
| CPU CenterSampled, warm |23.7925|19.2345|-19.16%|
| CPU VolumeWeighted, warm |25.0485|22.0835|-11.84%|
| CUDA CenterSampled, warm |12.0645|10.7460|-10.93%|
| CUDA VolumeWeighted, warm |13.5580|12.2455|-9.68%|
| CUDA CenterSampled, first epoch |139.7570|141.7780|+1.45%|
| CUDA VolumeWeighted, first epoch |163.7640|164.7095|+0.58%|

Each workload uses six balanced A/B pairs; medians/ranges and reciprocal
map-phase throughput are in the detailed report. CPU process peaks change less
than0.04%; CUDA allocated/reserved peaks are identical. No material memory gain
or isolated CUDA kernel improvement is claimed. Background load was high.
Cursor scans can lose against binary searches for other sparse-level layouts.

Exploratory whole-pair bootstrap analysis (20,000 draws) puts CenterSampled warm
CPU/CUDA median-change intervals at [-41.82,-8.02]% and [-15.85,-9.16]%.
VolumeWeighted intervals cross zero: CPU [-26.33,+3.86]%, CUDA [-21.03,+12.18]%.
Those VolumeWeighted point estimates remain inconclusive. Small cohorts,
serial load and uncertain pair independence limit these descriptive intervals.

## Gaussian backward atomics

Preserve the ten existing warp reduction trees, broadcast their sums and issue
adjacent attribute atomics from ten lanes instead of serially from lane zero.
The previous path remains available for controlled same-binary comparisons.
Eighty process trials use ten balanced pairs for each workload/control.

| Isolated backward kernel, GPU event median ms | Original | Candidate | Change |
|---|---:|---:|---:|
| Row-group control |2.02486|1.43217|-29.27%|
| Sparse control |2.36523|2.10533|-10.99%|
| Dense control |9.89513|9.58031|-3.18%|

Real-scene training changed-0.07% at512px and+0.76% at1024px, within unchanged
forward-control noise. No demonstrated training or memory gain is claimed.
Static generated code uses58 rather than62 registers, ten extra shuffles and
one rather than ten atomic instructions; these are not dynamic occupancy metrics.

Exploratory paired-bootstrap intervals are [-30.74,-26.56]% for row groups and
[-17.39,-7.00]% for sparse controls. Dense [-6.51,+0.19]% crosses zero, so its
3.18% point estimate is inconclusive. Real training intervals also cross zero:
512px [-3.59,+4.09]%, 1024px [-4.94,+4.03]%. The supplement retains all original
measurements and reports unadjusted descriptive sign tests, whose paired-win
null differs from the ratio-of-medians estimand. Nothing is confirmatory.

Full native branch CTest passes4/4 on both CPU and CUDA; CUDA Gaussian71/0.
Three focused cases include ten finite differences, edge tiles, contribution
counts0..513, nondefault streams and zero gradients. Memcheck/initcheck report
zero errors; racecheck zero hazards/errors/warnings, without exclusions.
The frozen203-file evidence package passes its portable verifier.
Committed Git-blob verification initially found94 ignored JSON/log/manifest
files missing from that publication. Metadata-only commit348e6b8 adds them;
all203 hashes and the manifest now match committed blobs. Adaptive134 and ML46
evidence files passed the same audit without missing files. No runtime source
or measured output changed in this correction.

## Real-object ML pilot

ModelNet10 preprocessing preserves official train/test membership, samples
triangle surfaces by area, selects40train/20test objects per class and stores
all object/source/split hashes. Every method receives the same400train/200test
objects and1024points/object. Six fixed epochs, batch16, Adam lr0.001 and seeds
1,2,3 are shared. No hyperparameters were selected on test results.

Both independent audits recompute all confusion matrices, class precision,
recall, F1, macro metrics and training-time sums, and verify all12 trial identities.

| Method | Accuracy% | Macro P% | Macro R% | Macro F1% | Parameters | Input channels |
|---|---:|---:|---:|---:|---:|---:|
| Uniform |74.5+/-2.8|76.1+/-2.4|74.5+/-2.8|74.3+/-2.9|677930|2|
| Adaptive |78.0+/-1.7|80.2+/-1.2|78.0+/-1.7|77.6+/-1.7|882650|3|
| Gaussian |79.5+/-2.6|82.3+/-1.2|79.5+/-2.6|78.4+/-3.5|110218|11|
| Combined |80.8+/-1.3|82.2+/-1.5|80.8+/-1.3|80.6+/-1.0|885242|9|

| Method | Train s | Cached batch1 ms | Batched eval samples/s | Peak allocated/reserved VRAM MiB | Lifetime RSS MiB | Mean active elements |
|---|---:|---:|---:|---:|---:|---:|
| Uniform |12.0+/-2.8|37.36+/-5.13|446+/-40|57/76|3777+/-24|785.81|
| Adaptive |6.7+/-0.4|10.86+/-0.36|948+/-11|171/200|4078+/-13|368.89|
| Gaussian |2.6+/-0.2|2.31+/-0.12|6738+/-225|42/58|3771+/-0|147.02|
| Combined |5.8+/-0.3|11.85+/-1.66|1135+/-74|94/120|3949+/-1|190.24|

These are means and sample standard deviations of a practical systems comparison.
Networks, feature information and parameter counts differ. Fixed method ordering,
first-use warmup and substantial background load limit latency interpretation;
three seeds do not establish statistical superiority or isolate representation.
Adaptive uses53.1% fewer elements yet approximately3x the allocated VRAM here.

Cached inference excludes conversion. Conversion medians are respectively
0.22,0.98,6.07,5.93ms/object (variability in detailed report); summing independent
medians is not measured end-to-end latency. Training VRAM peaks include per-epoch
evaluation; RSS is lifetime process high-water. Matched-information/capacity
ablations, a validation split before tuning, separate resettable phase VRAM
scopes and conversion-inclusive inference remain future work.

## Measurement and build correctness

- Summary guards now reject different dataset manifests or split hashes even
  when counts/seeds/budgets match. A before/after regression proves the old
  summary accepts such a pair while the changed one fails before output.
  Twenty summary regression cases pass.
- Portable RSS adds Linux getrusage KiB-to-MiB and Darwin byte conversion while
  preserving Windows PeakWorkingSetSize. A touched64MiB test validates units
  and lifetime high-water behavior; focused native CTest4/4 passes.
- Linux source compilation exposed duplicate legacy/unified CPU CoordinateManager
  definitions. The independent5line CMake fix excludes the legacy.cpp inCPU_ONLY.
  A configured-target CTest verifies exactly one unified implementation, with
  duplicate/missing negative fixtures. Baseline Docker failure evidence is retained.
- Documentation now describes the existing adaptive Gaussian bridge, fused
  projection/culling/gathering, frozen bridge geometry and marginal-axis covariance
  approximation accurately in the integration tree.

## Negative findings and limits

The earlier Gaussian warp-bound candidate8438c04 passed focused correctness but
was rejected after ten pairs: dense kernel+4.95%, row-groups+2.40%, sparse-3.55%,
real512px backward+4.11% with0/10paired wins. Lower theoretical scan counts did
not produce a useful measured improvement. Its raw history remains in `gaussian/`.
The complete negative-experiment records and source delta are also published as
`negative-warp-bounds.zip` and `negative-warp-bounds.patch` in the report package;
the rejected code is not part of the retained engine runtime.
The receipt-sharing interruption during the retained atomics A/B was recovered
without overwriting any of the first60 raw trials; their hashes still match.

Baseline Docker CI41507998304 failed before tests in all three repeated jobs.
Documentation run 41511099983 is excluded from test evidence. Actual source CI
41511100024 rebuilt and passed 13/13 suites in all three jobs; combined CI
41512323659 passed 14/14 in all three, including Linux RSS unit/high-water checks.
Both failed afterward because the standalone sanitizer harness requested C++17
for a C++20 type. Corrected CI 41514149790 requests C++20 and runs the sanitizer
first; all three jobs passed. Independent audit verified all 471 canonical source
blobs, 39 evidence-file identities, rebuilt linkage, JUnit, pre/post executable
hashes and actual Linux RSS results. The runner recorded four logical CPUs and
approximately 15.6 GiB RAM; its CPU model was not recorded or inferred.
No container GPU execution, isolated dynamic occupancy or real-scene Gaussian
training improvement has been demonstrated. Segmentation/reconstruction and
deterministic adaptive pooling need further separately scoped experiments.

An integrated EAGER CUDA-loading run timed out the existing Gaussian SSIM 17x300
reference case after 420.288 seconds, leaving 13/14 suites passed. Observed GPU
free memory was approximately 125 MiB. The exact same binaries passed all 14
suites on a full LAZY-loading retry in 116.41 seconds, without filtering,
rebuilding, relaxing tolerances or changing the 420-second timeout. Gaussian
117 cases passed in 20.4991 seconds; adaptive 199/0, split 6/0, core 51/0/1 and
memory 12/0. The EAGER failure remains an environment/stress finding; its cause
was not isolated.

An analytic reference quantifies the intentional BoxIntegral approximation.
For unit marginals with corr(X,Y)=rho and independent Z, positive-octant mass is
1/8+asin(rho)/(4*pi), while the marginal-product approximation gives 1/8. At
rho=0.9 this is 0.214108 versus 0.125 (-41.62%); at rho=-0.9 it is 0.035892 versus
0.125 (+248.27%). This compares mathematical models of the documented algorithm;
it is not measured output of a new bridge executable or an undocumented bug.
Formula, source identity and limitations are in gaussian-correlation-reference.json.

## Pull requests and reproduction

| PR | Change | Tests | Benchmark result | Review status |
|---|---|---|---|---|
| [#54](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/54) | Remove duplicate CPU manager definitions; actual-target source guard | Linux full suites, native guard and negative fixtures | Link failure becomes successful consumer execution; no runtime speed claim | Open, not merged |
| [#55](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/55) | ModelNet loader/preprocessing, dataset identity guards, portable RSS | Loader22, preprocessing5, summary20, RSS high-water, 12 ML trials | Four-method pilot; mean accuracies74.5/78.0/79.5/80.8%; architectures differ | Open, not merged |
| [#56](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/56) | Parallel warp-aggregated gradient atomics | CPU/CUDA suites, finite differences and all three CUDA sanitizers | Isolated kernels3.18–29.27% faster; real training approximately flat | Open, not merged |
| [#57](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/57) | Compact adaptive cached-part splitting | Differential6, portable guard6, CPU/CUDA suites and ASan/UBSan | Warm maps CPU19.16%/CUDA10.93% faster for CenterSampled; CUDA first epoch+1.45% | Open, not merged |

All four have comprehensive descriptions and technical-summary comments. Existing
PRs51–53 were preserved. Only fork branches were pushed; no upstream main push
or automatic merge occurred. PR54's initial upstream CUDA12.4 build exposed the
already known allocator namespace issue from existing PR32; merge4ac4292 retains
that prerequisite's ancestry rather than recreating its fix. All12 current-head
upstream compilation checks passed. Actual logged profiles are
CUDA12.4.131/LibTorch2.5.1, CUDA13.2.78/LibTorch2.15.0 and
CUDA13.4.92/LibTorch2.15.0. Independent audit verified PR heads, checked-out
synthetic merge ancestry, CPU_ONLY=OFF, CUDA objects and installation in all12
public job logs. These compilation results remain separate from native GPU
execution and the three repeated CPU_ONLY container runtime jobs. The certificate,
log identities and archived logs are in `ci-final/`.

Detailed reports include raw commands, deterministic seeds, hashes, compiler
versions, benchmark ranges and reproduction scripts:

- `benchmarks/adaptive_part_split_results/README.md`
- `benchmarks/gaussian_parallel_atomics_results/REPORT.md`
- `benchmarks/modelnet10_results/README.md`
- Local `docker-runtime/RECOVERY.md` and `integration-review/REVIEW.md`

Testing/Docker specialists recovered actual Linux jobs and fixed the source list;
adaptive engineering audited/packaged the split optimization; Gaussian/CUDA
engineering validated atomics and sanitizers; ML engineering added portable RSS
and packaged datasets/results; benchmark specialists independently checked all
metrics; integration specialists audited merges, test registration and binary
identities. Root coordinates source freezes, integration and publication.

| Teammate | Responsibility and completed contribution |
|---|---|
| testing_environment / docker_testing_recovery | Recovered actual container jobs, fixed CPU source selection and sanitizer command, audited source/linkage/RSS and production build logs |
| adaptive_benchmark | Recovered the split candidate, independently audited108 trials and26 summaries, packaged the portable runner and evidence |
| gaussian_cuda / gaussian_cuda_recovery | Recovered80 paired trials, completed native suites and three CUDA sanitizers, reviewed masks/streams and packaged evidence |
| machine_learning / ml_benchmark_recovery | Added portable RSS, validated datasets, documented model/features, packaged12 trials and independently reviewed uncertainty calculations |
| benchmark_specialist | Recomputed all ML confusion metrics and Gaussian benchmark summaries with provenance checks |
| integration_specialist | Certified14-suite CPU/CUDA runs, exact binary/source identities, source registration and preserved EAGER failure |
| Root integration lead | Added dataset-summary guards and source-selection regression, ran extra seeds, resolved merges, corrected ignored-file publication, verified exported artifacts and submitted PRs/comments |

## Remaining bottlenecks and recommended research

Further kernel changes need fresh profiles on an isolated GPU. The rejected
warp-bound experiment and approximately flat real-scene atomics training results
show diminishing returns from the current hypotheses; the shared device also
reached approximately 125 MiB free during validation. The next measurements
should separate kernel share, memory stalls and interference before retaining
another optimization.

The ModelNet pilot establishes a reproducible real-object pipeline. A validation
split before tuning, matched-information/capacity ablations, balanced method
ordering, measured conversion-inclusive inference and separate phase VRAM scopes
are needed before broader representation-quality claims. Gaussian conversion
medians exceed cached Gaussian inference here, making conversion a useful
profiling target; independent medians are not an end-to-end timing measurement.

Other follow-ups are deterministic adaptive Sum/Mean pooling profiles, opt-in
geometry gradients and correlated box integration, additional GPU architectures,
and GPU-container execution when suitable hardware/runtime access is available.
Segmentation and reconstruction should build on those measurement foundations.
