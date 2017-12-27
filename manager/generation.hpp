#ifndef MANAGER_GENERATION_HPP
#define MANAGER_GENERATION_HPP

#include "absl/types/optional.h"
#include "core/core.hpp"
#include "core/file_id.hpp"
#include "manager/event_queue.hpp"
#include "manager/source_file.hpp"
#include "proto/manager.pb.h"
#include "proto/task.pb.h"

namespace manager {

class Generation {
 public:
  Generation(EventQueue* queue, core::Core* core, const proto::Task& task,
             proto::CacheMode cache_mode, const std::string& executor);

  core::FileID* GetInput(int64_t testcase_id) const {
    return inputs_.at(testcase_id);
  }
  core::FileID* GetOutput(int64_t testcase_id) const {
    return outputs_.at(testcase_id);
  }
  SourceFile* GetChecker() const { return checker_.get(); }

  // To be called after Core.Run
  void WriteInputs(const proto::EvaluateTaskRequest& request);
  void WriteOutputs(const proto::EvaluateTaskRequest& request);
  void WriteChecker(const proto::EvaluateTaskRequest& request);

 private:
  std::unique_ptr<SourceFile> solution_;
  std::unique_ptr<SourceFile> checker_;

  std::map<int64_t, core::FileID*> inputs_;
  std::map<int64_t, core::FileID*> outputs_;
  std::map<int64_t, core::FileID*> validation_;

  proto::Task task_;
};

}  // namespace manager

#endif
