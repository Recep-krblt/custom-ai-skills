# Memory Leak & CPU Profiling Guide

## 1. Common Memory Leak Sources (Heap Analysis)

1. **Lingering Event Listeners:** `window.addEventListener` or `ipcRenderer.on` subscriptions left active after component unmount or DOM removal.
2. **Uncleared Timers:** `setInterval` or `setTimeout` handles never cleared via `clearInterval` / `clearTimeout`.
3. **Detached DOM Nodes:** Removed HTML elements still referenced by JavaScript variables, caches, or arrays.
4. **Unbounded Closures / Caches:** Long-lived closures or in-memory maps retaining large object graphs without eviction.

---

## 2. Two-Snapshot Heap Comparison Workflow (Chrome DevTools / Node.js)

1. **Baseline Snapshot:** Capture Heap Snapshot 1 after initial application load.
2. **Repeat Suspect Action:** Trigger the suspect lifecycle 5–10 times (e.g., open/close modal, copy clipboard item).
3. **Force GC:** Trigger garbage collection explicitly.
4. **Comparison Snapshot:** Capture Heap Snapshot 2 and select **"Objects allocated between Snapshot 1 and 2"**. Monotonically growing counts of `EventListener`, `Detached HTMLDivElement`, or `Buffer` pinpoint the leak root.

---

## 3. CPU Flamegraph & Event Loop Blocking
- Any synchronous task exceeding **50 ms** on the main thread causes UI jank or event-loop starvation.
- Offload heavy loops/parsing to Web Workers, worker threads, or chunked async scheduling (`setImmediate` / `requestAnimationFrame`).
