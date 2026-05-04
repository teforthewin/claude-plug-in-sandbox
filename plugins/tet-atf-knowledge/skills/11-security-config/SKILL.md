---
name: tet-atf-knowledge:11-security-config
description: TET-ATF configuration hierarchy (credentials from env vars only, base URLs from YAML only), credential rules, ConfigUtils usage patterns, CI/CD secret injection, and config write policy (always confirm before writing). Use when writing any code that reads config, handles credentials, or accesses environment-specific values.
---

# Skill 11 — Security & Configuration

## Configuration Hierarchy

```
Configuration values fall into two categories with different resolution strategies:

── Non-sensitive config (base_url, timeouts, feature flags, etc.)
   1. config/environments/{env}.yaml  ← single source of truth — MUST be set here
   2. config/global_config.yaml       ← framework-wide defaults (READ-ONLY)
   ENV variables do NOT override these values — YAML files are authoritative.

── Credentials & secrets (passwords, tokens, API keys, etc.)
   1. Environment Variables           ← only allowed location for secrets
   ENV variables are used exclusively for credentials — never for base URLs or URLs.
```

Access config: `ConfigUtils.get("api.auth_service.base_url")`

**Critical rule**: base URLs and connection settings MUST be set directly in the environment YAML files. They must NEVER be read from ENV variables and NEVER have a hardcoded `default=` fallback in generated code. If a base URL is missing from the YAML, the agent must ask the user for the correct value and write it to all environment files before generating any code that depends on it.

---

## Environment Config Structure

```yaml
api:
  {service_name}:
    base_url: "https://api.example.com"    # ← ONE base URL per service, NOT per endpoint

webui:
  {app_name}:
    base_url: "https://app.example.com"    # ← ONE base URL per web app

mobileApp:
  {app_name}:
    app_package: "..."
    platform_name: "..."
    device_name: "..."
    automation_name: "..."

test_reporting:
  s3_upload:
    enabled: false
    bucket: "..."
```

---

## Credential Rules

| Rule | Detail |
|------|--------|
| ❌ Never hardcode | No passwords, tokens, API keys, or base URLs in any source file |
| ❌ Never commit | `.env` files are local only — always in `.gitignore` |
| ❌ Never use ENV vars for base URLs | `base_url` values must come from YAML config files only |
| ❌ Never use `default=` for base URLs | `ConfigUtils.get("webui.app.base_url")` — no fallback parameter |
| ✅ Use env vars for secrets only | Read credentials/tokens from environment variables at runtime |
| ✅ Use ConfigUtils | `ConfigUtils.get("credentials.api_key")` (mapped to env var) |
| ✅ Set base URLs in YAML | Every `base_url` must be explicitly set in each `config/environments/*.yaml` |
| ✅ Mask in logs | All credential fields always masked by `Logger` |

---

## `config/` Write Policy — Confirm Before Write

Config files are the source of truth for all environment-specific values. Agents **must** audit them before generating test code and **may** update them, but only under strict conditions:

| Situation | Action |
|-----------|--------|
| Required key is **missing** from an env file | Ask user for the value → write on confirmation |
| Key exists but value **conflicts** with the new system being tested | Show both values → ask user which is correct → write on confirmation |
| Key exists and **value looks correct** | No action — leave as-is |
| Any **credential or secret** field | Never write — instruct user to set via environment variable |

**Hard rules:**
- **NEVER write to `config/`** without displaying the proposed change and receiving explicit user confirmation (`Y`)
- **NEVER modify an existing value** that is already used by passing tests without explicit user confirmation
- **NEVER write credentials, passwords, tokens, or secrets** to any config file — these must stay in `.env` or environment variables
- **ALWAYS write to ALL environment files** (`development.yaml`, `staging.yaml`, etc.) for new service entries, adapting values per environment

**Write scope**: only `api.{service}.base_url`, `webui.{app}.base_url`, and `mobileApp.{app}.*` blocks. Never touch `framework`, `directories`, `logging`, `execution`, `reporting`, or `cleanup` sections.

**Base URL granularity**: ONE `base_url` per API service (not per endpoint/resource). All ResourceApi classes within a service share the same base URL inherited from their AppBaseApi. Never create `api.{service}.{resource}.base_url` keys — this is always wrong.

---

## User Management

All test accounts are accessed exclusively through `UserManager` (Skill 04).
Credentials come from the `USER_CATALOG` environment variable — a YAML string
mapping role names to `{login, password}`.

| Rule | Detail |
|------|--------|
| ❌ Never hardcode login/password in tests or fixtures | Always call `UserManager.get_instance().get_user(role=...)` |
| ❌ Never use DataGenerator for credentials | Generated users don't exist in the system under test |
| ❌ Never commit the `.env` file | Gitignored — contains live secrets |
| ✅ Set `USER_CATALOG` in `.env` for local dev | YAML string mapping role → `{login, password}` |
| ✅ Inject `USER_CATALOG` via Helm `secretKeyRef` in Kubernetes | See Skill 13 |
| ✅ Document the variable in `.env.example` | Shows the expected format without real credentials |

**When adding a new test account role:**
1. Add an entry to the catalog YAML (the `USER_CATALOG` value) for both local `.env` and the Kubernetes Secret
2. Update `.env.example` to document the role name and expected shape
3. Never write a literal password in any committed file

---

## `.env.example` — Required Onboarding Artifact

Maintain a `.env.example` file (committed to the repo) listing every required environment variable with a placeholder value. This documents what secrets must be set locally and in CI/CD without exposing actual values.

```bash
# .env.example — commit this file; never commit .env
AUTH_SERVICE_API_KEY=your_api_key_here
DB_PASSWORD=your_db_password_here
EXTERNAL_SERVICE_TOKEN=your_token_here
```

- `.env` is local only — always in `.gitignore`
- `.env.example` is committed — serves as the canonical list of required secrets
- When adding a new secret, update `.env.example` in the same PR

---

## Secrets in CI/CD

- Store secrets in GitHub Actions secrets / Vault / AWS Secrets Manager
- Inject at runtime via environment variables only
- Never pass secrets through command-line arguments (they appear in logs)
- When a secret rotates, update only the CI/CD environment setting — no code change needed

---

## Self-Check

- [ ] Zero hardcoded credentials, tokens, passwords, or base URLs in generated code
- [ ] All `base_url` values read via `ConfigUtils.get()` with NO `default=` fallback parameter
- [ ] All `base_url` values are explicitly set in every `config/environments/*.yaml` file — not from ENV vars
- [ ] Credentials/secrets read from environment variables only (never from YAML files)
- [ ] `Logger` called with context dict — not formatted strings containing raw secrets
- [ ] No `.env` file committed to version control
- [ ] Config audit performed: every `ConfigUtils.get()` call in generated code has a corresponding key in all env files
- [ ] Any config additions were shown to the user and confirmed before writing
- [ ] No existing passing-test config values were silently overwritten
- [ ] No hardcoded login/password in test or fixture code — `UserManager.get_instance().get_user()` used instead
- [ ] `USER_CATALOG` is documented in `.env.example` with the expected role/shape format
- [ ] Every required role exists as a key in the `USER_CATALOG` catalog (local `.env` and Kubernetes Secret)

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (MAINT-003, SEC-001, SEC-002) and test cases (TC-MAINT-3-001, TC-SEC-1-xxx, TC-SEC-2-xxx)
