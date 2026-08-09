---
name: hubstaff-talent-search
version: 1.0.0
description: "Search public Hubstaff Talent remote jobs. Trigger: Hubstaff Talent jobs, remote freelance jobs, Hubstaff vacancies."
context: fork
enabled: true
allowed-tools: Bash(bun run .agents/skills/global-job-sources/cli/src/cli.ts *)
---

# Hubstaff Talent Search

Searches Hubstaff Talent's public remote-job search response through the shared zero-runtime-dependency Bun CLI.

```bash
bun run .agents/skills/global-job-sources/cli/src/cli.ts search --source hubstaff --query "Software Engineer" --jobage 14 --limit 20 --format json
```

Results are public listings only. Keep request volume low. The board returns a Rails UJS HTML fragment, parsed card-by-card; a malformed card is discarded without aborting the source.
