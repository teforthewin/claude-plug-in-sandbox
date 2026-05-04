---
name: tet-atf-knowledge:09-test-isolation
description: TET-ATF test isolation rules covering TestContext lifecycle (initialize/track/cleanup), resource tracking, unique test data generation via DataGenerator, parallel execution safety, and the mandatory conftest.py autouse fixture pattern. Use when writing test setup/teardown, conftest.py, or any code that creates test resources.
---

# Skill 09 — Test Isolation

## Core Principle

Every test is **fully independent** — no reliance on execution order, no shared mutable state between tests.

---

## TestContext Lifecycle (per test)

```
SETUP    → TestContext.initialize(testId, tags)
TEST     → TestContext.set/get for intra-test shared state
            TestContext.trackResource(type, id) for every resource created
TEARDOWN → TestContext.cleanup() — deletes all tracked resources
```

**One TestContext instance per test. Never share between tests.**

---

## Resource Tracking Rules

```
✅  Track every resource created during the test (users, tokens, entities, files, records)
✅  Cleanup runs in REVERSE creation order (respects dependencies)
✅  Cleanup is BEST-EFFORT: continue if individual deletion fails, log the error
✅  Cleanup runs EVEN IF the test fails (finally block / always-teardown)
❌  Never rely on environment cleanup — tests clean up after themselves
```

### Automatic tracking for API-created resources

`BaseApiClient` auto-registers every `POST → 201` response in `TestContext` (see Skill 06 — Auto Resource Tracking). This means:

- **L1/L2 code MUST NOT call `TestContext.trackResource()` for API resources** — it is already done transparently by the Core layer
- L1/L2 **MAY** call `trackResource()` for non-API resources (files, DB records created directly, external service state)
- The `Resource.metadata` field contains the **complete creation response** — use it in cleanup handlers instead of re-fetching

### What cleanup handlers receive

```python
for resource in TestContext().getResourcesForCleanup():
    # resource.type     → "user", "order", "token", …
    # resource.id       → primary ID used in the DELETE URL
    # resource.identifier → human-readable label for log messages
    # resource.metadata → full creation response dict — composite keys,
    #                     parent IDs, hrefs, everything needed to delete
    api.delete(f"/{resource.type}s/{resource.id}")
```

---

## Test Data Rules

```
✅  Unique data per test — use DataGenerator for every identifier
✅  Realistic data — use Faker via DataGenerator (names, emails, addresses)
✅  Deterministic preconditions — tests set up their own initial state
❌  Hardcoded test data (emails, IDs, names) — always generates conflicts in parallel runs
❌  Shared test accounts or shared state across tests
```

---

## Parallel Execution Safety

- All test data includes a unique prefix/suffix (e.g. `DataGenerator.generateUniqueId("USER")`)
- No static/global mutable state referenced by multiple tests simultaneously
- File outputs namespaced by test class: `build/test-results/{ClassName}/`

---

## When Cleanup Fails

Cleanup is best-effort — a cleanup failure must never mask the original test result.

```python
for resource in TestContext().getResourcesForCleanup():
    try:
        api.delete(f"/{resource.type}s/{resource.id}")
    except Exception as e:
        Logger.error(
            "Cleanup failed — resource may need manual deletion",
            error=e,
            context={"type": resource.type, "id": resource.id, "identifier": resource.identifier}
        )
        # continue to next resource; do not re-raise
```

---

## Pre-existing State (Reference Data)

For tests that require data to exist before the test runs (e.g. a product catalogue, role definitions, lookup tables):

- Create a **dedicated setup fixture** scoped to the test session or module — not inline in the test body
- The fixture checks if the data exists first; creates it only if absent
- Track the resource so it is cleaned up at the end of the fixture scope
- Never assume shared environment data is present — tests must be self-sufficient

---

## Fixture Pattern

```
SETUP FIXTURE    → TestContext.initialize(test_id, tags)  ← MANDATORY FIRST CALL
                   provision resources, register with TestContext.trackResource()
TEST BODY        → use resources via TestContext.get()
TEARDOWN FIXTURE → TestContext.cleanup() (resets state; actual deletions must be done before calling this)
```

### Mandatory Python/pytest pattern — MUST be in every conftest.py

Every `conftest.py` that serves test files **must** include this autouse fixture. Without it, `TestContext` is never initialized and the thread-local state is undefined across test runs.

```python
import pytest
from src.util.test_context import TestContext

@pytest.fixture(autouse=True)
def test_context(request):
    """Initialize and teardown TestContext for every test.

    WHY: TestContext uses thread-local storage — it must be explicitly
         initialized before each test and cleaned up after, even on failure,
         to prevent state leakage between tests in parallel runs.
    """
    ctx = TestContext()
    tags = [m.name for m in request.node.iter_markers()]
    ctx.initialize(test_id=request.node.nodeid, tags=tags)
    yield ctx
    ctx.cleanup()
```

**Rules:**
- `scope` must be omitted (defaults to `"function"`) — never `"session"` or `"module"` for TestContext
- `autouse=True` is mandatory — never rely on explicit fixture injection for isolation
- `ctx.cleanup()` runs in the `finally`-equivalent `yield` teardown — always executes even on test failure
- `test_id` = `request.node.nodeid` (gives a unique, human-readable identifier per test)
- `tags` = extracted from pytest markers so the context reflects the test's actual tag set

---

## Self-Check

- [ ] **`conftest.py` has an `autouse=True` `test_context` fixture calling `TestContext.initialize()` and `TestContext.cleanup()`** — if this is absent, STOP and add it before generating any test
- [ ] Every test creates its own unique test data (no hardcoded identifiers)
- [ ] API-created resources are auto-tracked by `BaseApiClient` — no manual `trackResource()` calls in L1/L2 for API resources
- [ ] Non-API resources (files, DB rows, external state) call `trackResource()` with `metadata` containing enough info to delete
- [ ] Teardown is always executed (not skipped on failure)
- [ ] No test depends on state left by another test
- [ ] Cleanup reverses creation order
- [ ] Cleanup handlers use `resource.metadata` instead of re-fetching the resource

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (REL-001, REL-002, REL-004) and test cases (TC-REL-1-xxx, TC-REL-2-001, TC-REL-4-xxx)
