---
name: lever-search
version: 1.0.0
description: Search the configured remote-friendly Lever company boards.
enabled: true
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Lever Search

Searches public job boards configured in `../ats-search/boards.json`.

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source lever --query "Technical Lead" --format json
```
