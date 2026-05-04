---
name: tet-atf-knowledge:03-tag-system
description: Defines the TET-ATF mandatory 4-category tag system (severity, category, domain, type) plus optional extensible labels for filtering and traceability. Use when writing or reviewing any test case to ensure every TC carries all required tag categories and any relevant additional labels.
---

# Skill: Tag System

## Rule: Every Test Case MUST Carry All 4 Mandatory Tag Categories

Missing any mandatory tag category is a **compliance violation**. Beyond the 4 mandatory categories, any number of additional `label:value` tags may be added freely — they are never a compliance violation.

> **Clarification on type tags:** the *type category* is mandatory — every test case must include at least one type tag reflecting the testing strategy that produced it. When multiple strategies apply, include all relevant type tags (comma-separated). Choose from the five defined type tags below.

---

## Severity Tags

| Tag | Meaning |
|-----|---------|
| `smoke` | Critical path — must always pass before any release |
| `mandatory` | Core business functionality — always included in regression |
| `required` | Standard feature coverage — included in regression |
| `advisory` | Nice-to-have, non-blocking |

---

## Category Tags

| Tag | Applies To |
|-----|-----------|
| `api` | REST/GraphQL/gRPC API interactions |
| `web` | Browser UI interactions |
| `mobile` | Native/hybrid mobile app interactions |

---

## Domain Tags

Custom per team — align with service or capability boundaries.

Examples: `authentication`, `payments`, `user-management`, `inventory`, `notifications`, `reporting`, `orders`, `checkout`

---

## Type Tags (mandatory — at least one per TC, comma-separated if multiple)

Reflects the testing strategy that produced the test case:

| Tag | When to use |
|-----|------------|
| `component-test` | Tests a single entity/operation in isolation |
| `integration-test` | Tests data flow or interactions across 2+ components |
| `edge-case` | Tests unusual, rare, or adversarial conditions |
| `limit-case` | Tests values at boundary edges (min/max/null/empty) |
| `cross-case` | Tests combinations of parameters, roles, states, or channels |

When a TC was produced by merging multiple strategies, include all applicable type tags:
`type:limit-case,cross-case`

---

## Additional Labels (Optional — Extensible)

Beyond the 4 mandatory categories, any number of `label:value` tags may be appended for filtering, traceability, and tooling integration. This list is open-ended and evolves with team needs — add labels as requirements emerge without modifying compliance rules.

| Label | Example values | Purpose |
|-------|---------------|---------|
| `feature` | `feature:dark-mode` | Product area or feature flag |
| `team` | `team:platform` | Owning squad |
| `sprint` | `sprint:42` | Iteration reference |
| `jira` | `jira:PROJ-123` | Ticket traceability |
| `automation` | `automation:automated`, `automation:manual` | Automation status |
| `persona` | `persona:admin`, `persona:guest` | User role under test |
| `data-sensitivity` | `data-sensitivity:pii` | Data classification |

**Format rules for additional labels:**
- Use `label:value` with kebab-case for both sides
- Any number of additional labels are allowed per TC
- Order: mandatory categories first, additional labels after

---

## Severity Assignment Guide by Operation Type

| Operation | Default Severity |
|-----------|-----------------|
| Critical-path create/read (main entity) | `smoke` |
| Update, delete (main entity) | `mandatory` |
| Valid state transitions | `mandatory` |
| Business rule enforcement | `mandatory` |
| Invalid state transitions | `required` |
| Error responses for bad input | `required` |
| Edge/adversarial conditions | `required` (security → `mandatory`) |
| Boundary values on financial fields | `mandatory` |
| Boundary values on non-critical fields | `required` |
| Optional/advisory coverage | `advisory` |

---

## Full Tag Examples

Minimal (4 mandatory categories only):
```
**Tags**: `severity:smoke` `category:api` `domain:payments` `type:component-test`
```

Multiple type tags (merged strategies):
```
**Tags**: `severity:mandatory` `category:api` `domain:orders` `type:limit-case,cross-case`
```

With additional labels for filtering:
```
**Tags**: `severity:mandatory` `category:api` `domain:orders` `type:integration-test` `feature:checkout-v2` `team:commerce` `jira:SHOP-456`
```
