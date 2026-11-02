# PR54 CUDA12.4 failure diagnosis

Read-only inspection of completed job `125514573743` in upstream run
`41514536062` confirms the failure is the existing benchmark allocator namespace
compatibility issue, not CPU manager source removal.

The saved raw log is `pr54-job-125514573743.log`. Around lines1972–1976 it records:

```text
tests/adaptive/bench_adaptive_kmap.cpp:219:20: error: 'c10::CachingAllocator' has not been declared
tests/adaptive/bench_adaptive_kmap.cpp:220:46: error: 'StatType' has not been declared
```

The same log shows `adaptive_tests` linked successfully before this benchmark
compilation error. This is not evidence that CUDA tests ran; this workflow only
builds the production image.

The exact existing fix is open [PR32](https://github.com/QuiteLiterallyConnor/Minkowski4CPP/pull/32),
head `38b23ecca6544de68089dbff02f7220cbc948175`, runtime commit
`4bb14b7249a0137510f85073e46a85bfef968ca1`. It uses
`c10::CachingDeviceAllocator::StatType::AGGREGATE`, supported by the older
LibTorch namespace and re-exported by the newer one. That commit updates both
affected benchmark files.

Recommendation: merge the existing PR32 head into the PR54 branch and disclose
the dependency, preserving original ancestry rather than creating a duplicate
fix. This specialist did not change or push the CPU fix worktree and did not
post a PR comment.
