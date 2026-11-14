# Surgical Code Edits & Terminal Log Pruning (Token Economy)

## 1. PowerShell & Terminal Output Filtering
Never dump unfiltered `cat`, `Get-Content`, or raw test output into the context window:
- **Stack Trace / Test Failure Filtering:**
  ```powershell
  dotnet test 2>&1 | Select-String -Pattern "FAIL|Error|Exception" -Context 0, 2
  ```
- **Large File / Log Inspection:**
  ```powershell
  Get-Content "app.log" -Tail 50
  Get-Content "large_data.json" -TotalCount 20
  ```
- **Scoped Directory Search:**
  ```powershell
  Get-ChildItem -Path . -Exclude "node_modules", ".git", "dist", "build" -Recurse -Filter "*.ts" | Select-Object -First 30 FullName
  ```

---

## 2. Surgical Code Editing (`edit_file` vs Full Rewrite)
- **Zero Fluff:** Omit conversational filler; focus directly on diagnosis, file paths, and minimal diffs.
- **Targeted Edits Only:** If 3 lines change in a 500-line file, never rewrite the full file—use `edit_file`.
- **Read Before Edit:** Always verify exact target lines and whitespace with `read_file` before calling `edit_file` to prevent retry loops.

---

## 3. Map-First Lookup, Subagent Offloading & Windows UTF-8
- **Map-First Lookup:** Run `python "C:\Users\<USERNAME>\.gemini\config\skills\token-and-context-ops\scripts\generate_repo_map.py" . --find "<symbol>"` to locate exact symbol line ranges (`Lxx`) before reading files (see [repo-map-guide.md](repo-map-guide.md)).
- **Subagent Offloading:** When scanning `10+` files or noisy build logs, delegate to `invoke_subagent` (`TypeName: "research"`) and return only `file#Lx-Ly` evidence.
- **Windows Console UTF-8:**
  ```powershell
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  $env:PYTHONIOENCODING = "utf-8"
  ```
