# References — Skill 11: Security & Configuration

## Linked Stories & Test Cases

This reference documents all framework stories and test cases that validate the configuration hierarchy (env vars > environment YAML > global YAML), credential rules, ConfigUtils usage, CI/CD secret injection, and config read-only enforcement defined in this skill.

---

## Story: MAINT-003 — Configuration Management
**Jira:** `TE-144` | **Priority:** mandatory | **Skeleton:** L1, L2

**User Story:** As a DevOps engineer, I want to manage configuration via YAML files, so that I can easily switch between environments (dev/staging/prod).

**Acceptance Criteria:**
- [ ] `ConfigUtils` reads YAML configuration files at startup
- [ ] Environment-specific configs in `config/environments/{env}.yaml`
- [ ] Global config constants in `config/global_config.yaml`
- [ ] Environment variables override file-based config (env vars take precedence)
- [ ] Runtime configuration injection supported (e.g., via system properties)
- [ ] Documentation shows config structure, hierarchy, and usage patterns

**Architectural Layer:** L4 Util (ConfigUtils)
**Keywords:** config, yaml, environment, runtime-injection, hierarchy

---

### TC-MAINT-3-001 — ConfigUtils Reads YAML Files
**Jira:** `TE-185` | **Parent:** MAINT-003

**Verification Steps:**
1. Verify two config layers exist: `config/global_config.yaml` and `config/environments/{env}.yaml`
2. Verify global config is loaded at startup
3. Verify environment config overrides global config for matching keys
4. Verify environment variables override file-based config
5. Verify `ConfigUtils.get("key")` returns the correct value for each config layer

---

## Story: SEC-001 — Data Masking
**Jira:** `TE-154` | **Priority:** smoke | **Skeleton:** L2, L3

**User Story:** As a compliance officer, I want sensitive data automatically masked in all logs and reports, so that passwords, tokens, and PII are never exposed.

**Acceptance Criteria:**
- [ ] Passwords masked as `****` in all log output and reports
- [ ] API tokens and Bearer tokens masked (show only last 4 chars if configured)
- [ ] PII masked: email addresses, phone numbers, SSNs
- [ ] Credit card numbers masked (show only last 4 digits)
- [ ] Custom secret patterns configurable via `config/global_config.yaml`
- [ ] Masked data in reports: no sensitive data in HTML or JSON reports
- [ ] Masking operations logged in audit trail (what was masked, not the value)
- [ ] Performance overhead of masking < 10% of logging time
- [ ] Full masking documentation with compliance notes provided

**Architectural Layer:** L4 Util (Logger)
**Keywords:** masking, pii, credentials, compliance, privacy, gdpr

---

### TC-SEC-1-001 — Password Masking in Logs
**Jira:** `TE-257` | **Parent:** SEC-001

**Verification Steps:**
1. Log a message containing a password field
2. Verify the password is not visible in plain text
3. Verify the password appears as a mask (e.g., `****`)
4. Verify masking applies to all occurrences of the password in the log
5. Verify the log line remains readable (context around the masked field is preserved)

---

### TC-SEC-1-002 — API Token Masking
**Jira:** `TE-258` | **Parent:** SEC-001

**Verification Steps:**
1. Log an HTTP header containing a Bearer token
2. Verify the token is masked in the log output
3. Verify only the last 4 characters remain visible (if configured)
4. Verify all token occurrences are masked consistently
5. Verify masking is consistent across all log entries

---

### TC-SEC-1-003 — PII Masking
**Jira:** `TE-259` | **Parent:** SEC-001

**Verification Steps:**
1. Log an email address
2. Verify the email is masked
3. Log a phone number
4. Verify the phone number is masked
5. Log an SSN (Social Security Number)
6. Verify the SSN is masked

---

### TC-SEC-1-004 — Credit Card Masking
**Jira:** `TE-260` | **Parent:** SEC-001

**Verification Steps:**
1. Log a credit card number
2. Verify the number is masked (only last 4 digits visible)
3. Verify all card number formats are masked
4. Verify the masking format is clear and standardized

---

### TC-SEC-1-005 — Custom Secret Masking
**Jira:** `TE-261` | **Parent:** SEC-001

**Verification Steps:**
1. Define a custom secret pattern in `config/global_config.yaml`
2. Log a message containing a field matching that pattern
3. Verify the matching value is masked
4. Configure a second distinct custom pattern
5. Verify values matching the new pattern are also masked

---

### TC-SEC-1-006 — Masked Data in Reports
**Jira:** `TE-262` | **Parent:** SEC-001

**Verification Steps:**
1. Generate a test report after a run that involved sensitive data
2. Verify the report contains no plain-text passwords
3. Verify the report contains no plain-text API tokens
4. Verify the report contains no PII
5. Verify the report is compliant with masking policy

---

### TC-SEC-1-007 — Mask Verification Log
**Jira:** `TE-263` | **Parent:** SEC-001

**Verification Steps:**
1. Execute logging with masking enabled
2. Verify masking operations are noted in the audit trail
3. Verify what type of data was masked is noted (e.g., "password masked")
4. Verify the actual masked value is NOT recorded in the audit trail
5. Verify the masking policy is documented alongside the audit log

---

### TC-SEC-1-008 — Performance Impact of Masking
**Jira:** `TE-264` | **Parent:** SEC-001

**Verification Steps:**
1. Log a batch of messages with masking enabled; measure logging latency
2. Log the same batch with masking disabled; measure logging latency
3. Compare performance with and without masking
4. Verify overhead is < 10% of total logging time

---

### TC-SEC-1-009 — Masking Configuration
**Jira:** `TE-265` | **Parent:** SEC-001

**Verification Steps:**
1. Review masking configuration options
2. Verify masking patterns are configurable (add/remove patterns)
3. Verify masking can be enabled or disabled via configuration
4. Verify different masking strategies are available (full mask, partial reveal)
5. Verify configuration is documented with examples

---

### TC-SEC-1-010 — Data Masking Documentation
**Jira:** `TE-266` | **Parent:** SEC-001

**Verification Steps:**
1. Review masking documentation
2. Verify all default masking patterns are documented
3. Verify configuration options are explained
4. Verify examples are provided for each pattern type
5. Verify compliance notes are included

---

## Story: SEC-002 — Credential Management
**Jira:** `TE-155` | **Priority:** mandatory | **Skeleton:** L1, L2

**User Story:** As a security engineer, I want credentials stored securely in environment variables or external secret managers, so that secrets are never checked into source control.

**Acceptance Criteria:**
- [ ] Credentials read from environment variables at runtime
- [ ] `.env` files supported for local development ONLY (must be in `.gitignore`)
- [ ] CI/CD secret manager integration supported (AWS Secrets Manager, HashiCorp Vault)
- [ ] OAuth credential flow (token acquisition, refresh) supported
- [ ] Zero credentials in code, config files, or repository — all sourced externally
- [ ] Credential rotation works without code changes (re-read from env/secret manager)

**Architectural Layer:** L4 Util (ConfigUtils) + L2 Business
**Keywords:** credentials, secrets, environment-variables, oauth, secret-manager

---

### TC-SEC-2-001 — Environment Variable Credentials
**Jira:** `TE-267` | **Parent:** SEC-002

**Verification Steps:**
1. Set a credential as an environment variable
2. Use the credential in a test via `ConfigUtils`
3. Verify the credential is read from the environment variable (not hardcoded)
4. Verify no credential value appears in source code or committed config files
5. Verify the test uses the environment variable value correctly

---

### TC-SEC-2-002 — OAuth Credential Flow
**Jira:** `TE-268` | **Parent:** SEC-002

**Verification Steps:**
1. Implement the OAuth token acquisition flow using framework utilities
2. Obtain an access token via OAuth
3. Use the token in API requests
4. Verify token refresh works when the token expires
5. Verify the token is managed securely (masked in logs, not stored in plain text)

---

### TC-SEC-2-003 — Credential Rotation
**Jira:** `TE-269` | **Parent:** SEC-002

**Verification Steps:**
1. Set a credential from an environment variable or secret manager
2. Rotate the credential in the secret manager
3. Execute the test (without code changes)
4. Verify the new credential is picked up automatically
5. Verify no code change is required for credential rotation

---

## Traceability Summary

| Story | Jira | Test Cases | TC Jira IDs |
|-------|------|-----------|-------------|
| MAINT-003 | TE-144 | TC-MAINT-3-001 | TE-185 |
| SEC-001 | TE-154 | TC-SEC-1-001 to TC-SEC-1-010 | TE-257, TE-258, TE-259, TE-260, TE-261, TE-262, TE-263, TE-264, TE-265, TE-266 |
| SEC-002 | TE-155 | TC-SEC-2-001 to TC-SEC-2-003 | TE-267, TE-268, TE-269 |

**Total:** 3 stories · 14 test cases
