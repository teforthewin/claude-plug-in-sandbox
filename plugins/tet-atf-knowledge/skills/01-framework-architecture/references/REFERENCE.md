# References — Skill 01: Framework Architecture

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate the 4-layer directory structure and multi-channel file placement rules defined in this skill.

---

## Story: MAINT-001 — 4-Layer Architecture
**Jira:** `TE-142` | **Priority:** smoke | **Skeleton:** L1, L2

**User Story:** As a framework architect, I want a clear 4-layer separation (Test → Business → Core → Util), so that the framework can scale to thousands of tests without refactoring.

**Acceptance Criteria:**
- [ ] Test layer (`tests/`) contains ONLY test definitions and fixtures — no algorithms, no loops
- [ ] Business layer (`src/business/`) handles ONLY orchestration and data transformation
- [ ] Core layer (`src/core/`) implements ONLY atomic technical operations (HTTP, UI, mobile drivers)
- [ ] Util layer (`src/util/`) provides ONLY generic, domain-agnostic reusable utilities
- [ ] Clear guidelines specify which layer owns which functionality
- [ ] Documentation explains architecture with concrete examples for each layer

**Architectural Layer:** All layers (foundational)
**Keywords:** 4-layer, architecture, separation-of-concerns, scalability

---

### TC-MAINT-1-001 — Test Layer Contains Only Definitions
**Jira:** `TE-177` | **Parent:** MAINT-001

**Verification Steps:**
1. Review test layer files in `tests/`
2. Verify test files use simple keywords/assertions
3. Verify no complex algorithms exist in tests
4. Verify no loops or conditionals exist in tests
5. Verify minimal implementation per test
6. Verify proper delegation to business layer for all logic

---

### TC-MAINT-1-002 — Business Layer Orchestration
**Jira:** `TE-178` | **Parent:** MAINT-001

**Verification Steps:**
1. Review business layer in `src/business/`
2. Verify business layer contains: data transformation logic, TestContext management, default test data injection, workflow orchestration
3. Verify business layer is called from tests (not directly from Core)
4. Verify Core layer is called from business layer (not from tests)

---

### TC-MAINT-1-003 — Core Layer Atomic Operations
**Jira:** `TE-179` | **Parent:** MAINT-001

**Verification Steps:**
1. Review core layer in `src/core/`
2. Verify direct system interactions (HTTP, UI, mobile drivers)
3. Verify atomic operations only (no multi-step workflows in Core)
4. Verify Page Objects pattern is used
5. Verify API client classes are present
6. Verify no business logic exists in Core

---

### TC-MAINT-1-004 — Util Layer Generic Utilities
**Jira:** `TE-180` | **Parent:** MAINT-001

**Verification Steps:**
1. Review util layer in `src/util/`
2. Verify the following utilities exist: `context_utils`, `converter_utils`, `date_utils`, `data_generator`, `config_utils`, `logger`, `storage_utils`, `validator_utils`
3. Verify utilities are domain-agnostic (no domain-specific logic)
4. Verify utilities are reusable across all domains

---

### TC-MAINT-1-005 — Layer Dependency Rules
**Jira:** `TE-181` | **Parent:** MAINT-001

**Verification Steps:**
1. Verify test layer only imports from business layer
2. Verify business layer only imports from core and util
3. Verify core layer only imports from util
4. Verify util layer has no framework-internal dependencies
5. Verify no circular dependencies exist
6. Run dependency analysis tool to confirm compliance

---

### TC-MAINT-1-006 — Architecture Validation Tool
**Jira:** `TE-182` | **Parent:** MAINT-001

**Verification Steps:**
1. Create or run architecture validation script
2. Analyze layer dependencies across all source files
3. Verify imports follow layer rules (no cross-layer violations)
4. Generate architecture compliance report
5. Confirm all violations are flagged

---

## Story: MAINT-004 — Multi-Domain Support
**Jira:** `TE-145` | **Priority:** required | **Skeleton:** L1, L2, L3

**User Story:** As a framework architect, I want the framework to support multiple domains (e.g., parking, charging, permits), so that teams can extend and maintain domain-specific logic independently.

**Acceptance Criteria:**
- [ ] Domain modules are isolated and pluggable (no cross-domain dependencies)
- [ ] Shared utilities in `src/util/` are not duplicated across domains
- [ ] Domain-specific configuration supported (`config/environments/{env}.yaml` keyed by domain)
- [ ] `tests/{domain}/api/`, `tests/{domain}/web/`, `tests/{domain}/mobile/` structure enforced
- [ ] `src/business/api/{domain}/`, `web/{domain}/`, `mobile/{domain}/` structure enforced
- [ ] Documentation explains how to add a new domain in under 30 minutes

**Architectural Layer:** All layers
**Keywords:** multi-domain, extensibility, isolation, pluggable

---

### TC-MAINT-4-001 — Channel-Domain Directory Structure
**Jira:** `TE-186` | **Parent:** MAINT-004

**Verification Steps:**
1. Verify `tests/api/{domain}/` directories exist (or can be created per doc)
2. Verify `tests/web/{domain}/` directories exist (or are structurally correct)
3. Verify `tests/mobile/{domain}/` directories exist (or are structurally correct)
4. Verify multiple domains are supported simultaneously
5. Verify each domain has its own isolated test directory

---

### TC-MAINT-4-002 — Domain-Specific Business Layer
**Jira:** `TE-187` | **Parent:** MAINT-004

**Verification Steps:**
1. Verify `src/business/api/{domain}/` exists or is prescribed by documentation
2. Verify `src/business/web/{domain}/` exists or is prescribed by documentation
3. Verify `src/business/mobile/{domain}/` exists or is prescribed by documentation
4. Verify domain-specific business classes exist and are isolated
5. Verify domain teams can independently own their business layer directory

---

### TC-MAINT-4-003 — Fixtures Per Domain
**Jira:** `TE-188` | **Parent:** MAINT-004

**Verification Steps:**
1. Verify common fixtures exist in `tests/common_fixtures.*`
2. Verify domain-specific fixtures exist in domain directories
3. Verify fixtures are imported correctly within domain tests
4. Verify domain fixtures extend or compose common fixtures
5. Verify fixture reuse where appropriate (no duplication)

---

### TC-MAINT-4-004 — Resource Organization by Domain
**Jira:** `TE-189` | **Parent:** MAINT-004

**Verification Steps:**
1. Verify `src/business/resource/templates/{domain}/` exists or is prescriptive
2. Verify `src/business/resource/data_schemas/{domain}/` exists or is prescriptive
3. Verify test data templates are domain-organized
4. Verify schema definitions are domain-organized
5. Verify domain resources are accessible from the business layer

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| MAINT-001 | TE-142 | TC-MAINT-1-001 to TC-MAINT-1-006 | TE-177, TE-178, TE-179, TE-180, TE-181, TE-182 |
| MAINT-004 | TE-145 | TC-MAINT-4-001 to TC-MAINT-4-004 | TE-186, TE-187, TE-188, TE-189 |

**Total:** 2 stories · 10 test cases
