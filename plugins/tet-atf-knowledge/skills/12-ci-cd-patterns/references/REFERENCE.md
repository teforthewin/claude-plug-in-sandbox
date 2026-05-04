# References — Skill 12: CI/CD Patterns

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate the 4-stage CI/CD pipeline architecture, job dependencies, artifact tagging strategy, two-phase test reporting, and security scanning layers defined in this skill.

---

## Story: CICD-001 — Docker Image
**Jira:** `TE-150` | **Priority:** mandatory | **Skeleton:** L1, L2

**User Story:** As a DevOps engineer, I want an optimized Docker image with all test dependencies, so that tests can run consistently in containers.

**Acceptance Criteria:**
- [ ] Image includes relevant runtime(s) and SDKs
- [ ] Chromium browser included for web test execution
- [ ] Prerequisites installed for Appium and/or Playwright
- [ ] Mobile SDK available as optional base layer
- [ ] Multi-stage build used for image size optimization
- [ ] Image published to Docker registry (AWS ECR or equivalent)

**Architectural Layer:** Infrastructure / DevOps
**Keywords:** docker, container, image, registry, multi-stage

---

### TC-CICD-1-001 — Tests Execute in Container
**Jira:** `TE-171` | **Parent:** CICD-001

**Verification Steps:**
1. Build the Docker image from the framework Dockerfile
2. Run the test container (`docker run`)
3. Execute a sample test inside the container
4. Verify test runs successfully
5. Verify output (logs, reports) is captured
6. Verify generated test outputs are accessible
7. Verify generated messages/metrics match expected format

---

### TC-CICD-1-002 — Image Published to Registry
**Jira:** `TE-172` | **Parent:** CICD-001

**Verification Steps:**
1. Build Docker image
2. Tag image with version identifier
3. Publish image to configured registry (ECR or equivalent)
4. Verify image is accessible in the registry
5. Verify image pull works from the registry

---

## Story: CICD-002 — Kubernetes Ready
**Jira:** `TE-151` | **Priority:** required | **Skeleton:** L1, L2

**User Story:** As a Kubernetes cluster administrator, I want the framework to run in Kubernetes with environment variables and config mounts, so that I can orchestrate test execution on my cluster.

**Acceptance Criteria:**
- [ ] Helm charts/templates available in `k8s/helm/`
- [ ] Pod runs as non-root user with read-only filesystem where possible
- [ ] Resource limits (CPU, memory) defined for all pods
- [ ] No privilege escalation allowed
- [ ] Secrets manager integration configured (no credentials in ConfigMaps)
- [ ] Test reports accessible after pod completion (volume mount or object storage)

**Architectural Layer:** Infrastructure / DevOps
**Keywords:** kubernetes, helm, pod-security, environment-variables

---

### TC-CICD-2-001 — Environment Variable Support
**Jira:** `TE-173` | **Parent:** CICD-002

**Verification Steps:**
1. Verify Helm config files are available in `k8s/helm/`
2. Execute all deployment workflows
3. Verify the service is correctly deployed and running in Kubernetes
4. Verify connection to Secrets Manager is correctly configured
5. Verify tests correctly reach the tested system and reports are stored/propagated

---

### TC-CICD-2-002 — Pod Security Standards
**Jira:** `TE-174` | **Parent:** CICD-002

**Verification Steps:**
1. Review pod specifications in Helm templates
2. Verify non-root user is used (no root-level process)
3. Verify read-only filesystem is configured where possible
4. Verify CPU and memory resource limits are set
5. Verify no privilege escalation is allowed

---

## Story: CICD-003 — GitHub Actions Support
**Jira:** `TE-152` | **Priority:** mandatory | **Skeleton:** L1, L2

**User Story:** As a GitHub user, I want workflow templates for running tests in GitHub Actions, so that I can automate test execution on every commit.

**Acceptance Criteria:**
- [ ] Workflow for unit tests on PRs (`on: pull_request`)
- [ ] Workflow for regression tests on nightly schedule
- [ ] Docker image build-and-push workflow
- [ ] Test results published to GitHub Checks API
- [ ] Failure notifications mechanism configured

**Architectural Layer:** CI/CD
**Keywords:** github-actions, ci-cd, workflows, checks-api, pr-automation

---

### TC-CICD-3-001 — PR Unit Tests Workflow
**Jira:** `TE-175` | **Parent:** CICD-003

**Verification Steps:**
1. Review GitHub Actions workflow configuration files
2. Verify workflow triggers correctly (`on: pull_request` or `on: push`)
3. Execute workflow manually via GitHub Actions UI
4. Verify tests run and report results to GitHub Checks API
5. Verify test artifacts are created and accessible

---

## Story: CICD-004 — Helm Charts
**Jira:** `TE-153` | **Priority:** required | **Skeleton:** L1, L2

**User Story:** As a Kubernetes operator, I want Helm charts for deploying test jobs, so that I can use standard Kubernetes deployment practices.

**Acceptance Criteria:**
- [ ] `Chart.yaml` with proper metadata (name, version, description)
- [ ] `values.yaml` with all configurable parameters
- [ ] Job template for one-time test runs
- [ ] CronJob template for scheduled test execution
- [ ] ConfigMap template for test configuration injection
- [ ] Secret template for credentials (references external secret manager)
- [ ] Ingress template for reporting dashboard exposure

**Architectural Layer:** Infrastructure / DevOps
**Keywords:** helm, kubernetes, job, cronjob, configmap, ingress

---

### TC-CICD-4-001 — Helm Chart Structure
**Jira:** `TE-176` | **Parent:** CICD-004

**Verification Steps:**
1. Verify required Helm files exist: `Chart.yaml`, `values.yaml`, Job template, CronJob template, ConfigMap template, Secret template
2. Verify application is correctly deployed in Kubernetes using `helm install`

---

## Story: OPS-001 — One-Command Setup
**Jira:** `TE-157` | **Priority:** smoke | **Skeleton:** L1, L2

**User Story:** As a new team member, I want to run a single setup script to install all prerequisites, so that I can be productive very fast.

**Acceptance Criteria:**
- [ ] Setup script at `scripts/setup-prerequisites.sh` (executable, with `#!/bin/bash` shebang)
- [ ] Script installs runtime(s) with conflict detection (no silent overwrite of existing installs)
- [ ] Script installs SDKs required by the tech stack
- [ ] Script configures git hooks (pre-commit, pre-push linting)
- [ ] Clear progress feedback during installation (step-by-step output)
- [ ] Errors handled gracefully with actionable remediation messages

**Architectural Layer:** Infrastructure
**Keywords:** setup, onboarding, prerequisites, script, developer-experience

---

### TC-OPS-1-001 — Setup Script Exists
**Jira:** `TE-214` | **Parent:** OPS-001

**Verification Steps:**
1. Verify `scripts/setup-prerequisites.sh` exists in the repository
2. Verify the script is executable (`chmod +x`)
3. Verify the script has a proper shebang line (`#!/bin/bash`)
4. Verify the script is documented (comments, README reference)

---

### TC-OPS-1-002 — Runtime Installation
**Jira:** `TE-215` | **Parent:** OPS-001

**Verification Steps:**
1. Remove the installed runtime from the test environment
2. Execute `scripts/setup-prerequisites.sh`
3. Verify the required runtime is installed
4. Verify the installed version matches the required version
5. Verify the runtime is available in `$PATH`

---

## Story: OPS-002 — Self-Service Execution
**Jira:** `TE-158` | **Priority:** mandatory | **Skeleton:** L2, L3

**User Story:** As a developer, I want to run tests locally via IDE or Docker without additional setup, so that I can test my changes immediately.

**Acceptance Criteria:**
- [ ] Tests runnable directly from IDE (IntelliJ, VSCode — no custom env required)
- [ ] Tests runnable via CLI with a single command
- [ ] Tests runnable in Docker container (`docker run` or `task test:docker`)
- [ ] HTML test reports generated locally and openable in browser
- [ ] No external service dependencies required unless explicitly configured
- [ ] Test filtering by file, method, or tag supported from CLI

**Architectural Layer:** All layers
**Keywords:** local-execution, ide, cli, docker, self-service

---

### TC-OPS-2-001 — CLI Test Execution
**Jira:** `TE-216` | **Parent:** OPS-002

**Verification Steps:**
1. Open a terminal in the project root
2. Run tests using the configured CLI command (e.g., Taskfile task or build script)
3. Verify tests execute and produce output
4. Verify results are reported clearly in the terminal
5. Verify exit code is 0 for all-pass, non-zero for failures

---

### TC-OPS-2-002 — Docker Test Execution
**Jira:** `TE-217` | **Parent:** OPS-002

**Verification Steps:**
1. Build the Docker image for the framework
2. Run tests inside a Docker container
3. Verify tests execute successfully inside the container
4. Mount a volume to expose test results to the host
5. Verify results are accessible on the host after the container exits

---

### TC-OPS-2-003 — Local Test Reports
**Jira:** `TE-218` | **Parent:** OPS-002

**Verification Steps:**
1. Execute tests locally
2. Verify test reports are generated after the run
3. Verify an HTML report exists
4. Open the HTML report in a browser
5. Verify the report is human-readable and fully functional

---

### TC-OPS-2-004 — Test Filtering
**Jira:** `TE-219` | **Parent:** OPS-002

**Verification Steps:**
1. Run a single test file; verify only that file's tests execute
2. Run a single test method by name; verify only that method executes
3. Run tests filtered by tag; verify only matching tests execute

---

## Story: OPS-003 — Task Automation
**Jira:** `TE-159` | **Priority:** required | **Skeleton:** L1, L2

**User Story:** As a DevOps engineer, I want pre-configured Taskfile tasks for common operations, so that I can automate framework operations consistently.

**Acceptance Criteria:**
- [ ] `Taskfile.yaml` at repository root with all tasks documented
- [ ] Setup tasks: `task setup`, install, configure
- [ ] Build tasks: `task build`, clean, compile, package, jar
- [ ] Test tasks: `task test:smoke`, `task test:mandatory`, `task test:all`, `task test:api`, `task test:web`, `task test:mobile`
- [ ] Report tasks: `task report:generate`, `task report:coverage`, `task report:open`
- [ ] Cleanup tasks: `task clean`
- [ ] All tasks have descriptions and usage examples in Taskfile

**Architectural Layer:** Build tool (Taskfile)
**Keywords:** taskfile, automation, build, ci-cd, developer-productivity

---

### TC-OPS-3-001 — Setup Tasks
**Jira:** `TE-220` | **Parent:** OPS-003

**Verification Steps:**
1. List all available Taskfile tasks (`task --list`)
2. Verify `task setup` exists and is documented
3. Verify all documented test tasks exist (`task test:smoke`, `task test:all`, etc.)
4. Execute relevant tasks
5. Verify each task produces the expected output and result

---

## Story: OPS-004 — Quick Start & Onboarding
**Jira:** `TE-160` | **Priority:** required | **Skeleton:** L1, L2

**User Story:** As a new developer, I want a comprehensive quick start guide with samples and tutorials, so that I can understand the framework and write my first test in 15 minutes.

**Acceptance Criteria:**
- [ ] Quick start guide with a clear 15-minute target (step-by-step)
- [ ] Prerequisites listed with exact versions
- [ ] Working sample tests for all three channels (API, Web UI, Mobile)
- [ ] Framework structure explanation: 4 layers, directory organization, role of each layer
- [ ] Channel-specific walkthroughs: API sample, Web UI sample, Mobile sample
- [ ] Configuration guide: YAML files, environment variables, examples
- [ ] Testing utilities guide: Logger, TestContext, DataGenerator usage with examples

**Architectural Layer:** Documentation
**Keywords:** quickstart, onboarding, documentation, samples, 15-minutes

---

### TC-OPS-4-001 — Quick Start Guide Documentation
**Jira:** `TE-221` | **Parent:** OPS-004

**Verification Steps:**
1. Verify a quick start guide exists (e.g., `docs/QUICK_START.md` or `README.md`)
2. Verify a 15-minute completion target is stated in the guide
3. Verify prerequisites are listed with exact versions
4. Verify step-by-step instructions are provided
5. Verify expected outcomes are stated for each step

---

### TC-OPS-4-002 — Sample Tests Provided
**Jira:** `TE-222` | **Parent:** OPS-004

**Verification Steps:**
1. Verify an API sample test exists in the repository
2. Verify a Web UI sample test exists
3. Verify a Mobile sample test exists
4. Verify all samples are runnable without modification
5. Verify each sample demonstrates its respective channel's patterns

---

### TC-OPS-4-003 — API Sample Walkthrough
**Jira:** `TE-223` | **Parent:** OPS-004

**Verification Steps:**
1. Review the API sample documentation
2. Verify HTTP method usage (GET, POST, PUT, DELETE) is shown
3. Verify request/response handling patterns are demonstrated
4. Verify assertions are demonstrated
5. Verify running the sample is explained step-by-step

---

### TC-OPS-4-004 — Web UI Sample Walkthrough
**Jira:** `TE-224` | **Parent:** OPS-004

**Verification Steps:**
1. Review the Web UI sample documentation
2. Verify page object usage is demonstrated
3. Verify element interaction patterns are shown
4. Verify assertions are demonstrated
5. Verify running the sample is explained step-by-step

---

### TC-OPS-4-005 — Mobile Sample Walkthrough
**Jira:** `TE-225` | **Parent:** OPS-004

**Verification Steps:**
1. Review the Mobile sample documentation
2. Verify Appium driver setup is shown
3. Verify screen navigation patterns are demonstrated
4. Verify interaction patterns are shown
5. Verify running the sample is explained step-by-step

---

### TC-OPS-4-006 — Framework Structure Explanation
**Jira:** `TE-226` | **Parent:** OPS-004

**Verification Steps:**
1. Review framework structure documentation
2. Verify the 4-layer architecture is explained with examples
3. Verify directory organization is described
4. Verify the role of each layer is clearly stated
5. Verify examples are provided for code in each layer

---

### TC-OPS-4-007 — Configuration Guide
**Jira:** `TE-227` | **Parent:** OPS-004

**Verification Steps:**
1. Review the configuration guide
2. Verify environment setup instructions are provided
3. Verify YAML config file structure and usage are explained
4. Verify environment variable override mechanism is explained
5. Verify practical examples are included

---

### TC-OPS-4-008 — Testing Utilities Guide
**Jira:** `TE-228` | **Parent:** OPS-004

**Verification Steps:**
1. Review the testing utilities guide
2. Verify `Logger` usage examples are provided
3. Verify `TestContext` usage examples are provided
4. Verify `DataGenerator` usage examples are provided
5. Verify examples cover the most common use cases for each utility

---

## Story: OPS-005 — Multi-Layer Update Mechanism
**Jira:** `TE-161` | **Priority:** advisory | **Skeleton:** L1, L2, L3

**User Story:** As a framework maintainer, I want to sync framework updates across the skeleton hierarchy (L1→L2→L3), so that improvements in the global template automatically propagate to tech-specific and team frameworks.

**Acceptance Criteria:**
- [ ] `scripts/sync-parent-template.sh` syncs L1 → L2 (executable, documented)
- [ ] `scripts/sync-team-framework.sh` syncs L2 → L3 (executable, documented)
- [ ] Sync is git-based (merge/rebase); conflicts require manual resolution
- [ ] Conflict detection notifies the user and halts sync for manual intervention
- [ ] Selective sync: choose specific changes to propagate, skip others
- [ ] Taskfile tasks available: `task sync:all`, `task sync:parent`, `task sync:team-framework`
- [ ] Documentation explains update architecture, process, and conflict resolution

**Architectural Layer:** Infrastructure / DevOps
**Keywords:** sync, multi-layer, hierarchy, propagation, git, l1-l2-l3

---

### TC-OPS-5-001 — L1 to L2 Sync Script
**Jira:** `TE-229` | **Parent:** OPS-005

**Verification Steps:**
1. Verify `scripts/sync-parent-template.sh` exists
2. Verify the script is executable
3. Verify the script has inline documentation (usage, options)
4. Execute sync from L1 to L2
5. Verify changes from L1 propagate to L2

---

### TC-OPS-5-002 — L2 to L3 Sync Script
**Jira:** `TE-230` | **Parent:** OPS-005

**Verification Steps:**
1. Verify `scripts/sync-team-framework.sh` exists
2. Verify the script is executable
3. Verify the script is documented
4. Execute sync from L2 to L3
5. Verify changes from L2 propagate to L3

---

### TC-OPS-5-003 — Git-Based Sync
**Jira:** `TE-231` | **Parent:** OPS-005

**Verification Steps:**
1. Make changes in L1
2. Run sync to L2
3. Verify git history shows a merge or rebase commit
4. Verify commits are tracked in git log
5. Verify git log clearly shows sync activity

---

### TC-OPS-5-004 — Conflict Detection
**Jira:** `TE-232` | **Parent:** OPS-005

**Verification Steps:**
1. Create conflicting changes in both L1 and L2 for the same file
2. Run the sync script
3. Verify the conflict is detected
4. Verify the user is notified with a clear message
5. Verify manual conflict resolution is possible (sync does not auto-corrupt the file)

---

### TC-OPS-5-005 — Selective Sync
**Jira:** `TE-233` | **Parent:** OPS-005

**Verification Steps:**
1. Make multiple independent changes in L1
2. Select a specific change to sync (not all changes)
3. Run sync with the selection
4. Verify only the selected change propagates to L2
5. Verify other unselected changes remain in L1 only

---

## Story: SEC-003 — Audit Trail
**Jira:** `TE-156` | **Priority:** required | **Skeleton:** L2, L3

**User Story:** As a compliance auditor, I want a complete audit trail of all test operations, so that I can trace what happened when for compliance reporting.

**Acceptance Criteria:**
- [ ] All operations (CREATE, READ, UPDATE, DELETE) logged with ISO 8601 timestamp
- [ ] Operation type explicitly logged (`operationType: CREATE | READ | UPDATE | DELETE`)
- [ ] Operation result logged (`result: SUCCESS | FAILURE` + reason on failure)
- [ ] Operation duration tracked per operation (aids performance analysis)
- [ ] Actor/user identity logged for each operation
- [ ] Resource identity (type, ID, name) logged for every operation
- [ ] Logs retained per configured retention policy

**Architectural Layer:** L4 Util (Logger)
**Keywords:** audit, trail, compliance, crud-logging, retention

---

### TC-SEC-3-001 — Operations Logged with Timestamp
**Jira:** `TE-270` | **Parent:** SEC-003

**Verification Steps:**
1. Create a resource via the framework
2. Verify the CREATE operation is logged with an ISO 8601 timestamp
3. Modify the resource
4. Verify the UPDATE is logged with a timestamp
5. Delete the resource
6. Verify the DELETE is logged with a timestamp

---

### TC-SEC-3-002 — Operation Type Logging
**Jira:** `TE-271` | **Parent:** SEC-003

**Verification Steps:**
1. Log a CREATE operation; verify `operationType = CREATE`
2. Log a READ operation; verify `operationType = READ`
3. Log an UPDATE operation; verify `operationType = UPDATE`
4. Log a DELETE operation; verify `operationType = DELETE`

---

### TC-SEC-3-003 — Operation Results Logged
**Jira:** `TE-272` | **Parent:** SEC-003

**Verification Steps:**
1. Execute a successful resource creation
2. Verify `result = SUCCESS` is logged for that operation
3. Attempt an invalid operation (e.g., creating a duplicate)
4. Verify `result = FAILURE` is logged
5. Verify the failure reason/message is captured in the log

---

### TC-SEC-3-004 — Operation Duration Tracking
**Jira:** `TE-273` | **Parent:** SEC-003

**Verification Steps:**
1. Perform any audited operation
2. Verify the duration of the operation is logged
3. Verify slow operations can be identified via the logged duration
4. Verify duration data aids performance analysis in audit reports

---

### TC-SEC-3-005 — Actor/User Identification
**Jira:** `TE-274` | **Parent:** SEC-003

**Verification Steps:**
1. Execute an operation as "User A"
2. Verify User A's identity is logged in the audit entry
3. Execute an operation as "User B"
4. Verify User B's identity is logged
5. Verify each operation can be traced back to a specific actor

---

### TC-SEC-3-006 — Resource Identification
**Jira:** `TE-275` | **Parent:** SEC-003

**Verification Steps:**
1. Create a resource with a known ID and type
2. Verify the resource ID is logged in the audit entry
3. Verify the resource type is logged
4. Verify the resource name (if applicable) is logged
5. Verify the resource can be uniquely identified from the audit log alone

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| CICD-001 | TE-150 | TC-CICD-1-001, TC-CICD-1-002 | TE-171, TE-172 |
| CICD-002 | TE-151 | TC-CICD-2-001, TC-CICD-2-002 | TE-173, TE-174 |
| CICD-003 | TE-152 | TC-CICD-3-001 | TE-175 |
| CICD-004 | TE-153 | TC-CICD-4-001 | TE-176 |
| OPS-001 | TE-157 | TC-OPS-1-001, TC-OPS-1-002 | TE-214, TE-215 |
| OPS-002 | TE-158 | TC-OPS-2-001 to TC-OPS-2-004 | TE-216, TE-217, TE-218, TE-219 |
| OPS-003 | TE-159 | TC-OPS-3-001 | TE-220 |
| OPS-004 | TE-160 | TC-OPS-4-001 to TC-OPS-4-008 | TE-221, TE-222, TE-223, TE-224, TE-225, TE-226, TE-227, TE-228 |
| OPS-005 | TE-161 | TC-OPS-5-001 to TC-OPS-5-005 | TE-229, TE-230, TE-231, TE-232, TE-233 |
| SEC-003 | TE-156 | TC-SEC-3-001 to TC-SEC-3-006 | TE-270, TE-271, TE-272, TE-273, TE-274, TE-275 |

**Total:** 10 stories · 30 test cases
