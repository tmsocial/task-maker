#include "core/execution.hpp"
#include "executor/local_executor.hpp"
#include "executor/remote_executor.hpp"

namespace core {

std::atomic<int32_t> Execution::next_id_{1};

FileID* Execution::Output(const std::string& name,
                          const std::string& description) {
  if (outputs_.count(name) == 0) {
    outputs_.emplace(name, std::unique_ptr<FileID>(
                               new FileID(store_directory_, description)));
  }
  return outputs_.at(name).get();
}

std::vector<int64_t> Execution::Deps() const {
  std::vector<int64_t> result;
  if (stdin_ != 0) result.push_back(stdin_->ID());
  for (const auto& in : inputs_) result.push_back(in.second->ID());
  return result;
}

std::vector<int64_t> Execution::Produces() const {
  std::vector<int64_t> result;
  result.push_back(stdout_->ID());
  result.push_back(stderr_->ID());
  for (const auto& out : outputs_) result.push_back(out.second->ID());
  return result;
}

proto::Response Execution::RunWithCache(executor::Executor* executor,
                                        const proto::Request& request) {
  proto::Response response;
  cached_ = true;
  if (caching_mode_ == CachingMode::ALWAYS) {
    if (cacher_->Get(request, &response)) return response;
  } else if (caching_mode_ == CachingMode::SAME_EXECUTOR) {
    if (cacher_->Get(request, executor->Id(), &response)) return response;
  }
  cached_ = false;
  try {
    response = executor->Execute(
        request, [this](const proto::SHA256& hash,
                        const util::File::ChunkReceiver& chunk_receiver) {
          util::File::Read(util::File::ProtoSHAToPath(store_directory_, hash),
                           chunk_receiver);
        });
    if (response.status() != proto::Status::INTERNAL_ERROR)
      cacher_->Put(request, executor->Id(), response);
  } catch (std::exception& ex) {
    if (ex.what() == std::string("exec: Exec format error")) {
      response.set_status(proto::Status::NOT_EXECUTABLE);
      response.set_error_message(std::string("Execution error: ") + ex.what());
    } else {
      response.set_status(proto::Status::INTERNAL_ERROR);
      response.set_error_message(std::string("Sandbox error: ") + ex.what());
    }
  }
  return response;
}

void Execution::Run(
    const std::function<util::SHA256_t(int64_t)>& get_hash,
    const std::function<void(int64_t, const util::SHA256_t&)>& set_hash) {
  std::unique_ptr<executor::Executor> executor;
  if (executor_.empty()) {
    executor.reset(new executor::LocalExecutor(store_directory_,
                                               temp_directory_, num_cores_));
  } else {
    executor.reset(new executor::RemoteExecutor(executor_));
  }

  // Command and args.
  proto::Request request;
  request.set_executable(executable_);
  request.set_keep_sandbox(keep_sandbox_);
  for (const std::string& arg : args_) *request.add_arg() = arg;
  for (const auto& out : outputs_) request.add_output()->set_name(out.first);

  // Inputs.
  auto prepare_input = [&request, &get_hash, this](FileID* id,
                                                   const char* name) {
    proto::FileInfo* in = request.add_input();
    if (*name == 0) in->set_type(proto::FileType::STDIN);
    in->set_name(name);
    util::File::SetSHA(store_directory_, get_hash(id->ID()), in);
    if (id->IsExecutable())
      in->set_executable(true);
  };
  if (stdin_ != nullptr) prepare_input(stdin_, "");
  for (const auto& input : inputs_)
    prepare_input(input.second, input.first.c_str());

  // Output names.
  for (const auto& output : outputs_)
    request.add_output()->set_name(output.first);

  // Resource limits and exclusivity.
  *request.mutable_resource_limit() = resource_limits_;
  request.set_extra_time(extra_time_);
  request.set_exclusive(exclusive_);

  // TODO(veluca): FIFO, as soon as we support them anywhere.

  // Run the request.
  response_ = RunWithCache(executor.get(), request);

  if (response_.status() == proto::Status::INTERNAL_ERROR) {
    throw std::runtime_error(response_.error_message());
  }

  successful_ = response_.status() == proto::Status::SUCCESS;
  message_ = response_.error_message();

  // Read output files.
  for (const proto::FileInfo& out : response_.output()) {
    std::string path = util::File::ProtoSHAToPath(store_directory_, out.hash());
    // skip the file if it already exists
    if (util::File::Size(path) < 0) {
      if (out.has_contents()) {
        util::File::Write(path, out.contents());
      } else {
        if (cached_)
          throw std::runtime_error("Cached request with missing output");
        using std::placeholders::_1;
        util::File::Write(path, std::bind(&executor::Executor::GetFile,
                                          executor.get(), out.hash(), _1));
      }
    }
    util::SHA256_t extracted_hash;
    util::ProtoToSHA256(out.hash(), &extracted_hash);
    int64_t id = 0;
    if (out.type() == proto::FileType::STDOUT) {
      stdout_->SetHash(out.hash());
      id = stdout_->ID();
    } else if (out.type() == proto::FileType::STDERR) {
      stderr_->SetHash(out.hash());
      id = stderr_->ID();
    } else {
      if (outputs_.count(out.name()) == 0)
        throw std::logic_error("Unrequested output");
      outputs_.at(out.name())->SetHash(out.hash());
      id = outputs_.at(out.name())->ID();
    }
    if (successful_) set_hash(id, extracted_hash);
  }
}

}  // namespace core
