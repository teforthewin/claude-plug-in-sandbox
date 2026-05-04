---
name: tet-atf-knowledge:02-layer-rules
description: Enforces TET-ATF cross-layer import boundaries (L1→L2→L3→L4 only), per-layer responsibility assignments, REST API routing rules through BaseApiClient, and internal tool patterns. Use when reviewing imports, writing code that crosses layers, or diagnosing a layer violation.
---

# Skill 02 — Layer Rules

## Layer Responsibility Table

| Layer | Path | Does | Does NOT |
|-------|------|------|----------|
| **L1 Test** | `tests/` | Declare tests, use fixtures, call L2 keywords | Contain loops, algorithms, or business logic |
| **L2 Business** | `src/business/` | Orchestrate workflows, convert data, manage TestContext, call L3 | Make direct HTTP/UI/DB calls |
| **L3 Core** | `src/core/` | Execute atomic HTTP calls, drive UI/mobile, atomic DB ops | Contain business logic or multi-step workflows |
| **L4 Util** | `src/util/` | Provide generic reusable helpers | Contain domain-specific logic |

---

## Import Rules (ENFORCED)

```
L1  may only import from:  L2
L2  may only import from:  L3, L4
L3  may only import from:  L4 + external libraries
L4  may only import from:  external libraries (no framework-internal deps)
```

❌ L1 importing L3 or L4 directly → **violation**  
❌ L3 importing L2 → **violation**  
❌ Any circular dependency → **violation**

---

## REST API — Strict Routing Rules

- ALL REST API calls go through `L3 BaseApiClient` hierarchy — **no raw HTTP in L1 or L2**
- Request bodies are generated from JSON schemas in `src/business/resource/data_schemas/`
- Responses are validated against the corresponding JSON schema
- `BaseApiClient` handles schema validation transparently — L1/L2 never re-implement it
- If schemas do not exist yet → create placeholder schema files before writing test code

---

## Internal Tool Pattern (MANDATORY for DB, S3, Elasticsearch, Brokers)

```
src/core/internal/{category}/
  ├── BaseInterface.*         ← define the contract
  └── {impl}/ConcreteImpl.*  ← implement the contract

src/business/internal/
  └── {Category}Manager.*    ← selects impl via config, exposes only interface

Tests / Business layer call Manager → NEVER ConcreteImpl directly
```

---

## Common Violations

| Violation | Where found | Correct fix |
|-----------|------------|-------------|
| `requests.post(url, ...)` in a business helper | L2 | Move HTTP call to a `ResourceApi` in L3 |
| `assert response.status == 200` inside a Page Object | L3 | Move assertion to L1 test or L2 business helper |
| `TestContext.get("user_id")` inside `BaseApiClient` | L3 | L3 must never read test state; pass the value as a parameter |
| `from src.core.api import UserApi` in a test file | L1 | Import the L2 business helper instead |
| `DataGenerator.generateEmail()` called inside a Core client | L3 | Data generation belongs in L2 or L1 fixtures |

---

## Fixture Placement

- Fixtures live in `tests/conftest.py` (L1) — never in `src/`
- A fixture may call L2 helpers to provision state, but must not contain business logic itself
- Shared fixtures across domains go in `tests/conftest.py`; domain-scoped fixtures go in `tests/{domain}/conftest.py`

---

## Self-Check After Any Code Generation

- [ ] Test layer has zero business logic / HTTP calls / DB calls
- [ ] Business layer has zero raw HTTP, UI driver, or DB calls
- [ ] Core layer has zero business logic or multi-step orchestration
- [ ] Util layer has zero domain-specific code
- [ ] No import crosses a layer boundary upward or non-adjacently
- [ ] All REST calls routed through BaseApiClient
- [ ] All response bodies schema-validated

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (MAINT-001, MAINT-002) and test cases (TC-MAINT-1-xxx, TC-MAINT-2-xxx)
