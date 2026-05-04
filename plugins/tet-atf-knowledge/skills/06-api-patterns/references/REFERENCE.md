# References — Skill 06: API Patterns

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate the API client 3-level hierarchy (`BaseApiClient` → `AppBaseApi` → `ResourceApi`), singleton pattern, JSON schema validation, and structured request logging defined in this skill.

---

## Story: QA-001 — Multi-Channel Testing (API channel)
**Jira:** `TE-134` | **Priority:** smoke | **Skeleton:** L2, L3

**User Story:** As a test automation engineer, I want to write tests for API, Web UI, and Mobile channels using a single framework, so that I can maintain tests across all channels without learning multiple tools.

**Acceptance Criteria (API-specific):**
- [ ] API tests use custom HTTP client (`BaseApiClient` hierarchy in `src/core/api/`)
- [ ] Tests are organized by channel: `tests/{domain}/api/`
- [ ] Documentation includes working examples for the API channel

**Architectural Layer:** L3 Core + L2 Business + L1 Test
**Keywords:** api, multi-channel, base-api-client

---

### TC-QA-1-001 — API Test Execution with Custom HTTP Client
**Jira:** `TE-234` | **Parent:** QA-001

**Verification Steps:**
1. Create an API test using the custom HTTP client
2. Execute a GET request to a test endpoint
3. Execute a POST request with request body
4. Execute a PUT request with modifications
5. Execute a DELETE request
6. Verify response status codes
7. Verify response body content
8. Verify response headers

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

## Story: MAINT-002 — Reusable Components (API Client)
**Jira:** `TE-143` | **Priority:** mandatory | **Skeleton:** L2, L3

**User Story:** As a test automation engineer, I want reusable Page Objects and API Clients, so that test code is DRY and maintainable.

**Acceptance Criteria (API Client-specific):**
- [ ] API Client base classes: `BaseApiClient` → `AppBaseApi` → `ResourceApi` in `src/core/api/`
- [ ] HTTP methods (GET, POST, PUT, DELETE, PATCH) implemented in `BaseApiClient`
- [ ] All API interactions logged via structured logger (JSON schema-compliant)
- [ ] Inheritance hierarchy enables maximum code reuse across domains

**Architectural Layer:** L3 Core
**Keywords:** api-client, base-api-client, inheritance, http-methods

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

## Story: OBS-004 — Performance Metrics (API Response Times)
**Jira:** `TE-149` | **Priority:** required | **Skeleton:** L2, L3

**User Story:** As a performance engineer, I want to track response times and test durations, so that I can identify performance regressions.

**Acceptance Criteria (API-specific):**
- [ ] HTTP response time logged per request (millisecond accuracy, within 10ms)
- [ ] API response times compared against configurable thresholds; breach flagged
- [ ] Performance metrics exported in test report for trend analysis

**Architectural Layer:** L4 Util + L3 Core (API client instrumentation)
**Keywords:** performance, response-time, api-instrumentation

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

### TC-OBS-4-005 — API Performance Thresholds
**Jira:** `TE-213` | **Parent:** OBS-004

**Verification Steps:**
1. Configure an API response time threshold (e.g., 1 second) in environment config
2. Execute an API test
3. Compare actual response time to the configured threshold
4. Verify the test or report flags a breach if the threshold is exceeded
5. Verify a performance report section is generated

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| QA-001 (API scope) | TE-134 | TC-QA-1-001, TC-QA-1-004 | TE-234, TE-237 |
| MAINT-002 (API scope) | TE-143 | TC-MAINT-2-002 | TE-184 |
| OBS-004 (API scope) | TE-149 | TC-OBS-4-001, TC-OBS-4-005 | TE-209, TE-213 |

**Total:** 3 stories · 5 test cases
