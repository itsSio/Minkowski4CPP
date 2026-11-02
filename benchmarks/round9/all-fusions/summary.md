# all-fusions: same-binary paired comparison

Source `f3f74919a64bede57fab7d5f303e94ca188c931a`; executable SHA256 `0DB5966C8CE7A14162B6E9D80E582053FCB3136FD9F150EA9D04E29CC1CFD331`.

10 balanced rounds; median [minimum, maximum] of per-process medians. Training throughput is derived from synchronized step latency. Byte metrics are converted to MiB. Peak allocated/reserved measurements are allocator statistics, not whole-device usage. Process working set covers the entire process. Host contention remains a limitation.

| Pixels | Metric | Toggle off | Toggle on | Change | On lower |
|---|---|---|---|---|---|
| 512 | backward_median_ms | 31.724 [30.297, 32.741] | 14.226 [13.375, 14.874] | -55.16% | 10/10 |
| 512 | cuda_peak_allocated_backward | 220.236 [220.236, 220.236] | 196.524 [196.524, 196.524] | -10.77% | 10/10 |
| 512 | cuda_peak_allocated_forward | 113.627 [113.627, 113.627] | 100.148 [100.148, 100.148] | -11.86% | 10/10 |
| 512 | cuda_peak_allocated_train | 295.282 [295.282, 295.282] | 218.286 [218.286, 218.286] | -26.08% | 10/10 |
| 512 | cuda_peak_reserved | 294.000 [294.000, 294.000] | 244.000 [244.000, 244.000] | -17.01% | 10/10 |
| 512 | cuda_peak_reserved_train | 338.000 [338.000, 338.000] | 268.000 [268.000, 268.000] | -20.71% | 10/10 |
| 512 | forward_backward_median_ms | 54.231 [50.746, 64.273] | 24.898 [23.184, 46.044] | -54.09% | 10/10 |
| 512 | forward_median_ms | 20.137 [18.607, 21.641] | 9.689 [8.479, 10.206] | -51.89% | 10/10 |
| 512 | process_peak_working_set | 1223.037 [1222.672, 1223.281] | 875.912 [875.516, 876.203] | -28.38% | 10/10 |
| 512 | train_median_ms | 56.553 [54.814, 59.053] | 17.489 [16.899, 19.171] | -69.07% | 10/10 |
| 512 | training_steps_per_second_derived | 17.682 [16.934, 18.244] | 57.178 [52.163, 59.175] | +223.36% | 0/10 |
| 1024 | backward_median_ms | 44.135 [42.160, 45.960] | 26.694 [25.534, 28.067] | -39.52% | 10/10 |
| 1024 | cuda_peak_allocated_backward | 313.180 [313.180, 313.180] | 233.076 [233.076, 233.076] | -25.58% | 10/10 |
| 1024 | cuda_peak_allocated_forward | 208.243 [208.243, 208.243] | 129.722 [129.722, 129.722] | -37.71% | 10/10 |
| 1024 | cuda_peak_allocated_train | 569.003 [569.003, 569.003] | 313.527 [313.527, 313.527] | -44.90% | 10/10 |
| 1024 | cuda_peak_reserved | 378.000 [378.000, 378.000] | 288.000 [288.000, 288.000] | -23.81% | 10/10 |
| 1024 | cuda_peak_reserved_train | 662.000 [662.000, 662.000] | 372.000 [372.000, 372.000] | -43.81% | 10/10 |
| 1024 | forward_backward_median_ms | 73.112 [69.989, 78.858] | 40.332 [38.316, 43.400] | -44.83% | 10/10 |
| 1024 | forward_median_ms | 26.561 [24.287, 31.534] | 12.535 [11.947, 13.495] | -52.81% | 10/10 |
| 1024 | process_peak_working_set | 1234.127 [1233.762, 1234.371] | 887.131 [886.734, 887.426] | -28.12% | 10/10 |
| 1024 | train_median_ms | 97.517 [91.168, 100.371] | 37.736 [36.634, 48.305] | -61.30% | 10/10 |
| 1024 | training_steps_per_second_derived | 10.255 [9.963, 10.969] | 26.500 [20.702, 27.297] | +158.41% | 0/10 |

Lower is better for latency and memory; higher is better for derived throughput. Only `cuda_peak_*_train` fields cover the training phase; older forward/backward fields do not. Sizes run in order within each process, so 1024-pixel allocator reservations may retain prior 512-pixel training state. Process peak working set is cumulative, not an isolated per-size allocation.
