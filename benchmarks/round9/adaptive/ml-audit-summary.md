# Independent adaptive ML audit

All18 completed rows independently checked against receipt controls, fixed geometry fingerprint, confusion-derived metrics, epoch sums, retained caps and exact source/binary identity.

Six repeated measurements of seed1 are not six independent training seeds. Default fused apply path is active; atomic sums may vary. Accuracy comparisons do not establish model-quality advantages. Allocator peaks cover training plus per-epoch evaluation; train_time excludes evaluation. End-group statistics include final evaluation and inference.

| Metric | Unlimited median [min,max] | 32MiB median [min,max] | 0MiB median [min,max] | 32MiB change | 0MiB change |
|---|---|---|---|---|---|
| accuracy | 0.2525 [0.245, 0.29] | 0.285 [0.25, 0.305] | 0.28 [0.27, 0.295] | +12.871% | +10.891% |
| macro_precision | 0.334822 [0.238442, 0.448688] | 0.44219 [0.339893, 0.490455] | 0.463448 [0.35021, 0.473017] | +32.067% | +38.416% |
| macro_recall | 0.2525 [0.245, 0.29] | 0.285 [0.25, 0.305] | 0.28 [0.27, 0.295] | +12.871% | +10.891% |
| macro_f1 | 0.219674 [0.205035, 0.260861] | 0.250103 [0.214392, 0.285658] | 0.25041 [0.237214, 0.275539] | +13.852% | +13.992% |
| train_time_s | 6.47604 [4.07572, 13.2184] | 5.38505 [5.142, 7.41541] | 5.75431 [4.92986, 12.6634] | -16.847% | -11.145% |
| first_epoch_s | 4.7086 [2.64312, 11.4102] | 3.7947 [3.44242, 5.56849] | 3.90808 [3.35384, 10.3212] | -19.409% | -17.001% |
| warm_epoch_mean_s | 0.78639 [0.716297, 1.01883] | 0.807048 [0.771975, 0.923461] | 0.896237 [0.788008, 1.17113] | +2.627% | +13.968% |
| training_samples_per_second_derived | 140.887 [68.0871, 220.82] | 167.135 [121.369, 175.029] | 157.423 [71.0708, 182.561] | +18.631% | +11.737% |
| inference_latency_ms_median_b1 | 12.6687 [11.0192, 13.9905] | 11.6263 [10.4992, 13.1494] | 13.4529 [11.6323, 16.6404] | -8.229% | +6.190% |
| throughput_samples_per_s | 633.676 [520.294, 786.98] | 771.406 [494.005, 885.401] | 626.67 [466.508, 720.618] | +21.735% | -1.106% |
| peak_cuda_alloc_mb_train | 335.354 [335.354, 335.354] | 295.638 [295.638, 295.638] | 252.638 [252.638, 252.638] | -11.843% | -24.665% |
| peak_cuda_reserved_mb_train | 388 [388, 388] | 340 [340, 340] | 292 [292, 292] | -12.371% | -24.742% |
| peak_rss_mb | 4440.32 [4393.26, 4467.54] | 4464.45 [4122.04, 4469.37] | 4464.58 [4310.14, 4469.15] | +0.543% | +0.546% |
| end_group_charge_mib | 70.2795 [70.2795, 70.2795] | 31.894 [31.894, 31.894] | 0 [0, 0] | -54.618% | -100.000% |
| peak_group_charge_mib | 70.2795 [70.2795, 70.2795] | 31.9976 [31.9976, 31.9976] | 0 [0, 0] | -54.471% | -100.000% |
