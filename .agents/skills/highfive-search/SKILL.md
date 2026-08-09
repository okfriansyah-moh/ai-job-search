---
name: highfive-search
version: 1.0.0
description: Documented Highfive Global source status for Southeast Asia technology hiring.
context: fork
enabled: false
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Highfive Global

Disabled deliberately. Highfive Global's public WordPress API exposes talent profiles and positions, not a searchable public job-posting feed. The shared CLI reports this as `skipped`, rather than pretending an empty scrape is healthy.

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source highfive --format json
```
