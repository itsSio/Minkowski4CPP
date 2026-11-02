#pragma once
// Throwaway phase profiler (round-7 profiling branch only, not for a PR).
// detail::profile().on = true enables device-synchronized phase timers.
#include <chrono>
#include <map>
#include <mutex>
#include <string>

#include <torch/cuda.h>

namespace minkowski {
namespace adaptive {
namespace detail {

struct ProfileSink {
  bool on = false;
  std::mutex mutex;
  std::map<std::string, double> ms;
};

inline ProfileSink &profile() {
  static ProfileSink s;
  return s;
}

inline void profile_sync() {
  if (torch::cuda::is_available())
    torch::cuda::synchronize();
}

struct ProfScope {
  const char *name;
  bool on;
  std::chrono::steady_clock::time_point t0;
  explicit ProfScope(const char *n) : name(n), on(profile().on) {
    if (on) {
      profile_sync();
      t0 = std::chrono::steady_clock::now();
    }
  }
  ~ProfScope() { stop(); }
  void stop() {
    if (!on)
      return;
    on = false;
    profile_sync();
    const double ms =
        std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    std::lock_guard<std::mutex> lock(profile().mutex);
    profile().ms[name] += ms;
  }
};

} // namespace detail
} // namespace adaptive
} // namespace minkowski
