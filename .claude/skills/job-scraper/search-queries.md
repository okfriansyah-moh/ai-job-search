# Search Queries for Job Scraper

## Installed portal CLIs
Use every portal skill installed under `.agents/skills/`, especially LinkedIn and Freehire. These web searches are fallback queries for portals without a CLI and for company career pages.

## Search scope
- **Languages:** Indonesian, English
- **CV language:** English
- **Geography:** Indonesia, US remote, South Korea, Japan, Germany, the Netherlands, Europe, Slovakia, Balkan territories, Singapore, Qatar, the UAE, Arab countries, Asia, and remote roles worldwide
- **Work model:** Indonesia roles may be onsite, hybrid, or remote. Outside Indonesia, remote is required; onsite or hybrid is allowed only with explicit employer-sponsored relocation/support and a relocation package.
- **Industries:** All, with priority for fintech, payments, banking, SaaS, platform engineering, and technology companies
- **Exclusion:** Do not return India-based roles, roles requiring work from India, or India-based employers unless explicitly requested. Remote roles for employers based elsewhere remain eligible.

## Priority 1: Engineering Leadership
```
site:linkedin.com/jobs "Engineering Manager" remote
site:linkedin.com/jobs "Software Engineering Manager" remote
site:linkedin.com/jobs "Director of Engineering" remote
site:linkedin.com/jobs "Engineering Lead" remote payments OR SaaS
site:linkedin.com/jobs "Team Lead" engineering remote
site:linkedin.com/jobs "Lead Engineer" remote
site:linkedin.com/jobs "Technical Lead" remote software
<!-- SETUP: Customize these queries based on your skills, target roles, and location -->

## Installed portal CLIs (primary for `/scrape`)

`/scrape` discovers every portal skill under `.agents/skills/*/SKILL.md` and runs its CLI first. Shipped country-agnostic CLIs include `linkedin-search` and `freehire-search`; Danish demos and any skill you add with `/add-portal` are included the same way. You do **not** need a matching `site:` line below for those CLIs to run.

The `site:` query templates in this file are the **WebSearch fallback** — for portals without a CLI, company career pages, or when a CLI fails.

**Language scope:** write every query category in every language listed in your CLAUDE.md Languages table (typically 1-2, sometimes more). A posting requiring a language you have *not* declared, as a job condition, is excluded before scoring; a posting requiring a *higher level* than you declared in a language you *do* work in is flagged for your own judgment, not excluded — see `04-job-evaluation.md`'s Language Gate, the single source of truth for this rule. Translate each category's keywords rather than machine-translating word-for-word (e.g. "Frontend Developer" -> "Desarrollador Frontend", not a literal word-for-word translation) if you work in more than one language.

## Search Sites

Primary (your market's job boards - scaffold one with `/add-portal`):
- **[YOUR_JOB_BOARD]** - your market's largest general job board
- **linkedin.com/jobs** - LinkedIn job listings (filter: [YOUR_COUNTRY] / [YOUR_CITY]); also covered by `linkedin-search` CLI
- **[YOUR_INDUSTRY_JOB_BOARD]** - a niche/industry board for your field (optional)
- **[YOUR_ADDITIONAL_JOB_BOARD]** - another major board for your market (optional)

Secondary (company career pages via Google):
- Direct Google searches with `site:` filters for known target companies

## Query Categories

Queries are grouped by priority. Write **each category in every language from your Languages table** (see Language scope above). Combine each query with your location terms (e.g. your city, region, or metro area) where the site supports it.

**Organize by function, not job title.** The same underlying work carries different titles across companies and markets (a "Data Scientist" role at one employer may be posted as "Insights Analyst" or "Data Consultant" at another). Name each priority category after the function it covers, and list several plausible job titles as query variants within that category rather than betting an entire priority tier on one exact title string.

### Priority 1: [YOUR_PRIMARY_ROLE_TYPE]

These match your strongest and most desired career direction.

```
site:[YOUR_JOB_BOARD] "[YOUR_PRIMARY_JOB_TITLE_1]" [YOUR_CITY]
site:[YOUR_JOB_BOARD] "[YOUR_PRIMARY_JOB_TITLE_2]" [YOUR_CITY]
site:[YOUR_JOB_BOARD] "[YOUR_KEY_SKILL]" [YOUR_CITY]
site:linkedin.com/jobs "[YOUR_PRIMARY_JOB_TITLE_1]" [YOUR_COUNTRY]
```

## Priority 2: Architecture and senior engineering
```
site:linkedin.com/jobs "Staff Engineer" remote
site:linkedin.com/jobs "Software Architect" remote
site:linkedin.com/jobs "Solution Architect" remote
site:linkedin.com/jobs "Solution Lead Engineer" remote
site:linkedin.com/jobs "Lead Software Engineer" remote
site:linkedin.com/jobs "Senior Software Engineer" remote Go OR Java
site:linkedin.com/jobs "Software Engineer II" remote Go OR Java
site:linkedin.com/jobs CTO remote startup
```

## Priority 3: Forward-deployed and AI-native leadership
```
site:linkedin.com/jobs "Forward Deployed Engineer" remote
site:linkedin.com/jobs "Forward Deployed Engineer Lead" remote
site:linkedin.com/jobs "Forward Deployed Manager" remote
site:linkedin.com/jobs "AI Native" engineering lead remote
site:linkedin.com/jobs "AI Engineer" remote
site:linkedin.com/jobs "AI Enablement" engineer remote
site:linkedin.com/jobs "Automation AI" engineer remote
site:linkedin.com/jobs "AI Engineering Lead" remote
```

## Priority 4: Domain and platform roles
```
site:linkedin.com/jobs payments engineering manager remote
site:linkedin.com/jobs fintech "Technical Lead" remote
site:linkedin.com/jobs banking API architect remote
site:linkedin.com/jobs "platform engineering" manager remote
site:linkedin.com/jobs "developer productivity" engineering manager remote
site:linkedin.com/jobs "Platform Engineer" remote Go OR Java
site:linkedin.com/jobs "Backend Engineer" remote Go OR Java
site:linkedin.com/jobs Go Java payments remote
```

## Priority 5: Related engineering roles with strong compensation potential
Use these when the role has senior scope, transparent compensation, or clear ownership of architecture, platforms, customer solutions, or AI enablement.
```
site:linkedin.com/jobs "Senior Backend Engineer" remote salary
site:linkedin.com/jobs "Principal Engineer" remote salary
site:linkedin.com/jobs "Staff Software Engineer" remote compensation
site:linkedin.com/jobs "Solutions Engineer" remote payments OR SaaS
site:linkedin.com/jobs "Technical Solutions Architect" remote
site:linkedin.com/jobs "Engineering Productivity" remote
site:linkedin.com/jobs "AI Platform Engineer" remote
```

## Indonesia search coverage
Use these as WebSearch fallbacks when no dedicated CLI is installed. Indonesia-based roles may be onsite, hybrid, or remote.
```
site:jobstreet.co.id "Engineering Manager" Indonesia
site:jobstreet.co.id "Software Engineering Manager" Jakarta
site:id.jobsdb.com "Engineering Manager" Indonesia
site:id.jobsdb.com "Senior Software Engineer" Jakarta Go OR Java
site:glints.com/id/en/opportunities/jobs "Engineering Manager" Indonesia
site:kalibrr.id "Software Engineer" Indonesia
site:linkedin.com/jobs "Engineering Manager" Indonesia
site:linkedin.com/jobs "Senior Software Engineer" Indonesia Go OR Java
```

## Target role titles
Engineering Manager; Director of Engineering; Staff Engineer; CTO; Software Architect; Solution Architect; Solution Lead Engineer; Lead Engineer; Engineering Lead; Team Lead; Lead Software Engineer; Senior Software Engineer; Software Engineer II; AI Engineer; AI-native Lead; AI Enablement Lead; Automation AI Engineer; Forward Deployed Engineer; Forward Deployed Engineer Lead; Senior Forward Deployed Engineer; Forward Deployed Manager; Software Engineering Manager; IT Manager; Platform Engineer; Backend Engineer; Developer Productivity Engineer; Solutions Engineer; Principal Engineer.

## Key searchable skills
Engineering leadership, Go, Java, TypeScript, payment infrastructure, banking APIs, system architecture, DORA metrics, SLOs, cloud-cost optimization, KYC, SaaS, AI enablement, automation, platform engineering, solution architecture, developer productivity.

## Compensation preference
Prioritize postings with strong compensation, senior scope, or transparent salary ranges. Do not reject a role solely because salary is undisclosed, but flag missing compensation for review and use `salary_lookup.py` when configured. Compensation never overrides the location gate or factual fit requirements.

## Location filter
- **Ideal:** Indonesia roles in any work model; otherwise fully remote worldwide, US remote, South Korea remote, Japan remote, Germany remote, Netherlands remote, Singapore remote, Qatar remote, UAE remote, Arab-region remote, and Asia remote.
- **Acceptable:** Slovakia and Balkan territories with remote-first arrangements.
- **Borderline:** Hybrid roles requiring occasional travel, or roles with difficult time-zone overlap.
- **Conditional outside Indonesia:** Onsite or hybrid roles only when employer-sponsored relocation/support and a relocation package are explicitly stated.
- **Too far / exclude:** Roles requiring relocation without support, or non-remote roles without a viable relocation package.
- **India exclusion:** Exclude India-based roles, India-based employers, and roles requiring work from India unless explicitly requested.

## Date and language filters
Only include jobs posted within the last 14 days or with an active deadline. Apply the Language Gate in `04-job-evaluation.md`: Indonesian and English are declared; undeclared job-condition languages are hard exclusions, while a higher English requirement is flagged for review.
