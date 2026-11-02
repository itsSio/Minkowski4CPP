### Interpretation of the adaptive cache comparison

The repeatable result is lower retained upload storage and lower CUDA allocator peaks.
With a 32 MiB retention budget, the epoch-loop allocated peak falls from 335.354 to
295.638 MiB (-11.84%) and reserved peak from 388 to 340 MiB (-12.37%). Disabling
retention lowers these to 252.638 MiB (-24.67%) and 292 MiB (-24.74%). Each memory
measurement is identical across the six processes within its arm. Retained upload
group charge ends at 70.279, 31.894 and 0 MiB respectively; the bounded peak is
31.998 MiB. The budget bounds cached upload groups, not active maps, temporary
allocations, in-flight consumers or total VRAM. Host working-set medians rise by
0.54% and 0.55%, so this is not a demonstrated CPU memory reduction.

Timing is less conclusive. CPU load sampled between runs is 59.5–86.2%, and a balanced
order cannot eliminate varying background load. The 32 MiB arm's total training
median falls 16.85%, but is faster in only 4/6 paired rounds. The zero-retention
median falls 11.14%, while only 2/6 paired rounds are faster. First-epoch variation
dominates these totals; they do not establish a general training speedup.

| Timing detail | Unlimited | 32 MiB | 0 MiB | Change at 32 / 0 MiB | Faster paired rounds at 32 / 0 MiB |
|---|---|---|---|---|---|
| First epoch, seconds | 4.709 | 3.795 | 3.908 | -19.41% / -17.00% | 4/6 / 2/6 |
| Mean of epochs 2–3, seconds per epoch | 0.786 | 0.807 | 0.896 | +2.63% / +13.97% | 2/6 / 2/6 |
| Batch-1 inference, milliseconds | 12.669 | 11.626 | 13.453 | -8.23% / +6.19% | 5/6 / 2/6 |
| Evaluation throughput, samples per second | 633.676 | 771.406 | 626.670 | +21.74% / -1.11% | 5/6 / 1/6 |

These are medians of the six process measurements. Warm epoch latency increases as
retention is reduced; zero retention also regresses median inference latency and
evaluation throughput. Full ranges and all convergence metrics remain in the summary
and raw files. Derived training throughput is the median of per-process
`900 / train_time_s`, not the reciprocal of median training time; the two summaries
can differ with an even number of processes. No isolated kernel timing or GPU
utilization change is inferred from these process measurements.

All arms use the same adaptive representation, geometry, architecture, parameters,
training budget, model seed and dataset seed. Default fused CUDA apply uses atomic
sums, so fixed seeds do not guarantee identical floating-point training trajectories.
Final accuracy medians are 25.25%, 28.50% and 28.00%; macro-F1 medians are 21.967%,
25.010% and 25.041%. These differences are not evidence that cache policy improves
model quality. Six repeats of one seed are not six independent training seeds, and
three epochs on synthetic shapes do not establish generalization or scene quality.

A separate correctness follow-up used one process per budget with deterministic
algorithms requested. All 163 compared numerical and categorical fields agree
exactly: epoch training losses/accuracies, test accuracies, confusion matrix,
per-class metrics, final quality metrics and geometry. All three runs finish at
29.0% accuracy, macro-F1 0.25504947752625773 and final training loss
0.6798359594847027. No warning lines were found in the captured process logs.
Deterministic mode uses the existing ATen per-slot apply path instead of fused
apply, so this confirms cache-policy equivalence for that workload and path; it is
not proof of deterministic fused kernels or identical parameters in every workload.
The request was in warn-only mode and the follow-up makes no timing claim.

Both experiments use runtime source `f3f74919a64bede57fab7d5f303e94ca188c931a`
and executable SHA256
`F66BB23A370DA9C7F4AF3BB5647C34337AE49A2BF7A093765B482280020DB35A`.
The current executable hash, integration build receipt, 18 balanced process results,
budget limits, geometry, confusion-derived metrics and epoch totals were checked
independently after restart. The three deterministic outputs and their comparison
are retained in the accompanying `ml-deterministic-check` evidence directory.
Epoch-loop allocator peaks include per-epoch evaluation, while training time
excludes evaluation. Cache statistics are sampled after final evaluation and
inference. Native runtime evidence and Docker compilation checks remain separate.
