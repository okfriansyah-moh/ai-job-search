---
name: jsremotely-search
version: 1.0.0
description: "Search JS Remotely remote JavaScript jobs. Trigger: JS Remotely jobs, JavaScript remote jobs, JavaScript.jobs vacancies."
context: fork
enabled: true
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# JS Remotely Search

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source jsremotely --query "TypeScript Engineer" --jobage 14 --limit 20 --format json
```

The supplied JS Remotely domain currently serves listings on `javascript.jobs`; source metadata records that canonical destination explicitly.
