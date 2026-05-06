---
name: ears
description: Defines the Easy Approach to Requirements Syntax (EARS) — five natural-language patterns (Ubiquitous, State-driven, Event-driven, Optional Feature, Unwanted Behaviour) plus a Complex composite — and the rules that make a requirement statement clear, concise, unambiguous, testable, and written in active voice with a specific system name. Use this skill whenever an agent must author, review, classify, or rewrite a requirement, validate that an L2 Requirement node (per the input-hierarchization skill) conforms to convention, distinguish a real requirement from a stakeholder goal, or decide whether EARS even applies to a given statement.
---

# Skill: EARS — Easy Approach to Requirements Syntax

## Why EARS exists

Most specifications are written in unconstrained natural language. Unconstrained NL is wordy, ambiguous, and easy to misinterpret — the dominant source of requirement defects, scrap, and rework. EARS "gently constrains" natural language with **five small patterns** so that every requirement carries the elements an engineer needs to implement and test it: the trigger, the preconditions, the actor, and the response.

EARS is *not* a heavyweight formalism. It is a philosophy with a tiny vocabulary (`shall`, `While`, `When`, `Where`, `If/Then`) that people use intuitively. If a requirement cannot be expressed in EARS, the most likely cause is that **key information — a precondition or a trigger — is missing**. That is a finding, not a failure of EARS.

---

## The Five Patterns

Four patterns describe **desired** behaviour. The fifth covers **unwanted** behaviour and undesirable conditions.

### 1. Ubiquitous Requirement (always active)

```
The <system name> shall <system response>.
```

> *Example.* `The control system shall prevent engine overspeed.`

Ubiquitous requirements are not invoked by any event or state — they are continuously true. **Always question whether a requirement is truly ubiquitous**; what looks ubiquitous is often actually state-driven and the state has been left implicit.

### 2. State-driven Requirement (`While`)

Active throughout the time a defined state remains true.

```
While <in a specific state>, the <system name> shall <system response>.
```

> *Example.* `While the aircraft is in-flight and the engine is running, the control system shall maintain engine fuel flow above XX lbs/sec.`

### 3. Event-driven Requirement (`When`)

Responds only when an event is detected at the system boundary.

```
When <trigger>, the <system name> shall <system response>.
```

> *Example.* `When continuous ignition is commanded by the aircraft, the control system shall switch on continuous ignition.`

### 4. Optional Feature Requirement (`Where`)

Applies only when an optional feature is present in the configuration.

```
Where <feature is included>, the <system name> shall <system response>.
```

> *Example.* `Where the control system includes an overspeed protection function, the control system shall test the availability of the overspeed protection function prior to aircraft dispatch.`

### 5. Unwanted Behaviour Requirement (`If / Then`)

Mitigates undesirable conditions or user behaviour. Same shape as event-driven, but the keyword `If/Then` signals to the reader that this is a mitigation requirement.

```
If <trigger>, then the <system name> shall <system response>.
```

> *Example.* `If the computed airspeed is unavailable, then the control system shall use modelled airspeed.`

> Tip: write unwanted-behaviour requirements in a **second pass**, after the normal-operation set is complete. For each normal-operation requirement, ask "what unwanted inputs or absent preconditions could break this?" and add `If/Then` requirements to mitigate them.

### 6. Complex Requirement (composite)

Real-world requirements often combine an optional feature, one or more preconditions, and a trigger.

```
Where <optional feature>, while <precondition(s)>, when <trigger>
    the <system name> shall <system response(s)>.
```

For unwanted behaviour replace `when` with `if/then`:

```
Where <optional feature>, while <precondition(s)>, if <trigger>, then
    the <system name> shall <system response(s)>.
```

> *Example.* `While the aircraft is on the ground, when reverse thrust is commanded, the control system shall enable deployment of the thrust reverser.`

---

## The Mandatory Element Order

EARS requirements always follow this temporal order. **The order is not stylistic — it mirrors the order in which conditions must hold and events must fire:**

```
[Where <feature>] [While <precondition(s)>] [When|If <trigger>] the <system> shall <response(s)>.
```

| Slot | Meaning | Mandatory? |
|---|---|---|
| `Where` | optional feature included in the build | optional |
| `While` | precondition / state that must hold | optional, can repeat |
| `When` / `If`/`Then` | trigger event at the boundary | optional |
| `the <system> shall` | actor + imperative verb | **mandatory** |
| `<response>` | observable system output | **mandatory** (≥1) |

- **Bold/mandatory** clauses must always be present.
- Optional clauses are present only when the requirement is contingent on them.
- The keyword (`While`, `When`, `Where`, `If/Then`) **identifies the type** of requirement — except for ubiquitous, where there is no keyword.

---

## Cardinality Rules (per requirement)

| Element | Allowed count |
|---|---|
| Preconditions (`While`) | 0 to many |
| Triggers (`When` / `If`) | 0 or 1 |
| System name | exactly 1 |
| System responses | 1 to many |

In practice, keep preconditions and responses to **two or three** within a single requirement. When more are needed, switch to a table or diagram — forcing more into a single sentence makes the requirement unreadable.

---

## Authoring Rules

These rules are what actually make EARS work. Apply them every time.

1. **Active voice, always.** The actor (the system) must perform the verb. EARS structurally enforces this because `the <system> shall …` puts the actor in the subject position. Reject `shall be recorded` and rewrite as `the <system> shall record …`.

2. **Use a specific system name, not a generic one.** Write `the control system shall …`, not `the system shall …` or `the pump shall …`. Generic names break when requirements are copied between documents or sent to multiple suppliers — readers no longer know *which* system owes the behaviour.

3. **Put mandatory information in the requirement, not in surrounding prose.** If a precondition lives in a paragraph above the `shall` statement, it will be lost when the requirement is exported, copied, or quoted. Move it into a `While` clause.

4. **One trigger per requirement.** If two triggers can each independently produce the response, write two requirements. If two events must *both* occur, that is a precondition + a trigger, not two triggers.

5. **Each requirement must specify exactly one system name.** Multiple actors → multiple requirements.

6. **Write requirements in two passes.** First pass: normal operation. Second pass: walk the normal-operation set and add `If/Then` requirements for unwanted inputs and missing preconditions. This is where EARS reveals coverage gaps that unconstrained NL hides.

7. **TBD / TBC for unknown values is acceptable.** Do not invent precision you do not have ("early false precision"). Use `TBD` / `TBC` and keep a documented plan for who resolves them and when.

---

## Goals are not Requirements

A frequent failure mode: confusing **stakeholder goals** with **system requirements**. They are different artifacts and they belong in different places.

| | Stakeholder Goal | System Requirement |
|---|---|---|
| Owned by | a stakeholder | the system specification |
| Aspirational? | yes — may be unattainable | no — must be agreed and verifiable |
| Conflicts allowed? | yes (between stakeholders) | no (within the system) |
| Achievement | "indicates a direction" | "must be possible to verify it has been achieved" |

Two anti-patterns to refuse:

- **Shoehorning a goal into a `shall` statement** (e.g., `The engine shall weigh 20% less than the previous engine`) — that is a goal, not a verifiable requirement, until the analysis exists to ground the 20% in first principles.
- **Watering down the goal** until it sounds achievable, then losing track of the original intent. Keep goals in a *Stakeholder Goals* section and trace each requirement back to the goals it advances.

When in doubt: ask "could a tester, given this statement, decide pass/fail without ambiguity?" If no, it is still a goal.

---

## Classification Protocol — given a candidate requirement

Apply in order; stop at the first match.

1. Does the statement describe a stakeholder aspiration with no agreed acceptance criterion? → **Goal**, not a requirement. Move it.
2. Does it use `If / Then` and describe mitigation of an undesirable condition? → **Unwanted Behaviour**.
3. Does it begin with `Where <feature is included>`? → **Optional Feature** (possibly Complex).
4. Does it begin with `While <state>`? → **State-driven** (possibly Complex).
5. Does it begin with `When <trigger>`? → **Event-driven** (possibly Complex).
6. Combinations of `Where` + `While` + `When|If/Then`? → **Complex**.
7. None of the above and the behaviour is genuinely always-on? → **Ubiquitous**. (Re-check; ubiquitous is rare.)
8. Cannot be classified? → **the requirement is incomplete** — surface the missing precondition or trigger.

---

## Review Checklist

For each requirement, verify:

- [ ] Begins with the correct keyword (`While` / `When` / `Where` / `If…then`) — or is ubiquitous.
- [ ] Element order is `Where → While → When|If → the <system> shall <response>`.
- [ ] System name is specific (not `the system`, not `the pump`).
- [ ] Active voice — the system is the subject of `shall`.
- [ ] At most one trigger; preconditions and responses ≤ 3 (else use a table).
- [ ] Every precondition and trigger needed to make the response unambiguous is *inside* the sentence.
- [ ] Statement is testable — a tester could decide pass/fail.
- [ ] Not a stakeholder goal in disguise.
- [ ] If `TBD`/`TBC` is used, a resolution plan is recorded.

---

## When NOT to use EARS

EARS injects rigour into NL requirements but is not always the right tool.

- **More than ~3 preconditions** within one requirement — switch to a table or decision matrix.
- **Mathematical formulas / flight envelopes / signal definitions** — express as the formula or graph; EARS adds friction without value.
- **Inherently graphical requirements** (state machines, sequence charts) — keep them graphical; EARS complements but does not replace them.
- **Audiences that are uniformly comfortable with a more precise notation** (e.g., pseudocode for a developer-only spec). Use the more appropriate notation.

A specification can be 95% EARS and 5% other formats. There is no value in forcing a requirement into prose when a table or diagram is clearer.

---

## Rewriting Example (from the source)

**Original (passive, ambiguous):**
> The software shall begin recording the call.

**Rewritten in EARS:**
> When the user selects record, the mobile phone software shall begin a recording of the call screen and of the audio from all participants.

Note how the rewrite supplies the **trigger** (`When the user selects record`), the **specific system** (`the mobile phone software`), and **enumerated responses** (`screen and audio from all participants`).

---

## Anti-patterns

- ❌ `The system shall …` — generic actor; pick the specific system name.
- ❌ `Data shall be logged.` — passive voice; rewrite with the system as subject.
- ❌ Using `shall` for an aspirational goal that has no acceptance criterion.
- ❌ Cramming five preconditions into one sentence — use a table.
- ❌ Burying a precondition in surrounding prose — pull it into a `While` clause.
- ❌ Two unrelated triggers in one requirement — split into two requirements.
- ❌ Writing only the happy path and skipping the second `If/Then` pass — coverage gaps will hide there.

---

## Why this matters for downstream work

EARS-conformant requirements produce two compounding benefits for any analysis pipeline:

- **Decomposition is honest.** A state-driven requirement names the state; an event-driven one names the trigger. That is exactly what a state-machine or test-case generator needs as input — no inference, no guessing.
- **Coverage is visible.** Once normal-operation requirements are written in EARS, the missing `If/Then` mitigations stand out as gaps. Unconstrained NL hides those gaps inside flowery prose.

This skill is the authoring convention referenced by the **L2 (Requirement)** layer of the `input-hierarchization` skill. Statements that fail this skill's review checklist must be flagged `needs-EARS-rewrite` rather than silently accepted or dropped.
