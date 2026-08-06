# Scheduler adapters

Every adapter invokes the same repository runner. Keep exactly one provider
schedule enabled by default; the run ledger and lock make fallbacks safe.

## Codex Scheduled Task (default)

Create a local scheduled task for 20:00 in `Asia/Jakarta` with this prompt:

```text
In the ai-job-search project, run:
python3 automation/run_daily.py --scheduler codex
Report the JSON summary and any portal or Telegram failures. Do not edit source
files or submit applications.
```

## Cursor Automation

Use the same prompt, replacing the scheduler flag with `cursor`.

## Claude Code

Use a scheduled local command or task prompt:

```text
Run `python3 automation/run_daily.py --scheduler claude` in the ai-job-search repository.
Only report the result. Never submit applications.
```

## GitHub Copilot / GitHub Actions

`github-actions.yml.example` is a template only. Do not enable it in the public
fork unless the profile/tracker state and secrets are intentionally hosted in a
private environment.

## cron

```cron
0 20 * * * cd /ABSOLUTE/PATH/ai-job-search && /usr/bin/python3 automation/run_daily.py --scheduler cron >> automation/state/cron.log 2>&1
```

## launchd

Copy `com.ai-job-search.daily.plist.example` to
`~/Library/LaunchAgents/com.ai-job-search.daily.plist`, replace the absolute
repository path, and load it with `launchctl load`. Use it as a fallback or as a
local primary trigger. The Telegram listener has a separate KeepAlive service.

