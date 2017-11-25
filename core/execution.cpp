#include "core/execution.hpp"
#include "executor/local_executor.hpp"

namespace core {

const FileID& Execution::Output(const std::string& name,
                                const std::string& description) {
  if (!outputs_.count(name)) {
    outputs_.emplace(name, FileID(description));
  }
  return outputs_.at(name);
}

std::vector<int64_t> Execution::Deps() const {
  std::vector<int64_t> result;
  if (stdin_) result.push_back(stdin_);
  for (const auto& in : inputs_) result.push_back(in.second.Id());
  return result;
}

bool Execution::Run(
    const std::function<util::SHA256_t(int64_t)>& get_hash,
    const std::function<void(int64_t, const util::SHA256_t&)>& set_hash) {
  // TODO(veluca): change this when we implement remote executors.
  std::unique_ptr<executor::Executor> executor{new executor::LocalExecutor()};

  // Command and args.
  proto::Request request;
  request.set_executable(executable_);
  for (const std::string& arg : args_) *request.add_arg() = arg;
  for (const auto& out : outputs_) request.add_output()->set_name(out.first);

  // Inputs.
  auto prepare_input = [&request, &get_hash](int64_t id, const char* name) {
    proto::FileInfo* in = request.add_input();
    if (!*name) in->set_type(proto::FileType::STDIN);
    in->set_name(name);
    util::File::SetSHA(get_hash(id), in);
  };
  if (stdin_) prepare_input(stdin_, "");
  for (const auto& input : inputs_)
    prepare_input(input.second.Id(), input.first.c_str());

  // Output names.
  for (const auto& output : outputs_)
    request.add_output()->set_name(output.first);

  // Resource limits and exclusivity.
  *request.mutable_resource_limit() = resource_limits_;
  request.set_exclusive(exclusive_);

  // TODO(veluca): FIFO, as soon as we support them anywhere.

  // Run the request.
  response_ = executor->Execute(
      request, [](const proto::SHA256& hash,
                  const util::File::ChunkReceiver& chunk_receiver) {
        util::File::Read(util::File::ProtoSHAToPath(hash), chunk_receiver);
      });

  if (response_.status() != 0 || response_.signal() != 0) {
    if (!die_on_error_) return false;
    throw execution_failure();
  }

  // Read output files.
  for (const proto::FileInfo& out : response_.output()) {
    std::string path = util::File::ProtoSHAToPath(out.hash());
    if (util::File::Size(path) >= 0) continue;
    if (out.has_contents()) {
      util::File::Write(path)(out.contents());
    } else {
      executor->GetFile(out.hash(), util::File::Write(path));
    }
    util::SHA256_t extracted_hash;
    util::ProtoToSHA256(out.hash(), &extracted_hash);
    int64_t id = 0;
    if (out.type() == proto::FileType::STDOUT) {
      util::ProtoToSHA256(out.hash(), &stdout_.hash_);
      id = stdout_.Id();
    } else if (out.type() == proto::FileType::STDERR) {
      util::ProtoToSHA256(out.hash(), &stderr_.hash_);
      id = stderr_.Id();
    } else {
      if (outputs_.count(out.name()) == 0)
        throw std::logic_error("Unrequested output");
      util::ProtoToSHA256(out.hash(), &outputs_.at(out.name()).hash_);
      id = outputs_.at(out.name()).Id();
    }
    set_hash(id, extracted_hash);
  }
  return true;
}

}  // namespace core
