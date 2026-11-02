In this combined stack, median training latency fell 15.01% at 512 pixels and
10.42% at 1024, with the fused path faster in all ten paired rounds. Derived median
step throughput increased 17.66% and 11.64%. CPU boundary samples ranged from 47.5%
to 100%; unchanged render controls also shifted (up to -4.91%), so these measurements
do not isolate GPU kernel time or establish a universal speedup. Absolute times are
not comparable with the quieter standalone branch run.

At 512, training peak allocated/reserved CUDA memory fell 5.24%/8.22%. At 1024 they
increased 0.16%/2.20%, which is a retained regression. Whole-process peak working set
fell about 3.2%. Reserved memory depends on prior size phases and allocator history;
it is not an optimizer-only storage measurement. Exact parameter/moment parity and
trainer tolerance tests passed, and the combined regression suites passed; no change
to model accuracy is inferred from this renderer timing experiment.
