---
name: academic-docs-and-pdf
description: Use when writing or auditing TÜBİTAK 2209-A/B proposals/reports, manipulating Word (.docx) OpenXML schemas cleanly, processing/filling PDF files, or writing ADRs and technical documentation.
---

# Academic Reporting, TÜBİTAK 2209, DOCX, PDF & ADRs

Load only the specific protocol guide needed for your document workflow:

| Document / Workflow | Reference Guide | Notes / Scripts |
| :--- | :--- | :--- |
| TÜBİTAK 2209-A/B proposals & reports, TYBS 10-table schema, desk-rejection shield | [references/tubitak-2209-protocol.md](references/tubitak-2209-protocol.md) | Clauses `4.1.8`/`5.1.1`/`6.1` bans & verification gate |
| Word (`.docx`) OpenXML schema, row cloning, metadata hygiene & Word COM check | [references/docx-openxml-standards.md](references/docx-openxml-standards.md) | `NO SILENT ROW TRUNCATION` & hanging indent |
| PDF reading, merging, splitting, form filling & visual page verification | [references/pdf-processing.md](references/pdf-processing.md) | Also: [pdf-forms.md](references/pdf-forms.md), [pdf-reference.md](references/pdf-reference.md), `scripts/*.py` |
| Architecture Decision Records (ADRs), API docs & documentation drift audit | [references/documentation-and-adrs.md](references/documentation-and-adrs.md) | ADR template, JSDoc/OpenAPI & changelog rules |
