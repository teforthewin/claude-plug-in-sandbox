---
name: tet-atf-knowledge:01-framework-architecture
description: Defines the TET-ATF 4-layer directory structure (tests/business/core/util), multi-channel file placement (API/Web/Mobile), and design pattern hierarchies. Use when scaffolding a new test project, creating directories, deciding where a new file belongs, or verifying the overall framework structure.
---

# Skill 01 — Framework Architecture

## Directory Structure

```
tet-test-framework-skeleton/
├── config/                             ← READ-ONLY (never generated or overwritten)
│   ├── global_config.yaml             # Framework constants
│   └── environments/{env}.yaml        # Environment overrides
├── src/
│   ├── business/                      # L2 — Orchestration
│   │   ├── api/{domain}/
│   │   ├── web/{domain}/
│   │   ├── mobile/{domain}/
│   │   ├── internal/                  # Abstraction managers for internal tools
│   │   └── resource/
│   │       ├── templates/             # HTML report templates, data templates
│   │       └── data_schemas/          # JSON schemas for API request/response
│   ├── core/                          # L3 — Atomic technical operations
│   │   ├── api/                       # HTTP clients
│   │   ├── web/                       # Page Objects
│   │   ├── mobile/                    # Mobile drivers / screens
│   │   └── internal/                  # DB, storage, broker implementations
│   └── util/                          # L4 — Generic reusable utilities
│       ├── logger.*
│       ├── test_context.*
│       ├── data_generator.*
│       ├── config_utils.*
│       ├── date_utils.*
│       ├── converter_utils.*
│       ├── validator_utils.*
│       └── storage_utils.*
└── tests/                             # L1 — Test definitions
    ├── {domain}/
    │   ├── api/
    │   ├── web/
    │   └── mobile/
    ├── unit/util/                     # Unit tests for all L4 utilities
    └── sample/                        # Sample test (produces all report types)
```

---

## 4-Layer Architecture

```
L1  tests/             → Natural-language keywords, no logic, delegates to L2
L2  src/business/      → Orchestration, data conversion, TestContext management
L3  src/core/          → Atomic ops: HTTP calls, UI interactions, mobile driver
L4  src/util/          → Generic helpers: logging, date, data, config, context
```

**Flow direction is strictly top-down: L1 → L2 → L3 → L4. Never reverse.**

---

## Multi-Channel File Placement

| Channel | Core (L3) | Business (L2) | Tests (L1) |
|---------|-----------|---------------|------------|
| **API** | `src/core/api/{service}/` | `src/business/api/{domain}/` | `tests/{domain}/api/` |
| **Web** | `src/core/web/{service}/` | `src/business/web/{domain}/` | `tests/{domain}/web/` |
| **Mobile** | `src/core/mobile/{service}/` | `src/business/mobile/{domain}/` | `tests/{domain}/mobile/` |

---

## Design Pattern Hierarchies

| Pattern | Hierarchy |
|---------|-----------|
| **API Client** | `BaseApiClient` → `AppBaseApi` → `ResourceApi` |
| **Page Object** | `BasePage` → `AppBasePage` → `SpecificPage` → `Component` |
| **Mobile Screen** | `BaseMobilePage` → `AppBaseMobilePage` → `SpecificScreen` |
| **Internal Tool** | `BaseInterface` → `ConcreteImpl` (managed by `{Category}Manager`) |

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (MAINT-001, MAINT-004) and test cases (TC-MAINT-1-xxx, TC-MAINT-4-xxx)
