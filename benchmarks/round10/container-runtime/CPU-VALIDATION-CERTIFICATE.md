# Combined-source Docker CPU validation passed

[CI run 41514149790](https://github.com/itsSio/Minkowski4CPP/actions/runs/41514149790)
passed all three jobs at exact source head
`aa74d97229e899adfb5ec7c8c0037d1d06d1245e`. Each job rebuilt the modified library,
passed all **14 named CTest suites**, and passed **6 standalone adaptive split
tests under GCC ASan/UBSan**, with no sanitizer diagnostic. No dependency setup
was performed: all jobs reused the existing pinned image.

| Job / inherited label | Library rebuild | CTest | ASan/UBSan split | Linux RSS before → 64 MiB touched → freed (MiB) |
|---|---|---|---|---|
| 125513256214 / 134 | passed | 14/14 | 6/6 | 2.9375 → 66.9375 → 66.9375 |
| 125513256481 / 124 | passed | 14/14 | 6/6 | 3.04688 → 67.0469 → 67.0469 |
| 125513256771 / 132 | passed | 14/14 | 6/6 | 3.04688 → 67.0469 → 67.0469 |

These labels repeat the **same pinned image in CPU_ONLY mode**. They do not
establish CUDA 12.4/13.2/13.4 runtime compatibility or any GPU execution.
Native CUDA measurements and sanitizer receipts remain separate evidence.

## Source and execution identity

The independent audit `audit-runtime-stages.py --run 41514149790 --require-passed`
completed successfully. It independently recomputed all **471 canonical Git blob
hashes** frozen at `1c9ac2a8704c40b6e608e8cd2833e40c9cc2647f`, verified all
**39 decoded evidence-file hashes**, and checked exact JUnit/discovered suite
coverage. The runner verified source hashes before and after execution and
recorded binary hashes before execution, then checked those hashes again after
all tests.

CMake linkage records identify the newly built
`/opt/minkowski-runtime/build/libminkowski_cpp.a` for every library consumer;
the installed image archive is excluded. Compile commands contain only the
canonical CPU_ONLY `coordinate_manager.cu`, excluding the duplicate legacy
`.cpp`. The source includes adaptive runtime `95093e2`, Gaussian runtime
`b96db27`, ModelNet `0e5c4fe`, summary identity guards `7460c7e`, Linux RSS
helper `2ceceea`, and CPU link fix `67c73d3`. The Gaussian CUDA kernel is not
executed by this CPU_ONLY path.

The actual Linux RSS regression confirms a roughly 64 MiB peak increase after
touching 64 MiB, with no decrease after freeing it. Linux `ru_maxrss` is in KiB;
the helper divides by 1024 to report MiB. This is lifetime high-water RSS, not
an isolated training/inference allocation measurement. Darwin conversion remains
unexecuted in this Linux validation.

## Recorded environment

- Existing image:
  `acaicia/minkowski4cpp@sha256:a4bf4c4e91ef5f4e50089f435005ca07f1a0a48deeeb9814ca4b526974de79ba`.
- Linux 7.0.0-1017-azure, x86_64, glibc2.39; 4 logical processors reported by
  `os.cpu_count`; MemTotal 16,367,520–16,367,524 KiB. CPU model was not recorded
  and is not inferred.
- Ubuntu GCC 13.3.0 (`13.3.0-6ubuntu2~24.04.1`), CMake4.2.3,
  LibTorch2.15.0+cu134; dependency toolkit CUDA13.4.92. No GPU runtime execution.
- Library rebuild elapsed 871.25/921.75/871.96 seconds; CTest elapsed
  57.36/58.78/57.17 seconds. These are validation wall times, not performance
  comparisons or benchmark claims.

## Reproduction and historical failures

From a checkout at `aa74d97`:

```sh
docker build --progress=plain --build-arg CUDA_VERSION=134 --build-arg JOBS=2 \
  -f docker/Dockerfile -t minkowski-runtime:aa74d97 .
```

The build uses the pinned existing image, verifies canonical source inputs,
runs the standalone sanitized split test with C++20, rebuilds the library, and
executes all 14 CTest suites serially. The full raw bundle appears in its build
logs and can be decoded with `tests/container_runtime/extract_evidence.py`.

Machine-readable certificate and CSV:

- `run-41514149790/independent-stage-certificate.json`
- `run-41514149790/runtime-stage-certificate.csv`

The earlier runs remain preserved. `41507998304` failed at duplicate CPU manager
linking; `41511100024` rebuilt and passed13 suites before a C++17 sanitizer
harness error; `41512323659` rebuilt and passed14 suites before the same harness
error. Their overall CI status remains failure. The corrected successful run
closes that sanitizer gate without changing the frozen library source.
