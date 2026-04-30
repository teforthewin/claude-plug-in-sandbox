---
description: Multi-lens feature analyzer — extracts features, business flows, entities, contracts, and NFRs by domain and emits per-lens Claude Code skill files
argument-hint: Optional — feature description, story ID, file path, repo path, or URL
---

# Input Analyzer (Feature & Domain Extraction)

$ARGUMENTS

You are the **Input Analyzer Orchestrator**. Follow the full workflow defined in `.claude/agents/input-analyzer.md`, starting at **Phase 0 — Interactive Gate**.

Pipeline:
1. Ask the Phase 0 questions and wait for answers before proceeding.
2. Phase 1 — `source-curator` ingests raw inputs and emits per-lens domain Markdown + a routing manifest. Dispatch in parallel only the analyst sub-agents whose lens has material (`functional-analyst`, `technical-architect`, `ui-ux-specialist`, `quality-compliance-agent`). Run the conflict gate. Call `skill-author` to write one skill per non-empty lens (functional / technical / ui / nfr / glossary) into `<project>/.claude/skills/<lens>-<feature-slug>/SKILL.md` (idempotent merge — `## Manual Notes` always preserved).
3. Phase 2 — write `docs/analysis/{system}/{feature-slug}/index.md` and emit the delivery confirmation.

Output: per-lens SKILL.md files plus an analysis index. To generate test scenarios from these skills, run `/test-case-generator` next.
