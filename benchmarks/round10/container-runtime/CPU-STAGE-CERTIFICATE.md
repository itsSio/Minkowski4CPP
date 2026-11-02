# Combined-source CPU runtime stage certificate

Independent audit passed for all three decoded jobs in
[CI run 41512323659](https://github.com/itsSio/Minkowski4CPP/actions/runs/41512323659).
All rebuilt-library and CTest stages passed. **Overall CI failed** afterward:
the standalone sanitizer command requested C++17 while the project requires C++20.
No sanitizer success is claimed from this run.

| Job / inherited label | Library build | Exact named CTest suites | Linux RSS before → 64 MiB touched → freed (MiB) | Overall CI |
|---|---|---|---|---|
| 125507027448 / 132 | passed | 14 passed, 0 failed | 2.87109 → 66.8711 → 66.8711 | failed: sanitizer compiler flag |
| 125507027883 / 124 | passed | 14 passed, 0 failed | 2.89062 → 66.8906 → 66.8906 | failed: sanitizer compiler flag |
| 125507027928 / 134 | passed | 14 passed, 0 failed | 2.77734 → 66.9023 → 66.9023 | failed: sanitizer compiler flag |

The labels execute the **same pinned existing image** in CPU_ONLY mode. They
are repeated validations, not CUDA-version runtime coverage. No GPU execution
or GPU memory measurements occurred in these container jobs.

## Independently checked evidence

- All 36 decoded evidence-file hashes (12 per job) match their checksummed
  manifests; each complete compressed bundle was previously checksummed by the
  extractor. These are integrity checks, not a cryptographic publisher signature.
- All 471 source paths and SHA256 values match canonical Git blobs at
  `1c9ac2a8704c40b6e608e8cd2833e40c9cc2647f`, independently recomputed with
  `git cat-file --batch`. Every job uses the same source manifest.
- Exact head for the run:
  `a4c2f3132c2f34d4f411a15328a4f2dd35c47564`.
- CTest discovery and JUnit agree on all 14 named suites, with no failed or
  skipped CTest wrappers. CUDA-only cases inside CPU suites remain explicitly
  skipped by the test framework.
- CMake linkage evidence points every library consumer at the newly rebuilt
  `/opt/minkowski-runtime/build/libminkowski_cpp.a`; no installed Minkowski
  archive is linked. Compile commands contain exactly one coordinate manager:
  `coordinate_manager.cu` with CPU_ONLY; legacy `.cpp` is excluded.
- All 11 built target identities have nonempty recorded pre-test hashes and
  sizes. The failed sanitizer stage prevented the harness's final post-test
  binary/source hash recheck, so these failed runs do not establish that final
  check. The corrected run retains it.
- Actual Linux memory regression output measures a 64.0–64.125 MiB high-water
  increase from touching 64 MiB; freeing it does not reduce the lifetime peak.
  The helper converts Linux `getrusage(RUSAGE_SELF).ru_maxrss` KiB to MiB by
  dividing by 1024. This is a lifetime RSS measurement, not per-phase memory.

Machine-readable outputs:

- `run-41512323659/independent-stage-certificate.json`
- `run-41512323659/runtime-stage-certificate.csv`
- Raw commands, outputs, JUnit, source/compile/linkage manifests and receipts are
  preserved in the three `run-41512323659/job-*` directories.
- Reproduce the independent audit:
  `python -I -B audit-runtime-stages.py` from this lab directory.

## Recorded environment and reproduction

| Field | Recorded value |
|---|---|
| Platform | Linux-7.0.0-1017-azure-x86_64-with-glibc2.39 |
| Logical processors | 4 (`os.cpu_count`) |
| Memory | MemTotal 16,367,524 KiB from `/proc/meminfo` |
| CPU model | not recorded; not inferred |
| C++ compiler | Ubuntu GCC 13.3.0 (`13.3.0-6ubuntu2~24.04.1`) |
| CMake | 4.2.3 |
| LibTorch | 2.15.0+cu134 |
| Dependency toolkit | CUDA 13.4.92; no GPU runtime execution |
| Existing image | `acaicia/minkowski4cpp@sha256:a4bf4c4e91ef5f4e50089f435005ca07f1a0a48deeeb9814ca4b526974de79ba` |

For the failed-harness history, check out exact run head `a4c2f31` and run:

```sh
docker build --progress=plain --build-arg CUDA_VERSION=134 --build-arg JOBS=2 \
  -f docker/Dockerfile -t minkowski-runtime:a4c2f31 .
```

That command is expected to pass 14 suites then fail the standalone C++17
sanitizer build. For the corrected harness, check out `aa74d97` and use the
same command with tag `minkowski-runtime:aa74d97`. It runs standalone ASan/UBSan
first with C++20, then rebuilds and tests the same canonical library source.
The corrected CI run is
[41514149790](https://github.com/itsSio/Minkowski4CPP/actions/runs/41514149790),
still pending at this certificate's creation. Its outcome must be reported
separately when available.
