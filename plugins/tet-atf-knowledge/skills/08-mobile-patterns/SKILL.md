---
name: tet-atf-knowledge:08-mobile-patterns
description: TET-ATF Appium mobile screen 3-level hierarchy (BaseMobilePage → AppBaseMobilePage → SpecificScreen), locator strategy priority (accessibility_id first), gesture methods, platform-aware coding, and YAML capability config. Use when creating or reviewing iOS/Android native app automation code.
---

# Skill 08 — Mobile Patterns (Appium)

## Mobile Screen Hierarchy

```
BaseMobilePage            ← src/core/mobile/
  └── AppBaseMobilePage   ← src/core/mobile/{service}/
        └── SpecificScreen  (e.g. LoginScreen, HomeScreen)
```

- `BaseMobilePage` — Appium driver reference, element finder helpers, wait strategies, screenshot
- `AppBaseMobilePage` — App package/bundle, launch/close app, common gestures
- `SpecificScreen` — Screen locators (private) + interaction methods (public)

---

## Configuration (in `config/environments/{env}.yaml`)

**Android:**
```yaml
mobileApp:
  {app_name}:
    app_package: "com.example.app"
    platform_name: "Android"
    device_name: "emulator-5554"
    automation_name: "UiAutomator2"
```

**iOS:**
```yaml
mobileApp:
  {app_name}:
    app_package: "com.example.App"      # bundleId
    platform_name: "iOS"
    device_name: "iPhone 15 Simulator"  # or physical device UDID
    automation_name: "XCUITest"
```

---

## Locator Strategy Rules

- Use `accessibility_id` first (most stable across platforms)
- Fall back to `id`, then `xpath` (last resort)
- Never expose locators outside the Screen class

---

## Gestures (in BaseMobilePage)

```
tap(element)
longPress(element, durationMs?)
swipe(direction, element?)      # up, down, left, right
scroll(direction)
doubleTap(element)
sendKeys(element, text)
```

---

## Screenshot Rule (MANDATORY — every mobile interaction step)

**Every public interaction method in a Screen class MUST capture a screenshot after the action completes.**

### Rules

| Rule | Detail |
|------|--------|
| **When** | After every `tap`, `longPress`, `swipe`, `scroll`, `doubleTap`, `sendKeys`, and any action that changes screen state |
| **Storage** | `build/test-results/{ClassName}/screenshots/{stepName}-{timestamp}.png` |
| **Report** | Screenshot path MUST be attached to the test step log via `Logger.info()` with `context: { screenshot: path }` so it is embedded in `report.html` |
| **On failure** | Always capture a screenshot on exception/assertion failure — even if no screenshot was taken during the step |
| **Naming** | `{ScreenClass}_{methodName}_{timestamp}.png` — human-readable, no spaces |
| **Platform** | Use Appium's `driver.save_screenshot(path)` — works for both iOS and Android |

### Pattern (in BaseMobilePage)

```python
def tap(self, element, step_name: str):
    element.click()
    screenshot_path = self.capture_screenshot(f"{self.__class__.__name__}_{step_name}")
    Logger.info(f"STEP: {step_name}", context={"action": "tap", "screenshot": str(screenshot_path)})
```

### Self-Check

- [ ] Every public interaction method calls `capture_screenshot()` after the action
- [ ] Screenshot path appears in the structured log entry for that step
- [ ] `report.html` template renders screenshot thumbnails linked to full-size images
- [ ] Failure screenshots are captured even when the step raises an exception (use `try/finally`)
- [ ] Platform-specific screenshot paths are correctly resolved for iOS vs Android

---

## Platform-Aware Code

- Use capability flags (`platform_name`) to branch iOS vs Android behavior
- Platform-specific locators defined as conditional constants inside the Screen class
- Avoid platform forks in L1 or L2 — encapsulate in the Screen class

---

## File Placement Example

```
src/core/mobile/
  ├── BaseMobilePage.*
  └── my_app/
        ├── MyAppBaseMobilePage.*
        ├── LoginScreen.*
        └── HomeScreen.*
```

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (QA-001, OBS-002) and test cases (TC-QA-1-003, TC-QA-1-004, TC-OBS-2-001, TC-OBS-2-003, TC-OBS-2-004, TC-OBS-2-009)
