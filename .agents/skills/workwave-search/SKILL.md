---
name: workwave-search
version: 1.0.0
description: "Search WorkWave's public careers board. Trigger: WorkWave careers, WorkWave jobs, WorkWave vacancies."
context: fork
enabled: true
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# WorkWave Search

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source workwave --query "Software Engineer" --jobage 14 --limit 20 --format json
```

WorkWave is an employer-specific source, not a broad remote board. It is isolated from the general Lever source to preserve accurate attribution.
