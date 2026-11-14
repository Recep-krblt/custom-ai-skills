# Go (Golang) Concurrency & Service Architecture

Standards for idiomatic, race-free, leak-free, high-throughput Go services and CLI tools.

## Core Principles

1. **Idiomatic Error Handling & Context Propagation:**
   - Never ignore errors (`_ = doSomething()`); wrap with `%w` (`fmt.Errorf("...: %w", err)`).
   - Pass `ctx context.Context` as the first parameter across all I/O and goroutine boundaries to enforce cancellation and deadlines.
2. **Bounded Concurrency & Leak Prevention:**
   - Use bounded **Worker Pools** instead of spawning unbounded goroutines.
   - Always run tests with the race detector (`go test -race ./...`).
3. **Resilient HTTP & Graceful Shutdown:**
   - Never use `http.DefaultClient`; configure an explicit `http.Client{Timeout: 10 * time.Second}`.
   - Trap `SIGTERM`/`SIGINT` to drain in-flight requests cleanly.
4. **Verification Gate:**
   - Run `go vet ./...` and `go test -race ./...` (or `go test ./...` when CGO is disabled on Windows) and verify clean output (`quality-testing-review` (`references/verification-before-completion.md`)).

---

## 1. Bounded Concurrency: Worker Pool Pattern

```go
package main

import (
	"context"
	"fmt"
	"sync"
)

type Job struct {
	ID    int
	Input string
}

type Result struct {
	JobID  int
	Output string
	Err    error
}

func Worker(ctx context.Context, id int, jobs <-chan Job, results chan<- Result, wg *sync.WaitGroup) {
	defer wg.Done()
	for {
		select {
		case <-ctx.Done():
			return
		case job, ok := <-jobs:
			if !ok {
				return
			}
			results <- Result{JobID: job.ID, Output: fmt.Sprintf("Worker %d: processed %s", id, job.Input)}
		}
	}
}
```

---

## 2. Graceful Shutdown (`SIGTERM` / `SIGINT`)

```go
ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
defer stop()

srv := &http.Server{Addr: ":8080", Handler: router}

go func() {
    if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
        slog.Error("server error", "err", err)
    }
}()

<-ctx.Done()
shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()

if err := srv.Shutdown(shutdownCtx); err != nil {
    slog.Error("forced shutdown error", "err", err)
}
```

---

## 3. Structured Logging (`log/slog`)

Use Go 1.21+ structured JSON logging instead of unstructured text logs:
```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
slog.SetDefault(logger)
slog.Info("order processed", "orderId", 1234, "latencyMs", 42)
```
