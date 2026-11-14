# DOCX & OpenXML Architecture Standards

Ensures Word (`.docx`) documents generated via Python (`python-docx`), PowerShell, or direct OpenXML manipulation pass Microsoft Word schema validation with zero corruption, zero silent data truncation, clean metadata, and publication-grade typography.

---

## 1. Negative Constraints (Strict Bans)

1. **No Silent Row Truncation (`NO SILENT ROW TRUNCATION`):**
   * When template row count (`len(table.rows)`) is smaller than the data list, **never silently skip extra rows** with `if idx < len(table.rows):`.
   * Clone the template's last data row at the XML level so `.docx` and parallel `.md`/`.pdf` outputs have identical row counts:
     ```python
     from copy import deepcopy
     while len(table.rows) < len(data_rows) + 1:
         new_tr = deepcopy(table.rows[-1]._tr)
         table._tbl.append(new_tr)
     ```
2. **No Empty Runs (`<w:r>`), Substring Namespace Traps, or Zero-Flag `<w:trPr>`:**
   * Do not leave empty `<w:r>` nodes without text or drawing elements; when clearing a cell, remove existing `<w:p>` and nested `<w:tbl>` nodes first and create a single clean `<w:p>`.
   * Never check paragraph preservation via raw substring `"pict" in p._p.xml` (matches `xmlns:pic=".../picture"` on every `<w:p>`); inspect local tag names via `node.tag.split("}")[-1]` (`sectPr`, `drawing`, `pict`, `numPr`).
   * Template `<w:cantSplit w:val="0"/>` and `<w:tblHeader w:val="0"/>` nodes disable row protection; remove them via `trPr.remove(...)` before appending clean `<w:cantSplit/>` / `<w:tblHeader/>`.
3. **Multi-Line Cells & Template Header Indentation (`<w:ind>` & `\n` Trap):**
   * Never use `\n` (`soft break`) under `WD_ALIGN_PARAGRAPH.JUSTIFY` (stretches short lines); create separate `<w:p>` paragraphs with `WD_ALIGN_PARAGRAPH.LEFT` for multi-item cells.
   * Strip leading/trailing whitespace and tabs from template headers; when centering table headers (`alignment = CENTER`), explicitly reset `left_indent = Pt(0)` and `first_line_indent = Pt(0)`.
4. **No Image–Caption Page Splits:**
   * Always set `p_img.paragraph_format.keep_with_next = True` on paragraphs containing figures so captions never orphan onto the next page.
5. **UTF-8 & Turkish Diacritics Integrity:**
   * Never degrade Turkish characters (`ğ, ü, ş, ı, İ, ö, ç`) to ASCII. Enforce `encoding="utf-8"` on all file I/O, `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`, and cross-platform `pathlib.Path` / `tempfile`.

---

## 2. Schema Integrity & Table Grid (`<w:tblGrid>` & `<w:sectPr>`)

1. **Table Grid Alignment:** `<w:gridCol>` count inside `<w:tblGrid>` must match the sum of cells and `gridSpan` values in every `<w:tr>`. Remove excess rows via `table._tbl.remove(row._tr)` without altering column counts.
2. **Section Properties (`<w:sectPr>`):** The final `<w:sectPr>` must remain the last child of `<w:body>`; never append paragraphs or tables after it.

---

## 3. Academic Bibliography & Hanging Indent

Apply XML-level hanging indentation (`w:left="426"`, `w:hanging="142"`) for clean reference alignment:
```python
pPr = p._p.get_or_add_pPr()
ind = pPr.get_or_add_ind()
ind.set(qn('w:left'), '426')     # 0.75 cm left indent
ind.set(qn('w:hanging'), '142')  # 0.25 cm hanging indent
run = p.add_run(f"[{i}] {ref_text}")
run.font.name = "Arial"
run.font.size = Pt(8.5)
```
* Format with `WD_ALIGN_PARAGRAPH.JUSTIFY`, `keep_together = True`, single line spacing (`1.0`), and `space_after = Pt(1.5–3)` with no empty paragraphs between entries.

---

## 4. Metadata Scrubbing & Multi-Format Sync

* `docProps/core.xml`: Scrub or update `dc:creator` and `cp:lastModifiedBy`; set `dcterms:modified` dynamically via `datetime.now(timezone.utc)` instead of leaving stale template timestamps/authors.
* `docProps/app.xml` & `customXml/*.xml`: Remove stale organization/company metadata from templates.
* **Dual-Output Sync:** When a single script generates both `.docx` and `.md`, enforce 1:1 parity across table row counts, figure paths, and section contents.

---

## 5. Mandatory Verification Gate (`quality-testing-review` (`references/verification-before-completion.md`))

Before delivering any `.docx` artifact, run after the final edit:
1. **OOXML Structural Audit:** Element order, unique bookmark IDs, nested tables = 0, empty bold runs = 0, table grid mismatch = 0.
2. **Word COM Repair-Free Open Check (PowerShell):**
   ```powershell
   $w = New-Object -ComObject Word.Application
   $w.Visible = $false
   $w.DisplayAlerts = 0
   try {
       $d = $w.Documents.Open("<PROJECT_PATH>\document.docx")
       $d.Close([ref]$false)
       Write-Host "DOCX VERIFIED: CLEAN"
   } finally {
       $w.Quit()
   }
   ```
3. **Visual PDF Inspection:** Export to PDF and inspect rendered pages to confirm zero clipped tables/figures and verify that all reported metrics come from live measurements rather than hardcoded values.
