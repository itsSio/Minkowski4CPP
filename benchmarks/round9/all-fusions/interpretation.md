This switches projection, tile construction, SSIM, Adam and attribute gathering
together in the same tested binary. It is not an original-upstream comparison or
the isolated contribution of any single PR. All twenty commands and five flag
values were independently checked against the raw receipt.

Training latency fell 69.07% at 512 pixels and 61.30% at 1024, with all ten paired
rounds faster. Allocated training CUDA peaks fell 26.08%/44.90%, reserved peaks
20.71%/43.81%, and process working set 28.38%/28.12%. Derived median step throughput
increased 223.36%/158.41%. CPU boundary utilization ranged 38.3–95.3%; these are
results on a contended host, not promises for an idle GPU or other hardware.

The renderer also changes in this comparison, so its timings are outcomes rather
than unchanged-path noise controls. Reserved memory at 1024 includes allocator
history from the prior 512 phase. Correctness is established by the integrated
test suites and per-feature numerical/gradient tests, not by these timings.
