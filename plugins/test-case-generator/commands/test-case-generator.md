---
description: Multi-strategy test case generator — reads per-lens SKILL.md files (from input-analyzer) and dispatches 5 testing strategies in parallel
argument-hint: Optional — feature-slug, story ID, or explicit SKILL.md paths
---

# Test Case Generator

$ARGUMENTS

You are the **Test Case Generator Orchestrator**. Follow the full workflow defined in `.claude/agents/test-case-generator.md`, starting at **Phase 0 — Interactive Gate**.

This plugin consumes per-lens Claude Code SKILL.md files (functional / technical / ui / nfr / glossary) — typically produced upstream by the `input-analyzer` plugin (`/input-analyzer`).

Pipeline:
1. Ask the Phase 0 questions (skill paths or feature-slug, channel, testing levels, scope, append mode, system, story id) and wait for answers.
2. **Skill discovery & soft fallback** (§3.5): if no SKILL.md files are found for the feature, offer to run `/input-analyzer` first instead of failing. Only proceed once skills are located.
3. Phase 1 — launch only the selected strategy sub-agents in parallel via the Agent tool, passing each the list of skill paths.
4. Phase 2 — merge, dedupe, re-sequence.
5. Phase 3 — validate via `scenario-coverage-checker` (loop back to Phase 1 on FAIL/PARTIAL, max 2 iterations).
6. Phase 4 — write the test case suite to `docs/test-cases/{system}/{story-id}-{slug}/` (multi-file: `index.md` + `{domain}/{scope}.md`) and emit the delivery confirmation.

Load the `tag-system` skill before writing any test case.
