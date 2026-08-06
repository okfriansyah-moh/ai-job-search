---
name: remoteok-search
version: 1.0.0
description: Search global remote jobs through Remote OK's public JSON feed.
enabled: true
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Remote OK Search

Use for fully remote technical roles worldwide.

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source remoteok --query "Technical Lead" --format json
```

Retain Remote OK attribution and link to the original posting URL.
