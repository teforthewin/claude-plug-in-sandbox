# References — Skill 07: Web Patterns

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate the Page Object Model 4-level hierarchy (`BasePage` → `AppBasePage` → `SpecificPage` → `Component`), locator encapsulation rules, explicit wait strategy, and file placement defined in this skill.

---

## Story: QA-001 — Multi-Channel Testing (Web channel)
**Jira:** `TE-134` | **Priority:** smoke | **Skeleton:** L2, L3

**User Story:** As a test automation engineer, I want to write tests for API, Web UI, and Mobile channels using a single framework, so that I can maintain tests across all channels without learning multiple tools.

**Acceptance Criteria (Web-specific):**
- [ ] Web UI tests use Page Object Model with framework-provided instructions
- [ ] Tests are organized by channel: `tests/{domain}/web/`
- [ ] Documentation includes working examples for the Web UI channel

**Architectural Layer:** L3 Core + L2 Business + L1 Test
**Keywords:** web, page-object, playwright, multi-channel

---

### TC-QA-1-002 — Web UI Test Execution with Page Object Model
**Jira:** `TE-235` | **Parent:** QA-001

**Verification Steps:**
1. Create a Web UI test file
2. Define page objects for application pages
3. Implement locator encapsulation in page objects
4. Execute navigation between pages
5. Perform user interactions (clicks, form fills)
6. Verify page elements and state

---

### TC-QA-1-004 — Shared Test Structure Across Channels
**Jira:** `TE-237` | **Parent:** QA-001

**Verification Steps:**
1. Review API test structure
2. Review Web UI test structure
3. Review Mobile test structure
4. Verify common fixture patterns are shared
5. Verify shared utility imports (Logger, TestContext, ConfigUtils)
6. Verify TestContext usage across all channels
7. Verify logging consistency across channels

---

## Story: MAINT-002 — Reusable Components (Page Objects)
**Jira:** `TE-143` | **Priority:** mandatory | **Skeleton:** L2, L3

**User Story:** As a test automation engineer, I want reusable Page Objects and API Clients, so that test code is DRY and maintainable.

**Acceptance Criteria (Page Object-specific):**
- [ ] Page Object Model pattern: `BasePage` → `AppBasePage` → `SpecificPage` hierarchy in `src/core/web/`
- [ ] Locators encapsulated in Page Objects (no raw selectors in test or business layer)
- [ ] Inheritance hierarchy enables maximum code reuse across domains

**Architectural Layer:** L3 Core
**Keywords:** page-object, pom, locator-encapsulation, inheritance

---

### TC-MAINT-2-001 — Page Object Base Class
**Jira:** `TE-183` | **Parent:** MAINT-002

**Verification Steps:**
1. Verify `BasePage` class exists in `src/core/web/`
2. Verify common methods exist (navigate, waitForElement, findElement, etc.)
3. Verify framework coding rules are respected (naming, logging, no business logic)

---

## Story: OBS-002 — Screenshots & Videos (Web)
**Jira:** `TE-147` | **Priority:** mandatory | **Skeleton:** L2, L3

**User Story:** As a test engineer debugging failures, I want automatic screenshots and videos on test failure, so that I can understand what went wrong without re-running tests.

**Acceptance Criteria (Web-specific):**
- [ ] Screenshots captured automatically on every test failure
- [ ] Videos recorded for web tests (full test duration)
- [ ] Artifacts stored in `build/test-artifacts/` by default
- [ ] Screenshot capture on success is configurable (OFF by default)
- [ ] Artifact links (relative paths) included in JSON and HTML test reports

**Architectural Layer:** L3 Core (Playwright)
**Keywords:** screenshots, videos, web-artifacts, failure-debugging

---

### TC-OBS-2-001 — Screenshot Capture on Failure
**Jira:** `TE-193` | **Parent:** OBS-002

**Verification Steps:**
1. Execute a test that fails an assertion
2. Verify a screenshot is automatically captured
3. Verify the screenshot file is created on disk
4. Verify the screenshot shows the application state at the point of failure
5. Verify multiple screenshots are captured for tests with multiple failures

---

### TC-OBS-2-002 — Video Recording for Web Tests
**Jira:** `TE-194` | **Parent:** OBS-002

**Verification Steps:**
1. Execute a web UI test
2. Verify video recording is enabled (by configuration)
3. Verify the video captures the entire test execution
4. Verify the video file is created on disk after the test
5. Verify the video can be played back

---

### TC-OBS-2-004 — Artifacts Stored in Standard Location
**Jira:** `TE-196` | **Parent:** OBS-002

**Verification Steps:**
1. Execute a test that produces a failure
2. Verify `build/test-artifacts/` directory is created
3. Verify screenshots are stored inside that directory
4. Verify videos are stored inside that directory
5. Verify the naming convention is consistent (test name + timestamp)

---

### TC-OBS-2-005 — Artifact Links in Reports
**Jira:** `TE-197` | **Parent:** OBS-002

**Verification Steps:**
1. Execute a failing test that produces screenshots
2. Generate the test report
3. Verify artifact links (relative paths) are embedded in the report
4. Verify links point to the correct screenshot/video files
5. Verify links are clickable in the HTML report

---

### TC-OBS-2-006 — Configurable Storage Location
**Jira:** `TE-198` | **Parent:** OBS-002

**Verification Steps:**
1. Configure a custom artifact directory path in environment config
2. Execute a test with a failure
3. Verify artifacts are stored in the custom location
4. Change the configured location to a different path
5. Verify the new location is used for subsequent tests

---

### TC-OBS-2-007 — Screenshot Optional on Success
**Jira:** `TE-199` | **Parent:** OBS-002

**Verification Steps:**
1. Enable "screenshot on success" in configuration
2. Execute a passing test
3. Verify a screenshot is captured
4. Disable "screenshot on success" in configuration
5. Execute a passing test
6. Verify no screenshot is captured (only on failure)

---

### TC-OBS-2-008 — Artifact Organization
**Jira:** `TE-200` | **Parent:** OBS-002

**Verification Steps:**
1. Execute multiple tests that each produce failures
2. Verify artifacts are organized per test (separate subfolder or naming prefix per test)
3. Verify screenshots for each test are clearly grouped
4. Verify videos for each test are clearly grouped
5. Verify naming is unambiguous (no collision between tests)

---

### TC-OBS-2-009 — Artifact Metadata
**Jira:** `TE-201` | **Parent:** OBS-002

**Verification Steps:**
1. Capture a screenshot during a test
2. Verify the filename includes the test name
3. Verify a timestamp is present in the filename or metadata
4. Verify resolution/dimensions metadata is captured
5. Verify metadata is sufficient to identify the artifact without opening it

---

### TC-OBS-2-010 — Screenshot & Video Documentation
**Jira:** `TE-202` | **Parent:** OBS-002

**Verification Steps:**
1. Review artifact capture documentation
2. Verify configuration options are documented (enable/disable, storage path)
3. Verify instructions for accessing artifacts are explained
4. Verify examples are provided
5. Verify performance impact of recording is documented

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| QA-001 (Web scope) | TE-134 | TC-QA-1-002, TC-QA-1-004 | TE-235, TE-237 |
| MAINT-002 (POM scope) | TE-143 | TC-MAINT-2-001 | TE-183 |
| OBS-002 (Web scope) | TE-147 | TC-OBS-2-001, TC-OBS-2-002, TC-OBS-2-004 to TC-OBS-2-010 | TE-193, TE-194, TE-196 to TE-202 |

**Total:** 3 stories · 11 test cases
