---
name: input-hierarchization
description: Defines the canonical specification vocabulary (Functional Domain, Capability, Asset, Feature, Process, Activity, Task, Golden Data) and the 6-level system hierarchization tree (Domain → Requirements → Processes → Steps → Features → Use Cases / Acceptance Criteria) used to classify and organize raw specification inputs. Use this skill whenever an input-analyzer agent must decide what a piece of input data IS, where it belongs in the system tree, or how to structure a heterogeneous input list — including specs, requirement documents, BPMN diagrams, OpenAPI files, user stories, or mixed legacy documentation.
---

# Skill: Input Hierarchization

## Purpose

Raw specification material arrives in heterogeneous shapes — a paragraph in a Word doc, a swagger endpoint, a BPMN lane, a user-story card, a diagram callout. Before any analysis can happen, each fragment must be answered against two questions:

1. **What IS this fragment?** (concept classification — the vocabulary)
2. **Where does it BELONG?** (placement in the system tree — the hierarchy)

This skill provides the controlled vocabulary and the placement rules. Every analyst sub-agent (functional, technical, ui-ux, quality-compliance) must classify and place every retained fragment using these definitions; otherwise downstream skills (test-case-generator, coverage-checker) cannot align across lenses.

> **Companion skill — `ears`.** Level-2 Requirement nodes must be authored in EARS syntax. Use the [`ears` skill](../../../ears/skills/ears/SKILL.md) for the five patterns, cardinality rules, the mandatory `Where → While → When|If → shall` element order, and the review checklist that defines what `needs-EARS-rewrite` flags should detect. This input-hierarchization skill decides *what level a fragment lives at*; the `ears` skill decides *whether an L2 fragment is well-formed*.

---

## Part 1 — Concept Dictionary (Vocabulary)

The dictionary is a *flat* set of concepts. Concepts are not all in a strict parent-child line; some are siblings attached to the same parent. The hierarchy in Part 2 says how they connect.

| # | Concept | Definition | Example |
|---|---------|------------|---------|
| 1 | **Functional Domain** | A logical grouping of coherent business responsibilities — the *department* of the system. Stable, large-scoped, owned by a business stakeholder group. | `Distribution and Sale` |
| 2 | **Capability** | What the system is *capable of doing* to fulfill its mission. A stable power, expressed as a noun phrase. Does not yet say *how* it is used (the *what*). Attached to a Domain. | `Physical sales management` |
| 3a | **Asset** | A resource of value (physical or digital) owned by a Domain. Not a behavior — a thing the system holds, references, or protects. | `Ticket vending machine`, `Graphic charter`, `Pricing referential` |
| 3b | **Dataset** | A structured collection of data records owned by a Domain. A specialization of Asset, called out separately when its schema and lifecycle matter. | `Customer master`, `Daily sales transactions` |
| 3c | **Feature** | A specific service offered to the user to meet a precise need. It is what is described in a *statement of requirements* — the *how*. Implements one or more Capabilities. | `Contactless payment` |
| 4 | **Process** | A sequence of cross-functional steps that mobilize several Domains to achieve a business result. Temporal and dynamic. Modeled in **BPMN**. | `The purchase of a ticket at the TVM` |
| 5 | **Activity** | A grouping of tasks linked to a major step within a Domain. One Activity belongs to exactly one Process. | `Securing of the monetary transaction` |
| 6 | **Task** | The elementary, indivisible, technical action. Lowest unit of behavior. | `Print the receipt` |
| 7 | **Golden Data** | The authoritative reference version of a critical business entity, maintained as the single source of truth. A subset of Dataset. | `Authoritative product catalog`, `Master tariff table` |

### Disambiguation rules

When a fragment looks like it could be two things, apply these tests in order:

- **Capability vs. Feature** — is it a noun describing *what the system can do* (Capability, e.g. "manage physical sales") or a noun describing *the service the user actually invokes* (Feature, e.g. "buy a ticket with contactless card")? Capabilities are reusable across many Features.
- **Feature vs. Process** — is the fragment a *user-facing service* (Feature) or a *cross-domain orchestration of steps* (Process)? A Feature can be invoked inside a Process step.
- **Process vs. Activity** — does the fragment span multiple Domains? Then it's a Process. Confined to one Domain? Activity.
- **Activity vs. Task** — is it further decomposable into smaller technical actions? If yes, Activity. If no, Task.
- **Asset vs. Dataset vs. Golden Data** — physical or non-data resource → Asset; structured records → Dataset; *the* authoritative copy of a critical entity → Golden Data.

---

## Part 2 — System Hierarchization (Tree)

The system is organized as a 6-level tree. Every retained input fragment must be attached to exactly one node.

```
L1  Functional Domain
     │
     ├── L2  Requirement   (authored in EARS convention)
     │       │
     │       └── L3  Process / Business Flow   (modeled in BPMN)
     │               │
     │               └── L4  Step
     │                       │
     │                       └── L5  Feature
     │                               │
     │                               └── L6  Use Case
     │                                       │
     │                                       └── Acceptance Criterion (Input → Output)
     │
     ├── (Capabilities are catalogued under the Domain — implemented by Features)
     └── (Assets / Datasets / Golden Data are catalogued under the Domain — referenced by Features and Tasks)
```

### Level definitions for placement

| Level | Node | What lives here | Authoring convention |
|-------|------|------------------|----------------------|
| **L1** | Functional Domain | Top-level grouping. One per business department. | — |
| **L2** | Requirement | Statement of *what the system shall do or constrain*. | **EARS** (Easy Approach to Requirements Syntax) — `When <trigger>, the <system> shall <response>`, `While <state>, …`, `If <condition>, …`, ubiquitous, optional. **See the companion [`ears` skill](../../../ears/skills/ears/SKILL.md)** for the full pattern set, cardinality rules, and the authoring/review checklist that defines what `needs-EARS-rewrite` means. |
| **L3** | Process / Business Flow | The cross-functional sequence that satisfies one or more Requirements. | **BPMN 2.0** (lanes, gateways, events). |
| **L4** | Step | A coarse phase inside a Process. Step boundaries are usually gateway-aligned in the BPMN. | — |
| **L5** | Feature | The user-invokable service exercised at a Step. One Feature can appear in several Steps across Processes. | Statement of requirements / user story. |
| **L6** | Use Case | A concrete way the Feature is exercised (one user goal, one nominal flow + alternates). | Use Case template. |
| L6.AC | Acceptance Criterion | Atomic, testable assertion attached to a Use Case. Must declare an **Input** and an expected **Output**. | Given/When/Then or Trigger/Logic Gate/State Mutation/Response. |

### Cross-cutting nodes (siblings under the Domain)

Three concept families do not sit on the main spine but are attached to the Domain and *referenced from* Features, Steps, and Tasks:

- **Capabilities** — listed under the Domain. Each Feature declares the Capabilities it implements.
- **Assets / Datasets / Golden Data** — listed under the Domain. Each Use Case declares the Assets it reads/writes and the Golden Data it depends on.
- **Activities & Tasks** — Activities decompose Steps inside a single Domain; Tasks are the leaves of Activities. They are the *implementation-level* view of a Step and feed technical contracts.

---

## Part 3 — Classification Protocol (single fragment)

Given one piece of input, classify it in this order. Stop at the first match.

1. **Is it a top-level grouping name?** → Functional Domain (L1).
2. **Is it a "shall" / "when … shall …" statement?** → Requirement (L2). If not in EARS, flag it for rewrite.
3. **Is it a flow diagram, swimlane diagram, or sequence of cross-domain steps?** → Process (L3). If not in BPMN, flag for normalization.
4. **Is it a phase / column / gateway-bounded segment of a Process?** → Step (L4).
5. **Is it a user-invokable service described by a requirements statement or user story?** → Feature (L5).
6. **Is it a concrete user goal with a flow + acceptance criteria?** → Use Case (L6).
7. **Is it a Given/When/Then or input→output assertion?** → Acceptance Criterion (under L6).
8. **Is it a noun describing a system power (not a service)?** → Capability (cross-cutting under L1).
9. **Is it a thing held by the system?** → Asset / Dataset / Golden Data (cross-cutting under L1).
10. **Is it a sub-step inside one Domain?** → Activity (under a Step).
11. **Is it an indivisible technical action?** → Task (under an Activity).
12. **None of the above** → tag as `unclassified` and surface it to the user — do not silently drop or invent a node.

---

## Part 4 — Organization Protocol (input list)

Given a heterogeneous input list, build the tree in this order — coarse before fine, structure before content.

1. **Identify Domains first.** Read the entire corpus and extract candidate L1 nodes. Reconcile synonyms (e.g. "Sales" vs. "Distribution and Sale") with the user before going further — domain names propagate everywhere.
2. **Place Requirements under each Domain.** Group by Domain. Mark any non-EARS statements `needs-rewrite`.
3. **Place Processes** under the Requirements they satisfy. If a Process satisfies several Requirements across Domains, attach it to the Domain that *owns the business outcome*; reference the others.
4. **Decompose each Process into Steps.** Use the BPMN gateways/events as natural Step boundaries.
5. **Attach Features to Steps.** A Feature can be attached to several Steps — record all attachments, do not duplicate the Feature.
6. **Decompose each Feature into Use Cases**, then Acceptance Criteria.
7. **Catalog cross-cutting nodes:** list Capabilities, Assets, Datasets, Golden Data once per Domain. From each Feature/Use Case, add typed *references* to these nodes (`implements:`, `reads:`, `writes:`, `depends-on-golden:`).
8. **Decompose Steps into Activities and Tasks** only when the technical lens (technical-architect) needs them — otherwise leave Step as the leaf of the business spine.
9. **Validate every leaf has a parent.** No orphan nodes. No cycles. Each node has exactly one parent on the main spine; cross-cutting references are typed and explicit.
10. **Surface gaps** — a Process without Steps, a Feature without Use Cases, a Use Case without Acceptance Criteria, a Requirement not satisfied by any Process — and report them. Gaps are deliverables, not failures.

---

## Part 5 — Output Conventions

When a fragment is classified, emit it in this canonical form so downstream skills can parse it uniformly:

```yaml
- id: <stable-slug>
  level: L1 | L2 | L3 | L4 | L5 | L6 | AC | capability | asset | dataset | golden-data | activity | task | unclassified
  name: <human-readable>
  parent: <id of parent on the main spine, or domain id for cross-cutting>
  references:
    implements: [<capability-id>, ...]      # Features only
    reads:      [<asset-id|dataset-id>, ...]
    writes:     [<asset-id|dataset-id>, ...]
    depends-on-golden: [<golden-id>, ...]
  source: <verbatim quote or doc-anchor>     # always preserve provenance
  convention-flags: [needs-EARS-rewrite, needs-BPMN-normalization, ...]  # optional
```

- **`source`** is mandatory — every node must trace back to a verbatim fragment of the original input. No invented content.
- **`convention-flags`** declare format debt; downstream agents may act on them or surface to the user.

---

## Anti-patterns

- ❌ Inventing a Domain or Feature to make an orphan fit. Use `unclassified` and surface it.
- ❌ Collapsing a Process into a Feature because both "describe behavior". Apply the Process-vs-Feature test in Part 1.
- ❌ Promoting an Acceptance Criterion to a Use Case because it is long. Length is not a level signal.
- ❌ Re-typing the same Feature under several Steps. Attach once, reference many.
- ❌ Dropping an EARS-violating statement. Keep it, flag it, surface it.
- ❌ Silently merging two Domains with similar names. Always reconcile with the user first.

---

## Why this matters

Every downstream lens — functional rules, technical contracts, UI flows, NFRs, test cases — is anchored to a node in this tree. If two analysts disagree on what a fragment *is*, their outputs cannot be cross-referenced and the coverage-checker cannot validate the system. The vocabulary and the tree are the shared coordinate system that makes multi-lens analysis composable.
