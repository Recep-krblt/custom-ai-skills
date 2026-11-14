# C11 & Modern C++ (C++17/20/23) Systems Programming

Standards for zero-cost abstractions, leak-free RAII memory management, race-free concurrency, and target-centric CMake builds.

## 1. Memory Ownership & RAII Discipline
- **C++:** Never use raw `new`/`delete`; manage dynamic resources via `std::unique_ptr`, `std::shared_ptr` (with `std::weak_ptr` to break cycles), or RAII wrappers.
- **Zero-Copy Observers:** Pass `std::span<const T>` or `std::string_view` for read-only buffer/string inspection instead of copying containers or smart pointers:
  ```cpp
  #include <span>
  #include <cstdint>

  void ProcessBuffer(std::span<const uint8_t> buffer) {
      for (auto byte : buffer) {
          // Safe, bounds-aware read-only access
      }
  }
  ```
- **C11:** Always check `malloc`/`calloc`/`realloc` return values for `NULL` and immediately set pointers to `NULL` after `free()`.

## 2. Compiler Warnings & Sanitizers (ASan / UBSan / TSan)
Enforce strict compiler warnings and sanitizers in debug/test builds:
- **GCC / Clang:** `-fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Wpedantic -Wconversion -Wshadow`
- **MSVC (Windows):** `/fsanitize=address /W4 /WX /permissive-`

## 3. Target-Centric Modern CMake
Avoid global `include_directories` or `link_libraries`; scope all flags and includes to explicit targets with `PUBLIC`, `PRIVATE`, and `INTERFACE`:
```cmake
cmake_minimum_required(VERSION 3.24)
project(EngineCore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(EngineCore STATIC
    src/buffer.cpp
    src/memory_pool.cpp
)

target_include_directories(EngineCore
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_options(EngineCore PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /permissive->
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall -Wextra -Wpedantic>
)
```

## 4. Verification Gate
- Run a clean CMake build (`cmake --build`) and execute the test suite (`ctest --output-on-failure`) with zero warnings and zero sanitizer violations (`quality-testing-review` (`references/verification-before-completion.md`)).
