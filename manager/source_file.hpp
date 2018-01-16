#ifndef MANAGER_SOURCE_FILE_HPP
#define MANAGER_SOURCE_FILE_HPP

#include <vector>

#include "absl/types/optional.h"
#include "core/core.hpp"
#include "core/execution.hpp"
#include "core/task_status.hpp"
#include "manager/event_queue.hpp"
#include "proto/task.pb.h"

namespace manager {
class SourceFile {
 public:
  static std::unique_ptr<SourceFile> FromProto(
      EventQueue* queue, core::Core* core, const proto::SourceFile& source,
      const absl::optional<proto::GraderInfo>& grader,
      bool fatal_failures = false);
  virtual core::Execution* execute(const std::string& description,
                                   const std::vector<std::string>& args) = 0;
  virtual void WriteTo(const std::string& path, bool overwrite,
                       bool exist_ok) = 0;
  const std::string& Name() { return name_; }

  virtual ~SourceFile() = default;
  SourceFile(const SourceFile&) = delete;
  SourceFile(SourceFile&&) = delete;
  SourceFile& operator=(const SourceFile&) = delete;
  SourceFile& operator=(SourceFile&&) = delete;

 protected:
  SourceFile(core::Core* core, EventQueue* queue, std::string name,
             bool fatal_failures)
      : core_(core),
        queue_(queue),
        name_(std::move(name)),
        fatal_failures_(fatal_failures){};

  core::Core* core_;
  EventQueue* queue_;
  std::string name_;
  bool fatal_failures_;
};

}  // namespace manager

#endif