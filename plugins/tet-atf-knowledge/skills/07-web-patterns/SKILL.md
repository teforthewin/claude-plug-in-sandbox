---
name: tet-atf-knowledge:07-web-patterns
description: TET-ATF Page Object Model 4-level hierarchy (BasePage → AppBasePage → SpecificPage → Component), locator encapsulation rules, explicit wait strategy, and mandatory screenshot capture after every interaction. Use when creating or reviewing browser UI automation code with Playwright.
---

# Skill 07 — Web Patterns (Page Object Model)

## Page Object Hierarchy (4 levels)

```
BasePage             ← src/core/web/
  └── AppBasePage    ← src/core/web/{service}/
        └── SpecificPage  (e.g. LoginPage, DashboardPage)
              └── Component  ← src/core/web/{service}/components/
```

- `BasePage` — driver reference, navigation helpers, generic wait strategies, screenshot util
- `AppBasePage` — app-specific base URL, common header/footer, shared authentication state
- `SpecificPage` — page locators (private) + page interaction methods (public)
- `Component` — reusable UI elements (forms, modals, nav bars)

---

## Locator Encapsulation Rules

```
✅  Locators defined as private fields/constants inside the Page Object class
✅  Interaction methods exposed publicly (e.g. clickLogin(), fillEmail())
❌  Raw CSS selectors / XPath in L1 tests — never
❌  Raw CSS selectors / XPath in L2 business layer — never
```

---

## One Page Object Per Page

- Each distinct page or full-screen view gets its own Page Object class
- Reusable sub-sections (modals, side panels, repeated forms) get their own `Component` class

---

## Wait Strategy (in BasePage)

- Use **explicit waits** (wait for element visible/clickable) — never hard-coded sleeps
- Timeout and polling interval configurable via `ConfigUtils`
- Log every wait timeout as a warning with page + element context

### Playwright-Specific Patterns

```python
# BasePage constructor — page object injected by fixture
class BasePage:
    def __init__(self, page: Page):
        self._page = page

# Preferred wait methods (in order of reliability)
self._page.wait_for_selector(locator, state="visible")   # element-level wait
self._page.wait_for_load_state("networkidle")            # post-navigation wait
self._page.wait_for_url(pattern)                         # URL-change wait

# Never use:
import time; time.sleep(n)   # ❌ hard-coded sleep
self._page.wait_for_timeout(n)  # ❌ equivalent to sleep
```

### iframes & Shadow DOM

```python
# iframes — get frame handle, then interact within it
frame = self._page.frame_locator("iframe#payment").locator("input#card")

# Shadow DOM — Playwright pierces shadow DOM automatically with >>> combinator
shadow_input = self._page.locator("my-component >>> input[name='email']")
```

---

## Screenshot Rule (MANDATORY — every UI interaction step)

**Every public interaction method in a Page Object MUST capture a screenshot after the action completes.**

### Rules

| Rule | Detail |
|------|--------|
| **When** | After every `click`, `fill`, `select`, `submit`, `navigate`, and any action that changes page state |
| **Storage** | `build/test-results/{ClassName}/screenshots/{stepName}-{timestamp}.png` |
| **Report** | Screenshot path MUST be attached to the test step log via `Logger.info()` with `context: { screenshot: path }` so it is embedded in `report.html` |
| **On failure** | Always capture a screenshot on exception/assertion failure — even if no screenshot was taken during the step |
| **Naming** | `{PageClass}_{methodName}_{timestamp}.png` — human-readable, no spaces |

### Pattern (in BasePage)

```python
def click(self, locator, step_name: str):
    element = self.wait_for(locator)
    element.click()
    screenshot_path = self.capture_screenshot(f"{self.__class__.__name__}_{step_name}")
    Logger.info(f"STEP: {step_name}", context={"action": "click", "screenshot": str(screenshot_path)})
```

### Self-Check

- [ ] Every public interaction method calls `capture_screenshot()` after the action
- [ ] Screenshot path appears in the structured log entry for that step
- [ ] `report.html` template renders screenshot thumbnails linked to full-size images
- [ ] Failure screenshots are captured even when the step raises an exception (use `try/finally`)

---

## File Placement Example

```
src/core/web/
  ├── BasePage.*
  └── main_application/
        ├── MainAppBasePage.*
        ├── LoginPage.*
        ├── DashboardPage.*
        └── components/
              ├── TopNavBar.*
              └── AlertModal.*
```

---

## Self-Check

- [ ] No raw locators outside Page Object files
- [ ] BasePage inherited all the way from the specific page
- [ ] No business logic (assertions beyond element visibility) in Page Objects
- [ ] One class per page — no monolithic "AllPagesHelper" class
- [ ] Every public interaction method captures a screenshot and logs its path
- [ ] Failure screenshots captured via `try/finally` in every interaction method

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (QA-001, MAINT-002, OBS-002) and test cases (TC-QA-1-002, TC-QA-1-004, TC-MAINT-2-001, TC-OBS-2-xxx)
