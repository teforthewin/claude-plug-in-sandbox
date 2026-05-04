# References — Skill 08: Mobile Patterns

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate Appium mobile screen hierarchy (`BaseMobilePage` → `AppBaseMobilePage` → `SpecificScreen`), locator strategy priority, gesture methods, and platform-aware coding defined in this skill.

---

## Story: QA-001 — Multi-Channel Testing (Mobile channel)
**Jira:** `TE-134` | **Priority:** smoke | **Skeleton:** L2, L3

**User Story:** As a test automation engineer, I want to write tests for API, Web UI, and Mobile channels using a single framework, so that I can maintain tests across all channels without learning multiple tools.

**Acceptance Criteria (Mobile-specific):**
- [ ] Mobile tests use Appium driver (`src/core/mobile/`)
- [ ] All three channels share common test structure, utilities, and `TestContext`
- [ ] Tests are organized by channel: `tests/{domain}/mobile/`
- [ ] Documentation includes working examples for the Mobile channel

**Architectural Layer:** L3 Core + L2 Business + L1 Test
**Keywords:** mobile, appium, ios, android, native-app, multi-channel

---

### TC-QA-1-003 — Mobile Test Execution with Appium Driver
**Jira:** `TE-236` | **Parent:** QA-001

**Verification Steps:**
1. Create a mobile test using Appium
2. Initialize Appium driver with desired capabilities
3. Perform native app interactions
4. Navigate between screens
5. Verify screen elements and properties
6. Capture screenshots

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

## Story: OBS-002 — Screenshots & Videos (Mobile)
**Jira:** `TE-147` | **Priority:** mandatory | **Skeleton:** L2, L3

**User Story:** As a test engineer debugging failures, I want automatic screenshots and videos on test failure, so that I can understand what went wrong without re-running tests.

**Acceptance Criteria (Mobile-specific):**
- [ ] Screenshots captured automatically on every test failure
- [ ] Videos recorded for mobile tests using Appium (full test duration)
- [ ] Artifacts stored in `build/test-artifacts/` by default
- [ ] Artifact links (relative paths) included in JSON and HTML test reports

**Architectural Layer:** L3 Core (Appium)
**Keywords:** mobile-screenshots, mobile-video, appium-recording, failure-debugging

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

### TC-OBS-2-003 — Video Recording for Mobile Tests
**Jira:** `TE-195` | **Parent:** OBS-002

**Verification Steps:**
1. Execute a mobile test using Appium
2. Verify video recording is enabled
3. Verify the video captures on-screen interactions
4. Verify the video file is created on disk
5. Verify the video shows device state throughout the test

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

### TC-OBS-2-009 — Artifact Metadata
**Jira:** `TE-201` | **Parent:** OBS-002

**Verification Steps:**
1. Capture a screenshot during a test
2. Verify the filename includes the test name
3. Verify a timestamp is present in the filename or metadata
4. Verify resolution/dimensions metadata is captured
5. Verify metadata is sufficient to identify the artifact without opening it

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| QA-001 (Mobile scope) | TE-134 | TC-QA-1-003, TC-QA-1-004 | TE-236, TE-237 |
| OBS-002 (Mobile scope) | TE-147 | TC-OBS-2-001, TC-OBS-2-003, TC-OBS-2-004, TC-OBS-2-009 | TE-193, TE-195, TE-196, TE-201 |

**Total:** 2 stories · 6 test cases
