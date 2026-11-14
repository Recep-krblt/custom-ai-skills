# Win32 & Electron Desktop Architecture

Standards for memory safety, non-blocking IPC, OS hook stability, and child-process cleanup in Windows and cross-platform desktop apps.

## 1. Win32 Clipboard Hooks & Deadlock Prevention
- **Use `AddClipboardFormatListener(hwnd)`:** Never use legacy `SetClipboardViewer` chains. Always call `RemoveClipboardFormatListener(hwnd)` on `WM_DESTROY` / shutdown to prevent OS handle leaks.
- **`OpenClipboard` Exponential Backoff:** Another process may temporarily lock the clipboard (`CLIPBRD_E_CANT_OPEN` / `0x800401D0`). Never block indefinitely:
  ```cpp
  int max_retries = 5;
  int delay_ms = 10;
  BOOL opened = FALSE;

  for (int i = 0; i < max_retries; ++i) {
      if (OpenClipboard(hwnd)) {
          opened = TRUE;
          break;
      }
      Sleep(delay_ms);
      delay_ms *= 2;
  }
  if (!opened) return ERROR_CLIPBOARD_LOCKED;
  // Read clipboard data...
  CloseClipboard();
  ```

## 2. Electron Process Isolation & Type-Safe Preload
- Enforce `nodeIntegration: false`, `contextIsolation: true`, `sandbox: true`, and `webSecurity: true`.
- **Ban `ipcRenderer.sendSync`:** Never block the main process event loop; always use async `ipcRenderer.invoke` / `ipcMain.handle`.
- **Return Unsubscribe Disposers in Preload:**
  ```typescript
  import { contextBridge, ipcRenderer, IpcRendererEvent } from 'electron';

  contextBridge.exposeInMainWorld('desktopAPI', {
    onClipboardUpdate: (callback: (payload: ClipboardItem) => void) => {
      const handler = (_event: IpcRendererEvent, payload: ClipboardItem) => callback(payload);
      ipcRenderer.on('clipboard:update', handler);
      return () => ipcRenderer.removeListener('clipboard:update', handler);
    },
    copyToClipboard: (data: ClipboardItem) => ipcRenderer.invoke('clipboard:write', data),
  });
  ```

## 3. High-Frequency Events & Memory Discipline
- **List Virtualization:** Render only visible viewport rows (`react-window` or virtual scroller) for high-frequency clipboard/event streams.
- **Large Binary Payloads:** Stream heavy image/RTF buffers to disk or SQLite BLOB storage with bounded cache instead of retaining them in main-process RAM.

## 4. Navigation Lockdown, CSP & Subprocess Cleanup
```ts
win.webContents.setWindowOpenHandler(({ url }) => {
  if (url.startsWith('https://')) shell.openExternal(url);
  return { action: 'deny' };
});

win.webContents.on('will-navigate', (event, targetUrl) => {
  if (!targetUrl.startsWith('app://') && !targetUrl.startsWith('http://localhost')) {
    event.preventDefault();
  }
});
```
- **CSP:** Enforce `default-src 'self'; script-src 'self'; object-src 'none';`.
- **Orphan Process Prevention:** Terminate spawned child process trees on `before-quit` using Win32 Job Objects or `taskkill /F /T /PID <pid>` (`quality-testing-review` (`references/verification-before-completion.md`)).
