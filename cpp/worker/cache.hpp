#ifndef WORKER_CACHE_HPP
#define WORKER_CACHE_HPP
#include <map>
#include <unordered_map>
#include "util/sha256.hpp"

namespace worker {

class Cache {
 public:
  Cache();
  void Register(util::SHA256_t hash);

 private:
  std::unordered_map<util::SHA256_t, size_t, util::SHA256_t::Hasher>
      file_sizes_;
  std::unordered_map<util::SHA256_t, size_t, util::SHA256_t::Hasher>
      file_access_times_;
  std::map<size_t, util::SHA256_t> sorted_files_;
  size_t total_size_ = 0;
  size_t last_access_time_ = 0;
};

}  // namespace worker
#endif
