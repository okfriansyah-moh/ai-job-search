---
name: ashby-search
version: 1.0.0
description: Search the configured remote-friendly Ashby company boards with disclosed compensation where available.
enabled: true
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Ashby Search

Searches public job boards configured in `../ats-search/boards.json`.

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source ashby --query "Principal Engineer" --format json
```
