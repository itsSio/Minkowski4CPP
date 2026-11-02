# Current-head production CI certificate

All **12 production CUDA compilation checks passed** for the four published PR
heads below. The final independent audit completed at
`2026-11-02T20:57:29.554562+00:00`.

| PR | Exact PR head | Successful production CI run | 124 job | 132 job | 134 job |
|---|---|---|---|---|---|
| [54](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/54) | `4ac4292e40fd78c4d3b81cdc3e775898737647f8` | [41517260319](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/actions/runs/41517260319) | 125523870280 | 125523870494 | 125523870782 |
| [55](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/55) | `d46eea3e23890e46da7c9b77a42a14f287620aed` | [41517409288](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/actions/runs/41517409288) | 125524371669 | 125524371283 | 125524371144 |
| [56](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/56) | `348e6b83da8bb068274ac02288f01defdbeaf5a3` | [41519874048](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/actions/runs/41519874048) | 125532822691 | 125532823032 | 125532823114 |
| [57](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/57) | `b5c4bd8ab8b0f3557f04ff1cca09feea8e95922b` | [41517408982](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/actions/runs/41517408982) | 125524369573 | 125524368838 | 125524370094 |

The actual production CMake configure output in every completed log reports:

| Inherited profile label | Actual CUDA compiler/toolkit version | Actual LibTorch version | CPU_ONLY |
|---|---|---|---|
| 124 | 12.4.131 | 2.5.1 | OFF |
| 132 | 13.2.78 | 2.15.0 | OFF |
| 134 | 13.4.92 | 2.15.0 | OFF |

These version values come from the real production CMake summary, not profile
labels, mocked builder-script tests, or versions quoted inside PR descriptions.
Each log records CUDA object compilation and completed installation. The audit
does not claim that these production image builds executed library tests or GPU
kernels. Builder-script regression tests are a separate workflow step.

GitHub checks out each PR's synthetic merge with upstream main. The logs record
these actual checked-out source identities:

| PR | Checked-out merge commit |
|---|---|
| 54 | `c615fba0848f77ceb0e4b06b24d1f7594c48871a` |
| 55 | `b18131972dcdc64853268bb5b4d6c9b6d4c0da2d` |
| 56 | `7623dbc9021bfa5a059ab9027b505d3c736bd2e6` |
| 57 | `123e989639ec149f6ace9c89e5500e0e2d8c9741` |

Every merge log explicitly includes the expected PR head and upstream base
`f4ac612d063698f587357881e910328c057b9217`. Documentation and security checks
were excluded from the twelve production build checks.

## Separate CPU runtime evidence

Internal [run41514149790](https://github.com/itsSio/Minkowski4CPP/actions/runs/41514149790)
at `aa74d97229e899adfb5ec7c8c0037d1d06d1245e` passed three repeated CPU_ONLY
source rebuilds in the same pinned existing image, each with14/14 CTest suites
and6/6 standalone ASan/UBSan adaptive split tests. Its three inherited labels
do **not** establish three CUDA runtime versions or container GPU execution.
That validation is documented separately in `docker-runtime/CPU-VALIDATION-CERTIFICATE.md`.

The current production matrix above genuinely compiles different CUDA/LibTorch
profiles, while native CUDA runtime and sanitizer results remain additional,
separate evidence. No workflow was started, cancelled, or rebuilt by this final
read-only audit.

Machine-readable outputs are `CERTIFICATE.json` and `CERTIFICATE.csv`, with all
12 job/run IDs, source identities, actual versions, and raw public-log SHA256s.
Raw logs are preserved as `pr*-job-*.log`. Reproduce the read-only check with:

```sh
python -I -B audit-final-ci.py
```

The earlier PR54 CUDA12.4 failure at its previous head remains preserved in
`docker-runtime/PR54-CUDA124-DIAGNOSIS.md`; it was the existing PR32 namespace
compatibility issue. Current-head success does not erase that history.
