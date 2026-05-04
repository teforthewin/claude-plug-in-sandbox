# References — Skill 05: Coding Standards

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate naming conventions, commenting rules, design patterns, version pinning policy, and code quality standards defined in this skill.

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

## Story: QA-002 — Code Coverage
**Jira:** `TE-137` | **Priority:** required | **Skeleton:** L2

**User Story:** As a quality manager, I want to measure and enforce code coverage targets, so that I can ensure adequate test coverage of the application code.

**Acceptance Criteria:**
- [ ] Coverage plugin integrated into build system
- [ ] Coverage reports generated after test runs
- [ ] 80% coverage threshold enforced (build fails if below)
- [ ] Coverage broken down by package and class
- [ ] HTML coverage report available at `build/reports/jacoco/`
- [ ] Coverage metrics included in CI/CD reporting

**Architectural Layer:** Build tool + L4 Util
**Keywords:** coverage, jacoco, ci-cd, quality-gate

---

### TC-QA-2-001 — Coverage Report Generation
**Jira:** `TE-238` | **Parent:** QA-002

**Verification Steps:**
1. Execute full test suite
2. Verify coverage report is generated
3. Verify report location is `build/reports/jacoco/`
4. Verify report is in HTML format
5. Verify report contains coverage data

---

### TC-QA-2-002 — HTML Coverage Report at Standard Location
**Jira:** `TE-239` | **Parent:** QA-002

**Verification Steps:**
1. Execute test suite
2. Verify `build/reports/jacoco/` directory exists
3. Verify `index.html` exists in directory
4. Open HTML report in browser
5. Verify report is fully functional

---

### TC-QA-2-003 — Coverage in CI/CD Reporting
**Jira:** `TE-240` | **Parent:** QA-002

**Verification Steps:**
1. Execute tests in CI/CD pipeline
2. Verify coverage metrics are captured
3. Verify metrics are output in pipeline logs
4. Verify metrics can be extracted programmatically
5. Verify trend tracking is possible

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| MAINT-002 | TE-143 | TC-MAINT-2-001, TC-MAINT-2-002 | TE-183, TE-184 |
| QA-002 | TE-137 | TC-QA-2-001 to TC-QA-2-003 | TE-238, TE-239, TE-240 |

**Total:** 2 stories · 5 test cases
