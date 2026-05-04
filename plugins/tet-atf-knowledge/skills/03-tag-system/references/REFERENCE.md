# References — Skill 03: Tag System

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate the mandatory 4-category tag system (severity, category, domain, metadata), execution profiles, and CLI filter behavior defined in this skill.

---

## Story: TEST-001 — Tag System
**Jira:** `TE-162` | **Priority:** smoke | **Skeleton:** L2

**User Story:** As a test lead, I want a dynamic tagging system (Severity, Category, Domain, Metadata), so that I can organize tests flexibly and run specific subsets.

**Acceptance Criteria:**
- [ ] All tag types accepted and parsed: severity, category, domain, metadata
- [ ] Tags applied via annotations directly in test definitions
- [ ] At least one severity tag (smoke/mandatory/required/advisory/deprecated) required per test
- [ ] Multiple tags per test supported (e.g., `@smoke @api @payments`)
- [ ] Tags appear in test reports with per-tag breakdown statistics
- [ ] Tag filters can be applied at execution time

**Architectural Layer:** All layers (cross-cutting)
**Keywords:** tags, severity, category, domain, metadata, annotations

---

### TC-TEST-1-001 — Tag Reporting
**Jira:** `TE-276` | **Parent:** TEST-001

**Verification Steps:**
1. Execute tests that have tags applied (severity, category, domain)
2. Generate a test report
3. Verify all tags appear in the report per test
4. Verify a tag breakdown section is present (count per tag)
5. Verify tag-based filters can be applied when viewing the report

---

## Story: TEST-002 — Selective Execution
**Jira:** `TE-163` | **Priority:** mandatory | **Skeleton:** L2, L3

**User Story:** As a CI/CD engineer, I want to filter and run tests by tags, so that I can execute appropriate test subsets at different pipeline stages.

**Acceptance Criteria:**
- [ ] CLI accepts `--tags` parameter for filtering
- [ ] Filter by severity tag: `--tags=@smoke` runs only smoke tests
- [ ] Filter by category tag: `--tags=@api` runs only API tests
- [ ] Filter by domain tag: `--tags=@payments` runs only payments tests
- [ ] Combined AND filter: `--tags=@smoke+@api` (smoke AND api)
- [ ] Combined OR filter: `--tags=@smoke,@api` (smoke OR api)
- [ ] Negation filter: `--tags=!@deprecated` excludes deprecated tests
- [ ] Filtering is case-insensitive; exit code correct (0 = all pass, non-zero = failures)

**Architectural Layer:** Framework runner + Build tool
**Keywords:** selective-execution, tag-filtering, cli, negation, boolean-logic

---

### TC-TEST-2-001 — Filter by Severity Tag
**Jira:** `TE-277` | **Parent:** TEST-002

**Verification Steps:**
1. Execute tests with `--tags=@smoke`
2. Verify only `@smoke`-tagged tests run
3. Verify `@mandatory` tests are NOT executed
4. Verify the test count matches the expected number of smoke tests
5. Verify the filter is case-insensitive (`@Smoke` = `@smoke`)

---

### TC-TEST-2-002 — Filter by Category Tag
**Jira:** `TE-278` | **Parent:** TEST-002

**Verification Steps:**
1. Execute tests with `--tags=@api`
2. Verify only `@api`-tagged tests run
3. Execute with `--tags=@web`
4. Verify only `@web`-tagged tests run
5. Verify channel filtering works correctly in isolation

---

### TC-TEST-2-003 — Filter by Domain Tag
**Jira:** `TE-279` | **Parent:** TEST-002

**Verification Steps:**
1. Execute with `--tags=@user-management`
2. Verify only user-management domain tests run
3. Execute with `--tags=@payment`
4. Verify only payment domain tests run
5. Verify domain filtering produces correct isolation

---

### TC-TEST-2-004 — Combined Tag Filtering
**Jira:** `TE-280` | **Parent:** TEST-002

**Verification Steps:**
1. Execute with `--tags=@smoke+@api` (AND logic)
2. Verify only tests tagged with BOTH `@smoke` AND `@api` run
3. Execute with `--tags=@smoke,@api` (OR logic)
4. Verify tests tagged with EITHER `@smoke` OR `@api` run
5. Verify boolean logic (AND vs OR) works as expected

---

### TC-TEST-2-005 — Negation Filtering
**Jira:** `TE-281` | **Parent:** TEST-002

**Verification Steps:**
1. Execute with `--tags=!@deprecated`
2. Verify all `@deprecated` tests are excluded
3. Execute with `--tags=!@flaky`
4. Verify all `@flaky` tests are excluded
5. Verify negation exclusion works correctly

---

### TC-TEST-2-006 — CLI Tag Filtering
**Jira:** `TE-282` | **Parent:** TEST-002

**Verification Steps:**
1. Run the test command with the `--tags` parameter
2. Verify the parameter is recognized by the CLI
3. Verify the filter is applied to test selection
4. Verify only matching tests execute
5. Verify exit code is 0 for all-pass, non-zero for failures

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| TEST-001 | TE-162 | TC-TEST-1-001 | TE-276 |
| TEST-002 | TE-163 | TC-TEST-2-001 to TC-TEST-2-006 | TE-277, TE-278, TE-279, TE-280, TE-281, TE-282 |

**Total:** 2 stories · 7 test cases
