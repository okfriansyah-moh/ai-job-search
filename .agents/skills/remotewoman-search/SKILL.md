---
name: remotewoman-search
version: 1.0.0
description: "Search public Remote Woman remote job listings. Trigger: Remote Woman jobs, remote women job board, remote developer jobs."
context: fork
enabled: true
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Remote Woman Search

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source remotewoman --query "Engineering Manager" --jobage 14 --limit 20 --format json
```

Uses Remote Woman's public WordPress job-listing endpoint. Original listing and application URLs are retained separately.
