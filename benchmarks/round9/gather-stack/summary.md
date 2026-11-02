# gather-stack: same-binary paired comparison

Source `f3f74919a64bede57fab7d5f303e94ca188c931a`; executable SHA256 `0DB5966C8CE7A14162B6E9D80E582053FCB3136FD9F150EA9D04E29CC1CFD331`.

10 balanced rounds; median [minimum, maximum] of per-process medians. Training throughput is derived from synchronized step latency. Byte metrics are converted to MiB. Peak allocated/reserved measurements are allocator statistics, not whole-device usage. Process working set covers the entire process. Host contention remains a limitation.

| Pixels | Metric | Toggle off | Toggle on | Change | On lower |
|---|---|---|---|---|---|
| 512 | backward_median_ms | 15.344 [14.726, 16.191] | 15.349 [14.154, 15.910] | +0.03% | 6/10 |
| 512 | cuda_peak_allocated_backward | 195.184 [195.184, 195.184] | 196.524 [196.524, 196.524] | +0.69% | 0/10 |
| 512 | cuda_peak_allocated_forward | 100.148 [100.148, 100.148] | 100.148 [100.148, 100.148] | +0.00% | 0/10 |
| 512 | cuda_peak_allocated_train | 218.596 [218.596, 218.596] | 218.286 [218.286, 218.286] | -0.14% | 10/10 |
| 512 | cuda_peak_reserved | 244.000 [244.000, 244.000] | 244.000 [244.000, 244.000] | +0.00% | 0/10 |
| 512 | cuda_peak_reserved_train | 268.000 [268.000, 268.000] | 268.000 [268.000, 268.000] | +0.00% | 0/10 |
| 512 | forward_backward_median_ms | 27.241 [24.896, 30.247] | 26.012 [23.524, 29.686] | -4.51% | 7/10 |
| 512 | forward_median_ms | 10.218 [9.079, 10.855] | 10.233 [9.276, 10.946] | +0.15% | 6/10 |
| 512 | process_peak_working_set | 875.723 [875.453, 875.953] | 875.855 [875.703, 876.070] | +0.02% | 1/10 |
| 512 | train_median_ms | 19.069 [17.813, 20.066] | 18.364 [16.581, 20.736] | -3.70% | 7/10 |
| 512 | training_steps_per_second_derived | 52.442 [49.837, 56.139] | 54.459 [48.226, 60.309] | +3.84% | 3/10 |
| 1024 | backward_median_ms | 29.443 [25.714, 31.166] | 29.212 [26.157, 32.289] | -0.79% | 5/10 |
| 1024 | cuda_peak_allocated_backward | 232.357 [232.357, 232.357] | 233.076 [233.076, 233.076] | +0.31% | 0/10 |
| 1024 | cuda_peak_allocated_forward | 129.722 [129.722, 129.722] | 129.722 [129.722, 129.722] | +0.00% | 0/10 |
| 1024 | cuda_peak_allocated_train | 312.863 [312.863, 312.863] | 313.527 [313.527, 313.527] | +0.21% | 0/10 |
| 1024 | cuda_peak_reserved | 288.000 [288.000, 288.000] | 288.000 [288.000, 288.000] | +0.00% | 0/10 |
| 1024 | cuda_peak_reserved_train | 396.000 [396.000, 396.000] | 372.000 [372.000, 372.000] | -6.06% | 10/10 |
| 1024 | forward_backward_median_ms | 45.158 [38.422, 50.361] | 45.501 [39.037, 48.501] | +0.76% | 5/10 |
| 1024 | forward_median_ms | 14.018 [11.882, 16.866] | 13.970 [11.940, 18.032] | -0.34% | 4/10 |
| 1024 | process_peak_working_set | 886.941 [886.672, 887.172] | 887.074 [886.922, 887.289] | +0.01% | 1/10 |
| 1024 | train_median_ms | 42.100 [38.087, 45.553] | 41.864 [37.178, 44.127] | -0.56% | 7/10 |
| 1024 | training_steps_per_second_derived | 23.759 [21.952, 26.256] | 23.889 [22.662, 26.898] | +0.55% | 3/10 |

Lower is better for latency and memory; higher is better for derived throughput. Only `cuda_peak_*_train` fields cover the training phase; older forward/backward fields do not. Sizes run in order within each process, so 1024-pixel allocator reservations may retain prior 512-pixel training state. Process peak working set is cumulative, not an isolated per-size allocation.
