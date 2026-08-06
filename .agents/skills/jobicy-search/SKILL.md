---
name: jobicy-search
version: 1.0.0
description: Search global remote jobs through Jobicy's public feed after contract validation.
enabled: false
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Jobicy Search

This adapter is implemented but disabled until its live response contract and reuse terms are revalidated.

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source jobicy --query "Principal Engineer" --format json
```
