#ifndef SERVER_DISPATCHER_HPP
#define SERVER_DISPATCHER_HPP

#include <kj/async.h>
#include <vector>
#include "capnp/evaluation.capnp.h"

namespace server {

class Dispatcher {
  template <typename T, typename U>
  using Queue = std::vector<std::pair<T, kj::Own<kj::PromiseFulfiller<U>>>>;

 public:
  kj::Promise<void> AddEvaluator(capnproto::Evaluator::Client evaluator);
  kj::Promise<capnproto::Result::Reader> AddRequest(
      capnproto::Request::Reader request);

 private:
  // TODO: I could not make a Queue<Evaluator, void> work, for some reason
  std::vector<capnproto::Evaluator::Client> evaluators_;
  std::vector<kj::Own<kj::PromiseFulfiller<void>>> fulfillers_;
  Queue<capnproto::Request::Reader, capnproto::Result::Reader> requests_;
};

}  // namespace server

#endif