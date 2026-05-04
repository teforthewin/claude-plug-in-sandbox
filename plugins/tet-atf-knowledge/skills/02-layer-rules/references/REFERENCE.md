# References — Skill 02: Layer Rules

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate cross-layer import boundaries, per-layer responsibilities, and REST API routing rules defined in this skill.

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

## Story: MAINT-002 — Reusable Components
**Jira:** `TE-143` | **Priority:** mandatory | **Skeleton:** L2, L3

**User Story:** As a test automation engineer, I want reusable Page Objects and API Clients, so that test code is DRY and maintainable.

**Acceptance Criteria:**
- [ ] Page Object Model pattern: `BasePage` → `AppBasePage` → `SpecificPage` hierarchy in `src/core/web/`
- [ ] API Client base classes: `BaseApiClient` → `AppBaseApi` → `ResourceApi` in `src/core/api/`
- [ ] Locators encapsulated in Page Objects (no raw selectors in test or business layer)
- [ ] HTTP methods (GET, POST, PUT, DELETE, PATCH) implemented in `BaseApiClient`
- [ ] All API interactions logged via structured logger (JSON schema-compliant)
- [ ] Inheritance hierarchy enables maximum code reuse across domains

**Architectural Layer:** L3 Core
**Keywords:** page-object, api-client, dry, inheritance, reuse

---

### TC-MAINT-2-001 — Page Object Base Class
**Jira:** `TE-183` | **Parent:** MAINT-002

**Verification Steps:**
1. Verify `BasePage` class exists in `src/core/web/`
2. Verify common methods exist (navigate, waitForElement, findElement, etc.)
3. Verify framework coding rules are respected (naming, logging, no business logic)

---

### TC-MAINT-2-002 — HTTP Methods in API Clients
**Jira:** `TE-184` | **Parent:** MAINT-002

**Verification Steps:**
1. Verify `BaseApiClient` class exists in `src/core/api/`
2. Verify GET method is implemented
3. Verify POST method is implemented
4. Verify PUT method is implemented
5. Verify DELETE method is implemented
6. Verify every API interaction is logged via structured logger (JSON schema-compliant)

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| MAINT-001 | TE-142 | TC-MAINT-1-001 to TC-MAINT-1-006 | TE-177, TE-178, TE-179, TE-180, TE-181, TE-182 |
| MAINT-002 | TE-143 | TC-MAINT-2-001, TC-MAINT-2-002 | TE-183, TE-184 |

**Total:** 2 stories · 8 test cases
