# Mac mini Codex Start Instructions

## Recommended start

On the Mac mini, open the local DieselPDF repository in Codex and fetch the remote branch:

```bash
git fetch origin
git switch agent/codex-project-handoff
```

Alternatively, create an isolated worktree for Phase 1:

```bash
git fetch origin
git worktree add ../DieselPDF-phase-1 -b agent/phase-1-architecture-audit origin/agent/codex-project-handoff
cd ../DieselPDF-phase-1
```

## Codex prompt

Use:

```text
Read root AGENTS.md, every file under docs/project-bible in numbered order, docs/project/CODEX_HANDOFF.md, and GitHub Issue #2. Inspect the complete repository and execute Phase 1 only. Produce all seven architecture review documents required by 16_CODEX_EXECUTION_BRIEF.md. Verify current library capabilities, activity, licences and Windows/macOS deployment using primary sources. Do not begin Phase 2 or rewrite the UI. Stop for Aaron's review and report exact files changed, recommendations, unresolved decisions and required engineering inputs.
```

## Required operating rules

- Work on a separate branch or worktree.
- Do not modify `main` directly.
- Do not begin production coding during Phase 1.
- Preserve all current files.
- Commit the seven Phase 1 documents and open a Draft PR.
- Do not merge until Aaron approves the architecture.
