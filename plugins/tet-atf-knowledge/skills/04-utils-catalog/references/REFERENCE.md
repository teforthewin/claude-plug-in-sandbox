# References — Skill 04: Utils Catalog

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate the utility modules in `src/util/` — Logger, TestContext, DataGenerator, ConfigUtils, DateUtils, and ConverterUtils — as defined in this skill.

---

## Story: MAINT-001 — 4-Layer Architecture (Util Layer)
**Jira:** `TE-142` | **Priority:** smoke | **Skeleton:** L1, L2

**User Story:** As a framework architect, I want a clear 4-layer separation (Test → Business → Core → Util), so that the framework can scale to thousands of tests without refactoring.

**Acceptance Criteria (Util-specific):**
- [ ] Util layer (`src/util/`) provides ONLY generic, domain-agnostic reusable utilities
- [ ] Utilities are reusable across all domains and channels

**Architectural Layer:** L4 Util
**Keywords:** util, generic-helpers, domain-agnostic

---

### TC-MAINT-1-004 — Util Layer Generic Utilities
**Jira:** `TE-180` | **Parent:** MAINT-001

**Verification Steps:**
1. Review util layer in `src/util/`
2. Verify the following utilities exist: `context_utils`, `converter_utils`, `date_utils`, `data_generator`, `config_utils`, `logger`, `storage_utils`, `validator_utils`
3. Verify utilities are domain-agnostic (no domain-specific logic)
4. Verify utilities are reusable across all domains

---

## Story: REL-001 — Test Isolation
**Jira:** `TE-138` | **Priority:** smoke | **Skeleton:** L2, L3

**User Story:** As a test framework user, I want each test to run independently with its own data, so that tests don't interfere with each other and can run in any order.

**Acceptance Criteria:**
- [ ] Each test gets an isolated `TestContext` instance (no shared mutable state between tests)
- [ ] Per-test fixtures initialize fresh state before each test
- [ ] Data cleanup occurs between tests when needed
- [ ] Tests are order-independent and produce identical results regardless of execution order
- [ ] Tests can be parallelized safely (no race conditions, no data collisions)
- [ ] Test isolation best practices and anti-patterns are documented

**Architectural Layer:** L4 Util (TestContext) + L1 Test
**Keywords:** isolation, parallel, test-context, independence, fixtures

---

### TC-REL-1-001 — Isolated TestContext Per Test
**Jira:** `TE-241` | **Parent:** REL-001

**Verification Steps:**
1. Create two concurrent tests
2. Verify each test has a unique `TestContext` instance
3. Set values in first test's context
4. Verify second test's context is empty (no shared state)
5. Verify contexts don't share data between tests
6. Verify context is cleaned up after each test completes

---

### TC-REL-1-002 — Per-Test Fixture Initialization
**Jira:** `TE-242` | **Parent:** REL-001

**Verification Steps:**
1. Define a fixture that initializes test data
2. Execute first test using that fixture
3. Verify data is created fresh (new IDs, new records)
4. Execute second test using the same fixture
5. Verify data is re-initialized from scratch
6. Verify no data from the first test carries over

---

### TC-REL-1-003 — Parallel Test Execution Safety
**Jira:** `TE-243` | **Parent:** REL-001

**Verification Steps:**
1. Enable parallel test execution in framework config
2. Set parallel thread count to > 1
3. Execute the full test suite in parallel
4. Verify all tests complete successfully
5. Verify no data collisions occur between parallel threads
6. Verify no race conditions (flakiness under parallel mode)

---

### TC-REL-1-004 — TestContext Cleanup Verification
**Jira:** `TE-244` | **Parent:** REL-001

**Verification Steps:**
1. Set multiple values in `TestContext` during a test
2. Track `TestContext` references for inspection
3. Complete test execution (pass or fail)
4. Verify `TestContext` is fully cleared after the test
5. Verify no memory leaks from context data
6. Verify all tracked resources are released

---

### TC-REL-1-005 — Exception Handling in Cleanup
**Jira:** `TE-245` | **Parent:** REL-001

**Verification Steps:**
1. Create a test that throws an exception mid-execution
2. Verify cleanup/teardown still executes despite the exception
3. Verify all tracked resources are released
4. Verify the next test is unaffected by the previous exception
5. Verify the exception is properly reported (not swallowed)

---

### TC-REL-1-006 — Test Isolation Documentation
**Jira:** `TE-246` | **Parent:** REL-001

**Verification Steps:**
1. Review isolation documentation in `docs/` or README
2. Verify examples demonstrate isolated data usage per test
3. Verify anti-patterns (shared state, global variables) are documented
4. Verify best practices are clearly stated
5. Verify documentation is sufficient for new team members to understand isolation

---

## Story: REL-002 — Resource Management
**Jira:** `TE-139` | **Priority:** mandatory | **Skeleton:** L2

**User Story:** As a test engineer, I want created test resources (API users, database records, etc.) automatically cleaned up, so that I don't have orphaned test data polluting the system.

**Acceptance Criteria:**
- [ ] `TestContext.trackResource(type, id)` registers every created resource for cleanup
- [ ] Cleanup executes in reverse creation order (respects resource dependencies)
- [ ] Cleanup failures are logged and do NOT mask the original test result
- [ ] Summary of all cleanup actions is logged after each test
- [ ] Database records and API-created entities are deleted after tests complete

**Architectural Layer:** L4 Util (TestContext) + L2 Business
**Keywords:** cleanup, resource-tracking, teardown, reverse-order

---

### TC-REL-2-001 — TestContext Resource Tracking
**Jira:** `TE-247` | **Parent:** REL-002

**Verification Steps:**
1. Create a test that creates a resource (API entity, DB record)
2. Call `TestContext.trackResource(type, id)` after creation
3. Verify the resource is registered in `TestContext`
4. Create multiple resources
5. Verify all resources are tracked (type, id, metadata)
6. After test completion, verify all tracked resources are cleaned up in reverse creation order

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| MAINT-001 (util scope) | TE-142 | TC-MAINT-1-004 | TE-180 |
| REL-001 | TE-138 | TC-REL-1-001 to TC-REL-1-006 | TE-241, TE-242, TE-243, TE-244, TE-245, TE-246 |
| REL-002 | TE-139 | TC-REL-2-001 | TE-247 |

**Total:** 3 stories · 8 test cases
