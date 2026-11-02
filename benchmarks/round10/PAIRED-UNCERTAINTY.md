# Exploratory paired-trial uncertainty

Exploratory analysis of existing trials, not an additional timed benchmark.
Bootstrap resamples whole A/B pairs with replacement (20,000 draws, deterministic
seeds) and uses percentile intervals for median(B)/median(A)-1. Small cohorts,
fixed alternating order and nonstationary background load limit interpretation.
Bootstrap blocks are assumed approximately independent/representative; serial
load can violate that assumption. The sign test targets paired win probability
0.5, not the ratio of marginal medians used by the bootstrap interval.
The exact sign calculation discards ties and assumes independent exchangeable
signs under the null. P values are unadjusted across multiple workloads/metrics;
none is a confirmatory claim. Original reported point estimates and raw evidence
remain unchanged. Intervals/p values do not establish real-training benefit or
universal superiority.

| Workload | Pairs | Lower | Median change% | Paired bootstrap95% | Unadjusted sign p |
|---|---:|---:|---:|---:|---:|
| adaptive/cpu/center/kmap_batch_first_epoch_ms | 6 | 6 | -7.37 | [-12.19, -2.94] | 0.03125 |
| adaptive/cpu/center/kmap_batch_later_epochs_ms | 6 | 6 | -19.16 | [-41.82, -8.02] | 0.03125 |
| adaptive/cpu/volume/kmap_batch_first_epoch_ms | 6 | 4 | -2.05 | [-15.43, +13.70] | 0.68750 |
| adaptive/cpu/volume/kmap_batch_later_epochs_ms | 6 | 5 | -11.84 | [-26.33, +3.86] | 0.21875 |
| adaptive/cuda/center/kmap_batch_first_epoch_ms | 6 | 4 | +1.45 | [-21.60, +23.76] | 0.68750 |
| adaptive/cuda/center/kmap_batch_later_epochs_ms | 6 | 6 | -10.93 | [-15.85, -9.16] | 0.03125 |
| adaptive/cuda/volume/kmap_batch_first_epoch_ms | 6 | 3 | +0.58 | [-28.58, +18.87] | 1.00000 |
| adaptive/cuda/volume/kmap_batch_later_epochs_ms | 6 | 5 | -9.68 | [-21.03, +12.18] | 0.21875 |
| gaussian/1024/backward_median_ms | 10 | 7 | -0.77 | [-5.16, +3.07] | 0.34375 |
| gaussian/1024/train_median_ms | 10 | 6 | +0.76 | [-4.94, +4.03] | 0.75391 |
| gaussian/512/backward_median_ms | 10 | 5 | -2.11 | [-7.49, +4.99] | 1.00000 |
| gaussian/512/train_median_ms | 10 | 6 | -0.07 | [-3.59, +4.09] | 0.75391 |
| gaussian/dense/gpu_ms | 10 | 8 | -3.18 | [-6.51, +0.19] | 0.10938 |
| gaussian/row-groups/gpu_ms | 10 | 10 | -29.27 | [-30.74, -26.56] | 0.00195 |
| gaussian/sparse/gpu_ms | 10 | 9 | -10.99 | [-17.39, -7.00] | 0.02148 |
