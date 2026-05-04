---
name: tet-atf-knowledge:05-coding-standards
description: TET-ATF naming conventions, commenting rules (WHY not WHAT), design patterns (singleton, POM, factory), and dependency version pinning policy. Use when generating or reviewing any TET-ATF source code to enforce consistent style and quality across the framework.
---

# Skill 05 — Coding Standards

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| **Files** | `snake_case.py` | `user_api.py`, `login_page.py` |
| **Classes** | `PascalCase` | `UserApi`, `LoginPage`, `TestContext` |
| **Methods / Functions** | `snake_case` | `create_user()`, `click_submit()` |
| **Constants** | `UPPER_SNAKE_CASE` | `DEFAULT_TIMEOUT`, `BASE_PATH` |
| **Test functions** | `test_<what>_<condition>` | `test_login_with_invalid_password` |
| **Test classes** | `Test<Domain><Channel>` | `TestAuthApi`, `TestCheckoutWeb` |
| **Private attributes** | `_leading_underscore` | `_base_url`, `_driver` |
| **Config keys** | `dot.notation.snake_case` | `api.auth_service.base_url` |

---

## Comments — WHY, not WHAT

```
✅  WHY — explains intent, business reason, or non-obvious decision
    Using retry=3 because the auth service has eventual consistency during peak load

❌  WHAT — describes code that already reads itself
    Set the retry count to 3
```

---

## Design Patterns

| Pattern | Where | Rule |
|---------|-------|------|
| **Singleton** | API clients | One global instance per client type |
| **Page Object** | Web / Mobile | One class per page/screen, locators private |
| **Factory / Builder** | Test data | Use `DataGenerator`, not hardcoded values |
| **Interface / Abstract** | Internal tools | Always abstract; expose only contract |
| **Fixture** | Setup/Teardown | Use framework-native fixtures; track resources |

---

## Dependency Version Pinning

- **ALWAYS** resolve every library/tool version to the latest stable release before writing it
- **NEVER** emit a guessed or invented version number (e.g. `1.0.0`, `latest`, `*`)
- When unsure → search for the current version before generating the dependency manifest
- Applies to: `requirements.txt`, `package.json`, `pom.xml`, `build.gradle`, `go.mod`, `Gemfile`, etc.

---

## Code Quality Checklist

- [ ] No `TODO` or `FIXME` comments in delivered code
- [ ] No unused imports or dead code
- [ ] No hardcoded strings that should come from config or data generator
- [ ] Every public method / function has a short docstring or comment explaining purpose
- [ ] No deeply nested logic (max 2-3 levels of indentation)
- [ ] Error messages are actionable (they tell you what failed and where)

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (MAINT-002, QA-002) and test cases (TC-MAINT-2-xxx, TC-QA-2-xxx)
