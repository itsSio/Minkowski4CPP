# adam-stack: same-binary paired comparison

Source `f3f74919a64bede57fab7d5f303e94ca188c931a`; executable SHA256 `0DB5966C8CE7A14162B6E9D80E582053FCB3136FD9F150EA9D04E29CC1CFD331`.

10 balanced rounds; median [minimum, maximum] of per-process medians. Training throughput is derived from synchronized step latency. Byte metrics are converted to MiB. Peak allocated/reserved measurements are allocator statistics, not whole-device usage. Process working set covers the entire process. Host contention remains a limitation.

| Pixels | Metric | Toggle off | Toggle on | Change | On lower |
|---|---|---|---|---|---|
| 512 | backward_median_ms | 14.280 [13.751, 15.076] | 14.199 [13.244, 14.860] | -0.57% | 6/10 |
| 512 | cuda_peak_allocated_backward | 196.524 [196.524, 196.524] | 196.524 [196.524, 196.524] | +0.00% | 0/10 |
| 512 | cuda_peak_allocated_forward | 100.148 [100.148, 100.148] | 100.148 [100.148, 100.148] | +0.00% | 0/10 |
| 512 | cuda_peak_allocated_train | 230.368 [230.368, 230.368] | 218.286 [218.286, 218.286] | -5.24% | 10/10 |
| 512 | cuda_peak_reserved | 244.000 [244.000, 244.000] | 244.000 [244.000, 244.000] | +0.00% | 0/10 |
| 512 | cuda_peak_reserved_train | 292.000 [292.000, 292.000] | 268.000 [268.000, 268.000] | -8.22% | 10/10 |
| 512 | forward_backward_median_ms | 24.422 [22.886, 25.656] | 24.238 [22.775, 25.210] | -0.75% | 8/10 |
| 512 | forward_median_ms | 9.945 [9.422, 10.616] | 9.701 [8.425, 10.274] | -2.45% | 8/10 |
| 512 | process_peak_working_set | 904.736 [904.352, 905.102] | 875.906 [875.551, 876.176] | -3.19% | 10/10 |
| 512 | train_median_ms | 20.807 [19.470, 22.343] | 17.685 [16.561, 18.254] | -15.01% | 10/10 |
| 512 | training_steps_per_second_derived | 48.061 [44.758, 51.360] | 56.550 [54.783, 60.381] | +17.66% | 0/10 |
| 1024 | backward_median_ms | 27.088 [25.311, 28.736] | 26.468 [24.871, 27.765] | -2.29% | 9/10 |
| 1024 | cuda_peak_allocated_backward | 232.865 [232.865, 232.865] | 233.076 [233.076, 233.076] | +0.09% | 0/10 |
| 1024 | cuda_peak_allocated_forward | 129.722 [129.722, 129.722] | 129.722 [129.722, 129.722] | +0.00% | 0/10 |
| 1024 | cuda_peak_allocated_train | 313.015 [313.015, 313.015] | 313.527 [313.527, 313.527] | +0.16% | 0/10 |
| 1024 | cuda_peak_reserved | 292.000 [292.000, 292.000] | 288.000 [288.000, 288.000] | -1.37% | 10/10 |
| 1024 | cuda_peak_reserved_train | 364.000 [364.000, 364.000] | 372.000 [372.000, 372.000] | +2.20% | 0/10 |
| 1024 | forward_backward_median_ms | 41.525 [38.356, 43.722] | 40.251 [37.742, 42.885] | -3.07% | 8/10 |
| 1024 | forward_median_ms | 13.024 [12.344, 14.428] | 12.385 [11.308, 13.683] | -4.91% | 8/10 |
| 1024 | process_peak_working_set | 915.922 [915.477, 916.320] | 887.125 [886.758, 887.395] | -3.14% | 10/10 |
| 1024 | train_median_ms | 42.273 [38.653, 44.106] | 37.869 [35.609, 40.557] | -10.42% | 10/10 |
| 1024 | training_steps_per_second_derived | 23.657 [22.673, 25.871] | 26.410 [24.657, 28.083] | +11.64% | 0/10 |

Lower is better for latency and memory; higher is better for derived throughput. Unchanged render-only paths in this optimizer/loss toggle are noise controls. Only `cuda_peak_*_train` fields cover the training phase; older forward/backward fields do not. Sizes run in order within each process, so 1024-pixel allocator reservations may retain prior 512-pixel training state. Process peak working set is cumulative, not an isolated per-size allocation.
