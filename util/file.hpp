#ifndef UTIL_FILE_HPP
#define UTIL_FILE_HPP
#include <functional>

#include "proto/file.pb.h"
#include "util/sha256.hpp"

namespace util {

static const constexpr uint32_t kChunkSize = 32 * 1024;

class File {
 public:
  using ChunkReceiver = std::function<void(const proto::FileContents&)>;

  // Reads the file specified by path in chunks.
  static void Read(const std::string& path,
                   const ChunkReceiver& chunk_receiver);

  // Returns a ChunkReceiver that writes the given data to a file.
  // The file is closed when the ChunkReceiver goes out of scope.
  static ChunkReceiver Write(const std::string& path);

  // Computes the hash of the file specified by path.
  static SHA256_t Hash(const std::string& path);

  // Creates all the folder that are needed to write the specified file
  // or, if path is a directory, creates all the folders.
  static void MakeDirs(const std::string& path);

  // Makes a full copy of the given file.
  static void DeepCopy(const std::string& from, const std::string& to);

  // Copies from -> to, but the files may still share the underlying data.
  static void Copy(const std::string& from, const std::string& to);

  // Moves a file to a new position.
  static void Move(const std::string& from, const std::string& to);

  // Removes a file.
  static void Remove(const std::string& path);

  // Recursively removes a tree.
  static void RemoveTree(const std::string& path);

  // Computes the path for a file with the given hash.
  static std::string PathForHash(const SHA256_t& hash);

  // Joins two paths.
  static std::string JoinPath(const std::string& first,
                              const std::string& second);

  // Computes a file's size. Returns a negative number in case of errors.
  static int64_t Size(const std::string& path);
};

class TempDir {
 public:
  explicit TempDir(const std::string& base);
  const std::string& Path() const;
  void Keep();
  ~TempDir();

  TempDir(TempDir&&) = default;
  TempDir& operator=(TempDir&&) = default;
  TempDir(const TempDir&) = delete;
  TempDir& operator=(const TempDir&) = delete;

 private:
  std::string path_;
  bool keep_ = false;
};

}  // namespace util

#endif
