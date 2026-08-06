---
name: adzuna-search
version: 1.0.0
description: Search Adzuna's global job API across configured target markets.
enabled: true
requires_env: ADZUNA_APP_ID,ADZUNA_APP_KEY
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Adzuna Search

Requires `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in ignored `automation/.env`. Without both values, it exits successfully with `skipped: not configured`.

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source adzuna --query "Software Engineering Manager" --format json
```
