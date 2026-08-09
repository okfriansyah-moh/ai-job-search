---
name: wellfound-search
version: 1.0.0
description: Documented Wellfound source status for startup job searches.
context: fork
enabled: false
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Wellfound

Disabled deliberately. Wellfound has no supported public search API and blocks unauthenticated automated job-search access. The pipeline does not bypass access controls.
