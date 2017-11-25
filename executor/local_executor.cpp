#include "executor/local_executor.hpp"
#include "util/file.hpp"
#include "util/flags.hpp"

#include <ctype.h>

#include <algorithm>
#include <thread>

namespace {
bool IsValidChar(char c) {
  return isalnum(c) || c == '.' || c == '-' || c == '_';
}
}  // namespace

namespace executor {

proto::Response LocalExecutor::Execute(
    const proto::Request& request, const RequestFileCallback& file_callback) {
  if (request.fifo_size()) {
    throw std::logic_error("FIFOs are not implemented yet");
  }
  for (const auto& input : request.input()) {
    MaybeRequestFile(input, file_callback);
  }

  sandbox::ExecutionInfo result;
  util::TempDir tmp(FLAGS_temp_directory);
  std::string sandbox_dir = util::File::JoinPath(tmp.Path(), kBoxDir);
  util::File::MakeDirs(sandbox_dir);

  // Folder and arguments.
  sandbox::ExecutionOptions exec_options(sandbox_dir, request.executable());
  for (const std::string& arg : request.arg()) {
    exec_options.args.push_back(arg);
  }

  // Limits.
  exec_options.cpu_limit_millis = request.resource_limit().cpu_time() * 1000;
  exec_options.wall_limit_millis = request.resource_limit().wall_time() * 1000;
  exec_options.memory_limit_kb = request.resource_limit().memory();
  exec_options.max_files = request.resource_limit().nfiles();
  exec_options.max_procs = request.resource_limit().processes();
  exec_options.max_file_size_kb = request.resource_limit().fsize();
  exec_options.max_mlock_kb = request.resource_limit().mlock();
  exec_options.max_stack_kb = request.resource_limit().stack();

  // Input files.
  for (const auto& input : request.input()) {
    PrepareFile(input, tmp.Path(), &exec_options);
  }

  // Stdout/err files.
  exec_options.stdout_file = util::File::JoinPath(tmp.Path(), "stdout");
  exec_options.stderr_file = util::File::JoinPath(tmp.Path(), "stderr");

  // Actual execution.
  {
    ThreadGuard guard(/*exclusive = */ request.exclusive());
    std::unique_ptr<sandbox::Sandbox> sb = sandbox::Sandbox::Create();
    std::string error_msg;
    if (!sb->Execute(exec_options, &result, &error_msg)) {
      throw std::runtime_error(error_msg);
    }
  }

  proto::Response response;
  response.set_request_id(request.id());

  // Resource usage.
  response.mutable_resource_usage()->set_cpu_time(result.cpu_time_millis /
                                                  1000.0);
  response.mutable_resource_usage()->set_sys_time(result.sys_time_millis /
                                                  1000.0);
  response.mutable_resource_usage()->set_wall_time(result.wall_time_millis /
                                                   1000.0);
  response.mutable_resource_usage()->set_memory(result.memory_usage_kb);

  // Termination status.
  response.set_status_code(result.status_code);
  response.set_signal(result.signal);
  response.set_status(result.signal == 0 ? proto::Status::SUCCESS
                                         : proto::Status::SIGNAL);

  // Output files.
  proto::FileInfo info;
  info.set_type(proto::FileType::STDOUT);
  RetrieveFile(info, tmp.Path(), &response);
  info.set_type(proto::FileType::STDERR);
  RetrieveFile(info, tmp.Path(), &response);
  for (const proto::FileInfo& info : request.output()) {
    RetrieveFile(info, tmp.Path(), &response);
  }
  return response;
}

void LocalExecutor::PrepareFile(const proto::FileInfo& info,
                                const std::string& tmp,
                                sandbox::ExecutionOptions* options) {
  std::string name = info.name();
  if (info.type() == proto::FileType::STDIN) {
    name = "stdin";
    options->stdin_file = util::File::JoinPath(tmp, name);
  } else {
    if (std::find_if(name.begin(), name.end(), IsValidChar) != name.end()) {
      throw std::runtime_error("Invalid file name");
    }
    name = util::File::JoinPath(kBoxDir, name);
  }
  std::string source_path = ProtoSHAToPath(info.hash());
  util::File::Copy(source_path, util::File::JoinPath(tmp, name));
}

void LocalExecutor::RetrieveFile(const proto::FileInfo& info,
                                 const std::string& tmp,
                                 proto::Response* options) {
  std::string name = info.name();
  if (info.type() == proto::FileType::STDIN ||
      info.type() == proto::FileType::STDOUT) {
    name = info.type() == proto::FileType::STDIN ? "stdin" : "stderr";
  } else {
    if (std::find_if(name.begin(), name.end(), IsValidChar) != name.end()) {
      throw std::runtime_error("Invalid file name");
    }
    name = util::File::JoinPath(kBoxDir, name);
  }
  util::SHA256_t hash = util::File::Hash(util::File::JoinPath(tmp, name));
  proto::FileInfo out_info = info;
  util::SHA256ToProto(hash, out_info.mutable_hash());
  std::string destination_path = ProtoSHAToPath(out_info.hash());
  util::File::Copy(util::File::JoinPath(tmp, name), destination_path);

  if (util::File::Size(destination_path) <= util::kChunkSize) {
    util::File::Read(
        destination_path, [&out_info](const proto::FileContents& bf) {
          if (out_info.contents().chunk().size() != 0) {
            throw std::runtime_error("Small file with more than one chunk");
          }
          *out_info.mutable_contents() = bf;
        });
  }

  *options->add_output() = std::move(out_info);
}

void LocalExecutor::MaybeRequestFile(const proto::FileInfo& info,
                                     const RequestFileCallback& file_callback) {
  std::string path = ProtoSHAToPath(info.hash());
  if (util::File::Size(path) >= 0) return;
  if (info.has_contents()) {
    util::File::Write(path)(info.contents());
  } else {
    file_callback(info.hash(), util::File::Write(path));
  }
}

std::string LocalExecutor::ProtoSHAToPath(const proto::SHA256& hash) {
  util::SHA256_t extracted_hash;
  ProtoToSHA256(hash, &extracted_hash);
  return util::File::JoinPath(FLAGS_store_directory,
                              util::File::PathForHash(extracted_hash));
}

void LocalExecutor::GetFile(const proto::SHA256& hash,
                            const util::File::ChunkReceiver& chunk_receiver) {
  util::File::Read(ProtoSHAToPath(hash), chunk_receiver);
}

LocalExecutor::LocalExecutor() {
  util::File::MakeDirs(FLAGS_temp_directory);
  util::File::MakeDirs(FLAGS_store_directory);

  if (FLAGS_num_cores == 0) {
    FLAGS_num_cores = std::thread::hardware_concurrency();
  }
}

LocalExecutor::ThreadGuard::ThreadGuard(bool exclusive)
    : exclusive_(exclusive) {
  std::lock_guard<std::mutex> lck(Mutex());
  if (exclusive_) {
    if (CurThreads() != 0) {
      throw too_many_executions("Exclusive execution failed: worker busy");
    }
    CurThreads() = MaxThreads();
  } else {
    if (CurThreads() == MaxThreads()) {
      throw too_many_executions("Execution failed: worker busy");
    }
    CurThreads()++;
  }
}

LocalExecutor::ThreadGuard::~ThreadGuard() {
  std::lock_guard<std::mutex> lck(Mutex());
  CurThreads() = exclusive_ ? 0 : (CurThreads() - 1);
}

int32_t& LocalExecutor::ThreadGuard::MaxThreads() {
  static int32_t max = FLAGS_num_cores;
  return max;
}

int32_t& LocalExecutor::ThreadGuard::CurThreads() {
  static int32_t cur = 0;
  return cur;
}

std::mutex& LocalExecutor::ThreadGuard::Mutex() {
  static std::mutex mtx;
  return mtx;
}
}  // namespace executor
