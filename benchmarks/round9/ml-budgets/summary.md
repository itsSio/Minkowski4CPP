# Adaptive training with device cache budgets

Source `f3f74919a64bede57fab7d5f303e94ca188c931a`; executable SHA256 `F66BB23A370DA9C7F4AF3BB5647C34337AE49A2BF7A093765B482280020DB35A`.

Six balanced order permutations, fixed seed1 and dataset seed2026; these are repeat measurements of one training seed, not independent accuracy trials. Three epochs, 300 training and 200 test samples, 2048 points/sample, batch16, 512MiB host part cache. Median [minimum, maximum]. Deterministic mode is off to exercise the default fused CUDA apply path, which deterministic mode bypasses. Seeds are fixed, but atomic summation may vary.

| Metric | Unlimited | 32 MiB | 0 MiB | 32 MiB change | 0 MiB change |
|---|---|---|---|---|---|
| accuracy (%) | 25.250 [24.500, 29.000] | 28.500 [25.000, 30.500] | 28.000 [27.000, 29.500] | +3.25 pp | +2.75 pp |
| macro_precision (%) | 33.482 [23.844, 44.869] | 44.219 [33.989, 49.045] | 46.345 [35.021, 47.302] | +10.74 pp | +12.86 pp |
| macro_recall (%) | 25.250 [24.500, 29.000] | 28.500 [25.000, 30.500] | 28.000 [27.000, 29.500] | +3.25 pp | +2.75 pp |
| macro_f1 (%) | 21.967 [20.504, 26.086] | 25.010 [21.439, 28.566] | 25.041 [23.721, 27.554] | +3.04 pp | +3.07 pp |
| train_time_s | 6.476 [4.076, 13.218] | 5.385 [5.142, 7.415] | 5.754 [4.930, 12.663] | -16.85% | -11.14% |
| train_samples_per_s_derived | 140.887 [68.087, 220.820] | 167.135 [121.369, 175.029] | 157.423 [71.071, 182.561] | +18.63% | +11.74% |
| inference_latency_ms_median_b1 | 12.669 [11.019, 13.991] | 11.626 [10.499, 13.149] | 13.453 [11.632, 16.640] | -8.23% | +6.19% |
| throughput_samples_per_s | 633.676 [520.294, 786.980] | 771.406 [494.005, 885.401] | 626.670 [466.508, 720.618] | +21.74% | -1.11% |
| peak_cuda_alloc_mb_train | 335.354 [335.354, 335.354] | 295.638 [295.638, 295.638] | 252.638 [252.638, 252.638] | -11.84% | -24.67% |
| peak_cuda_reserved_mb_train | 388.000 [388.000, 388.000] | 340.000 [340.000, 340.000] | 292.000 [292.000, 292.000] | -12.37% | -24.74% |
| peak_rss_mb | 4440.322 [4393.258, 4467.535] | 4464.453 [4122.043, 4469.367] | 4464.580 [4310.141, 4469.152] | +0.54% | +0.55% |
| kmap_part_device_bytes (MiB) | 70.279 [70.279, 70.279] | 31.894 [31.894, 31.894] | 0.000 [0.000, 0.000] | -54.62% | -100.00% |
| kmap_part_device_peak_bytes (MiB) | 70.279 [70.279, 70.279] | 31.998 [31.998, 31.998] | 0.000 [0.000, 0.000] | -54.47% | -100.00% |
| kmap_part_device_hits | 3086.000 [3086.000, 3086.000] | 1154.000 [1154.000, 1154.000] | 0.000 [0.000, 0.000] | -62.61% | -100.00% |
| kmap_part_device_misses | 1944.000 [1944.000, 1944.000] | 3876.000 [3876.000, 3876.000] | 5030.000 [5030.000, 5030.000] | +99.38% | +158.74% |
| kmap_part_device_groups | 128.000 [128.000, 128.000] | 61.000 [61.000, 61.000] | 0.000 [0.000, 0.000] | -52.34% | -100.00% |
| active_elements_mean | 839.597 [839.597, 839.597] | 839.597 [839.597, 839.597] | 839.597 [839.597, 839.597] | +0.00% | +0.00% |

Cache statistics are sampled at experiment end, including evaluation and single-item inference. They are conservative retained-upload accounting, not total model/device memory. Training allocator peaks and whole-process working set are measured separately. Legacy *_train allocator peaks cover the epoch loop including per-epoch evaluation; train_time_s excludes evaluation. No inference about multi-seed generalization is justified.

| Epoch | Budget | Loss | Training accuracy (%) | Test accuracy (%) | Epoch seconds |
|---|---|---|---|---|---|
| 1 | -1.0 | 2.312 [2.311, 2.313] | 19.167 [19.000, 19.333] | 26.500 [26.500, 27.000] | 4.709 [2.643, 11.410] |
| 1 | 32.0 | 2.313 [2.311, 2.313] | 19.000 [19.000, 19.333] | 26.500 [26.500, 27.000] | 3.795 [3.442, 5.568] |
| 1 | 0.0 | 2.313 [2.311, 2.313] | 19.000 [19.000, 19.333] | 27.000 [26.000, 27.000] | 3.908 [3.354, 10.321] |
| 2 | -1.0 | 1.434 [1.432, 1.444] | 47.167 [46.667, 48.000] | 34.500 [30.000, 36.500] | 0.832 [0.732, 1.129] |
| 2 | 32.0 | 1.434 [1.429, 1.435] | 46.833 [46.333, 48.667] | 34.500 [33.000, 37.000] | 0.832 [0.791, 1.017] |
| 2 | 0.0 | 1.434 [1.428, 1.437] | 47.000 [46.667, 48.667] | 34.250 [33.000, 35.500] | 0.918 [0.776, 1.284] |
| 3 | -1.0 | 0.682 [0.676, 0.690] | 94.000 [93.333, 94.667] | 25.250 [24.500, 29.000] | 0.749 [0.684, 0.909] |
| 3 | 32.0 | 0.677 [0.674, 0.682] | 93.667 [93.000, 94.000] | 28.500 [25.000, 30.500] | 0.771 [0.717, 0.909] |
| 3 | 0.0 | 0.680 [0.678, 0.683] | 93.667 [92.667, 94.000] | 28.000 [27.000, 29.500] | 0.879 [0.726, 1.058] |
