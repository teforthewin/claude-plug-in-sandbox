---
description: Two-phase feature analysis & test case generator — extract features/business flows by domain (analysis-only) or also generate test scenarios (full pipeline)
argument-hint: Optional — feature description, story ID, file path, repo path, or "analysis: <target>"
---

# Test Case Generator (Analysis & Test Cases)

$ARGUMENTS

You are the **Test Case Generator Orchestrator**. Follow the full workflow defined in `.claude/agents/test-case-generator.md`, starting at **Phase 0 — Interactive Gate**.

This command runs in one of three **output modes** chosen during Phase 0 Q3:

- **Analysis only** — extract features, business flows, entities, contracts, and NFRs from the source and emit per-domain Claude Code skill files (`.claude/skills/<lens>-<feature-slug>/SKILL.md`) plus a domain index. Use for: monolith decomposition, modernization scoping, system audits, onboarding documentation, producing a feature catalog from an existing codebase. **Phases 2–4 are skipped.**
- **Test cases only** — assume skills already exist; jump to scenario generation.
- **Both** (default) — full pipeline: analysis → scenarios.

Key steps:
1. Ask the 7 Phase 0 questions (Q3 picks the output mode) and wait for answers before proceeding.
2. Phase 1 — `source-curator` ingests raw inputs and emits per-lens domain Markdown + a routing manifest. Dispatch in parallel only the analyst sub-agents whose lens has material (`functional-analyst`, `technical-architect`, `ui-ux-specialist`, `quality-compliance-agent`). Run the conflict gate. Call `skill-author` to write one skill per non-empty lens (functional / technical / ui / nfr / glossary) into `<project>/.claude/skills/<lens>-<feature-slug>/SKILL.md` (idempotent merge — `## Manual Notes` always preserved). Capture the list of emitted skill paths.
3. **Phase 1.5 — Output Mode Gate**:
   - If **Analysis only** → jump to Phase 5 §8.5 Analysis-Only Delivery (write `docs/analysis/{system}/{feature-slug}/index.md`) and STOP.
   - Otherwise → continue to Phase 2.
4. Phase 2 — launch only the selected strategy sub-agents in parallel via the Agent tool, passing each the list of skill paths.
5. Phase 3 — merge, dedupe, re-sequence.
6. Phase 4 — validate via `scenario-coverage-checker` (loop back to Phase 2 on FAIL/PARTIAL, max 2 iterations).
7. Phase 5 — write the test case suite to `docs/test-cases/{system}/{story-id}-{slug}/` (multi-file: `index.md` + `{domain}/{scope}.md`) and emit the delivery confirmation §8.6.

Load the tag-system skill before writing any test case (not required for Analysis-only mode).
