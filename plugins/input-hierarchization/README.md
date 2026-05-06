# input-hierarchization

A **read-only knowledge bundle** that gives Claude a shared vocabulary and a placement protocol for specification content.

It packages a single skill, `input-hierarchization`, that activates whenever an agent must:

- decide *what* a piece of input data IS (Domain? Requirement? Process? Feature? Use Case? Acceptance Criterion? Asset? Golden Data?), or
- organize a heterogeneous input list (specs, OpenAPI, BPMN, user stories, legacy docs) into a coherent system tree.

No commands. No agents. No side effects. Pure knowledge.

## Concept dictionary (vocabulary)

| Concept | What it is |
|---|---|
| Functional Domain | The "department" of the system — a logical grouping of business responsibilities |
| Capability | A stable power of the system (the *what*), attached to a Domain |
| Asset / Dataset / Golden Data | Resources owned by a Domain (physical/digital, structured records, authoritative reference) |
| Feature | The user-invokable service described in a statement of requirements (the *how*) |
| Process | A cross-functional sequence achieving a business result — modeled in BPMN |
| Activity | A grouping of tasks linked to a major step inside one Domain |
| Task | The elementary, indivisible technical action |

## System hierarchization (tree)

```
L1 Functional Domain
 └── L2 Requirement   (EARS)
      └── L3 Process  (BPMN)
           └── L4 Step
                └── L5 Feature
                     └── L6 Use Case
                          └── Acceptance Criterion (Input → Output)
```

Capabilities, Assets, Datasets, and Golden Data are catalogued as **cross-cutting** nodes under the Domain and are referenced (not duplicated) from Features, Use Cases, and Tasks.

## When the skill activates

Whenever you mention specifications, requirements, BPMN flows, user stories, features, use cases, acceptance criteria, or ask Claude to classify or organize input documentation. The skill is also intended as a foundational lens for the `input-analyzer` plugin — every analyst sub-agent (functional, technical, ui-ux, quality-compliance) anchors its output to nodes defined here so that downstream skills (test-case-generator, coverage-checker) can align across lenses.

## Authoring conventions enforced by the skill

- **Requirements** must be written in **EARS** (Easy Approach to Requirements Syntax). Non-EARS statements are flagged `needs-EARS-rewrite`, never silently dropped.
- **Processes** must be modeled in **BPMN 2.0**. Non-BPMN flows are flagged `needs-BPMN-normalization`.
- Every classified node carries a **mandatory `source`** field — verbatim provenance back to the original input. No invented content.
