# tet-atf-knowledge

A **read-only knowledge bundle** for the TET-ATF (Test Enablement Team Automated Test Framework) skeleton. It packages the complete set of framework skills so Claude knows all conventions, patterns, and rules when working inside any TET-ATF-based test repository — without requiring commands or agents.

## What it does

This plugin installs **14 skills** that activate independently based on context. Each skill is loaded only when Claude needs it (e.g. the API patterns skill activates when writing API clients, not when writing a CI/CD pipeline). This keeps the active context as small as possible.

No slash commands. No agents. No side effects. Pure knowledge.

## Skills included

| Skill | Activates when… |
|---|---|
| `01-framework-architecture` | Scaffolding a new project, creating directories, or verifying where a file belongs |
| `02-layer-rules` | Reviewing imports, writing code that crosses layers, or diagnosing a layer violation |
| `03-tag-system` | Writing or reviewing test tags (severity, category, domain, type) |
| `04-utils-catalog` | Using Logger, TestContext, DataGenerator, DateUtils, ConfigUtils, ConverterUtils, ValidatorUtils, StorageUtils, or UserManager |
| `05-coding-standards` | Generating or reviewing any source code for style and quality |
| `06-api-patterns` | Creating or reviewing API clients, REST test code, or data schema files |
| `07-web-patterns` | Creating or reviewing browser UI automation code with Playwright |
| `08-mobile-patterns` | Creating or reviewing iOS/Android native app automation code with Appium |
| `09-test-isolation` | Writing test setup/teardown, `conftest.py`, or any code that creates test resources |
| `10-logging-reporting` | Implementing logging calls, report generation, or reviewing output-producing code |
| `11-security-config` | Writing code that reads config, handles credentials, or accesses env-specific values |
| `12-ci-cd-patterns` | Setting up CI/CD workflows, configuring test jobs, or implementing artifact publishing |
| `13-k8s-user-secrets` | Managing user credentials via Kubernetes Secrets, Helm, or `USER_CATALOG` |
| `playwright-cli` | Exploring a live page to discover locators, debugging selectors, or generating Page Object scaffolding |

Each skill also carries a `references/` folder with linked Jira stories and test cases for full traceability.

## Source

Skills are ported verbatim from the `skeleton-automated-tests-framework` repository (`.claude/skills/`). The only changes are the frontmatter `name` and `description` fields, which have been rewritten for plugin triggering accuracy.

## Usage

Install this plugin in any TET-ATF-based test repository. Claude will automatically load the relevant skill(s) whenever you ask it to write, review, or debug test code following the TET-ATF conventions.

No configuration required.
