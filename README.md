# Custom AI Skills

**[Türkçe](#türkçe-özet) | [English](#english-overview) | [Kurulum & Kullanım / Installation](#kurulum-ve-kullanım--installation)**

Antigravity, Claude Code, Cursor ve benzeri yapay zekâ kodlama ajanları için oluşturulmuş ve özelleştirilmiş **12 modüler yetenek (skill)** paketinin kişisel verilerden arındırılmış arşividir. Her yetenek; düşük başlangıç bağlam maliyeti için kısa bir `SKILL.md` yönlendiricisi, ilgili `references/` belgeleri ve yardımcı `scripts/` araçlarıyla birlikte gelir.

> This repository curates **12 customized AI agent skill packs** across software engineering, quality/security, workflow automation, Turkish academic writing, and data science—scrubbed of local machine paths, credentials, and private project identifiers.

---

## Türkçe Özet

Bu depodaki yetenekler, sistemdeki varsayılan/yerleşik yetenekler ve dışarıdan olduğu gibi kurulan eklentiler dışarıda bırakılarak yalnızca bizzat oluşturulan veya özelleştirilen paketlerden seçilmiştir. Tüm dosyalar aşağıdaki 5 ana kategori altında toplanmıştır:

| Kategori | Yetenek (Skill) | Açıklama | Referans / Betik |
| :--- | :--- | :--- | :--- |
| `yazilim-gelistirme/` | [`backend-and-sql`](yazilim-gelistirme/backend-and-sql/SKILL.md) | Node, Go, Python ve Java Spring Boot 3 ile REST API geliştirme, Go eşzamanlılık desenleri ve PostgreSQL/MySQL/SQLite şema, sorgu ve işlem (transaction) optimizasyonu. | 4 referans |
| `yazilim-gelistirme/` | [`web-frontend-suite`](yazilim-gelistirme/web-frontend-suite/SKILL.md) | React, Next.js, Astro, Tailwind CSS ve HTML/CSS arayüz geliştirme, Core Web Vitals optimizasyonu, görsel tasarım ilkeleri ve Playwright tarayıcı test otomasyonu (`with_server.py`). | 4 referans, 1 betik |
| `yazilim-gelistirme/` | [`systems-and-desktop`](yazilim-gelistirme/systems-and-desktop/SKILL.md) | Modern C11/C++17–23, CMake, sanitizer kullanımı, Electron main/preload/IPC güvenliği, Win32 API kancaları ve native Node C++ eklentileri (`systems-desktop-pro` eklenti yeteneği). | 2 referans |
| `kalite-guvenlik-ve-mimari/` | [`workflow-planning-execution`](kalite-guvenlik-ve-mimari/workflow-planning-execution/SKILL.md) | Özellik tasarımı, uygulama planı bölme, tekli veya alt-ajan destekli adım adım yürütme, paralel ajan koordinasyonu ve görev doğrulama (`sdd_helper.py`). | 16 referans, 1 betik |
| `kalite-guvenlik-ve-mimari/` | [`quality-testing-review`](kalite-guvenlik-ve-mimari/quality-testing-review/SKILL.md) | Kök neden analizi, zaman aşımı korumalı TDD (`run_with_timeout.py`), kararsız test temizliği (`find_polluter.py`), kod sadeleştirme ve tamamlama öncesi doğrulama kapısı. | 13 referans, 2 betik |
| `kalite-guvenlik-ve-mimari/` | [`cyber-security-analyst`](kalite-guvenlik-ve-mimari/cyber-security-analyst/SKILL.md) | Kimlik doğrulama/yetkilendirme denetimi (BOLA/IDOR), SSRF ve dosya yolu güvenliği, kriptografi/ağ incelemesi, web güvenlik başlıkları ve gizli bilgi hijyeni. | 4 referans |
| `verimlilik-ve-otomasyon/` | [`token-and-context-ops`](verimlilik-ve-otomasyon/token-and-context-ops/SKILL.md) | Artırımlı önbellekli `.repo-map.md` üretici/sorgulayıcı (`generate_repo_map.py`), çapraz dosya bağları, `--compact`/`--changed`/`--stats`/`--check`, `.github/workflows` ayrıştırma, `rtk` log budama ve bağlam bütçesi yönetimi. | 3 referans, 1 betik |
| `verimlilik-ve-otomasyon/` | [`devops-git-cicd`](verimlilik-ve-otomasyon/devops-git-cicd/SKILL.md) | Git iş akışları (worktree, rebase, reflog kurtarma), çok aşamalı Dockerfile/Compose kurulumları ve güvenli GitHub Actions CI/CD hatları. | 3 referans |
| `verimlilik-ve-otomasyon/` | [`skill-and-mcp-tools`](verimlilik-ve-otomasyon/skill-and-mcp-tools/SKILL.md) | Yetenek/eklenti tasarımı ve doğrulama (`validate_skills.py`), ayrıca Python (FastMCP) ve TypeScript MCP sunucusu geliştirme ile değerlendirme araçları. | 8 referans, 5 yardımcı dosya |
| `akademik-ve-yazim/` | [`academic-docs-and-pdf`](akademik-ve-yazim/academic-docs-and-pdf/SKILL.md) | TÜBİTAK 2209-A/B başvuru ve rapor standartları, temiz Word (`.docx`) OpenXML şema düzenleme, PDF form doldurma/doğrulama betikleri ve ADR teknik dokümantasyon (`turkish-academic-docs` eklenti yeteneği). | 6 referans, 8 PDF betiği |
| `akademik-ve-yazim/` | [`dogal-turkce-metin-ustasi`](akademik-ve-yazim/dogal-turkce-metin-ustasi/SKILL.md) | Akademik, teknik ve eğitsel Türkçe metinlerde İngilizce çeviri kokan kalıpları, yapay zekâ klişelerini ve doğrulanmamış epistemik abartıları önleme kılavuzu. | 2 referans |
| `yapay-zeka-ve-veri-bilimi/` | [`ai-data-science-master`](yapay-zeka-ve-veri-bilimi/ai-data-science-master/SKILL.md) | Tabular ML iş akışları, veri sızıntısı önleyen Scikit-learn `Pipeline` mimarisi, LightGBM/XGBoost/CatBoost, Optuna ve SHAP açıklanabilirlik standartları (`ml-data-science` eklenti yeteneği). | 2 referans |

---

## English Overview

All 12 skill packages are self-contained inside 5 thematic folders. Built-in defaults, untouched marketplace extensions, private workspace rules, and local machine logs were excluded before publishing.

| Category | Skill | Summary | Assets |
| :--- | :--- | :--- | :--- |
| `yazilim-gelistirme/` | [`backend-and-sql`](yazilim-gelistirme/backend-and-sql/SKILL.md) | REST API architecture (Node/Go/Python/Java Spring Boot 3), Go concurrency patterns, and SQL schema, query, and transaction optimization. | 4 refs |
| `yazilim-gelistirme/` | [`web-frontend-suite`](yazilim-gelistirme/web-frontend-suite/SKILL.md) | React, Next.js, Astro, Tailwind CSS UI engineering, Core Web Vitals tuning, aesthetic design guidance, and Playwright E2E helper (`with_server.py`). | 4 refs, 1 script |
| `yazilim-gelistirme/` | [`systems-and-desktop`](yazilim-gelistirme/systems-and-desktop/SKILL.md) | Modern C11/C++17–23, CMake & sanitizers, Electron IPC/preload security, Win32 API hooks, and native Node C++ addons (`systems-desktop-pro` plugin skill). | 2 refs |
| `kalite-guvenlik-ve-mimari/` | [`workflow-planning-execution`](kalite-guvenlik-ve-mimari/workflow-planning-execution/SKILL.md) | Spec breakdown, brainstorming, single-session/subagent execution loops, parallel dispatch, and state tracking (`sdd_helper.py`). | 16 refs, 1 script |
| `kalite-guvenlik-ve-mimari/` | [`quality-testing-review`](kalite-guvenlik-ve-mimari/quality-testing-review/SKILL.md) | Root-cause debugging, timeout-guarded TDD (`run_with_timeout.py`), test-pollution discovery (`find_polluter.py`), code simplification, and verification gates. | 13 refs, 2 scripts |
| `kalite-guvenlik-ve-mimari/` | [`cyber-security-analyst`](kalite-guvenlik-ve-mimari/cyber-security-analyst/SKILL.md) | BOLA/IDOR auditing, SSRF/path boundary threat modeling, cryptography & network review, web security headers, and secret hygiene. | 4 refs |
| `verimlilik-ve-otomasyon/` | [`token-and-context-ops`](verimlilik-ve-otomasyon/token-and-context-ops/SKILL.md) | Incremental v4 repository mapper (`generate_repo_map.py`) producing `.repo-map.md`, cross-file wiring, hardened `--compact`/`--changed`/`--stats`/`--check` CLI, `.github/workflows` indexing, `rtk` log pruning, and context-budget rules. | 3 refs, 1 script |
| `verimlilik-ve-otomasyon/` | [`devops-git-cicd`](verimlilik-ve-otomasyon/devops-git-cicd/SKILL.md) | Git recovery/worktree/rebase patterns, hardened multi-stage Docker/Compose setups, and secure GitHub Actions CI/CD pipelines. | 3 refs |
| `verimlilik-ve-otomasyon/` | [`skill-and-mcp-tools`](verimlilik-ve-otomasyon/skill-and-mcp-tools/SKILL.md) | Skill/plugin authoring & linting (`validate_skills.py`), plus Python (FastMCP) and TypeScript MCP server implementation & evaluation harnesses. | 8 refs, 5 helpers |
| `akademik-ve-yazim/` | [`academic-docs-and-pdf`](akademik-ve-yazim/academic-docs-and-pdf/SKILL.md) | TÜBİTAK 2209-A/B grant standards, Word (`.docx`) OpenXML editing, PDF form/annotation tooling, and ADR technical documentation (`turkish-academic-docs` plugin skill). | 6 refs, 8 PDF scripts |
| `akademik-ve-yazim/` | [`dogal-turkce-metin-ustasi`](akademik-ve-yazim/dogal-turkce-metin-ustasi/SKILL.md) | Eliminates translationese, AI clichés, and unsupported epistemic claims in academic and technical Turkish prose. | 2 refs |
| `yapay-zeka-ve-veri-bilimi/` | [`ai-data-science-master`](yapay-zeka-ve-veri-bilimi/ai-data-science-master/SKILL.md) | Leakage-free Scikit-learn `Pipeline` standards for tabular ML, gradient boosting (LightGBM/XGBoost/CatBoost), Optuna, and SHAP XAI (`ml-data-science` plugin skill). | 2 refs |

---

## Kurulum ve Kullanım / Installation

1. Kullanmak istediğiniz yetenek klasörünü ajanınızın global yetenek dizinine kopyalayın (örneğin `~/.gemini/config/skills/`, `~/.claude/skills/` veya `~/.cursor/skills/`):
   ```bash
   # Örnek: token-and-context-ops yeteneğini kurma
   cp -r verimlilik-ve-otomasyon/token-and-context-ops ~/.gemini/config/skills/
   ```
2. Bazı doküman ve komut örneklerindeki yer tutucuları kendi ortamınıza göre güncelleyin:
   - `<USERNAME>`, `<PROJECT_PATH>`: yerel kullanıcı adınız ve proje dosya yolunuz
   - `<PROJECT_NAME>`: örnek komutlardaki proje adınız
   - `<GITHUB_TOKEN>`, `<API_KEY>`, `<API_TOKEN>`: örnek komutlardaki kimlik doğrulama değerleri
3. Bir kategori klasöründeki tüm yeteneklerin şema, iç bağlantı ve Python sözdizimi doğrulamasını çalıştırmak için:
   ```bash
   python verimlilik-ve-otomasyon/skill-and-mcp-tools/scripts/validate_skills.py verimlilik-ve-otomasyon
   ```

---

## Gizlilik Notu / Privacy Note

- Bu depodaki tüm yetenekler yalnızca genel uygulama kurallarını (tarifleri) ve yardımcı araçları içerecek şekilde düzenlenmiş; yerel kullanıcı yolları, geçmiş projelere/raporlara ait özel içerikler ve örnek token dizgeleri tamamen arındırılmıştır (`<USERNAME>`, `<PROJECT_PATH>`, `<PROJECT_NAME>`, `<GITHUB_TOKEN>`, `<API_KEY>`, `<API_TOKEN>`).
