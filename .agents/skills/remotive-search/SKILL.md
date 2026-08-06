---
name: remotive-search
version: 1.0.0
description: Search remote technical jobs from Remotive's public API.
enabled: true
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Remotive Search

Use for fully remote technical roles worldwide. Results include the full posting description, candidate location restriction, job type, published date, and salary when disclosed.

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source remotive --query "Senior Software Engineer" --format json
```

Keep Remotive attribution and its posting URL when presenting results.
