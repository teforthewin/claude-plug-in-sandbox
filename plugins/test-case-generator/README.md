# test-case-generator

> **Maintained by**: Test Enablement — Technology  
> **Category**: testing  
> **Maturity**: community

## What it does

Converts business requirements, acceptance criteria, technical specs, or source code into structured, domain-organized test scenario documents using **5 parallel testing strategies simultaneously**:

| Strategy | Focus |
|---|---|
| **Component** | Individual units/entities in isolation |
| **Integration** | Interactions between sub-systems and services |
| **Edge Case** | Unusual, rare, or adversarial conditions |
| **Limit Case** | Boundary and min/max values |
| **Cross Case** | Combinatorial/pairwise parameter interactions |

The plugin produces technology-agnostic Markdown test case documents — no code, no selectors, no endpoints. Any tester (manual or automated) can read them. They are also ready for automated test code generation tools.

---

## Installation

```shell
/plugin install test-case-generator@claude-code-marketplace
```

---

## Usage

Once installed, invoke the test case generator via the agent:

```
Generate test cases for [story/feature/requirement]
```

Or more specifically:

```
Generate test cases for this acceptance criteria: [paste AC text]
Create test scenarios for the payment flow feature
What should I test for this requirement: [description]
Design test cases for story TE-123
```

The agent will ask 7 clarifying questions (source material, channels, testing levels, coverage scope, domain context, system name, use cases), then dispatch all selected strategies in parallel.

---

## What you get

A structured Markdown document at `docs/test-cases/{system}/{story-id}-{slug}.md` containing:

- **YAML frontmatter** with metadata (system, domain, story, channel, total tests, use cases, coverage)
- **Test cases organized by** Story/Scenario → Use Case → Layer → TC
- **Every TC includes**: ID, description, severity/category/domain/type tags, prerequisites, steps, assertions table, cleanup
- **Coverage matrix** showing which strategies contributed to each test case
- **Optimization report** showing how many raw scenarios were merged/deduplicated
- **Quality checklist** confirming readiness for implementation

---

## Agents included

| Agent | Role |
|---|---|
| `test-case-generator` | Main orchestrator — runs the full 5-phase workflow |
| `component-strategy` | Generates component isolation scenarios |
| `integration-strategy` | Generates cross-service interaction scenarios |
| `edge-case-strategy` | Generates unusual/adversarial condition scenarios |
| `limit-case-strategy` | Generates boundary value scenarios |
| `cross-case-strategy` | Generates combinatorial/pairwise scenarios |
| `scenario-designer` | Writes the actual TC Markdown from strategy inputs |
| `scenario-coverage-checker` | Validates that all ACs are covered by generated TCs |

---

## Skills included

| Skill | Purpose |
|---|---|
| `tag-system` | Defines the mandatory 4-category tag system: severity, category, domain, type |

---

## Tag system

Every test case produced by this plugin carries 4 mandatory tags:

| Category | Values |
|---|---|
| **severity** | `smoke` / `mandatory` / `required` / `advisory` |
| **category** | `api` / `web` / `mobile` |
| **domain** | Custom per team (e.g. `payments`, `authentication`) |
| **type** | `component-test` / `integration-test` / `edge-case` / `limit-case` / `cross-case` |

---

## Output example

```markdown
##### TC-TE-123-001: Create Order — valid input produces new order with status "created"

**Tags**: `severity:smoke` `category:api` `domain:orders` `type:component-test`

**Prerequisites**:
- Authenticated user account exists

**Steps**:
1. User submits order with valid product ID and quantity
2. System processes the order request

**Assert**:
| Assertion | Expected Value | Type |
|-----------|---------------|------|
| Order status | "created" | state |
| Order ID returned | non-null UUID | schema |
| Inventory updated | quantity decremented | state |

**Cleanup**:
- Cancel and delete the test order
```

---

## Source

Full framework and documentation:  
[easyparkgroup/claude-code-marketplace](https://github.com/easyparkgroup/claude-code-marketplace)
