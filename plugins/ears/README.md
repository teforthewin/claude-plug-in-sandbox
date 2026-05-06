# ears

A **read-only knowledge bundle** for **EARS — the Easy Approach to Requirements Syntax** (Mavin et al., Rolls-Royce / IEEE 2009).

EARS is a philosophy that "gently constrains" natural language with five small patterns. It eliminates the most common sources of requirement ambiguity (passive voice, missing actor, missing trigger, missing precondition) without forcing teams into a heavyweight formal notation.

## Patterns at a glance

| Pattern | Keyword | Template |
|---|---|---|
| Ubiquitous | (none — always active) | `The <system> shall <response>.` |
| State-driven | `While` | `While <state>, the <system> shall <response>.` |
| Event-driven | `When` | `When <trigger>, the <system> shall <response>.` |
| Optional Feature | `Where` | `Where <feature is included>, the <system> shall <response>.` |
| Unwanted Behaviour | `If / Then` | `If <trigger>, then the <system> shall <response>.` |
| Complex | combinations | `Where <feature>, while <preconditions>, when <trigger> the <system> shall <response>.` |

## Cardinality (per requirement)

- Preconditions: 0..many · Triggers: 0 or 1 · System name: exactly 1 · Responses: 1..many

## When the skill activates

Whenever you mention requirements, "shall" statements, requirement reviews, ambiguous specifications, or ask Claude to write/rewrite/check requirements. It is also referenced by the `input-hierarchization` plugin as the authoring convention for L2 (Requirement) nodes.

## Source

Synthesized from *EARS — The Easy Approach to Requirements Syntax: The Definitive Guide* (QRA Corp / Alistair Mavin). For training and coaching, see [alistairmavin.com](https://www.alistairmavin.com).
