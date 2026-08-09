# Daily Job Search Automation

The repository is the source of truth. Scheduler integrations only invoke the
same local command:

```bash
python3 automation/run_daily.py --scheduler codex
```

The runner searches enabled portal CLIs, applies the candidate gates, ranks new
jobs through the configured CLI-agent fallback chain, updates local state, and
sends Telegram cards. It never submits an application.

## Configuration

Keep secrets outside Git. Export these variables in the environment used by the
chosen scheduler:

```bash
export TELEGRAM_BOT_TOKEN='...'
export TELEGRAM_CHAT_ID='...'
export AUTOMATION_AGENT_CHAIN='claude,codex,copilot'
# Optional: enables the Adzuna global-market source.
export ADZUNA_APP_ID='...'
export ADZUNA_APP_KEY='...'
```

`TELEGRAM_ALLOWED_CHAT_ID` remains supported for compatibility. To discover the
ID automatically, first create the bot with BotFather, open a chat with it, send
`/start`, and run:

```bash
python3 automation/telegram_setup.py --write
```

The command writes the single discovered chat ID to the ignored
`automation/.env` file. If more than one chat is pending, use
`python3 automation/telegram_setup.py --json` and choose the intended ID
manually.

For local schedulers, the same values may be stored in the ignored
`automation/.env` file as simple `KEY=value` lines. Existing environment
variables always take precedence.

Use `AUTOMATION_DISABLE_AI=1` to force deterministic ranking during diagnostics.
Agent command overrides are available as `AUTOMATION_AGENT_CLAUDE_CMD`,
`AUTOMATION_AGENT_CODEX_CMD`, and `AUTOMATION_AGENT_COPILOT_CMD`.

## Sources

Every enabled portal skill is searched. Alongside LinkedIn, Freehire, and the
Danish portals, the automation includes Remotive, Remote OK, Hubstaff Talent,
Remote Woman, We Work Remotely, JS Remotely (via its current `javascript.jobs`
canonical site), WorkWave's official Lever board, Adzuna, and direct public
Greenhouse, Lever, and Ashby company boards configured in
`.agents/skills/ats-search/boards.json`.

Highfive Global, Eztrackr, Wellfound, AI Jobs, Toptal, and FlexJobs are installed
as explicitly disabled source records. They currently have no stable, supported
public vacancy feed, are access controlled, or do not serve job listings. This
is intentional: the source-health report says `skipped` with the reason instead
of falsely treating an empty scrape as healthy. Jobicy remains disabled until its
live API contract and reuse terms are revalidated. All enabled integrations make
public GET requests only; none can submit an application.

## Commands

```bash
python3 automation/run_daily.py --dry-run
python3 automation/run_daily.py --health
python3 automation/run_daily.py --force --scheduler manual
python3 automation/telegram_setup.py
python3 automation/telegram_listener.py
```

`--dry-run` does not update `seen_jobs.json`, the tracker, or the run ledger. It
prints the Telegram preview instead.

## Scheduler options

Codex Scheduled Task is the default. Use the provider-specific prompt in
`automation/schedulers/` and invoke `run_daily.py` on this Mac at 20:00 WIB.
The cron and launchd examples are local fallbacks. Multiple schedulers can be
installed safely because the shared run ledger makes a completed day a no-op.

The Telegram listener is separate from the daily trigger and should be kept
alive with launchd while the Mac is online.

## Delivery idempotency

Each Telegram card is reserved in `automation/state/notification_ledger.sqlite3`
before it is sent. The ledger hashes canonical URLs, source-scoped job IDs, and
company/title/location aliases, so the same listing cannot be announced twice
even when a second portal syndicates it under a different URL. SQLite uses WAL
and transactional claims for scheduler/process safety.

Known Telegram rejections (for example rate limits) remain in the JSON outbox
and retry safely. Network-interrupted requests are marked `uncertain` in the
ledger and are deliberately not replayed automatically: Telegram offers no
idempotency key, so replaying an ambiguous request could duplicate a card.

## Telegram actions

Job cards support opening the posting, saving interest, skipping, confirming an
application, changing status, and adding notes. `/pipeline`, `/today`, `/new`,
`/job <id>`, `/note <id> <text>`, and `/help` are available. Telegram actions
write the existing tracker and application archive; they do not submit forms.
