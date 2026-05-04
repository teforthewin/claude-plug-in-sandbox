---
name: tet-atf-knowledge:06-api-patterns
description: TET-ATF API client 3-level hierarchy (BaseApiClient → AppBaseApi → ResourceApi), singleton pattern, mandatory JSON schema validation, structured request logging with 9 required fields, and mutation context storage in TestContext. Use when creating or reviewing API clients, REST test code, or data schema files.
---

# Skill 06 — API Patterns

## Client Hierarchy (3 levels, ALWAYS follow)

```
BaseApiClient          ← src/core/api/
  └── AppBaseApi       ← src/core/api/{service}/
        └── ResourceApi  ← src/core/api/{service}/{Resource}Api.*
```

- `BaseApiClient` — HTTP methods (GET, POST, PUT, PATCH, DELETE), auth headers, logging, **schema validation** (transparent)
- `AppBaseApi` — **Single service-level base URL** (loaded from `ConfigUtils`), service-specific auth, shared headers
- `ResourceApi` — Resource-specific methods only (e.g. `createUser()`, `getUserById()`, `deleteUser()`). Defines only a `_PATH` constant (relative path). **Never overrides `base_url`** — always inherits from `AppBaseApi`.

### Base URL Ownership Rule

```
ONE base URL per API service — set ONLY in AppBaseApi.
ResourceApi classes MUST NOT have their own base_url. They define a relative _PATH only.
```

✅ CORRECT — one config key per service:
```yaml
api:
  auth_service:
    base_url: "https://api.example.com/auth"   # ← shared by UserApi, TokenApi, etc.
```

❌ ANTI-PATTERN — one config key per endpoint (NEVER do this):
```yaml
api:
  auth_service:
    users:
      base_url: "https://api.example.com/auth/users"
    tokens:
      base_url: "https://api.example.com/auth/tokens"
```

---

## Singleton Rule

```
API clients MUST be global singletons — one instance per client type.
Use a registry/factory pattern to get/create instances.
```

---

## JSON Schema Validation (MANDATORY)

`BaseApiClient` transparently handles:

| Step | Rule |
|------|------|
| Request | Serialize body from schema file: `src/business/resource/data_schemas/{resource}-{operation}-request.schema.json` |
| Response | Validate against: `src/business/resource/data_schemas/{resource}-response.schema.json` |
| Missing schemas | Create placeholder schema files **before** writing test code that depends on them |
| L1/L2 code | **Never** validate manually — always delegate to `BaseApiClient` |

---

## Request Logging (MANDATORY — every API call, via BaseApiClient)

Every HTTP call made through `BaseApiClient` MUST produce a structured log entry containing all of the following fields. This log entry MUST be readable in the HTML report.

### Mandatory log fields

| Field | Rule |
|-------|------|
| `method` | HTTP verb: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `uri` | Full URL including path and query parameters |
| `requestHeaders` | All request headers — **strip Authorization, Cookie, X-Api-Key and any token/secret headers** — replaced with `"[MASKED]"` |
| `requestBody` | Full serialized request body (from schema); mask password/token fields per Skill 10 masking rules |
| `responseStatus` | HTTP status code + reason phrase (e.g. `"200 OK"`) |
| `responseHeaders` | All response headers (no masking required unless they echo auth data) |
| `responseBody` | Full response body (mask sensitive fields per Skill 10 masking rules) |
| `durationMs` | Elapsed time in milliseconds from request send to response received |
| `testId` | `TestContext.test_id` — links this call to the test that triggered it |

### Pattern (in BaseApiClient)

```python
def _execute(self, method, url, headers, body):
    safe_headers = {k: "[MASKED]" if k.lower() in SENSITIVE_HEADER_NAMES else v
                    for k, v in headers.items()}
    start = time.monotonic()
    response = self._http.request(method, url, headers=headers, json=body)
    duration_ms = int((time.monotonic() - start) * 1000)
    Logger.info("API call", context={
        "method": method,
        "uri": url,
        "requestHeaders": safe_headers,
        "requestBody": self._mask(body),
        "responseStatus": f"{response.status_code} {response.reason}",
        "responseHeaders": dict(response.headers),
        "responseBody": self._mask(response.json()),
        "durationMs": duration_ms,
        "testId": TestContext.current().test_id,
    })
    return response
```

### Sensitive header names to always mask

```
authorization, api-key, x-api-key, x-auth-token, cookie, set-cookie,
x-access-token, x-refresh-token, proxy-authorization
```

### Self-Check

- [ ] Every HTTP call logs all 9 mandatory fields
- [ ] Authorization / token / cookie headers are masked before logging
- [ ] Request body sensitive fields masked per Skill 10 rules
- [ ] Log entry is linked to `testId` from `TestContext`
- [ ] Log appears in `report.html` under the corresponding test step

---

## Example Structure

```
src/core/api/
  ├── BaseApiClient.*
  └── auth_service/
        ├── AuthServiceBaseApi.*
        ├── UserApi.*
        └── TokenApi.*

src/business/resource/data_schemas/
  ├── user-create-request.schema.json
  ├── user-response.schema.json
  └── token-create-request.schema.json
```

---

## Mutation Context Storage (MANDATORY — POST, PUT, PATCH, DELETE)

Every mutating HTTP call MUST store a structured snapshot in `TestContext` immediately after the response is received. This gives every subsequent test step access to the full call details without any re-fetch.

### What gets stored per method

| Method | Trigger condition | TestContext action |
|--------|------------------|--------------------|
| `POST` | Any `2xx` response | Store snapshot **+** register resource for cleanup via `trackResource()` |
| `PUT` | Any `2xx` response | Store snapshot + update tracked resource metadata if resource was previously tracked |
| `PATCH` | Any `2xx` response | Store snapshot + update tracked resource metadata if resource was previously tracked |
| `DELETE` | `200` or `204` | Store snapshot + **remove** the resource from the cleanup list (already deleted) |

### Context key convention

```
TestContext.set(f"api_last_{resource_type}", snapshot_dict)
```

`resource_type` is derived from the URL path: last non-ID segment, singularised (e.g. `/api/v1/users/123` → `"user"`).

The `snapshot_dict` always contains: `method`, `uri`, `requestBody` (masked), `responseStatus`, `responseBody` (masked).

### Rules

```
✅  Every POST/PUT/PATCH/DELETE stores a snapshot in TestContext
✅  Snapshot key follows the convention: api_last_{resource_type}
✅  POST auto-registers resource for cleanup (trackResource)
✅  PUT/PATCH update the tracked resource's metadata in place
✅  DELETE removes the resource from the cleanup list
✅  metadata always contains the complete response dict (never a subset)
✅  Snapshots available to any subsequent test step via TestContext.get("api_last_{type}")
❌  Manual trackResource() calls in L1/L2 for API-created resources
❌  Partial snapshot (e.g. only status code)
```

---

## Rules Summary

- ❌ No raw HTTP calls (library-level HTTP functions) in L1 or L2 — all calls go through `BaseApiClient`
- ❌ No manual JSON construction in L1 or L2 — use schema-based generation
- ✅ All response validation through `BaseApiClient`
- ✅ All schema files committed alongside the client code
- ✅ Every API call logs URI, request headers (auth stripped), request body, response headers, response body, status, duration, testId
- ✅ All 9 mandatory log fields must be visible and readable in `report.html`
- ✅ POST/PUT/PATCH/DELETE store a full snapshot in `TestContext` as `api_last_{resource_type}`
- ✅ POST registers the resource for teardown cleanup (`trackResource`)
- ✅ PUT/PATCH refresh the tracked resource's `metadata` in place
- ✅ DELETE removes the resource from the cleanup list

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (QA-001, MAINT-002, OBS-004) and test cases (TC-QA-1-001, TC-QA-1-004, TC-MAINT-2-002, TC-OBS-4-xxx)
