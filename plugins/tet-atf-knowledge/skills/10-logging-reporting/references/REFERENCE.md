# References — Skill 10: Logging & Reporting

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate structured JSON log format, sensitive data masking, two-phase test reporting pipeline, and required report artifacts defined in this skill.

---

## Story: OBS-001 — Structured JSON Logging
**Jira:** `TE-146` | **Priority:** smoke | **Skeleton:** L2, L3

**User Story:** As a platform engineer, I want all test logs in structured JSON format, so that I can ingest them into log aggregation systems (ELK, Splunk, CloudWatch).

**Acceptance Criteria:**
- [ ] Every log line is valid JSON (parseable, no malformed entries)
- [ ] Log fields: `timestamp` (ISO 8601), `level` (DEBUG/INFO/WARNING/ERROR), `message`, `testId`, `tags`, `executionId`
- [ ] Structure is consistent and validated against the Logger JSON schema
- [ ] `TestContext` data (testId, tags, variables) automatically injected into log context
- [ ] Sensitive data (passwords, tokens, PII, credit cards) automatically masked before writing
- [ ] Log levels are configurable at runtime

**Architectural Layer:** L4 Util (Logger)
**Keywords:** logging, json, structured, masking, context, elk

---

### TC-OBS-1-001 — JSON Log Format
**Jira:** `TE-190` | **Parent:** OBS-001

**Verification Steps:**
1. Execute a test that generates log output
2. Capture all log output
3. Attempt to parse each log line as JSON
4. Verify every line is valid, parseable JSON (no malformed entries)
5. Verify `timestamp` field is present in ISO 8601 format
6. Verify `level` field is present (DEBUG, INFO, WARNING, or ERROR)
7. Verify `message` field is present
8. Verify overall structure is consistent with the defined JSON schema

---

### TC-OBS-1-002 — Context Data in Logs
**Jira:** `TE-191` | **Parent:** OBS-001

**Verification Steps:**
1. Set `testId` in `TestContext` before generating logs
2. Generate a log entry
3. Verify `testId` appears in the log's context field
4. Apply tags to the test
5. Generate another log entry
6. Verify tags are included in the log context
7. Set additional variables in `TestContext`
8. Verify those variables appear in subsequent log entries

---

### TC-OBS-1-003 — Sensitive Data Masking in Logs
**Jira:** `TE-192` | **Parent:** OBS-001

**Verification Steps:**
1. Log a message containing a password
2. Verify the password is masked (e.g., `*****`) — no plain-text password visible
3. Log a message containing an API token
4. Verify the token is masked
5. Log a message containing a credit card number
6. Verify the card number is masked
7. Verify masking is consistent across all log levels

---

## Story: OBS-002 — Screenshots & Videos
**Jira:** `TE-147` | **Priority:** mandatory | **Skeleton:** L2, L3

**User Story:** As a test engineer debugging failures, I want automatic screenshots and videos on test failure, so that I can understand what went wrong without re-running tests.

**Acceptance Criteria:**
- [ ] Screenshots captured automatically on every test failure
- [ ] Videos recorded for web and mobile tests (full test duration)
- [ ] Artifacts stored in `build/test-artifacts/` by default
- [ ] Storage location configurable via environment config
- [ ] Screenshot capture on success is configurable (OFF by default)
- [ ] Artifact links (relative paths) included in JSON and HTML test reports
- [ ] Artifacts organized by test name with consistent naming convention
- [ ] Artifact metadata includes: test name, timestamp, resolution

**Architectural Layer:** L3 Core (WebDriver, Appium)
**Keywords:** screenshots, videos, artifacts, failure-debugging, recording

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

## Story: OBS-003 — Rich Error Context & Diagnostics
**Jira:** `TE-148` | **Priority:** required | **Skeleton:** L2, L3

**User Story:** As a test engineer, I want detailed error information including stack traces and context, so that I can quickly diagnose and fix test failures.

**Acceptance Criteria:**
- [ ] Full stack traces captured on every exception (all frames, file names, line numbers)
- [ ] Error context includes: what operation was being performed, resource state, input data
- [ ] Screenshot and video artifact links included in error output
- [ ] Console output (stdout/stderr) captured and attached to error report
- [ ] Exception type and message clearly stated (not just "AssertionError")
- [ ] Reproduction steps documented in error context (test steps up to failure)

**Architectural Layer:** L4 Util (Logger) + L3 Core
**Keywords:** error-context, stack-trace, diagnostics, reproduction-steps

---

### TC-OBS-3-001 — Full Stack Traces Captured
**Jira:** `TE-203` | **Parent:** OBS-003

**Verification Steps:**
1. Execute a test that throws an exception
2. Verify the full stack trace is captured in the error output
3. Verify all stack frames are included (not truncated)
4. Verify file names and line numbers are present in each frame
5. Verify the trace is properly formatted for readability

---

### TC-OBS-3-002 — Error Context Information
**Jira:** `TE-204` | **Parent:** OBS-003

**Verification Steps:**
1. Execute a test that creates a resource and throws an exception during creation
2. Verify the error includes context about what operation was being performed
3. Verify the resource state (ID, type, partial data) is captured in the error
4. Verify the action being performed (CREATE, UPDATE, DELETE) is noted in the error

---

### TC-OBS-3-003 — Screenshot Link with Error
**Jira:** `TE-205` | **Parent:** OBS-003

**Verification Steps:**
1. Execute a failing test (UI test)
2. Capture error diagnostics
3. Verify a screenshot link is included in the error output
4. Verify the link points to the correct screenshot file
5. Verify the screenshot shows the error state of the UI

---

### TC-OBS-3-004 — Video Link with Error
**Jira:** `TE-206` | **Parent:** OBS-003

**Verification Steps:**
1. Execute a failing web or mobile test
2. Capture error diagnostics
3. Verify a video link is included in the error output
4. Verify the video shows events leading up to the failure
5. Verify the failure sequence can be replayed

---

### TC-OBS-3-005 — Console Output with Error
**Jira:** `TE-207` | **Parent:** OBS-003

**Verification Steps:**
1. Execute a test that produces console output before throwing an exception
2. Verify all console output (stdout/stderr) before the error is captured
3. Verify all output before the error is included in the diagnostics
4. Verify the output helps identify the root cause

---

### TC-OBS-3-006 — Reproduction Steps
**Jira:** `TE-208` | **Parent:** OBS-003

**Verification Steps:**
1. Execute a failing test
2. Capture error diagnostics
3. Verify test steps executed up to the failure are documented
4. Verify input data used by the test is captured in diagnostics
5. Verify the reproduction information is sufficient to re-run the failure manually

---

## Story: OBS-004 — Performance Metrics
**Jira:** `TE-149` | **Priority:** required | **Skeleton:** L2, L3

**User Story:** As a performance engineer, I want to track response times and test durations, so that I can identify performance regressions.

**Acceptance Criteria:**
- [ ] HTTP response time logged per request (millisecond accuracy, within 10ms)
- [ ] Total test duration tracked (setup + execution + teardown separately)
- [ ] Slow tests (> 30s threshold, configurable) flagged and highlighted in reports
- [ ] API response times compared against configurable thresholds; breach flagged
- [ ] Performance metrics exported in test report for trend analysis

**Architectural Layer:** L4 Util + L3 Core (API client instrumentation)
**Keywords:** performance, response-time, duration, slow-test, metrics

---

### TC-OBS-4-001 — HTTP Response Time Logging
**Jira:** `TE-209` | **Parent:** OBS-004

**Verification Steps:**
1. Execute an API test that makes HTTP requests
2. Verify response time is captured for each HTTP request
3. Verify timing is in milliseconds
4. Verify accuracy is within 10ms of actual elapsed time
5. Verify response time is included in structured JSON log

---

### TC-OBS-4-002 — Test Duration Tracking
**Jira:** `TE-210` | **Parent:** OBS-004

**Verification Steps:**
1. Execute a test with a known approximate duration
2. Capture the total test time (setup + execution + teardown)
3. Verify duration includes all phases
4. Verify duration is included in the test report
5. Verify accuracy is within 100ms of actual elapsed time

---

### TC-OBS-4-003 — Setup vs Execution Separation
**Jira:** `TE-211` | **Parent:** OBS-004

**Verification Steps:**
1. Execute a test with a distinct setup phase
2. Record timestamp at setup completion
3. Record timestamp at test execution start
4. Complete test execution and teardown
5. Verify setup time, execution time, and teardown time are reported separately
6. Verify each phase duration is measured independently

---

### TC-OBS-4-004 — Slow Test Identification
**Jira:** `TE-212` | **Parent:** OBS-004

**Verification Steps:**
1. Execute a test suite containing tests that exceed 30 seconds
2. Verify tests exceeding the threshold are flagged in the report
3. Verify slow tests are marked distinctly (e.g., warning label or color)
4. Verify all slow tests are collected in a summary section
5. Verify a slow test summary is generated at the end of the run

---

### TC-OBS-4-005 — API Performance Thresholds
**Jira:** `TE-213` | **Parent:** OBS-004

**Verification Steps:**
1. Configure an API response time threshold (e.g., 1 second) in environment config
2. Execute an API test
3. Compare actual response time to the configured threshold
4. Verify the test or report flags a breach if the threshold is exceeded
5. Verify a performance report section is generated

---

## Story: TEST-003 — Test Reports
**Jira:** `TE-164` | **Priority:** mandatory | **Skeleton:** L2

**User Story:** As a test manager, I want machine-readable JSON and human-readable HTML test reports, so that I can integrate results into dashboards and analytics.

**Acceptance Criteria:**
- [ ] JSON metrics report generated per test class (`metrics-{ClassName}.json`)
- [ ] HTML report generated per test class (`report.html`) from template `src/business/resource/templates/test-report.html`
- [ ] Global HTML summary generated after all test processes complete (`results-{testRunId}.html`)
- [ ] Reports include execution metadata: timestamp, environment, framework version
- [ ] Per-test details: ID, name, tags, status (passed/failed/ignored), duration (ms)
- [ ] Failure details included: message, stack trace, log file link
- [ ] Artifact links (screenshots, videos) embedded in HTML report
- [ ] Report schema documented in `src/business/resource/templates/metrics-schema.json`

**Architectural Layer:** L2 Business (TestReporter) + Framework core
**Keywords:** reports, json, html, metrics, schema, test-results

---

### TC-TEST-3-001 — JSON Report Generation
**Jira:** `TE-283` | **Parent:** TEST-003

**Verification Steps:**
1. Execute tests spanning multiple test suites
2. Verify per-class JSON metrics files are created (`metrics-{ClassName}.json`)
3. Verify per-class HTML reports are created (`report.html`)
4. Verify a global HTML summary report is created (`results-{testRunId}.html`)
5. Verify each JSON report is valid JSON
6. Verify reports contain test results
7. Verify report location follows the standard (`build/test-results/`)

---

### TC-TEST-3-002 — Execution Metadata in Report
**Jira:** `TE-284` | **Parent:** TEST-003

**Verification Steps:**
1. Generate a test report
2. Verify the execution timestamp is present (ISO 8601)
3. Verify the environment identifier is present
4. Verify the test framework version is present
5. Verify all required metadata fields are present per `metrics-schema.json`

---

### TC-TEST-3-003 — Artifact Links in Report
**Jira:** `TE-285` | **Parent:** TEST-003

**Verification Steps:**
1. Execute tests that produce screenshots and videos
2. Generate the test report
3. Verify screenshot links are embedded in the HTML report
4. Verify video links are embedded in the HTML report
5. Verify all links are accessible (relative paths resolve correctly)

---

### TC-TEST-3-004 — Test Statistics in Report
**Jira:** `TE-286` | **Parent:** TEST-003

**Verification Steps:**
1. Generate a test report
2. Verify the total test count is correct
3. Verify the passed count is correct
4. Verify the failed count is correct
5. Verify the skipped/ignored count is correct
6. Verify pass/fail percentages are calculated correctly

---

## Story: TEST-004 — Test Statistics
**Jira:** `TE-165` | **Priority:** required | **Skeleton:** L2

**User Story:** As a test analyst, I want aggregated test statistics (pass rate, flakiness, duration trends), so that I can monitor test suite health and identify problem areas.

**Acceptance Criteria:**
- [ ] Statistics generated after each test run (total, pass/fail rates per tag and overall)
- [ ] Pass/fail rates broken down by severity tag, category tag, and domain tag
- [ ] Flakiness detection: tests that pass/fail inconsistently are flagged
- [ ] Duration trends tracked over time (requires persistent storage or comparison)
- [ ] Statistics exportable as CSV and JSON
- [ ] Visualizations suitable for embedding in dashboards

**Architectural Layer:** L2 Business (TestReporter + aggregation)
**Keywords:** statistics, pass-rate, flakiness, duration-trends, dashboards

*(Note: No sub-task test cases defined in current Jira export for TEST-004)*

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| OBS-001 | TE-146 | TC-OBS-1-001 to TC-OBS-1-003 | TE-190, TE-191, TE-192 |
| OBS-002 (report scope) | TE-147 | TC-OBS-2-005 | TE-197 |
| OBS-003 | TE-148 | TC-OBS-3-001 to TC-OBS-3-006 | TE-203, TE-204, TE-205, TE-206, TE-207, TE-208 |
| OBS-004 | TE-149 | TC-OBS-4-001 to TC-OBS-4-005 | TE-209, TE-210, TE-211, TE-212, TE-213 |
| TEST-003 | TE-164 | TC-TEST-3-001 to TC-TEST-3-004 | TE-283, TE-284, TE-285, TE-286 |
| TEST-004 | TE-165 | *(no sub-tasks in Jira export)* | — |

**Total:** 6 stories · 19 test cases
