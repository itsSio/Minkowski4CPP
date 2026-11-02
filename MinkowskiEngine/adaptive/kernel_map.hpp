#ifndef MINK_CPP_ADAPTIVE_KERNEL_MAP_HPP
#define MINK_CPP_ADAPTIVE_KERNEL_MAP_HPP

#include "adaptive_tensor.hpp"

#include <array>
#include <memory>
#include <mutex>
#include <utility>
#include <vector>

namespace minkowski {
namespace adaptive {

enum class AdaptiveConvMode {
  // Sample the leaf containing each tap point; weight 1. Default; reduces to
  // the standard sparse convolution on uniform aligned grids.
  CenterSampled,
  // Same neighbors, weight V_in / V_out.
  VolumeWeighted,
  // Every leaf overlapping the tap box; weight = overlap volume / V_out.
  OverlapWeighted,
  // Opt-in. Like CenterSampled while the leaf containing the tap point is at the output
  // leaf's level or coarser (weight 1). When it is finer, or no leaf contains the tap point,
  // the tap reads the average of the leaves inside the tap box (the output-sized cell around
  // the tap point), weighted by overlap volume / total overlap volume. Coarse outputs over
  // fine inputs (output_level_shift < 0, or coarse leaves next to refined regions) then read
  // every child instead of the one child whose corner sits on the tap point. Identical to
  // CenterSampled on uniform grids.
  CenterAveraged,
};

struct AdaptiveKernelConfig {
  int kernel_size = 3; // odd, per dimension
  AdaptiveConvMode mode = AdaptiveConvMode::CenterSampled;
  // 0 keeps the input leaves as outputs. -n coarsens outputs n levels (never
  // below level 0). Refining outputs is not supported.
  int output_level_shift = 0;
};

// Sparse (out, in, kernel-slot, weight) tuples sorted by kernel slot, then out.
struct AdaptiveKernelMap {
  at::Tensor in_index;     // [P] int64
  at::Tensor out_index;    // [P] int64
  at::Tensor kernel_index; // [P] int64
  at::Tensor weight;       // [P] double
  std::vector<int64_t> kernel_offsets; // num_kernels + 1 prefix offsets into the arrays
  int64_t num_kernels = 0;
};

// Row blocks of at most `rows` pairs over each kernel slot's pair range, for the fused CUDA
// apply_map. `slots` (int64) holds the map's num_kernels + 1 kernel offsets followed by
// num_kernels + 1 prefix counts of blocks per slot: block t lies in the slot k with
// prefix[k] <= t < prefix[k + 1] and starts at offsets[k] + (t - prefix[k]) * rows. `blocks`
// ([count, 3] int64: begin, end, slot) lists them; on CUDA it is expanded from `slots` on the
// device, so a new map uploads 2 (num_kernels + 1) values instead of the whole table.
struct TileTable {
  at::Tensor slots;
  at::Tensor blocks;
  int64_t count = 0;
  int64_t rows = 0;
};

// Copies of one kernel map's index/weight tensors on the devices and dtypes it was applied
// with, so repeated convolutions upload them once. Shared by every copy of a cache entry and
// freed with it (KernelMapCache::clear() or eviction releases the device memory).
class KernelMapDeviceCache {
public:
  struct Arrays {
    at::Tensor in_index;  // [P] int64 on `device`
    at::Tensor out_index; // [P] int64 on `device`
    at::Tensor weight;    // [P] `dtype` on `device`, undefined if not requested
  };
  // in/out indices on `device`, and the weights as `dtype` if `with_weight`.
  Arrays get(const AdaptiveKernelMap &map, const at::Device &device, at::ScalarType dtype,
             bool with_weight);
  // The map's TileTable for `rows` pairs per block on `device` (built once per device and row
  // count; 2 (num_kernels + 1) values, so cheap to build for every new map).
  TileTable tiles(const AdaptiveKernelMap &map, const at::Device &device, int64_t rows);
  // Installs arrays built on `device` (part reuse composes batch maps there; `weight` is
  // float64 or undefined for weight 1). The map's host arrays may then stay undefined until a
  // caller asks for them (KernelMapCache::get_or_build with host_arrays).
  void put(const at::Device &device, at::Tensor in_index, at::Tensor out_index, at::Tensor weight);
  // The first slot's in/out indices and float64 weights (undefined if none); used to fill
  // the host arrays of a map that was built on a device.
  Arrays first_slot();

private:
  struct Slot {
    at::Device device{at::kCPU};
    at::Tensor in_index, out_index;
    std::vector<std::pair<at::ScalarType, at::Tensor>> weights;
    std::vector<TileTable> tiles;
  };
  Slot &slot_for(const AdaptiveKernelMap &map, const at::Device &device); // mutex_ held
  std::mutex mutex_;
  std::vector<Slot> slots_;
};

struct KernelMapEntry {
  AdaptiveKernelMap map;
  std::shared_ptr<const detail::Topology> out_topology;
  std::shared_ptr<KernelMapDeviceCache> device = std::make_shared<KernelMapDeviceCache>();
};

namespace detail {
// Byte budget of the CUDA apply_map's per-group temporaries (a group's products and their
// concatenation). Consecutive kernel slots are processed together while their pairs fit;
// a slot larger than the budget is its own group. Default 32 MiB; 0 = one group for all
// slots. Process-wide tuning/test hook; set it before convolutions run, not concurrently.
int64_t &cuda_apply_map_group_bytes();
// Whether float/double CUDA apply_map calls use the fused single-launch kernels
// (fused_apply_cuda.cu) instead of the per-slot GEMMs above. Default on. Deterministic mode
// (at::globalContext().deterministicAlgorithms()) always takes the per-slot path, whose
// results do not depend on atomic ordering. Process-wide tuning/test hook like the above.
bool &cuda_apply_map_fused();
// Whether part reuse composes the batch maps of CUDA tensors on the device (default on): the
// parts' pair arrays stay on the device, a new batch map uploads only a segment table and its
// leaf numbering, and the map's host arrays are filled only on request. Off: host composition
// and one upload of the composed map, as before. Process-wide tuning/test hook.
bool &cuda_part_compose();
// Parts with at most this many input and output leaves keep 16-bit device indices (default
// 65536, the most 16 bits can address). Test hook: 0 stores every part with 32-bit indices.
int64_t &cuda_part_compose_narrow_limit();
#ifdef USE_CUDA
// kernel_map_cuda.cu. `table` (int64, on the device) holds `segments` rows (dst, q0, n, part),
// then per part (in ptr, out ptr, weight ptr or 0, index width 2|4), per part (input base, output base), then
// n_in input and n_out output leaf indices. Writes in/out_index (and *weight if given).
void cuda_compose_parts(const at::Tensor &table, int64_t segments, int64_t parts,
                        int64_t n_in, int64_t n_out, at::Tensor &in_index, at::Tensor &out_index,
                        at::Tensor *weight);
#endif
} // namespace detail

// Kernel slot of an offset in {-r..r}^D, r = (kernel_size-1)/2, first dimension slowest.
int64_t kernel_index(std::array<int, 3> offset, int kernel_size);

AdaptiveKernelMap build_adaptive_kernel_map(const AdaptiveSparseTensor &input,
                                            const AdaptiveKernelConfig &config);

// Cache keyed by (input topology id, kernel size, mode, output shift). A topology
// change produces a new id, so stale maps are never returned.
//
// Part reuse (opt-in, set_part_reuse_bytes > 0; CenterSampled and VolumeWeighted only).
// Training batches are usually built by placing samples side by side along the first axis,
// which gives every batch a new topology and so a full map build, although each sample's
// part of the map is the same every time it appears. With part reuse, a topology whose leaves
// fall into groups separated along the first axis by at least (kernel_size - 1) / 2 empty
// level-0 cells is split into those parts (a topology that does not split is one part, so
// repeated single samples, e.g. a validation set evaluated every epoch, are reused as well).
// No tap can reach from one part into another, so the map is the union of the parts' maps. Each part is matched by content (its leaf keys,
// translated by whole level-0 cells, plus D, max_depth, base voxel size and the kernel
// config) against maps kept from earlier batches; the batch map is then put together from
// them instead of searched again. The result is identical to a full build, pair for pair:
// taps resolve with integer cell arithmetic, so a translated part resolves the same leaves.
// Parts seen for the first time are built and kept (least recently used ones are dropped
// beyond the byte budget).
class KernelMapCache {
public:
  struct Stats {
    size_t hits = 0;
    size_t misses = 0;
    size_t entries = 0;
    size_t part_hits = 0;   // parts whose map came from the part store
    size_t part_misses = 0; // parts that had to be built
    size_t part_bytes = 0;  // host bytes held by the part store
  };

  static KernelMapCache &instance();
  ~KernelMapCache();

  // host_arrays = false (the convolutions) lets an entry whose map was composed on the input's
  // device keep only its device arrays; true (default) always returns the host arrays.
  KernelMapEntry get_or_build(const AdaptiveSparseTensor &input,
                              const AdaptiveKernelConfig &config, bool host_arrays = true);
  void clear();
  Stats stats() const;
  void set_capacity(size_t max_entries);
  // Byte budget of the part store; 0 (the default) turns part reuse off and frees the store.
  void set_part_reuse_bytes(size_t max_bytes);

private:
  KernelMapCache();
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

} // namespace adaptive
} // namespace minkowski

#endif
