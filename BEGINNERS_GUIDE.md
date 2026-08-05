# AI Job Search Framework: A Complete Beginner's Guide

> 👋 Welcome! This guide is written for people who are **new to this framework** and want to get up and running as quickly as possible.
> No prior coding experience needed. Just follow the steps in order.

---

## Table of Contents

1. [What Is This Framework?](#1-what-is-this-framework)
2. [Choosing Your AI Agent](#2-choosing-your-ai-agent)
3. [Installation & Setup](#3-installation--setup)
4. [Fill In Your Profile](#4-fill-in-your-profile)
5. [The Job Search Workflow](#5-the-job-search-workflow)
6. [Using Each AI Agent](#6-using-each-ai-agent)
   - [Claude Code](#61-claude-code-recommended)
   - [GitHub Copilot](#62-github-copilot)
   - [Cursor](#63-cursor)
   - [Google Codex / Antigravity](#64-google-codex--antigravity)
   - [OpenAI Codex](#65-openai-codex)
7. [Common Tasks](#7-common-tasks)
8. [Quick-Start Checklist](#8-quick-start-checklist)
9. [Video & Learning Resources](#9-video--learning-resources)
10. [Troubleshooting](#10-troubleshooting)
11. [Frequently Asked Questions](#11-frequently-asked-questions)

---

## 1. What Is This Framework?

The AI Job Search framework is a **smart job application toolkit powered by AI**. It helps you:

| What it does | What that means for you |
|---|---|
| 🔍 Search job boards | Automatically finds jobs matching your profile |
| 📊 Score & rank jobs | Shows you which jobs are the best fit — before you apply |
| 📝 Write tailored CVs | Generates a customized resume for each job |
| ✉️ Write cover letters | Writes a personalized cover letter for each application |
| 🎤 Prepare for interviews | Generates practice questions and talking points |
| 📁 Track outcomes | Keeps a record of every application you've made |

**The core idea:** Instead of sending the same resume to every job, this framework helps you craft a custom application for each role — automatically.

### Why does that matter?

```
❌ Old way: One generic resume → low callback rate
   "Dear Hiring Manager, I'm interested in this position."

✅ This framework: Tailored application for each job → higher callback rate
   "Your team is scaling in Southeast Asia — here's how my experience
    directly maps to what you need in this role."
```

The creator of this framework used it to land 20 first interviews from 69 applications, and accepted an AI engineering offer in June 2026.

---

## 2. Choosing Your AI Agent

An **AI agent** is the AI tool that reads your profile, thinks, and does the work for you. This framework supports several:

### Side-by-Side Comparison

| Feature | Claude Code | GitHub Copilot | Cursor | Google Codex | OpenAI Codex |
|---|---|---|---|---|---|
| Full workflow (`/apply`, `/interview`) | ✅ Full | ⚠️ Partial | ⚠️ Partial | ⚠️ Partial | ⚠️ Partial |
| Job search (LinkedIn, Freehire, etc.) | ✅ | ✅ via CLI | ✅ via CLI | ✅ Auto | ✅ Auto |
| CV & cover letter generation | ✅ Automated | ✅ Manual assist | ✅ Manual assist | ⚠️ Basic | ⚠️ Basic |
| Interview prep | ✅ Guided | ✅ Manual | ✅ Manual | ⚠️ Basic | ⚠️ Basic |
| Beginner-friendliness | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Requires coding knowledge | ❌ No | ❌ No | ❌ No | ⚠️ Some | ⚠️ Some |
| Cost | Claude Pro ($20/mo) or API key | $10–$39/mo | Free tier + paid | Varies | Varies |

### My recommendation:

- **You want the simplest, most complete experience** → Use **Claude Code**
- **You already pay for GitHub Copilot** → Use **GitHub Copilot** (works well, slightly more manual)
- **You prefer a dedicated AI editor** → Use **Cursor**
- **You use Google Cloud / want Google's AI** → Use **Google Codex / Antigravity**
- **You use OpenAI / ChatGPT** → Use **OpenAI Codex**

> 💡 You can switch agents later. Your profile files work with all of them.

---

## 3. Installation & Setup

### 3.1 Install Required Tools

These tools are needed regardless of which AI agent you choose.

---

#### Step 1: Install Python 3.10+

Python is used by the salary lookup and other background tools.

**Check if already installed:**
```bash
python3 --version
# Should show: Python 3.10.x or higher
```

**If not installed:**
- **macOS:** `brew install python@3.10` (requires [Homebrew](https://brew.sh))
- **Windows:** Download from [python.org](https://www.python.org/downloads/) and check "Add to PATH" during install
- **Linux:** `sudo apt install python3.10`

---

#### Step 2: Install Bun

Bun runs the job search tools (LinkedIn search, Freehire search, etc.).

**macOS/Linux:**
```bash
curl -fsSL https://bun.sh/install | bash
# Restart your terminal after this
```

**Windows PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -c "irm https://bun.sh/install.ps1 | iex"
```

**Verify:**
```bash
bun --version
# Should show a version number like: 1.x.x
```

---

#### Step 3: Install LaTeX

LaTeX converts your CV and cover letter templates into PDF documents. It's like a document compiler.

- **macOS:** Download [MacTeX](https://tug.org/mactex/) (~4GB) or install via `brew install mactex`
- **Windows:** Download [MiKTeX](https://miktex.org/download)
- **Linux:** `sudo apt install texlive-full`

**Verify:**
```bash
lualatex --version
xelatex --version
```

> ⏱️ LaTeX is a large install — it may take 10–20 minutes.

##### Minimal install alternative (macOS — TinyTeX)

If you'd rather not install 4GB of LaTeX, use TinyTeX:

```bash
curl -fsSL https://yihui.org/tinytex/install-bin-unix.sh -o /tmp/tinytex-install-bin-unix.sh
sh /tmp/tinytex-install-bin-unix.sh /tmp --no-path
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"

# Install required packages
tlmgr install \
  moderncv fontawesome5 fontawesome6 academicons import luatexbase pgf \
  titlesec textpos xltxtra xunicode cite realscripts needspace
```

---

#### Step 4: Install job search tools

This installs the LinkedIn, Freehire, and other job board search tools.

**macOS/Linux:**
```bash
cd ai-job-search

for tool in jobbank-search jobdanmark-search jobindex-search jobnet-search linkedin-search freehire-search; do
  (cd .agents/skills/$tool/cli && bun install)
done
```

**Windows PowerShell:**
```powershell
cd ai-job-search

$tools = @("jobbank-search", "jobdanmark-search", "jobindex-search", "jobnet-search", "linkedin-search", "freehire-search")
foreach ($tool in $tools) {
  Push-Location ".agents/skills/$tool/cli"
  bun install
  Pop-Location
}
```

> You should see: `+ packages installed` for each tool.

---

#### Step 5: Install PDF text extractor (optional but recommended)

This lets the framework verify that automated screening systems (ATS) can read your CV.

- **macOS:** `brew install poppler`
- **Linux:** `sudo apt install poppler-utils`
- **Windows:** `choco install poppler`

---

### 3.2 Install Your AI Agent

#### Claude Code
```bash
npm install -g @anthropic-ai/claude-code
```
Get your API key at [console.anthropic.com](https://console.anthropic.com) and set it:
```bash
export ANTHROPIC_API_KEY=your_key_here
# Add this to your ~/.zshrc or ~/.bashrc to make it permanent
```

#### GitHub Copilot
1. Install [VS Code](https://code.visualstudio.com/)
2. Install the **GitHub Copilot** extension from the Extensions panel
3. Sign in with your GitHub account
4. Enable **Copilot Chat** for the best experience

#### Cursor
1. Download from [cursor.com](https://cursor.com)
2. Install and open it
3. Sign in or start the free trial
4. Open your `ai-job-search` folder in Cursor

#### Google Codex / Antigravity
1. Follow [Google's setup guide](https://cloud.google.com/)
2. The `.agents/skills/` portal skills are auto-discovered automatically

#### OpenAI Codex
1. Install via `npm install -g @openai/codex` or the OpenAI CLI
2. Set your API key: `export OPENAI_API_KEY=your_key_here`
3. The `.agents/skills/` portal skills are auto-discovered automatically

---

## 4. Fill In Your Profile

Your profile is the **heart of everything**. It tells the AI who you are, what you've done, and what you're looking for. The better your profile, the better your tailored CVs, cover letters, and interview prep.

### What files to fill in

| File | What it contains | Priority |
|---|---|---|
| `CLAUDE.md` | Master profile — everything about you | 🔴 Required |
| `.claude/skills/job-application-assistant/01-candidate-profile.md` | Structured resume data | 🔴 Required |
| `.claude/skills/job-application-assistant/02-behavioral-profile.md` | Work style, strengths, personality | 🟡 Important |
| `.claude/skills/job-application-assistant/03-writing-style.md` | Your communication style | 🟡 Important |
| `.claude/skills/job-application-assistant/04-job-evaluation.md` | What matters to you in a job | 🟡 Important |
| `cv/main_example.tex` | Your LaTeX CV template | 🔴 Required |
| `cover_letters/cover.cls` | Cover letter class (don't edit this) | ✅ Already set |

---

### Option A: Automated setup (Claude Code only)

```bash
cd ai-job-search
claude /setup
```

This walks you through an interactive interview. It will:
- Ask about your background, skills, and experience
- Generate all profile files automatically
- Create an example CV with your information
- Set up your job search queries

> ⏱️ Takes about 15–30 minutes for a thorough setup.

---

### Option B: Manual setup (all agents)

#### Step 1: Gather your information first

Write these down before you start editing files:

```
Personal:
  - Full name
  - Email, phone, LinkedIn URL
  - City, country
  - Languages and levels (e.g., English - Native, Spanish - B2)

Education (most recent first):
  - Degree, field, institution, year
  - Thesis or major project (if any)

Work experience (most recent first):
  - Job title, company, dates
  - 3–5 key responsibilities per role
  - Achievements with numbers (e.g., "Reduced load time by 40%")

Skills:
  - Technical: programming languages, frameworks, tools
  - Domain: industries you know well
  - Soft skills: leadership, communication, etc.

What you're looking for:
  - Target job titles
  - Target industries/companies
  - Must-haves (e.g., remote work, no on-call)
  - Deal-breakers
```

#### Step 2: Edit `CLAUDE.md`

Open `CLAUDE.md` and replace every `[PLACEHOLDER]` with your real information.

**Before:**
```markdown
### Identity
- **Name:** [YOUR_NAME]
- **Location:** [YOUR_CITY], [YOUR_COUNTRY] ([YOUR_COMMUTE_CONSTRAINTS])
- **Status:** [YOUR_EMPLOYMENT_STATUS]
```

**After:**
```markdown
### Identity
- **Name:** Sarah Johnson
- **Location:** San Francisco, USA (Hybrid or remote preferred, open to on-site within SF Bay Area)
- **Status:** Currently employed, passively looking
```

Fill in every section: Identity, Education, Professional Experience, Technical Skills, Behavioral Profile, Target Sectors, and Deal-breakers.

#### Step 3: Edit `01-candidate-profile.md`

This is a more structured version of your resume. Open `.claude/skills/job-application-assistant/01-candidate-profile.md` and fill it in following the template.

> 💡 This file is what the AI reads when generating your CV and cover letters, so be thorough here.

#### Step 4: Edit your CV template

Open `cv/main_example.tex` and replace all placeholders. You don't need to know LaTeX — just find and replace the `[PLACEHOLDER]` tokens.

Then test it compiles:
```bash
cd cv
lualatex -interaction=nonstopmode -halt-on-error main_example.tex
# Open main_example.pdf and check it looks right
```

---

## 5. The Job Search Workflow

Here's the full lifecycle of using this framework:

```
┌─────────────────────────────────────────────────────────────┐
│  YOUR PROFILE (fill in once, update as you grow)            │
│  CLAUDE.md + 01-candidate-profile.md + cv/main.tex         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  /scrape → Search job boards for matching positions         │
│  LinkedIn, Freehire, Jobindex, Jobnet, Jobbank, Jobdanmark  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  /rank → Score all found jobs against your profile          │
│  Get a ranked shortlist of the best-fit positions           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  /apply <job_url> → For each job you want to apply to:      │
│  1. Evaluate fit (skills, experience, behavioral match)     │
│  2. Draft tailored CV as cv/main_<company>.tex              │
│  3. Draft cover letter as cover_letters/cover_<company>.tex │
│  4. Compile both to PDF and do final review                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  /interview → Prepare for a specific interview              │
│  STAR stories, tough questions, company research,           │
│  mock interview roleplay                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  /outcome → Record what happened                            │
│  Track each application: interview stage, offer, rejection  │
│  This data feeds back into /setup calibration over time     │
└─────────────────────────────────────────────────────────────┘
```

### Additional commands

| Command | What it does |
|---|---|
| `/expand` | Enriches your profile by mining documents you upload |
| `/upskill` | Identifies skill gaps across your tracked jobs and builds a learning plan |
| `/rank` | Scores all scraped jobs against your profile |
| `/add-portal` | Adds a new job board for your market |
| `/add-template` | Registers your own LaTeX CV or cover letter template |
| `/reset` | Clears parts of the framework to start fresh |

---

## 6. Using Each AI Agent

### 6.1 Claude Code (Recommended)

Claude Code gives you the **full experience** — every command works, everything is automated.

#### Starting Claude Code
```bash
cd ai-job-search
claude
```

#### Running the workflow
```bash
claude /setup          # First time only: fill in your profile
claude /scrape         # Search for jobs
claude /rank           # Score and rank results
claude /apply https://example.com/job  # Apply to a specific job
claude /interview      # Prepare for interview
claude /outcome        # Record what happened
```

#### Tips for Claude Code
- Use `/scrape` once a week to find new listings
- Always run `/rank` before picking which jobs to apply to
- The `/apply` workflow takes ~10–15 minutes per application — let it run
- After an interview, use `/outcome` to log the result and improve future calibration

---

### 6.2 GitHub Copilot

GitHub Copilot works best through **VS Code with the Copilot Chat panel**. The job search CLI tools work directly; for CV/cover letter generation you'll work interactively in the chat.

#### Setup
1. Open the `ai-job-search` folder in VS Code
2. Open the **Copilot Chat** panel (click the chat icon in the sidebar)
3. Enable `@workspace` context so Copilot can read all your profile files

#### Search for jobs
Run in the VS Code terminal:
```bash
cd .agents/skills/linkedin-search/cli
bun run search.ts "software engineer remote"
```

For other boards:
```bash
cd .agents/skills/freehire-search/cli
bun run search.ts "data analyst Copenhagen"
```

#### Evaluate and apply to a job
In the Copilot Chat panel:
```
@workspace I found this job posting. Please:
1. Evaluate my fit based on my profile in CLAUDE.md and 01-candidate-profile.md
2. Tell me which skills I match and which I'm missing
3. Recommend whether I should apply

Job posting:
[PASTE THE JOB POSTING TEXT HERE]
```

#### Generate a tailored CV
```
@workspace Based on the job posting above and my profile, please:
1. Identify which of my experiences to highlight
2. Rewrite the key bullets in my CV to match the role's language
3. Suggest any skills to add or reorder

I'll update cv/main.tex with your suggestions.
```

#### Generate a cover letter
```
@workspace Write a tailored cover letter for this role using:
- My profile from CLAUDE.md
- The cover letter structure in .claude/skills/job-application-assistant/06-cover-letter-templates.md
- The company name and role title from the posting

Format it so I can paste it into cover_letters/cover_<company>.tex
```

#### Compile your PDF
```bash
cd cv && lualatex -interaction=nonstopmode main_<company>.tex
cd ../cover_letters && xelatex cover_<company>.tex
```

---

### 6.3 Cursor

Cursor's **Agent mode** is the most powerful way to use this framework outside of Claude Code. It can read files, run commands, and make edits autonomously.

#### Setup
1. Open `ai-job-search` folder in Cursor
2. Press `Cmd+L` (Mac) or `Ctrl+L` (Windows) to open the AI chat
3. Switch to **Agent** mode (dropdown in chat)

#### Run a full application workflow
In Cursor's Agent chat:
```
I want to apply to a job. Here's the posting: [URL or paste text]

Please follow these steps from .claude/commands/apply.md:
1. Evaluate my fit using my profile in CLAUDE.md and 01-candidate-profile.md
2. Draft a tailored CV and save it as cv/main_<company>.tex
3. Draft a cover letter and save it as cover_letters/cover_<company>.tex
4. Compile both to PDF and tell me if there are any issues
```

Cursor Agent will read your profile, follow the apply workflow steps, generate the files, and run the LaTeX compilation — automatically.

#### Search for jobs
```
@workspace Search for [job title] jobs in [location] using the LinkedIn search tool 
at .agents/skills/linkedin-search/cli/
```

#### Prepare for an interview
```
@workspace I have an interview for [POSITION] at [COMPANY]. 
Follow the interview prep steps in .claude/commands/interview.md.
Read my profile from CLAUDE.md and help me prepare.
```

#### Tips for Cursor
- Use `@codebase` or `@workspace` to give Cursor access to your profile files
- Agent mode is much more powerful than regular chat — always use it for multi-step tasks
- Cursor can edit files directly — review its suggestions before saving

---

### 6.4 Google Codex / Antigravity

Google Codex and Antigravity **auto-discover the portal search skills** in `.agents/skills/`, so job searching works out of the box. For the full workflow, you'll reference the command files manually.

#### Job search (auto-discovered)
Just ask naturally:
```
Search for machine learning engineer jobs in Berlin
```
Codex will automatically find and use the LinkedIn and Freehire skills.

#### Full workflow (manual)
Open `.claude/commands/apply.md` and use it as a prompt template. Copy the steps and paste them into your Codex session with the job posting.

Example prompt:
```
I want to apply to this job: [PASTE JOB TEXT]

My profile is in CLAUDE.md and .claude/skills/job-application-assistant/01-candidate-profile.md

Please follow these steps:
1. Evaluate my fit (match skills, experience, behavioral profile)
2. Draft a tailored CV based on cv/main_example.tex
3. Draft a cover letter based on the structure in .claude/skills/job-application-assistant/06-cover-letter-templates.md
```

---

### 6.5 OpenAI Codex

OpenAI Codex works similarly to Google Codex, with auto-discovery of agent skills.

#### Job search
```bash
# Or through the OpenAI Codex CLI:
codex "Find backend developer jobs in Singapore using the skills in .agents/skills/"
```

#### Full workflow
Same approach as Google Codex — use `.claude/commands/apply.md` as your prompt template.

#### Tips for OpenAI Codex
- Point Codex at specific files: "Read my profile from CLAUDE.md and 01-candidate-profile.md"
- Paste the raw job posting text rather than a URL for better results
- For PDF generation, run the LaTeX commands yourself in the terminal

---

## 7. Common Tasks

### Search for jobs

| Agent | Command |
|---|---|
| Claude Code | `claude /scrape` |
| GitHub Copilot / Cursor | `cd .agents/skills/linkedin-search/cli && bun run search.ts "your query"` |
| Codex (Google/OpenAI) | Auto-discovered — just ask naturally |

---

### Apply to a job

| Agent | How |
|---|---|
| Claude Code | `claude /apply https://job-url` |
| GitHub Copilot | Paste posting in chat, ask for CV + cover letter help |
| Cursor (Agent mode) | Ask agent to follow `.claude/commands/apply.md` steps |
| Codex | Use `.claude/commands/apply.md` as your prompt template |

---

### Compile a PDF

```bash
# CV (uses lualatex)
cd cv
lualatex -interaction=nonstopmode -halt-on-error main_<company>.tex

# Cover letter (uses xelatex)
cd cover_letters
xelatex -interaction=nonstopmode -halt-on-error cover_<company>.tex
```

---

### Add a job board for your country

```bash
claude /add-portal
# Or ask: "Help me add a portal skill for [YOUR COUNTRY'S JOB BOARD]"
```

This scaffolds a new skill following the same format as the existing portals. Your local board gets picked up automatically by `/scrape`.

---

### Prepare for an interview

| Agent | Command |
|---|---|
| Claude Code | `claude /interview` |
| GitHub Copilot / Cursor | Ask: "Help me prepare for a [POSITION] interview at [COMPANY] using `.claude/commands/interview.md`" |
| Codex | Use `.claude/commands/interview.md` as your prompt |

---

### Track an application outcome

| Agent | Command |
|---|---|
| Claude Code | `claude /outcome` |
| All others | Update `job_search_tracker.csv` manually: add the result (interviewed, offered, rejected) to the relevant row |

---

## 8. Quick-Start Checklist

Use this checklist to get up and running. Check off each item as you complete it.

### Installation
- [ ] Python 3.10+ installed (`python3 --version`)
- [ ] Bun installed (`bun --version`)
- [ ] LaTeX installed (`lualatex --version`)
- [ ] Job search tools installed (`bun install` in each `.agents/skills/*/cli/`)
- [ ] Your AI agent installed and configured
- [ ] (Optional) `pdftotext` installed for ATS checking

### Profile Setup
- [ ] `CLAUDE.md` — all `[PLACEHOLDER]` tokens replaced with real info
- [ ] `01-candidate-profile.md` — full work history and skills
- [ ] `02-behavioral-profile.md` — work style and behavioral traits
- [ ] `03-writing-style.md` — your communication preferences
- [ ] `04-job-evaluation.md` — what matters to you in a job
- [ ] `cv/main_example.tex` — your base CV compiles to a clean 2-page PDF

### First Job Search
- [ ] Run `/scrape` (or CLI equivalent) and see results
- [ ] Run `/rank` to score the results
- [ ] Pick 1 job and run `/apply` on it
- [ ] Review the generated CV and cover letter PDFs
- [ ] Make any edits and recompile
- [ ] Submit your application!

### Ongoing
- [ ] Run `/scrape` once a week
- [ ] Log every application with `/outcome`
- [ ] After 10+ applications, run `/setup` again — it recalibrates based on what worked

---

## 9. Video & Learning Resources

### Understanding LaTeX (for CV editing)

If you want to understand the `.tex` files better:
- [Overleaf's 30-minute LaTeX Introduction](https://www.overleaf.com/learn/latex/Learn_LaTeX_in_30_minutes) — free, browser-based, no install needed
- [LaTeX for Beginners (PDF)](https://www.maths.tcd.ie/~dwilkins/LaTeXPrimer/) — covers the basics clearly
- [moderncv documentation](https://ctan.org/pkg/moderncv) — the specific CV class used in this framework

### Understanding Markdown (for profile files)

The profile files use Markdown — a simple text formatting syntax:
- `**bold text**` → **bold text**
- `# Heading` → a big header
- `- item` → a bullet point

That's basically all you need to know. Any text editor works.

### AI Agent resources

- **Claude Code:** [docs.anthropic.com/en/docs/claude-code](https://docs.anthropic.com/en/docs/claude-code)
- **GitHub Copilot:** [docs.github.com/en/copilot](https://docs.github.com/en/copilot)
- **Cursor:** [docs.cursor.com](https://docs.cursor.com)
- **Google Codex / Antigravity:** [cloud.google.com](https://cloud.google.com)
- **OpenAI Codex:** [platform.openai.com/docs](https://platform.openai.com/docs)

---

## 10. Troubleshooting

### "command not found: claude"
Claude Code is not installed or not on your PATH.
```bash
npm install -g @anthropic-ai/claude-code
# Restart your terminal
```

### "command not found: bun"
Bun is not installed or not on your PATH.
```bash
curl -fsSL https://bun.sh/install | bash
# Restart your terminal, then:
bun --version
```

### "lualatex: command not found"
LaTeX is not installed.
- **macOS:** `brew install mactex` (then restart terminal)
- **Windows:** Download MiKTeX from https://miktex.org/download
- **Linux:** `sudo apt install texlive-full`

### LaTeX compile fails with font errors
Missing packages. Fix with:
```bash
# macOS/Linux (TinyTeX or BasicTeX):
tlmgr install moderncv fontawesome5 fontawesome6 academicons needspace

# Linux (texlive):
sudo apt install texlive-fonts-extra texlive-xetex
```

### CV is 3 pages instead of 2
Your profile has too much content for 2 pages. Try:
- Shortening bullet points (aim for 1 line each)
- Reducing the number of bullets per role (3–4 is ideal)
- Removing very old or irrelevant experience
- Ask the AI: "My CV is 3 pages. Help me trim it to 2 pages without losing the most important content."

### Cover letter overflows to page 2
The letter is too long. Try:
- Cutting the last paragraph
- Shortening each paragraph to 2–3 sentences
- Ask the AI: "My cover letter is slightly over 1 page. Trim it to fit."

### Job search returns no results
- Try broader search terms (e.g., "developer" instead of "senior TypeScript developer")
- Try different job boards (LinkedIn often has more results than niche boards)
- Check your internet connection
- Check Bun is installed: `bun --version`

### PDF looks wrong / garbled text
This usually means the wrong compiler was used.
- **CV must use `lualatex`** (not `pdflatex` or `xelatex`)
- **Cover letter must use `xelatex`** (not `lualatex` or `pdflatex`)

### "Placeholder still in file" warning
You have unfilled placeholders like `[YOUR_NAME]` in your profile. Search for `[YOUR_` in your files:
```bash
grep -r "\[YOUR_" CLAUDE.md .claude/skills/job-application-assistant/
```
Fill in everything that shows up.

---

## 11. Frequently Asked Questions

**Q: Do I need to know how to code?**
A: No. You need to run a few terminal commands (copy-paste from this guide), but no coding knowledge is required. The AI does all the writing.

**Q: How long does the full setup take?**
A: Roughly 2 hours total:
- Installing tools: 30–60 minutes (mostly LaTeX downloading)
- Filling in your profile: 30–45 minutes
- First job search and application: 30–45 minutes

**Q: Can I use this with my existing CV?**
A: Yes! You can paste your existing resume content into the LaTeX template. The AI will help you format it and tailor it per application.

**Q: Which job boards are supported?**
A: Out of the box: LinkedIn (global), Freehire.dev (global), Jobindex (Denmark), Jobnet (Denmark), Jobbank (Denmark), Jobdanmark (Denmark).
To add your local job board, run `/add-portal` and the framework will scaffold a new skill for it.

**Q: Does this work for any country?**
A: The core workflow (profile, CV, cover letter, interview prep) works everywhere. The built-in job search portals lean Danish, but LinkedIn and Freehire are global. You can add portals for your market with `/add-portal`.

**Q: Is my data private?**
A: Your profile lives only in your local files and your private GitHub fork. Nothing is sent anywhere unless you explicitly share it (e.g., when the AI fetches a job URL to read).

**Q: How much does it cost to run?**
A: The framework itself is free and open-source. You pay for your AI agent:
- Claude Code: Claude Pro ($20/month) or pay-per-use API
- GitHub Copilot: $10–$39/month
- Cursor: Free tier available
- Google/OpenAI Codex: Pay-per-use API pricing

**Q: Can I use multiple agents?**
A: Yes! Since profiles are in plain text files, you can use Claude Code for `/apply`, GitHub Copilot for quick edits, and Cursor for reviewing LaTeX — they all read the same files.

**Q: What if the AI makes something up about me?**
A: This is taken seriously in the framework. The `/apply` workflow has a "Factual Grounding Audit" step that checks every claim in your CV and cover letter against your profile files. If something can't be verified, it gets flagged. Always review PDFs before sending.

**Q: I got hired! What do I do?**
A: Log it with `/outcome`, then consider a coffee for the creator ☕ → [ko-fi.com/madslorentzen](https://ko-fi.com/madslorentzen).

---

## Getting Help

- 💬 **GitHub Discussions** — Ask questions: [github.com/MadsLorentzen/ai-job-search/discussions](https://github.com/MadsLorentzen/ai-job-search/discussions)
- 🌍 **Community forks** — See how others adapted this for their market: [discussions/78](https://github.com/MadsLorentzen/ai-job-search/discussions/78)
- 🐛 **Bug reports** — Open an issue on GitHub
- 📚 **Framework docs** — `AGENTS.md`, `SETUP.md`, `CONTRIBUTING.md` in this repo

---

*Good luck with your job search!* 🚀
