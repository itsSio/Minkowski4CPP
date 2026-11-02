# Docker testing recovery after session restart

The earlier `candidate-state.json` chose Documentation run `41511099983` by
creation order. Its success is not library validation. Its extraction failed,
as expected for documentation jobs without runtime evidence.

The genuine existing CI run is:
https://github.com/itsSio/Minkowski4CPP/actions/runs/41511100024

Source head `e7b0810de398ce5a7f25815789c139f0362b07de`; jobs
`125502834676` (134), `125502835143` (124), `125502835152` (132). All three
labels rebuild the same pinned existing CUDA-enabled image in CPU_ONLY mode;
they do not establish three-version CUDA runtime compatibility or GPU execution.
The correct durable monitor PID is `32672`, logs `ci-monitor.stdout.log` and
`ci-monitor.stderr.log`, output directory `run-41511100024`. The monitor now
rejects workflows whose name is not `CI`.

That run was already active and was neither restarted nor cancelled. At recovery
inspection its Docker jobs were still compiling; no pass is claimed yet.

Prepared follow-up source in the same worktree, now pushed at root's request:

- `144921f`: portable RSS and its standalone memory regression, original `2ceceea`.
- `cfe48d7`: Gaussian parallel atomics, original runtime `b96db27`, plus its direct
  benchmark source; conflicting Gaussian test lists preserve all existing suites.
- `1c9ac2a`: include the direct benchmark CMake target and require the new standalone
  memory target/suite in the container profile. Evidence guard tests pass 10/10.
- `a4c2f31`: freeze the canonical source manifest for this combined candidate.

Final combined CI run:
https://github.com/itsSio/Minkowski4CPP/actions/runs/41512323659

Exact remote head `a4c2f3132c2f34d4f411a15328a4f2dd35c47564`; canonical
manifest freezes `1c9ac2a8704c40b6e608e8cd2833e40c9cc2647f`, 471 source files.
This is the CI workflow, selected explicitly by workflow name and exact source
head. Documentation run `41512323687` is separate and supplies no test evidence.
Durable final-CI monitor PID `27420`, logs `final-ci-monitor.*`, output directory
`run-41512323659`. Existing run `41511100024` remains untouched.

The new known source profile requires exactly 14 named CTest suites and the
standalone GCC ASan/UBSan adaptive split test. No host development environment
was installed. Native CUDA validation is separate from this CPU container path.

The first combined runtime run `41511100024` has now completed. All three jobs
successfully rebuilt the library and passed all 13 CTest suites. Its overall CI
result is still failure: the extra standalone sanitizer build used C++17, while
`AdaptiveVoxelKey` requires C++20 defaulted equality. All checksummed bundles are
preserved under `run-41511100024`; `independent-stage-audit.json` verifies every
job's stage exits and 13-suite JUnit result. Representative suite counts: adaptive
175 passed/21 CUDA-only skipped; split 6/0 skipped; Gaussian 78 passed/11 skipped;
core 37 passed/15 skipped; point dataset 22 passed; summary Python20 passed;
preprocessing Python5 passed; memory6 passed/6 skipped.

Final candidate `a4c2f31` run `41512323659` contains that same harness-standard
error and may likewise pass its 14 real suites before failing the extra sanitizer
compile. Do not treat its eventual overall failure as proof that CTest failed.

The corrected combined run is:
https://github.com/itsSio/Minkowski4CPP/actions/runs/41514149790

Exact head `aa74d97229e899adfb5ec7c8c0037d1d06d1245e`. Only the runtime harness
and its regression checks changed; all 471 canonical runtime/test source identities
remain frozen as before. The standalone ASan/UBSan test now compiles with C++20
and runs before LibTorch compilation, giving quick feedback. Evidence guards pass
11/11. Durable corrected monitor PID `17040`, logs `corrected-ci-monitor.*`, output
directory `run-41514149790`. Prior runs and monitors are untouched.

The original baseline run `41507998304` failed before any CTest execution because
both legacy coordinate_manager.cpp and unified coordinate_manager.cu defined the
same CPU symbols. Its checksummed failure bundles remain preserved. The isolated
fix is `67c73d3` (cherry-picked into integration by root).
