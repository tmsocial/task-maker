#ifndef WORKER_MANAGER_HPP
#define WORKER_MANAGER_HPP
#include <capnp/ez-rpc.h>
#include <cstdlib>
#include <functional>
#include <queue>
#include <string>
#include <vector>

#include "worker/cache.hpp"

namespace worker {

// Class that requests work from the server at server:port, keeping at most
// max_pending_requests requests pending to the server and ensuring that the
// running requests do not use up more than num_cores.
class Manager {
 public:
  Manager(const std::string& server, uint32_t port, int32_t num_cores,
          int32_t pending_requests, std::string name)
      : client_(server, port),
        num_cores_(num_cores),
        max_pending_requests_(pending_requests),
        name_(std::move(name)) {}

  // Starts the manager.
  void Run();

  // Schedule a task that uses size cores. This should be called following an
  // answer from the server.
  template <typename T>
  kj::Promise<T> ScheduleTask(size_t size, std::function<kj::Promise<T>()> f) {
    kj::PromiseFulfillerPair<void> pf = kj::newPromiseAndFulfiller<void>();
    reserved_cores_ += size;
    pending_requests_--;
    waiting_tasks_.emplace(size, std::move(pf.fulfiller));
    OnDone();
    return pf.promise.then(
        [this, f, size]() {
          kj::Promise<T> ret = f();
          return ret.then(
              [size, this](T r) {
                running_cores_ -= size;
                OnDone();
                return r;
              },
              [size, this](kj::Exception exc) {
                KJ_LOG(WARNING, "Task failed: ", exc.getDescription());
                running_cores_ -= size;
                OnDone();
                return exc;
              });
        },
        [](kj::Exception exc) {
          KJ_LOG(WARNING, "Task preparation failed: ", exc.getDescription());
          return kj::Promise<T>(std::move(exc));
        });
  }

  // Removes a pending request to the server, typically because of a failure.
  void CancelPending();

  // Automatically called to run scheduled tasks and to refill the pending
  // request queue.
  void OnDone();

  int32_t NumCores() const { return num_cores_; }

  capnp::EzRpcClient& Client() { return client_; }

 private:
  capnp::EzRpcClient client_;
  const int32_t num_cores_;
  const int32_t max_pending_requests_;
  int32_t reserved_cores_ = 0;
  int32_t running_cores_ = 0;
  int32_t pending_requests_ = 0;
  std::queue<std::pair<int32_t, kj::Own<kj::PromiseFulfiller<void>>>>
      waiting_tasks_;
  size_t last_worker_id_ = 0;
  std::string name_;
  kj::PromiseFulfillerPair<void> on_error_ = kj::newPromiseAndFulfiller<void>();
  Cache cache_;
};

}  // namespace worker
#endif
