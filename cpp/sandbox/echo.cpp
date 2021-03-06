#include "sandbox/echo.hpp"

#include <iostream>

namespace sandbox {

bool Echo::ExecuteInternal(const ExecutionOptions& options, ExecutionInfo* info,
                           std::string* /*error_msg*/) {
  std::cout << "[FAKE] Executing ";
  std::cout << options.executable;
  for (const auto& arg : options.args) {
    if (!arg[0]) break;
    std::cout << " " << arg;
  }
  std::cout << std::endl;
  std::cout << "Inside folder: " << options.root << std::endl;
  info->cpu_time_millis = 0;
  info->sys_time_millis = 0;
  info->wall_time_millis = 0;
  info->memory_usage_kb = 0;
  info->signal = 0;
  info->status_code = 0;
  return true;
}

namespace {
Sandbox::Register<Echo> r;  // NOLINT
}  // namespace

}  // namespace sandbox
