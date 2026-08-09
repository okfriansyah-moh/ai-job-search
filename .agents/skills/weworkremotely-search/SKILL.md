---
name: weworkremotely-search
version: 1.0.0
description: "Search We Work Remotely public RSS jobs. Trigger: We Work Remotely jobs, WWR jobs, worldwide remote vacancies."
context: fork
enabled: true
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# We Work Remotely Search

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source weworkremotely --query "Principal Engineer" --jobage 14 --limit 20 --format json
```

Uses the public RSS feed and retains the source posting URL. Feed records are parsed independently so malformed XML in one record cannot invalidate the batch.
