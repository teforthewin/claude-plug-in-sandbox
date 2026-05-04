---
name: tet-atf-knowledge:10-logging-reporting
description: TET-ATF structured JSON log format, mandatory sensitive data masking rules, two-phase test reporting pipeline (per-class + global aggregation), required report artifacts, and Datadog CI Visibility JUnit XML contract. Use when implementing logging calls, report generation, or reviewing any output-producing code.
---

# Skill 10 — Logging & Reporting

## Test Step Logging (MANDATORY — every test method)

Every test method MUST emit at least one `Logger().info()` call that makes intent,
input, and output human-readable in reports without reading the source code.

### Pattern A — simple test (single assertion)

```
result = SomeUtil.method(input)
Logger.info(
  "method: plain-English description of what is verified",
  context: { input: input, output: result, expected: expected }
)
assert result == expected
```

### Pattern B — multi-step test

```
Logger.info("STEP: what we set up or trigger", context: { input: ..., count: ... })
result = SomeUtil.complexMethod(...)
Logger.info("ASSERT: contract we verify", context: { output: result, expected: ... })
assert result == expected
```

### Rules

| Rule | Detail |
|------|--------|
| **Message** | Short verb phrase in plain English — `"to_int: convert numeric string → int"`, not `"test_converts_string"` |
| **`input`** | Always include the value passed in (except large fixture objects) |
| **`output`** | Always include the actual returned / observed value |
| **`expected`** | Include the assertion target so the log is self-contained |
| **Log level** | `Logger.info()` — never raw print statements or native logging calls |
| **Mocked tests** | Log what was captured from the mock and what assertion follows |
| **File I/O tests** | Log the file path and key facts (size, schema valid, key field values) |

---

## Structured JSON Log Format

Every log entry MUST include:

```json
{
  "timestamp": "2026-02-26T10:00:00.000Z",
  "level": "INFO",
  "testId": "TC-001",
  "executionId": "exec-20260226T100000",
  "tags": { "severity": "smoke", "category": "api" },
  "message": "...",
  "context": { "key": "value" }
}
```

Use `Logger.*` — never raw print statements or native logging calls.

---

## Sensitive Data Masking (MANDATORY)

Always mask these fields before logging:

| Field type | Masking rule |
|-----------|-------------|
| Passwords | `"***"` |
| Tokens / API keys | `"{first4}...{last4}"` |
| PII (email, phone, SSN) | `"[MASKED]"` |
| Credit card numbers | `"****-****-****-{last4}"` |

`Logger` applies masking automatically when context keys match sensitive patterns.

---

## Channel-Specific Observability Rules (MANDATORY)

These rules extend the base logging requirements above. They apply on top of the standard `Logger.info()` contract.

### Web & Mobile — Screenshot Rule

| Requirement | Detail |
|-------------|--------|
| **Trigger** | Every public interaction method in `BasePage` / `BaseMobilePage` hierarchy |
| **What** | Capture a full-page / full-screen screenshot immediately after the action completes |
| **Storage** | `build/test-results/{ClassName}/screenshots/{ClassName}_{methodName}_{timestamp}.png` |
| **Log field** | `screenshot` key in the `Logger.info()` context for that step — value is the relative path |
| **On failure** | Capture screenshot inside `finally` block so it is always saved even when the step throws |
| **Report** | `report.html` MUST render screenshot thumbnails (click to enlarge) inline with the step log entry |

```
✅  screenshot captured after every interaction method
✅  screenshot path logged in structured step entry
✅  screenshot embedded as thumbnail in report.html
❌  screenshots stored outside build/test-results/{ClassName}/screenshots/
❌  screenshot path missing from Logger context
```

### API — Request/Response Logging Rule

Every `BaseApiClient` HTTP call MUST produce ONE structured log entry containing ALL of the following:

| Field | Rule |
|-------|------|
| `method` | HTTP verb: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `uri` | Full URL with path and query params |
| `requestHeaders` | All headers — Authorization / Cookie / X-Api-Key / token headers → `"[MASKED]"` |
| `requestBody` | Full body; mask password/token fields per Sensitive Data Masking table |
| `responseStatus` | Status code + reason (e.g. `"200 OK"`) |
| `responseHeaders` | All response headers |
| `responseBody` | Full body; mask sensitive fields |
| `durationMs` | Integer ms from send to last byte received |
| `testId` | `TestContext.current().test_id` |

```
✅  all 9 fields present in every API log entry
✅  auth headers masked before logging
✅  API log entry visible and formatted in report.html
❌  partial logging (e.g. only status code)
❌  raw Authorization header value logged
```

---

## Two-Phase Test Reporting

### Phase 1 — Per Test Class (runs inside each test process)

Each test class produces its own output folder:

```
build/test-results/{ClassName}/
  ├── report.html                    ← rendered from src/business/resource/templates/test-report.html
  ├── metrics-{ClassName}.json       ← validated against metrics-schema.json
  └── {ClassName}.log                ← raw structured log for this class
```

### Phase 2 — Global Aggregation (runs after ALL processes finish)

```
build/test-results/
  ├── global-summary.json            ← validated against report-schema.json
  ├── results-{testRunId}.html       ← rendered from global-summary-report.html template
  └── test-results-{timestamp}-final.zip
```

---

## Required Report Artifacts per Test Run

Every test run MUST produce:

| Artifact | Schema / Template |
|----------|-------------------|
| `metrics-{ClassName}.json` | `metrics-schema.json` |
| `report.html` | `test-report.html` |
| JUnit XML | CI-compatible (GitHub Actions, Jenkins, GitLab CI, **Datadog CI Visibility**) |
| `screenshots/*.png` | Web/Mobile tests only — one file per interaction step + one on failure |

`report.html` MUST render:
- For web/mobile tests: screenshot thumbnails inline with each step log entry (click to enlarge)
- For API tests: collapsible request/response blocks showing URI, headers (auth masked), body, status, response headers, response body

---

## JUnit XML — Datadog CI Visibility Contract (MANDATORY)

Datadog's JUnit uploader parses **only** `<property>` elements whose `name`
attribute matches the exact format `dd_tags[key]`. **All other property
names are silently dropped** — bare-named properties like `service`,
`environment`, `testRunId`, or `<property name="tag" value="smoke"/>`
**never** surface as searchable fields in the Datadog UI.

Source: <https://docs.datadoghq.com/tests/setup/junit_xml/> — *"To be
processed, the `name` attribute in the `<property>` element must have the
format `dd_tags[key]`. Other properties are ignored."*

### Required `<testsuite>` properties

Every JUnit XML emitted MUST carry both forms for each metadatum — bare-named
for GitHub Actions / Jenkins / GitLab consumers, and `dd_tags[...]` for
Datadog. Emit duplicates, not replacements.

| Metadatum | Bare-named (other CI) | `dd_tags[...]` (Datadog, REQUIRED) |
|---|---|---|
| Run ID | `testRunId`, `executionId` | `dd_tags[test.run_id]`, `dd_tags[test.execution_id]` |
| Service | `service` | `dd_tags[service]`, `dd_tags[framework.name]` |
| Environment | `environment` | `dd_tags[env]` |
| Framework version | `frameworkVersion` | `dd_tags[framework.version]` |
| Runtime (name/version/vendor/arch) | `pythonVersion` | `dd_tags[runtime.name]`, `dd_tags[runtime.version]`, `dd_tags[runtime.vendor]`, `dd_tags[runtime.architecture]` |
| OS (platform/version/arch) | — | `dd_tags[os.platform]`, `dd_tags[os.version]`, `dd_tags[os.architecture]` |

### Required `<testcase>` properties

Every `<testcase>` MUST expose its ID and tag set under `dd_tags[test.*]`
keys so each test span is searchable in Datadog:

| Key | Source | Multiplicity |
|---|---|---|
| `dd_tags[test.id]` | Stable scenario/test ID (e.g. `TC-042`) | exactly 1 |
| `dd_tags[test.severity]` | Severity tag (`smoke`, `mandatory`, `required`, `advisory`, `deprecated`) | 0 or 1 |
| `dd_tags[test.category]` | Channel tag (`api`, `web`, `mobile`) | 0..N |
| `dd_tags[test.domain]` | Domain tag (e.g. `auth`, `billing`) | 0..N |
| `dd_tags[test.metadata]` | Metadata tag (`flaky`, `skip`, `manual`) | 0..N |

### `datadog-ci junit upload` invocation

The CLI must always receive `--env` and run-level `--tags` — tags not
present in the XML (or that must win over XML) go here:

```bash
datadog-ci junit upload \
  --service "$SERVICE" \
  --env "$ENVIRONMENT" \
  --tags "test.run_id:$RUN_ID" \
  --tags "framework.name:$SERVICE" \
  --tags "framework.version:$FRAMEWORK_VERSION" \
  --report-tags "test.run_id:$RUN_ID" \
  "$JUNIT_PATH"
```

### Self-check

```
✅ every run-level metadatum present both as bare-name AND as dd_tags[...]
✅ every testcase carries dd_tags[test.id] + applicable dd_tags[test.{severity,category,domain,metadata}]
✅ export-datadog.* script passes --env, --tags, and --report-tags
❌ a metadatum emitted only as bare-named <property name="X" .../> (Datadog drops it)
❌ per-test tags emitted only as <property name="tag" value="..."/> (Datadog drops them)
❌ datadog-ci junit upload called without --env (environment silently missing)
```

---

## testRunId

A single unique ID shared across all parallel processes in one test run.  
Passed via system property or env var. Stored in `TestContext` as `executionId`.

---

## Post-Run Cleanup

After **successful** ZIP creation → delete all intermediate per-class folders. Only the final ZIP is retained.

On **failed** runs → preserve all per-class folders until the next successful run, so developers can inspect individual class logs and screenshots without unpacking the archive. The CI artifact retention policy should keep failed-run artifacts for at least 7 days.

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (OBS-001, OBS-002, OBS-003, OBS-004, TEST-003, TEST-004) and test cases (TC-OBS-1-xxx, TC-OBS-2-005, TC-OBS-3-xxx, TC-OBS-4-xxx, TC-TEST-3-xxx)
