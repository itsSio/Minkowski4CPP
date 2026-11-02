Combined-stack training latency changed -3.70% at 512 pixels and -0.56% at 1024,
with seven of ten paired rounds faster at each size. The wide overlapping ranges
and host contention make the 1024 difference inconclusive. This supplements the
standalone -4.1%/-2.1% observations and the measured reduction in GPU operations;
it does not establish a speedup for every combined workload.

Training peak allocated CUDA memory changed -0.14% at 512 and +0.21% at 1024.
Render-backward peaks increased 0.69%/0.31%, while reserved training memory was flat
at 512 and decreased 6.06% at 1024. Whole-process peak working set increased about
0.02%/0.01%. These small regressions and allocator-history effects are preserved.
The complete combined suites passed, including the gather gradient and lifetime
tests; this timing experiment does not measure reconstruction or classification quality.
