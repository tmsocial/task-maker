#include "worker/main.hpp"
#include "sandbox/main.hpp"
#include "server/main.hpp"
#include "util/daemon.hpp"
#include "util/flags.hpp"
#include "util/misc.hpp"
#include "util/version.hpp"

class TaskMakerMain {
 public:
  TaskMakerMain(kj::ProcessContext& context) : context(context) {}
  kj::MainFunc getMain() {
    return kj::MainBuilder(context, "Task-Maker (" + util::version + ")",
                           "The new cmsMake!")
        .addOptionWithArg({'l', "logfile"}, util::setString(Flags::log_file),
                          "<LOGFILE>",
                          "Path where the log file should be stored")
        .addOption({'d', "daemon"}, util::setBool(Flags::daemon),
                   "Become a daemon")
        .addOptionWithArg({'P', "pidfile"}, util::setString(Flags::pidfile),
                          "<PIDFILE>",
                          "Path where the pidfile should be stored")
        .addOptionWithArg({'S', "store-dir"},
                          util::setString(Flags::store_directory), "<DIR>",
                          "Path where the files should be stored")
        .addOptionWithArg({'T', "temp-dir"},
                          util::setString(Flags::temp_directory), "<DIR>",
                          "Path where the sandboxes should be crated")
        .addSubCommand("worker", KJ_BIND_METHOD(wm, getMain), "run the worker")
        .addSubCommand("server", KJ_BIND_METHOD(sm, getMain), "run the server")
        .addSubCommand("sandbox", KJ_BIND_METHOD(bm, getMain),
                       "run the sandbox")
        .build();
  }

 private:
  kj::ProcessContext& context;
  worker::Main wm = context;
  server::Main sm = context;
  sandbox::Main bm = context;
};

KJ_MAIN(TaskMakerMain);
