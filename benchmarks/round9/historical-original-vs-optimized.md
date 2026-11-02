# Original vs optimized — end-to-end benchmarks

Measured by bench-r4 (2026-11-02 01:36-05:49), written up by the lead. Generator: `results/bench-r4/gen_report.py`;
raw runs `results/bench-r4/raw/`; binary hashes `mink-build/bench-r4/MANIFEST.tsv`.

## What is compared

| side | commit | contents |
|---|---|---|
| original | upstream `f93b7bc` | CUDA build `mink-build/base-cuda`; CPU build `base-cpu` (= f93b7bc + the #5 link fix, needed to build CPU-only at all) |
| optimized | `e1af851` (`integrate/round3`) | main 3524eff (#15 #18 #22 #23 #24 #25 merged) + #6-#14 #16 #17 #19 #20 #21 #26 #27 #28 + continuous interp (#33). **Not included:** #29, #30 (fused CPU rasterizer), #31, #32, #34-#39 |

Hardware: Ryzen 5 5600X 6C/12T, 16 GB, RTX 2080 SUPER 8 GB (sm_75), driver 610.88, Windows 11, MSVC 19.44, CUDA 13.4.3,
LibTorch 2.15.0 (+cpu / +cu134). Docker is not available on this host; the native toolchain mirrors
`docker/cuda-profile.sh`, and upstream CI builds `docker/Dockerfile` for every PR.

## Method and caveats (read before using any number)

- Each workload runs as fresh processes, original then optimized (A B), inside the exclusive bench lock, 5 timed rounds
  (overlap kmap: 3), each process with its own in-process warm-ups. Cells are median [min-max] over rounds.
  **The A/B order was never swapped** — the lab later found an order effect inside a lock (second binary slower on CUDA,
  often faster on CPU), so small differences (< ~15 %) in either direction are not meaningful here.
- **All rows are contended**: the host was shared with the owner's services (CPU load 34-99 % before blocks; Whisper and
  ollama hold ~29-31 % GPU and ~3.7 GB VRAM). Block 2 (03:47, 98.7 % load) ran 10-20x slower and is **excluded**; blocks
  3-4 were skipped (99.5-99.8 % load).
- "cold" = first call in the process (includes kernel-map build / first launch / uploads); "warm" = after warm-ups.
- GPU utilization was sampled every 200 ms, but it is device-wide (other processes share the GPU), so it is not
  attributed to our process; use the CUDA-event and caching-allocator rows.
- **The original CPU sparse convolution computes wrong values** (GEMM layout bug, fixed by #10); CPU conv timings compare
  a wrong result against a correct one. The original also drops ATen to 1 OpenMP thread after the first SparseTensor (#12).
- `train` gives a different final loss on every run of the same binary (not deterministic), so its loss is not compared.
- Not run: `adaptive_bench 200k/d5`, `gaussian_bench 100k / 1M`, `train` batch 4; CPU `train` dropped (wrong original conv).

## Headline

| area | workload | original | optimized | change |
|---|---|---|---|---|
| adaptive CUDA conv | fwd+bwd CenterSampled, 20k pts, 41,376 leaves | 15.69 ms | 5.30 ms | x2.96 |
| adaptive CUDA conv | fwd+bwd, 200k pts, 32->64 ch | 19.02 ms | 17.03 ms | -10.5 % |
| adaptive CPU kernel map | OverlapWeighted, cold, 33,754 leaves | 7,052 ms | 87.6 ms | x80.5 |
| adaptive CPU kernel map | CenterSampled, cold, 20k / 200k pts | 211 / 308 ms | 43.6 / 60.8 ms | x4.8 / x5.1 |
| adaptive interpolation | Multilinear, 20k queries | 737 ms | 10.9 ms | x67.5 |
| core CPU conv (original wrong) | first fwd incl. map, 100k 64->64 | 272.8 ms | 99.4 ms | -63.6 % |
| Gaussian CUDA | train step, 139k splats, 512 px | 41.0 ms | 26.0 ms | -36.6 % |
| Gaussian CPU | train step, 5000 splats, 128 px (CPU build) | 413 ms | 288 ms | -30.4 % (without #30's fused rasterizer) |

## Regressions (not hidden)

| PR | workload | original | optimized | change |
|---|---|---|---|---|
| #28 | CUDA max reserved, 20k / 200k pts | 128 / 776 MB | 302 / 1,482 MB | +136 % / +91 % |
| #28 | CUDA max allocated, 20k / 200k pts | 116 / 659 MB | 161 / 1,037 MB | +38 % / +57 % |
| #28 | first CUDA conv after map build (uploads into the device cache), 20k / 200k | 38.7 / 48.7 ms | 45.6 / 61.9 ms | +18 % / +27 % |
| #12 | CPU conv 100k 32->32 fwd+bwd: wall -2.4 % but process CPU time | 2.98 s | 8.61 s | +188 % (6 threads now used, little gain on small per-offset GEMMs) |
| ? | CPU adaptive conv fwd+bwd / `adaptive_bench` conv fwd, fwd+bwd | | | flat..+10 % / +36 %, +44 % (overlapping ranges, unswapped order: unconfirmed) |
| ? | CUDA `train` epoch, batch 1 | 3.0 s | 3.3 s | +10 % (within order-effect range) |

---

# Full tables (generated)

#### cuda_conv_adaptive_20k_d4_c8x16

`adaptive_kmap_bench --conv cuda --n 20000 --depth 4 --channels 8 --cout 16 --modes center,volume --warmup 3 --reps 10`

timed rounds orig 5 / opt 5; lock blocks started 01:36; CPU load [69.1, 45.2] gate=timeout-contended; workload: conv_center_pairs=905,482, leaves=41,376, points=20,000

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| first conv after map build (uploads incl.), CenterSampled | cold | 38.70 [37.72-43.83] | 45.59 [36.24-50.93] | +17.8 % | x0.85 |
| first conv, VolumeWeighted | cold | 29.07 [25.41-39.04] | 27.20 [23.61-34.35] | -6.4 % | x1.07 |
| fwd CenterSampled (host-synchronized) | warm | 4.84 [4.58-5.94] | 1.75 [1.49-1.79] | -63.7 % | x2.76 |
| fwd CenterSampled (CUDA events) | warm | 5.16 [3.46-6.59] | 2.02 [1.75-2.05] | -60.9 % | x2.56 |
| fwd+bwd CenterSampled | warm | 15.69 [11.89-16.49] | 5.30 [4.75-6.06] | -66.2 % | x2.96 |
| fwd VolumeWeighted | warm | 7.17 [5.35-8.87] | 1.93 [1.81-2.04] | -73.0 % | x3.71 |
| fwd+bwd VolumeWeighted | warm | 18.87 [14.10-21.47] | 6.34 [4.74-7.37] | -66.4 % | x2.97 |
| CUDA max allocated MB | mem | 116.1 [116.1-116.1] | 160.7 [160.7-160.7] | +38.4 % |  |
| CUDA max reserved MB | mem | 128.0 [128.0-128.0] | 302.0 [302.0-302.0] | +135.9 % |  |
| process wall = cold start + whole run (ms) | cold | 2,176 [1,829-2,275] | 1,218 [1,080-1,503] | -44.1 % | x1.79 |
| process peak working set MB | mem | 620.1 [619.6-620.2] | 583.7 [582.4-585.1] | -5.9 % |  |
| process CPU time s | proc | 4.58 [3.98-4.86] | 2.34 [2.22-2.62] | -48.8 % |  |
| device GPU util mean % (all processes) | gpu | 15.91 [14.78-19.18] | 21.00 [15.57-28.67] | +32.0 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,981 [3,927-4,003] | 4,114 [4,098-4,206] | +3.3 % |  |

#### cuda_conv_adaptive_200k_d4_c32x64

`adaptive_kmap_bench --conv cuda --n 200000 --depth 4 --channels 32 --cout 64 --modes center --warmup 3 --reps 10`

timed rounds orig 5 / opt 5; lock blocks started 01:39; CPU load [69.1, 45.2] gate=timeout-contended; workload: conv_center_pairs=1,613,781, leaves=64,001, points=200,000

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| first conv, CenterSampled | cold | 48.67 [38.50-50.51] | 61.85 [57.01-66.46] | +27.1 % | x0.79 |
| fwd CenterSampled | warm | 9.49 [9.34-10.32] | 8.87 [8.77-9.11] | -6.6 % | x1.07 |
| fwd CenterSampled (CUDA events) | warm | 9.55 [9.45-9.63] | 8.91 [8.81-9.64] | -6.7 % | x1.07 |
| fwd+bwd CenterSampled | warm | 19.02 [18.93-19.22] | 17.03 [16.68-17.07] | -10.5 % | x1.12 |
| CUDA max allocated MB | mem | 659.0 [659.0-659.0] | 1,037 [1,037-1,037] | +57.4 % |  |
| CUDA max reserved MB | mem | 776.0 [776.0-776.0] | 1,482 [1,482-1,482] | +91.0 % |  |
| process wall = cold start + whole run (ms) | cold | 1,891 [1,674-2,088] | 1,531 [1,440-1,817] | -19.0 % | x1.24 |
| process peak working set MB | mem | 656.1 [649.2-656.5] | 644.4 [643.9-649.1] | -1.8 % |  |
| process CPU time s | proc | 4.95 [4.72-5.05] | 3.86 [3.70-4.17] | -22.1 % |  |
| device GPU util mean % (all processes) | gpu | 30.11 [28.00-32.50] | 30.89 [25.75-42.00] | +2.6 % |  |
| device GPU memory used max MB (all processes) | gpu | 4,630 [4,602-4,646] | 5,337 [5,286-5,408] | +15.3 % |  |

#### cpu_kmap_20k_d4

`adaptive_kmap_bench --n 20000 --depth 4 --modes center,volume --interp 20000 --warmup 2 --reps 5`

timed rounds orig 5 / opt 5; lock blocks started 01:36; CPU load [69.1, 45.2] gate=timeout-contended; workload: kmap_center_pairs=905,482, leaves=41,376, points=20,000

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| kmap CenterSampled, fresh topology | cold | 211.1 [169.9-227.8] | 43.60 [34.45-49.36] | -79.3 % | x4.84 |
| kmap CenterSampled, cached indices | warm | 200.1 [177.7-202.2] | 30.64 [26.41-39.44] | -84.7 % | x6.53 |
| kmap VolumeWeighted, fresh topology | cold | 220.6 [204.5-256.5] | 33.66 [28.06-44.78] | -84.7 % | x6.55 |
| kmap VolumeWeighted, cached indices | warm | 230.0 [204.5-250.5] | 30.46 [25.20-54.33] | -86.8 % | x7.55 |
| interpolate Multilinear, 20k queries | warm | 737.4 [711.3-969.0] | 10.93 [7.04-14.14] | -98.5 % | x67.50 |
| interpolate Nearest, 20k queries | warm | 5.27 [3.27-10.07] | 3.08 [2.50-6.25] | -41.5 % | x1.71 |
| process wall = cold start + whole run (ms) | cold | 12,763 [12,079-13,208] | 1,778 [1,483-1,924] | -86.1 % | x7.18 |
| process peak working set MB | mem | 199.3 [198.6-199.9] | 175.4 [175.2-175.8] | -12.0 % |  |
| process CPU time s | proc | 40.47 [36.03-42.58] | 7.09 [6.75-7.81] | -82.5 % |  |
| device GPU util mean % (all processes) | gpu | 27.14 [17.13-31.72] | 30.44 [6.78-31.00] | +12.2 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,762 [3,731-3,779] | 3,726 [3,684-3,769] | -1.0 % |  |

#### cpu_kmap_200k_d4_center

`adaptive_kmap_bench --n 200000 --depth 4 --modes center --interp 0 --warmup 2 --reps 5`

timed rounds orig 5 / opt 5; lock blocks started 05:49; CPU load [44.3, 34.1] gate=timeout-contended; workload: kmap_center_pairs=1,613,781, leaves=64,001, points=200,000

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| kmap CenterSampled, fresh topology | cold | 308.3 [251.6-319.1] | 60.78 [45.07-71.68] | -80.3 % | x5.07 |
| kmap CenterSampled, cached indices | warm | 274.5 [253.8-299.7] | 56.45 [36.69-78.75] | -79.4 % | x4.86 |
| process wall = cold start + whole run (ms) | cold | 5,033 [4,553-5,614] | 1,418 [1,076-1,924] | -71.8 % | x3.55 |
| process peak working set MB | mem | 288.9 [285.8-289.0] | 243.5 [234.2-244.0] | -15.7 % |  |
| process CPU time s | proc | 16.52 [16.22-17.61] | 4.89 [4.66-5.77] | -70.4 % |  |
| device GPU util mean % (all processes) | gpu | 28.35 [26.36-30.23] | 28.86 [26.00-31.11] | +1.8 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,766 [3,732-3,793] | 3,707 [3,664-3,773] | -1.6 % |  |

#### cpu_kmap_overlap_2k_d4

`adaptive_kmap_bench --n 2000 --depth 4 --modes overlap --interp 0 --warmup 2 --reps 5`

timed rounds orig 3 / opt 3; lock blocks started 05:41, 05:45; CPU load [44.3, 34.1] gate=timeout-contended / CPU load [61.9, 74.1] gate=timeout-contended; workload: kmap_overlap_pairs=854,938, leaves=33,754, points=2,000

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| kmap OverlapWeighted, fresh topology | cold | 7,052 [5,875-7,447] | 87.61 [78.64-90.93] | -98.8 % | x80.50 |
| kmap OverlapWeighted, cached indices | warm | 7,261 [6,626-7,353] | 148.1 [142.1-159.1] | -98.0 % | x49.03 |
| process wall = cold start + whole run (ms) | cold | 112,712 [99,052-119,507] | 2,100 [1,976-2,234] | -98.1 % | x53.68 |
| process peak working set MB | mem | 195.9 [193.9-196.0] | 172.6 [170.8-172.8] | -11.9 % |  |
| process CPU time s | proc | 112.5 [106.0-121.2] | 9.36 [9.36-9.41] | -91.7 % |  |
| device GPU util mean % (all processes) | gpu | 27.64 [27.62-27.83] | 28.00 [27.20-30.40] | +1.3 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,798 [3,780-3,801] | 3,679 [3,664-3,705] | -3.1 % |  |

#### cpu_conv_adaptive_20k_d4_c8x16

`adaptive_kmap_bench --conv cpu --n 20000 --depth 4 --channels 8 --cout 16 --modes center,volume --warmup 3 --reps 10`

timed rounds orig 5 / opt 5; 2 runs of a 98.7 %-CPU block excluded as invalid (10-20x slower); lock blocks started 01:39; CPU load [69.1, 45.2] gate=timeout-contended; workload: conv_center_pairs=905,482, leaves=41,376, points=20,000

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| first conv, CenterSampled | cold | 23.41 [15.55-36.18] | 46.20 [18.97-89.96] | +97.4 % | x0.51 |
| fwd CenterSampled | warm | 17.94 [12.13-29.80] | 17.54 [15.07-24.24] | -2.2 % | x1.02 |
| fwd+bwd CenterSampled | warm | 73.37 [61.67-105.9] | 80.43 [69.39-88.08] | +9.6 % | x0.91 |
| fwd VolumeWeighted | warm | 23.93 [19.41-40.34] | 25.71 [17.93-31.27] | +7.4 % | x0.93 |
| fwd+bwd VolumeWeighted | warm | 101.8 [94.87-191.7] | 101.4 [74.01-144.6] | -0.4 % | x1.00 |
| process wall = cold start + whole run (ms) | cold | 4,346 [3,548-6,032] | 4,327 [3,850-6,315] | -0.5 % | x1.00 |
| process peak working set MB | mem | 258.6 [238.0-286.8] | 256.9 [255.6-257.5] | -0.6 % |  |
| process CPU time s | proc | 19.11 [17.78-24.52] | 17.45 [16.56-23.23] | -8.7 % |  |
| device GPU util mean % (all processes) | gpu | 29.89 [13.35-31.71] | 28.50 [27.14-29.00] | -4.7 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,724 [3,708-3,780] | 3,738 [3,727-3,777] | +0.4 % |  |

#### cpu_adaptive_bench_20k_d4

`adaptive_bench 20000 4`

timed rounds orig 5 / opt 5; 12 runs of a 98.7 %-CPU block excluded as invalid (10-20x slower); lock blocks started 01:38; CPU load [69.1, 45.2] gate=timeout-contended; workload: adaptive_voxels=41,376

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| voxelization | warm | 4.57 [4.25-4.99] | 4.78 [4.33-12.87] | +4.5 % | x0.96 |
| refine ROI | warm | 16.37 [15.20-26.70] | 18.09 [13.84-22.27] | +10.5 % | x0.91 |
| kernel map (cache cleared each call) | warm | 190.6 [177.1-256.2] | 45.62 [29.91-62.51] | -76.1 % | x4.18 |
| conv fwd (f64) | warm | 14.12 [12.46-41.87] | 19.19 [13.06-23.91] | +35.9 % | x0.74 |
| conv fwd+bwd (f64) | warm | 61.01 [56.64-67.60] | 87.85 [53.00-127.6] | +44.0 % | x0.69 |
| process wall = cold start + whole run (ms) | cold | 2,102 [1,977-2,730] | 1,563 [988.9-1,767] | -25.6 % | x1.34 |
| process peak working set MB | mem | 211.5 [211.2-211.9] | 219.1 [217.9-222.3] | +3.6 % |  |
| process CPU time s | proc | 9.55 [9.41-9.92] | 5.61 [4.88-6.30] | -41.2 % |  |
| device GPU util mean % (all processes) | gpu | 28.50 [12.50-30.85] | 29.67 [11.25-31.00] | +4.1 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,725 [3,660-3,791] | 3,727 [3,665-3,788] | +0.1 % |  |

#### cpu_adaptive_bench_200k_d5

PENDING (not run yet)

#### cpu_core_conv_10k_c32_b1

`core_conv_bench --device cpu --points 10000 --extent 96 --batches 1 --cin 32 --cout 32 --stride 1 --warmup 3 --repeats 10 --seed 0`

timed rounds orig 5 / opt 5; lock blocks started 01:41; CPU load [69.1, 45.2] gate=timeout-contended; workload: in_rows=10,000, out_rows=10,000

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| first fwd incl. coordinate + kernel map | cold | 13.08 [12.12-17.89] | 7.90 [6.42-9.22] | -39.6 % |  |
| fwd (cached map) | warm | 2.76 [2.49-3.88] | 2.21 [1.63-3.73] | -20.1 % | x1.25 |
| bwd | warm | 4.28 [3.68-4.84] | 3.54 [2.65-4.96] | -17.5 % | x1.21 |
| fwd+bwd | warm | 6.54 [6.42-9.04] | 5.81 [4.33-8.36] | -11.2 % | x1.13 |
| ATen threads after first SparseTensor | proc | 1.00 [1.00-1.00] | 6.00 [6.00-6.00] | +500.0 % |  |
| process wall = cold start + whole run (ms) | cold | 496.3 [403.8-539.3] | 421.2 [374.1-468.0] | -15.1 % | x1.18 |
| process peak working set MB | mem | 105.5 [105.0-105.6] | 100.9 [100.7-101.3] | -4.4 % |  |
| process CPU time s | proc | 0.969 [0.75-1.12] | 0.812 [0.734-0.906] | -16.1 % |  |
| device GPU util mean % (all processes) | gpu | 30.00 [29.50-30.33] | 30.00 [29.00-31.00] | +0.0 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,714 [3,689-3,725] | 3,690 [3,681-3,725] | -0.6 % |  |

#### cpu_core_conv_40k_c16to64_s2_b2

`core_conv_bench --device cpu --points 20000 --extent 96 --batches 2 --cin 16 --cout 64 --stride 2 --warmup 3 --repeats 10 --seed 0`

timed rounds orig 5 / opt 5; lock blocks started 01:40; CPU load [69.1, 45.2] gate=timeout-contended; workload: in_rows=40,000, out_rows=36,917

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| first fwd incl. coordinate + kernel map | cold | 63.90 [53.37-80.21] | 24.49 [23.00-36.24] | -61.7 % |  |
| fwd (cached map) | warm | 16.28 [13.85-18.43] | 10.12 [7.46-14.97] | -37.8 % | x1.61 |
| bwd | warm | 17.47 [15.17-20.80] | 11.26 [10.53-16.65] | -35.5 % | x1.55 |
| fwd+bwd | warm | 34.35 [28.65-42.38] | 22.67 [17.50-32.70] | -34.0 % | x1.52 |
| ATen threads after first SparseTensor | proc | 1.00 [1.00-1.00] | 6.00 [6.00-6.00] | +500.0 % |  |
| process wall = cold start + whole run (ms) | cold | 896.5 [806.3-948.1] | 686.8 [534.6-1,021] | -23.4 % | x1.31 |
| process peak working set MB | mem | 130.4 [129.7-130.6] | 127.5 [125.1-128.3] | -2.2 % |  |
| process CPU time s | proc | 1.55 [1.48-1.91] | 2.30 [1.80-2.67] | +48.5 % |  |
| device GPU util mean % (all processes) | gpu | 29.75 [27.20-31.40] | 30.67 [29.00-32.00] | +3.1 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,721 [3,682-3,736] | 3,703 [3,679-3,736] | -0.5 % |  |

#### cpu_core_conv_100k_c32_b2

`core_conv_bench --device cpu --points 50000 --extent 96 --batches 2 --cin 32 --cout 32 --stride 1 --warmup 3 --repeats 10 --seed 0`

timed rounds orig 5 / opt 5; lock blocks started 01:38; CPU load [69.1, 45.2] gate=timeout-contended; workload: in_rows=100,000, out_rows=100,000

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| first fwd incl. coordinate + kernel map | cold | 216.0 [181.2-248.4] | 89.05 [74.15-141.5] | -58.8 % |  |
| fwd (cached map) | warm | 52.02 [47.36-57.46] | 50.83 [42.56-60.62] | -2.3 % | x1.02 |
| bwd | warm | 75.48 [67.69-87.34] | 69.99 [62.84-97.76] | -7.3 % | x1.08 |
| fwd+bwd | warm | 123.9 [117.5-143.1] | 120.9 [106.4-164.5] | -2.4 % | x1.02 |
| ATen threads after first SparseTensor | proc | 1.00 [1.00-1.00] | 6.00 [6.00-6.00] | +500.0 % |  |
| process wall = cold start + whole run (ms) | cold | 2,207 [2,099-2,536] | 2,048 [1,924-2,655] | -7.2 % | x1.08 |
| process peak working set MB | mem | 231.1 [228.5-231.2] | 199.4 [198.6-199.5] | -13.7 % |  |
| process CPU time s | proc | 2.98 [2.94-3.16] | 8.61 [7.58-8.98] | +188.5 % |  |
| device GPU util mean % (all processes) | gpu | 28.33 [28.00-31.45] | 29.70 [28.00-30.50] | +4.8 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,716 [3,659-3,770] | 3,718 [3,658-3,776] | +0.1 % |  |

#### cpu_core_conv_100k_c64_b4

`core_conv_bench --device cpu --points 25000 --extent 96 --batches 4 --cin 64 --cout 64 --stride 1 --warmup 3 --repeats 10 --seed 0`

timed rounds orig 5 / opt 5; lock blocks started 01:40; CPU load [69.1, 45.2] gate=timeout-contended; workload: in_rows=100,000, out_rows=100,000

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| first fwd incl. coordinate + kernel map | cold | 272.8 [193.5-357.8] | 99.41 [95.35-132.3] | -63.6 % |  |
| fwd (cached map) | warm | 81.86 [69.53-93.49] | 65.76 [61.58-66.67] | -19.7 % | x1.24 |
| bwd | warm | 129.1 [105.8-135.4] | 91.60 [87.67-101.7] | -29.1 % | x1.41 |
| fwd+bwd | warm | 212.8 [172.2-231.0] | 155.2 [150.6-179.9] | -27.0 % | x1.37 |
| ATen threads after first SparseTensor | proc | 1.00 [1.00-1.00] | 6.00 [6.00-6.00] | +500.0 % |  |
| process wall = cold start + whole run (ms) | cold | 3,579 [3,019-3,902] | 2,868 [2,735-3,480] | -19.9 % | x1.25 |
| process peak working set MB | mem | 352.9 [351.4-353.7] | 300.8 [300.5-301.4] | -14.8 % |  |
| process CPU time s | proc | 4.00 [3.94-4.14] | 11.50 [10.83-12.27] | +187.5 % |  |
| device GPU util mean % (all processes) | gpu | 29.81 [17.37-31.11] | 30.00 [23.27-32.06] | +0.6 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,728 [3,702-3,782] | 3,714 [3,660-3,764] | -0.4 % |  |

#### cuda_gaussian_ply_i5

`gaussian_ply_bench --input C:/Users/User/Work/Minkowski4CPP/tests/data/test.ply --input C:/Users/User/Work/Minkowski4CPP/tests/data/test_compressed.ply --iterations 5 --output {json}`

timed rounds orig 5 / opt 5; lock blocks started 05:31, 05:37; CPU load [61.9, 74.1] gate=timeout-contended / CPU load [79.0, 71.2] gate=timeout-contended

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| PLY load, first (cold file cache inside process) | cold | 69.00 [48.63-600.3] | 60.07 [45.70-65.65] | -12.9 % | x1.15 |
| PLY load, warm | warm | 66.44 [50.13-124.3] | 49.76 [42.76-51.16] | -25.1 % | x1.34 |
| compressed PLY load, warm | warm | 26.95 [18.09-31.97] | 24.93 [22.31-27.58] | -7.5 % | x1.08 |
| covariances CPU (139k) | warm | 19.79 [12.06-55.55] | 9.83 [8.99-13.76] | -50.3 % | x2.01 |
| transform CPU | warm | 34.47 [20.38-42.96] | 24.79 [18.30-31.91] | -28.1 % | x1.39 |
| optimizer step CPU | warm | 1.00 [0.76-6.26] | 1.02 [0.848-3.74] | +1.8 % | x0.98 |
| render fwd CPU, 5000 splats 128 px | warm | 92.44 [62.17-142.6] | 107.9 [46.13-1,195] | +16.7 % | x0.86 |
| train step CPU, 5000 splats 128 px | warm | 711.7 [521.4-1,453] | 510.6 [423.3-686.0] | -28.3 % | x1.39 |
| covariances CUDA | warm | 0.593 [0.436-0.599] | 0.522 [0.371-0.576] | -11.9 % | x1.14 |
| render fwd CUDA, 139k splats 512 px | warm | 13.03 [12.07-13.63] | 13.51 [9.17-16.35] | +3.7 % | x0.96 |
| train step CUDA, 139k splats 512 px | warm | 40.99 [37.88-47.04] | 25.99 [24.29-31.41] | -36.6 % | x1.58 |
| render fwd CUDA torch fallback 512 px | warm | 1,959 [1,799-2,345] | 1,743 [1,563-2,120] | -11.0 % | x1.12 |
| train step CUDA torch fallback 512 px | warm | 8,483 [7,521-9,693] | 7,346 [7,032-9,009] | -13.4 % | x1.15 |
| process wall = cold start + whole run (ms) | cold | 39,120 [36,182-43,082] | 33,593 [29,638-37,217] | -14.1 % | x1.16 |
| process peak working set MB | mem | 1,315 [1,294-1,318] | 1,347 [1,339-1,363] | +2.5 % |  |
| process CPU time s | proc | 46.95 [46.23-50.97] | 39.83 [37.30-44.75] | -15.2 % |  |
| device GPU util mean % (all processes) | gpu | 28.79 [27.72-29.41] | 28.43 [25.78-28.68] | -1.3 % |  |
| device GPU memory used max MB (all processes) | gpu | 4,308 [4,301-4,309] | 4,257 [4,245-4,268] | -1.2 % |  |

#### cpu_gaussian_ply_i5

`gaussian_ply_bench --input C:/Users/User/Work/Minkowski4CPP/tests/data/test.ply --input C:/Users/User/Work/Minkowski4CPP/tests/data/test_compressed.ply --iterations 5 --output {json}`

timed rounds orig 5 / opt 5; lock blocks started 05:40; CPU load [61.9, 74.1] gate=timeout-contended

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| PLY load, first (cold file cache inside process) | cold | 66.42 [47.05-89.73] | 54.80 [45.17-104.9] | -17.5 % | x1.21 |
| PLY load, warm | warm | 52.47 [46.27-64.25] | 47.24 [43.18-75.87] | -10.0 % | x1.11 |
| compressed PLY load, warm | warm | 25.07 [23.46-30.48] | 23.83 [17.46-28.39] | -5.0 % | x1.05 |
| covariances CPU (139k) | warm | 12.84 [9.74-17.63] | 12.15 [8.75-17.16] | -5.3 % | x1.06 |
| transform CPU | warm | 18.36 [16.85-50.19] | 20.87 [15.58-66.23] | +13.6 % | x0.88 |
| optimizer step CPU | warm | 0.884 [0.745-1.02] | 0.869 [0.675-3.05] | -1.7 % | x1.02 |
| render fwd CPU, 5000 splats 128 px | warm | 57.92 [56.51-387.9] | 62.62 [51.35-99.92] | +8.1 % | x0.93 |
| train step CPU, 5000 splats 128 px | warm | 413.1 [284.2-1,089] | 287.6 [198.9-295.0] | -30.4 % | x1.44 |
| process wall = cold start + whole run (ms) | cold | 3,128 [2,615-5,369] | 2,821 [2,651-2,950] | -9.8 % | x1.11 |
| process peak working set MB | mem | 233.1 [227.1-233.5] | 225.8 [224.5-233.2] | -3.1 % |  |
| process CPU time s | proc | 12.70 [11.89-17.08] | 11.61 [10.95-11.75] | -8.6 % |  |
| device GPU util mean % (all processes) | gpu | 29.85 [25.80-31.59] | 30.38 [10.43-33.00] | +1.8 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,732 [3,682-3,773] | 3,715 [3,662-3,771] | -0.5 % |  |

#### cuda_gaussian_bench_100k

PENDING (not run yet)

#### cuda_gaussian_bench_1M

PENDING (not run yet)

#### cuda_train_1ep_b1

`train --data_dir C:/Users/User/Work/Minkowski4CPP/tests/data/voxels --epochs 1 --batch_size 1 --save_dir {tmp}`

timed rounds orig 5 / opt 5; lock blocks started 05:38; CPU load [61.9, 74.1] gate=timeout-contended

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| epoch time (train.exe print, s) | warm | 3.00 [2.70-3.10] | 3.30 [2.80-3.60] | +10.0 % | x0.91 |
| final epoch loss | proc | 0.221 [0.18-0.335] | 0.279 [0.186-0.34] | +26.3 % |  |
| pos-precision | proc | 0.0848 [0-0.524] | 0.3 [0-0.4] | +253.8 % |  |
| process wall = cold start + whole run (ms) | cold | 9,961 [8,646-13,089] | 9,622 [8,623-10,029] | -3.4 % | x1.04 |
| process peak working set MB | mem | 769.3 [769.3-770.7] | 769.5 [768.8-771.4] | +0.0 % |  |
| process CPU time s | proc | 19.41 [17.78-21.45] | 27.69 [24.25-29.84] | +42.7 % |  |
| device GPU util mean % (all processes) | gpu | 29.40 [28.71-30.41] | 28.78 [27.84-29.33] | -2.1 % |  |
| device GPU memory used max MB (all processes) | gpu | 4,170 [4,061-4,210] | 4,137 [4,115-4,141] | -0.8 % |  |

#### cuda_train_1ep_b4

PENDING (not run yet)

#### cpu_train_1ep_b1

PENDING (not run yet)

#### cuda_sphere

`sphere`

timed rounds orig 5 / opt 5; lock blocks started 01:39; CPU load [69.1, 45.2] gate=timeout-contended

| metric | phase | original f93b7bc | optimized e1af851 | change | speed-up |
|---|---|---|---|---|---|
| process wall = cold start + whole run (ms) | cold | 446.4 [408.5-545.0] | 443.2 [417.4-617.7] | -0.7 % | x1.01 |
| process peak working set MB | mem | 292.9 [292.8-293.1] | 292.9 [292.8-293.1] | +0.0 % |  |
| process CPU time s | proc | 0.453 [0.422-0.562] | 0.469 [0.406-0.562] | +3.4 % |  |
| device GPU util mean % (all processes) | gpu | 31.00 [28.00-31.67] | 31.00 [28.00-32.00] | +0.0 % |  |
| device GPU memory used max MB (all processes) | gpu | 3,704 [3,703-3,717] | 3,703 [3,693-3,718] | -0.0 % |  |

