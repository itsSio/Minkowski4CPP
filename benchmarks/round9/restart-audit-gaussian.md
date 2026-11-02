# Gaussian/CUDA continuation audit

Audited 2026-11-02T19:44:30.566718+01:00 by gaussian_cuda. Read-only review of source, raw evidence and current GitHub state; no new benchmark or compilation run.

Validated runtime source: `f3f74919a64bede57fab7d5f303e94ca188c931a`.

## Independent raw-data check

| Comparison | Pixels | Off median ms | On median ms | Change | Faster pairs |
|---|---|---:|---:|---:|---:|
| adam-stack | 512 | 20.80690 | 17.68460 | -15.006% | 10/10 |
| adam-stack | 1024 | 42.27260 | 37.86900 | -10.417% | 10/10 |
| gather-stack | 512 | 19.06860 | 18.36370 | -3.697% | 7/10 |
| gather-stack | 1024 | 42.09955 | 41.86375 | -0.560% | 7/10 |
| all-fusions | 512 | 56.55325 | 17.48945 | -69.074% | 10/10 |
| all-fusions | 1024 | 97.51700 | 37.73595 | -61.303% | 10/10 |

All 60 Gaussian processes, 120 image-size records, phase medians and every Gaussian metric in `metrics-final.json` were independently checked against raw JSON. Every run exited zero; paired order alternates; all-fusion flags switch together. The current benchmark binary SHA256 matches both the complete integration validation receipt and all three measurement receipts: `0db5966c8ce7a14162b6e9d80e582053fcb3136fd9f150ea9d04e29cc1cfd331`.

The summary uses medians across process medians. Raw samples are emitted with finite decimal precision; printed per-process medians agree within 0.00011 ms. Derived throughput has higher-is-better semantics; the generated `On lower` column is a literal lower-value count, not a throughput win count.

## Correctness and limitations

- Source review: fused gather uses unique renderer permutation/subset IDs; its backward scatters assignments without atomics, returns zeros for unselected rows, preserves means2d gradient routing and allocates only requested gradient groups. IDs are an internal contract. Noncontiguous input preparation and current-stream launch ordering are covered by tests. No uncovered first-order correctness flaw was found in this review.
- Six gather tests cover exact permutations/gradients, 112 finite differences, current-stream temporaries, invalid metadata, frozen-input allocation and retained render gradients. This is source/log review, not a new execution. Higher-order autograd is not claimed.
- Adam documentation correctly distinguishes the old scale-aware bound from actual ULP distance, records reciprocal-only rejection, and limits bit-identity to measured LibTorch 2.15/CUDA13.4/SM75. Five tests and eight trainer steps are not evidence of long-run independent-dataset convergence.
- The report preserves the failed filtered Adam initcheck and known LibTorch indexing-backward exclusions. These restrictions must remain visible.
- Training CUDA peaks are reset before model clone/trainer construction and sampled after the training loop. Forward/backward fields are sampled earlier; 1024 reserved allocation can retain 512 training cache. Process working set is cumulative. These are allocator/process metrics, not whole-device VRAM or kernel-only measurements.
- Host contention is severe. Gather 1024 training is inconclusive (-0.56%, 7/10); its render forward/backward median regresses +0.76% and backward allocation +0.31%. Adam 1024 training reserved allocation increases +2.20%. All-fusions comparison is against switches disabled in the combined binary, not original upstream. No cross-block absolute timing comparisons are justified.

## Live PR and Docker check

- PR51 remains open at `2f947caf3edc9401562d4e7558253b813e0cdc38`. Docker 12.4/13.2/13.4 checks are successful, matching the stored receipt. [Technical summary](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/51#issuecomment-6584483800); [Docker follow-up](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/51#issuecomment-6584897200).
  Stacked follow-up comments presently found: 0.
- PR53 remains open at `229f04dfd678b999dbe711a947a4b3b3ea608d1f`. Docker 12.4/13.2/13.4 checks are successful, matching the stored receipt. [Technical summary](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/53#issuecomment-6584555848); [Docker follow-up](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/53#issuecomment-6585041280).
  Stacked follow-up comments presently found: 0.

Docker results are compilation/builder checks only. Native runtime acceptance is separate; the absent local Docker/GPU container execution remains a disclosed resource limitation. No existing implementation/CI update is missing; only the planned combined-stack follow-ups await root publication.

## Publication helper review

`publish-stacked.py` was reviewed without executing it. It verifies successful CPU/CUDA integration and measurement receipts, matching runtime hashes and executable hash, remote availability of the artifact commit, the expected PR head, and an unchanged PR body before append. It saves the old body, appends rather than replacing historic findings, and uses a stable source/tag marker in both body and comment to prevent ordinary duplicate publication. It cannot merge or modify source.

Current comments are well below the helper's first-page limit (100); no pagination risk for this publication. After posting, root should read back both body and comment, and verify linked raw/report paths exist in the published commit. The helper checks remote commit existence but does not itself verify those tree paths or CAS-guard the remote body write. With root as sole publisher and prior CI publishers finished, those are manageable verification requirements rather than a blocker.

No new Gaussian optimization is justified without a new isolated profile; the final combined evidence already reaches the documented diminishing-return boundary on this shared host.
