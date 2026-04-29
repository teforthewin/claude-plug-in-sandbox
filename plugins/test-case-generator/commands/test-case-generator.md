---
description: Multi-strategy test case generator from specs, stories, or code
argument-hint: Optional feature description, story ID, or file path
---

# Test Case Generator

$ARGUMENTS

You are the **Test Case Generator Orchestrator**. Follow the full workflow defined in `.claude/agents/test-case-generator.md`, starting at **Phase 0 — Interactive Gate**.

Key steps:
1. Ask the 7 Phase 0 questions and wait for answers before proceeding
2. Phase 1 — dispatch four analyst sub-agents in parallel (`functional-analyst`, `technical-architect`, `ui-ux-specialist`, `quality-compliance-agent`), run the conflict gate, then call `skill-author` to write one Claude Code skill per non-empty domain into `<project>/.claude/skills/<feature-slug>-<domain>/SKILL.md` (idempotent: existing skills are merged, the `## Manual Notes` section is preserved). Capture the list of emitted skill paths.
3. Phase 2 — launch only the selected strategy sub-agents in parallel via the Agent tool, passing each the list of skill paths as input
4. Phase 3 — merge, deduplicate, re-sequence, and check the coverage threshold
5. Phase 4 — validate coverage via the `scenario-coverage-checker` sub-agent (loop back to Phase 2 on FAIL/PARTIAL)
6. Phase 5 — write the final test case document to `docs/test-cases/{system}/{story-id}-{slug}.md` and emit the delivery confirmation + skill coverage matrix

Load the tag-system skill before writing any test case.
