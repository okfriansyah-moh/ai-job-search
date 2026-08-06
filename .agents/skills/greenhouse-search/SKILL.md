---
name: greenhouse-search
version: 1.0.0
description: Search the configured remote-friendly Greenhouse company boards.
enabled: true
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Greenhouse Search

Searches public job boards configured in `../ats-search/boards.json`.

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source greenhouse --query "Senior Software Engineer" --format json
```
