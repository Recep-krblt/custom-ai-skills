---
name: systems-and-desktop
description: Use when writing C11/modern C++ (C++17/20/23), CMake targets, sanitizers, Electron main/preload/IPC security, Win32 API hooks (clipboard), or native Node C++ addons.
---

# C/C++ Systems Programming & Desktop Electron/Win32 Architecture

Load the system layer reference matching your task:

| Domain | Reference Guide | Coverage |
| :--- | :--- | :--- |
| C11, C++17/20/23, RAII, smart pointers, CMake, ASan/UBSan | [references/c-cpp-systems.md](references/c-cpp-systems.md) | `std::unique_ptr`, target-centric CMake, `ctest` gate |
| Electron IPC isolation, CSP, Win32 clipboard hooks, native DLLs | [references/desktop-electron-win32.md](references/desktop-electron-win32.md) | `contextIsolation`, `OpenClipboard` backoff, Job cleanup |
