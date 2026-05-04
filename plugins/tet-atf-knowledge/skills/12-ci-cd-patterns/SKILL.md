---
name: tet-atf-knowledge:12-ci-cd-patterns
description: TET-ATF 4-stage CI/CD pipeline architecture (validate→test→report→publish), job dependencies, artifact tagging strategy, two-phase test reporting, execution profiles (smoke/regression/nightly), and security scanning layers. Use when setting up CI/CD workflows, configuring test execution jobs, or implementing artifact publishing.
---

# Skill 12 — CI/CD Pipeline Patterns

## 4-Stage Pipeline Architecture

```
Stage 1: VALIDATE & SCAN (2 min, parallel)
  ├─ Job A: validate-tests (smoke tests + code analysis)
  └─ Job B: security-scan (dependencies + artifact prep)
         ↓
Stage 2: BUILD & TEST (5-60 min)
  └─ Job: test-regression (full test suite, depends on Stage 1)
         ↓
Stage 3: REPORT & EXPORT (2 min)
  └─ Job: report (aggregation, JUnit, Datadog export, depends on Stage 2)
         ↓
Stage 4: PUBLISH (5 min, main branch only)
  └─ Job: build (artifact build, scan, push to registry, depends on Stage 3)
```

**Key:** Each stage waits for previous stage → prevents broken artifacts from publishing.

---

## Job Dependency Rules

| Job | Depends On | Runs On | Condition |
|-----|-----------|---------|-----------|
| validate-tests | None | Every commit | Always |
| security-scan | None | Every commit | Always (parallel to validate-tests) |
| test-regression | validate-tests + security-scan | After Stage 1 | Always |
| report | test-regression | After Stage 2 | Always (even if tests fail) |
| build | report | After Stage 3 | `main` branch + `push` event only |

**CRITICAL:** Use `if: always()` on report job so it runs even if tests fail — ensures results are captured.

---

## Artifact Tagging Strategy

### Tag Structure (4 layers)

```
{version}-{environment}-{source}-{timestamp}

Examples:
  v1.2.3-release-sha-abc123-20260227           ← Release build
  dev-main-sha-abc123-20260227                 ← Development
  v1.2.3-rc.1-staging-sha-abc123              ← Release candidate
  dev-feature-branch-xyz789-20260227          ← Feature branch
```

**Layer 1: Version**
- `v{semver}` for releases (e.g., v1.2.3)
- `dev` for development/snapshots
- `v{semver}-rc.N` for release candidates

**Layer 2: Environment**
- `release` (production-ready)
- `staging` (pre-production)
- `dev` (development)
- `main` (main branch development)
- `{branch-name}` (feature branch)

**Layer 3: Source**
- `sha-{short-sha}` (git commit identifier)
- Enables traceability to exact code version

**Layer 4: Timestamp**
- `{YYYYMMDD}` or ISO-8601 (e.g., 20260227, 2026-02-27T09:30:00Z)
- Enables chronological ordering, debugging

---

## Test Reporting Architecture (Two-Phase)

### Phase 1: Per-Test-Class Results (Parallel-Safe)

**When:** During Stage 2 (test-regression job)  
**Where:** Each test process writes independently to `test-outputs/reports/{ClassName}/`  
**Files generated:**
- `metrics-{ClassName}.json` — Test results (schema-validated)
- `{ClassName}.log` — Logs with sensitive data masking
- `report.html` — HTML report for this test class

**Key:** No process touches another's files → safe for parallel execution.

### Phase 2: Global Aggregation (Sequential)

**When:** Stage 3 (report job), after all test processes complete  
**What:** Merge all Phase 1 results into single source of truth  
**Files generated:**
- `global-summary.json` — Aggregated statistics (pass/fail/skip counts, timing)
- `results-{executionId}.html` — Global report with navigation between test classes
- `junit.xml` — JUnit format for CI/CD tools (Jenkins, GitHub, GitLab)
- `test-results-final.zip` — Archive containing all results

**Why two phases:**
- Prevents "last-writer-wins" corruption when tests run in parallel
- Each process owns its own results file (no locking needed)
- Aggregation is deterministic and repeatable

---

## Security Scanning Layers

### Layer 1: Code Analysis (Stage 1, validate-tests)

**Purpose:** Find static vulnerabilities in YOUR code  
**Tools per language:**
- JavaScript/TypeScript → ESLint, TSLint + security plugins
- Python → pylint, bandit
- Java/Kotlin → checkstyle, SpotBugs
- Go → golangci-lint (includes security checks)

**Failure behavior:**
- CRITICAL → blocks pipeline
- HIGH → warning, continues
- MEDIUM/LOW → report only

### Layer 2: Dependency Scanning (Stage 1, security-scan)

**Purpose:** Find vulnerabilities in 3rd-party libraries  
**Tools per language:**
- JavaScript/npm → npm audit, Snyk, OWASP CycloneDX
- Python/pip → pip-audit, safety
- Java/Maven → OWASP CycloneDX, Maven dependency-check
- Go → nancy, go list

**Exception management:** `.npmignore`, `.python-safety`, `.trivyignore`, etc.

**Failure behavior:**
- CRITICAL → blocks pipeline
- HIGH → warning (with justification + expiration date required)
- MEDIUM/LOW → report only

### Layer 3: Artifact Scanning (Stage 4, after artifact build)

**Purpose:** Find vulnerabilities in built artifacts (Docker images, packages)  
**Universal tools:**
- Trivy (Docker images, packages, multiformat)
- Grype (images, packages)
- Anchore (Docker)

**Failure behavior:**
- CRITICAL → blocks publication to registry
- HIGH → warning (review required)
- MEDIUM/LOW → report only

---

## Execution Strategies

| Strategy | Filter | Duration | Trigger | Stop on First Failure |
|----------|--------|----------|---------|----------------------|
| **smoke** | @smoke only | ~5 min | Every commit | Yes (fail-fast) |
| **regression** | @smoke + @mandatory + @required | ~20-60 min | Before release, merge to main | No (run all) |
| **nightly** | All except @deprecated | 1-4 hours | Scheduled nightly | No (run all) |
| **custom** | User-specified | Variable | On-demand | User choice |

**Implementation:** Pass tag filter to test runner per language:
```bash
# Smoke tests
task test:smoke          # Runs @smoke only

# Regression tests
task test:regression     # Runs @smoke,@mandatory,@required

# Nightly
task test:nightly        # Runs all except @deprecated

# Custom
task test --filter @api  # User-specified tags
```

---

## CI/CD Workflow Structure (GitHub Actions Example)

```yaml
name: Build and Scan Test Framework

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 9 * * 1'  # Weekly scan

jobs:
  # Stage 1a: Validate & Test
  validate-tests:
    runs-on: ubuntu-latest
    steps:
      - install dependencies
      - run smoke tests (@smoke)
      - upload results

  # Stage 1b: Security Scan (parallel with validate-tests)
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - run code analysis
      - run dependency audit
      - upload results

  # Stage 2: Full Test Suite (depends on Stage 1)
  test-regression:
    needs: [validate-tests, security-scan]
    runs-on: ubuntu-latest
    steps:
      - install dependencies
      - run regression tests (@smoke,@mandatory,@required)
      - upload Phase 1 results

  # Stage 3: Aggregate & Export (depends on Stage 2)
  report:
    needs: test-regression
    if: always()  # Run even if tests fail
    runs-on: ubuntu-latest
    steps:
      - download all Phase 1 results
      - aggregate into global report (Phase 2)
      - generate JUnit XML
      - export to Datadog (optional)
      - upload final archive

  # Stage 4: Publish (main only, depends on Stage 3)
  build:
    needs: report
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - build artifact (Docker, npm, JAR, etc.)
      - scan artifact for vulnerabilities
      - push to registry (ECR, npm, PyPI, Maven)
```

---

## PR Branch Pipeline

On feature / PR branches, run only Stages 1–2 (no publish). This keeps feedback fast while preventing untested artifacts from reaching the registry.

```yaml
# Stage 4 (publish) — main branch only
build:
  needs: report
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
```

On PR branches, smoke tests run in Stage 1 instead of the full regression suite to keep CI under 10 minutes.

---

## Related Skills

- **Skill 05** (Coding Standards) — Task implementation quality
- **Skill 10** (Logging & Reporting) — Log masking, report generation
- **Skill 11** (Security & Config) — Credential management, env vars
- **Skill 03** (Tag System) — Test tag filtering, execution profiles
- **Skill 09** (Test Isolation) — TestContext, resource cleanup in tests

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (CICD-001 to 004, OPS-001 to 005, SEC-003) and test cases (TC-CICD-xxx, TC-OPS-xxx, TC-SEC-3-xxx)

---

**END OF SKILL 12 — CI/CD PIPELINE PATTERNS**
