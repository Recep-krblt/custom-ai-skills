# TÜBİTAK 2209-A/B Grant Proposal & Report Protocol

Ensures TÜBİTAK 2209-A and 2209-B proposals and reports strictly comply with the official TYBS template, call rules (including desk-rejection filters), claim-to-source fidelity, and brand/institution anonymization. *(All examples below are synthetic illustrative examples.)*

---

## 1. Negative Constraints (Desk-Rejection Shield)

1. **No Brand, Commercial Product, or Institution Promotion (Call Clauses 4.1.8 & 5.1.1):**
   * **Desk-rejection risk.** Never mention commercial brands, companies, hardware models, commercial cloud/hosting services, or host university/institution names in the Title, Abstract, Sections 1.1, 1.2, 2 (**including flowcharts and figure captions**), 3.1–3.3, 4, or 5.
   * **Illustrative Examples (Forbidden → Required Generic Turkish Equivalent):**
     - `Raspberry Pi 5 / NVIDIA Jetson` → `gömülü uç birim hesaplama kartı / harici hızlandırıcı`
     - `AWS S3 / Google Firebase` → `bulut tabanlı veri depolama ve senkronizasyon altyapısı`
     - `MATLAB / SolidWorks` → `sayısal analiz ve üç boyutlu simülasyon yazılımı`
     - `GitHub / GitLab deposu` → `açık erişimli sürüm kontrol ve kod deposu`
     - `X Üniversitesi Merkez Laboratuvarı` → `ilgili bölüm araştırma laboratuvarı`
   * **Exceptions:** The mandatory `Kurum/Kuruluş` field in Table 0 (`A. Genel Bilgiler`), academic citations in `EK-1: Kaynaklar`, and standard open-source languages/protocols (`Python`, `OpenCV`, `REST API`, `MQTT`, etc.).
2. **No Fixed Calendar Dates or Forbidden Work-Package Activities (Call Clause 6.1):**
   * Project duration is at most **12 months** from announcement; never write fixed dates (`01.03.2027 – 29.02.2028`). Use relative month intervals only (`1.–3. ay`, `4.–6. ay`, etc.; total `≤ 12 ay`).
   * Never include these forbidden terms in work-package titles, tasks, or success criteria: `literatür taraması`, `sonuç raporu hazırlama`, `dokümantasyon`, `akademik bildiri/makale metni tamamlama`, `sonuçların paylaşımı`, `malzeme alımı`.
   * *Illustrative Example:* Replace `"performans raporu hazırlama"` with **`"performans analizi çıktılarının elde edilmesi"`**. Place dissemination/publication targets only in Section 4 (`Yaygın Etki`).
3. **Data / Material Access Feasibility:**
   * If datasets or experimental materials require external permissions, quotas, or field access, align: (a) acquisition plan in Section 2 (`Yöntem`), (b) preparation task in WP-1 (`İP-1`), and (c) concrete **Plan B** (e.g., open-access fallback dataset or synthetic generation) in Section 3.2 (`Risk Yönetimi`).
4. **No Leftover Placeholders:** Never leave template instructions or placeholders (`[...doldur...]`, `GÜNCELLEME LAZIM`) in final `.docx`, `.md`, or `.pdf` deliverables.

---

## 2. Academic Style & Claim-to-Source Fidelity ("Zero-Slop & Fidelity")

1. **No First-Person Plural or Hyperbole:** Never use `görmekteyiz`, `planlıyoruz`, `projemiz`, `çalışmamızda`, `devrim niteliğinde`, `en iyi`, `son derece`, `üstünlük`. Write in objective, passive academic Turkish.
2. **Claim-to-Source Fidelity Gate:**
   * **Topic Alignment:** Cite dataset or single-component papers only for dataset/split/baseline facts, never for broad domain claims.
   * **Do Not Attribute Novel Contributions to Prior Work:** Clearly separate what prior literature established from the novel components proposed by the project.
   * **Scope, Protocol & Domain Accuracy:** Explicitly state domain differences *(Illustrative Example: `uydu görüntüsü` vs `mikroskobik görüntü`)* and analytical estimation vs empirical measurement; attribute official dataset splits only to the primary dataset paper; never claim `"üstünlük"` without direct comparative evidence.
   * **Illustrative Numbers vs Empirical Findings:** Never merge an author's illustrative figure *(Illustrative Example: `örneğin %15 paket kaybı`)* with a cited study's empirical finding in the same clause. Only label a study `"küçük ölçekli"` after verifying its actual sample size.
   * **Cross-Section Metric & Policy Consistency:** Keep target metrics and decision thresholds *(Illustrative Example: `F1-Skoru ≥ 0.85` or `gecikme ≤ 50 ms`)* identical across Sections `1.2`, `2`, `3.1`, and `5`. Cite national policy documents only with verified clause numbers and exact official institution names matching `EK-1`.
   * **Epistemic Caution:** Write **`"raporlanmamıştır"`** instead of `"ölçülmemiştir"` when a metric is absent from a paper; use cautious phrasing (`göz önünde tutulmalıdır`) for unverified generalizations. Enforce `< 3` non-citation parentheses per sentence and `≤ 45` words per sentence.

---

## 3. In-Text Citations, Bibliography (`EK-1`) & Figures

* **In-Text Citations (Author-Year):** Never use bracketed numbers `[1]` in body text. *Illustrative Examples:* `(Kaya, 2019)`, `(Kaya ve Demir, 2021)`, `(Arslan vd., 2023)`, `(Yılmaz vd., 2020; Çelik ve Aydın, 2022)`.
* **Bibliography (`EK-1`):** Sort **alphabetically** by first author surname (`[1] ...` numbered prefix in alphabetical order), include mandatory `DOI:` when available, full URL + `Son erişim tarihi: Gün Ay Yıl.` for web sources, Arial `8.5 pt`, XML hanging indent (`w:left="426" w:hanging="142"`). Every listed reference must be cited in the text where it directly supports the claim.
* **Dual-Figure Flow:** When including both conceptual and detailed architecture diagrams in Section 2, follow **General Overview → Figure 1 (Conceptual Flow) → Transition → Figure 2 (Detailed Architecture) → Phase-by-Phase Breakdown**. Export figures at `≥ 300 DPI` (`.png`/`.jpg`) with zero brand or institution names in labels or captions.

---

## 4. TYBS 10-Table Architecture & Budget

* **Table 0 (`Genel Bilgiler`):** Lead, Title, Advisor, Institution (mandatory field).
* **Table 1 (`Özet`):** 25–450 words (ideal 300–360); covers scientific quality, objective, method, and expected output; zero brand names.
* **Table 2 (`1.1 Bilimsel Nitelik`) & Table 3 (`1.2 Amaç ve Hedefler`):** `≥ 350` chars each; literature gap, strategic alignment, and SMART targets.
* **Table 4 (`2. Yöntem`):** `≥ 350` chars; variables, data/material acquisition plan, experimental protocol, evaluation metrics, formulas, and figure references.
* **Table 5 (`3.1 Çalışma Takvimi`):** Relative month ranges (`1.–3. ay`, etc.), total `≤ 12 ay`, contribution sum **exactly 100%**, zero forbidden activity terms.
* **Table 6 (`3.2 Risk Yönetimi`):** All critical risks with concrete Plan B mitigations; clone template rows so no risk row is truncated (`DOCX = MD` parity).
* **Table 7 (`3.3 Araştırma Olanakları`):** Generic hardware, lab, open-source software, and compute descriptions with zero commercial brands.
* **Table 8 (`4. Yaygın Etki`):** Academic/technical outputs, open-access sharing targets, and researcher training impact.
* **Table 9 (`5. Diğer Konular`):** Decision/evaluation criteria summary and call-specific notes.
* **Budget (TYBS Portal):** Generic hardware/service/consumable items within the active call ceiling.

---

## 5. Mandatory Pre-Submission Checklist (Verification Gate)

1. Confirm `0` matches for commercial brands, hardware models, commercial cloud services, or host institution promotion across body text and figures (`grep`).
2. Verify consistency between data/material acquisition (Section 2 & WP-1) and access-risk Plan B (Section 3.2).
3. Confirm relative month ranges (`1.–3. ay`), `100%` contribution sum, and absence of `literatür taraması`, `dokümantasyon`, or `bildiri/rapor yazımı` in WP tables.
4. Verify every citation against primary source abstracts/full text.
5. Run project audit scripts (1st-person plural ban, epistemic checks, `< 3` non-citation parentheses, sentence length, and OOXML schema validation — `0 errors, 0 warnings`) **after** the final edit.
