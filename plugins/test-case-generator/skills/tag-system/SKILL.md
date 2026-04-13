---
name: tag-system
description: Defines the mandatory 4-category tag system (severity, category, domain, type) with assignment rules and examples. Use when writing or reviewing test cases to ensure every TC carries all required tag categories.
---

# Skill: Tag System

## Rule: Every Test Case MUST Carry All 4 Tag Categories

Missing any tag category is a **compliance violation**.

> **Clarification on type tags:** the *type category* is mandatory — every test case must include exactly one type tag reflecting the testing strategy that produced it. The default when no other strategy applies is `regression`.

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

## Type Tags (mandatory — exactly one per TC)

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

## Full Tag Example

```
**Tags**: `severity:smoke` `category:api` `domain:payments` `type:component-test`
```

Multiple type tags (merged strategies):
```
**Tags**: `severity:mandatory` `category:api` `domain:orders` `type:limit-case,cross-case`
```
