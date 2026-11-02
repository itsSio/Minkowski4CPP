# Reproducing round 9

Measured native source: `f3f74919a64bede57fab7d5f303e94ca188c931a`.
The integration support branch adds documentation and evidence only. Build from source;
do not link the image's previously installed `libminkowski_cpp.a` as an imported library.
The actual native commands, compiler/hardware versions, source and binary hashes are
in `environment.json`, `integration-final/receipt.json` and each experiment receipt.

The published Docker image was not executable on the measured Windows host because
Docker and WSL were absent. Nine GitHub Docker builds passed for the three feature PRs;
these did not execute the library's CTest suites. The following Linux/container recipe
is prepared for reproduction, not a claimed container result.

## Build and test the mounted source using the existing image

```bash
git clone https://github.com/itsSio/Minkowski4CPP.git
cd Minkowski4CPP
git checkout f3f74919a64bede57fab7d5f303e94ca188c931a
docker pull acaicia/minkowski4cpp:latest
docker image inspect acaicia/minkowski4cpp:latest --format '{{.Id}} {{json .RepoDigests}}'
mkdir -p ../round9-replay
docker run --rm -it --gpus all -v "$PWD:/workspace/src:ro" \
  -v mink-round9-build:/workspace/build \
  -v "$(cd ../round9-replay && pwd):/workspace/results" \
  -w /workspace/src acaicia/minkowski4cpp:latest bash
```

Inside the container (SM75 is the measured RTX 2080 SUPER; select the correct target
architecture on different hardware):

```bash
export TORCH_CUDA_ARCH_LIST=7.5
cmake -S . -B /workspace/build -GNinja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=/opt/libtorch -DCMAKE_CUDA_ARCHITECTURES=75 \
  -DMINK_BUILD_TESTS=ON -DMINK_BUILD_GAUSSIAN_BENCHMARKS=ON \
  -DMINK_BUILD_ML_EXPERIMENTS=ON
cmake --build /workspace/build --parallel 2
ctest --test-dir /workspace/build --output-on-failure \
  --output-junit /workspace/results/ctest.xml
sha256sum /workspace/build/{gaussian_render_bench,ml_representations} \
  /workspace/src/tests/data/test.ply > /workspace/results/hashes.txt
```

Do not time benchmarks while compilation, another GPU workload or another experiment
is active. Record host load and `nvidia-smi`; do not stop household services to create
an artificially idle host. Timers inside the executables synchronize CUDA. Results
on another compiler/GPU/LibTorch version are a new experiment, not replacement values.
If the existing image's dependencies cannot compile this source, preserve the failure
and extend `docker/Dockerfile` instead of installing a new host development stack.

## Gaussian comparisons

Run ten pairs, reversing order on alternating rounds. For the combined experiment,
all five switches change together; for a single-feature comparison, pass only that
switch and leave the other fusions at this source's defaults. The following reproduces
the combined experiment's sizes, warmups, sample counts and order:

```bash
set -euo pipefail
mkdir -p /workspace/results/all-fusions
for round in $(seq 1 10); do
  arms="0 1"; if (( round % 2 == 0 )); then arms="1 0"; fi
  for arm in $arms; do
    /workspace/build/gaussian_render_bench \
      --input /workspace/src/tests/data/test.ply --counts 0 --sizes 512,1024 \
      --devices cuda --warmup 3 --iterations 10 --train \
      --fused-projection "$arm" --fused-tiles "$arm" --fused-ssim "$arm" \
      --fused-adam "$arm" --fused-gather "$arm" \
      --label "all-fusions-train_a${arm}_r${round}" \
      --output "/workspace/results/all-fusions/train_a${arm}_r${round}.json"
  done
done
```

For Adam/gather alone use their separate output directories and only `--fused-adam`
or `--fused-gather`. Preserve source, input and executable hashes plus exit codes and
argument lists with each new run. The original receipts provide all exact arguments.
The 1024-pixel phase follows 512 within each process, so reserved allocator memory can
retain earlier work. Working-set peaks cover the whole process. Derive throughput
from synchronized median step latency; retain medians, min/max and paired counts.

## Adaptive cache-budget training

Three arms are unlimited (`-1`), 32 MiB and no retention (`0`). Use every order
permutation once, as the six original rounds did:

```bash
export CUDA_MODULE_LOADING=EAGER
export CUBLAS_WORKSPACE_CONFIG=:4096:8
mkdir -p /workspace/results/ml-budgets
budgets=(-1 32 0)
orders=('0 1 2' '2 1 0' '1 2 0' '0 2 1' '2 0 1' '1 0 2')
for index in "${!orders[@]}"; do
  round=$((index + 1))
  for arm in ${orders[$index]}; do
    /workspace/build/ml_representations --method adaptive --seed 1 --device cuda \
      --train-per-class 30 --test-per-class 20 --epochs 3 --batch 16 \
      --points 2048 --data-seed 2026 --profile-steps 0 \
      --kmap-part-reuse-mb 512 --kmap-part-device-mb "${budgets[$arm]}" \
      --fused-apply 1 --deterministic 0 \
      --output "/workspace/results/ml-budgets/adaptive_b${arm}_r${round}.json"
  done
done
```

The performance study intentionally uses nondeterministic fused apply. For a separate
numerical check, run one process per budget with `--deterministic 1` and otherwise
identical controls, retaining its warnings and output in a different directory.
This selects the ATen fallback, not fused apply; it is not a performance comparison.
`adaptive/compare-deterministic.py` records the original 163-field equality check.
Legacy `*_train` allocator peaks include per-epoch evaluation; `train_time_s` excludes
evaluation. Cache statistics at exit include inference, and retained upload charge is
not total VRAM. Three-epoch results do not establish generalization quality.

## Archived native runners and independent audits

`run-integration.ps1`, `run-gaussian-ab.ps1` and `run-ml-budgets.ps1` are the actual
Windows lab runners. They intentionally retain original absolute paths. Supporting
snapshots are under `native-helpers/`; recreate or adapt lab paths before rerunning.
`mink-env.ps1` expects the already provisioned native toolchain. These snapshots do
not instruct installation of a new native environment in place of the Docker image.
The lock helper coordinates GPU use and excludes compiles from benchmark windows.

`summarize-final.py --ml` recomputes the archived Gaussian and ML summaries using only
Python's standard library. It writes summaries beside its inputs; use a copy to keep
the published artifact and manifest immutable. Independent restart audit reports state
what was rechecked and what remains a limitation. `manifest.json` hashes every packaged
file except itself and the separately generated validation receipt.
