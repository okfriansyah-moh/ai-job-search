#!/usr/bin/env bun

type Json = Record<string, unknown>
type Source = "remotive" | "remoteok" | "jobicy" | "adzuna" | "greenhouse" | "lever" | "ashby"

type Job = {
  id: string
  title: string
  company: string
  url: string
  applyUrl?: string
  location?: string
  workMode?: string
  description?: string
  date?: string
  salary?: string
  employmentType?: string
  seniority?: string
  source: Source
  externalId: string
  sourceUrls: string[]
}

const SOURCES = new Set<Source>(["remotive", "remoteok", "jobicy", "adzuna", "greenhouse", "lever", "ashby"])
const TIMEOUT_MS = 20_000

function values(argv: string[], name: string): string[] {
  const out: string[] = []
  for (let index = 0; index < argv.length; index++) if (argv[index] === name && argv[index + 1]) out.push(argv[++index])
  return out
}

function value(argv: string[], name: string, fallback = ""): string {
  return values(argv, name)[0] || fallback
}

function text(value: unknown): string {
  return String(value || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()
}

function stripHtml(value: unknown): string {
  return String(value || "").replace(/<br\s*\/?>/gi, "\n").replace(/<\/(p|li|div|h\d)>/gi, "\n").replace(/<[^>]+>/g, " ").replace(/\s*\n\s*/g, "\n").trim()
}

function declaredWorkMode(location: unknown, description: string, fallback: unknown): string {
  const value = `${text(location)} ${description}`.toLowerCase()
  if (/\bhybrid\b/.test(value)) return "hybrid"
  if (/\b(on-site|onsite|in-office)\b/.test(value)) return "onsite"
  if (/\b(remote|distributed|work from anywhere|worldwide)\b/.test(value) || fallback === true) return "remote"
  return ""
}

function ashbySalary(value: unknown): string {
  if (!value || typeof value !== "object") return ""
  const compensation = value as Json
  return text(compensation.scrapeableCompensationSalarySummary || compensation.compensationTierSummary)
}

async function request(url: string): Promise<unknown> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const response = await fetch(url, { headers: { Accept: "application/json", "User-Agent": "ai-job-search/1.0 (personal job search)" }, signal: controller.signal })
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
    return response.json()
  } finally {
    clearTimeout(timer)
  }
}

function matches(job: Job, queries: string[]): boolean {
  if (!queries.length) return true
  const haystack = job.title.toLowerCase()
  return queries.some((query) => query.toLowerCase().split(/\s+/).filter(Boolean).every((word) => haystack.includes(word)))
}

function isRecent(job: Job, days: number): boolean {
  if (!job.date || days >= 9999) return true
  const timestamp = Date.parse(job.date)
  if (Number.isNaN(timestamp)) return true
  return timestamp >= Date.now() - days * 24 * 60 * 60 * 1000
}

function remotive(payload: Json): Job[] {
  return ((payload.jobs || []) as Json[]).map((item) => ({
    id: `remotive:${item.id}`, externalId: String(item.id), source: "remotive" as const,
    title: text(item.title), company: text(item.company_name), url: text(item.url), location: text(item.candidate_required_location),
    workMode: "remote", description: stripHtml(item.description), date: text(item.publication_date), salary: text(item.salary),
    employmentType: text(item.job_type), sourceUrls: [text(item.url)].filter(Boolean),
  }))
}

function remoteOk(payload: unknown): Job[] {
  const rows = Array.isArray(payload) ? payload.filter((item): item is Json => Boolean(item && typeof item === "object" && "position" in item)) : []
  return rows.map((item) => ({
    id: `remoteok:${item.id || item.slug}`, externalId: String(item.id || item.slug || item.url), source: "remoteok" as const,
    title: text(item.position), company: text(item.company), url: text(item.url), location: text(item.location || "Worldwide"), workMode: "remote",
    description: stripHtml(item.description), date: text(item.date), salary: text(item.salary), employmentType: text(item.employment_type),
    sourceUrls: [text(item.url)].filter(Boolean),
  }))
}

function jobicy(payload: Json): Job[] {
  return ((payload.jobs || []) as Json[]).map((item) => ({
    id: `jobicy:${item.id || item.jobSlug}`, externalId: String(item.id || item.jobSlug), source: "jobicy" as const,
    title: text(item.jobTitle), company: text(item.companyName), url: text(item.url || item.jobUrl), location: text(item.jobGeo || item.jobLevel || "Worldwide"),
    workMode: "remote", description: stripHtml(item.jobDescription), date: text(item.pubDate), salary: text(item.annualSalaryMin || item.annualSalaryMax),
    employmentType: text(item.jobType), seniority: text(item.jobLevel), sourceUrls: [text(item.url || item.jobUrl)].filter(Boolean),
  }))
}

function adzuna(payload: Json, country: string): Job[] {
  return ((payload.results || []) as Json[]).map((item) => ({
    id: `adzuna:${country}:${item.id}`, externalId: `${country}:${item.id}`, source: "adzuna" as const,
    title: text(item.title), company: text((item.company as Json | undefined)?.display_name), url: text(item.redirect_url),
    location: text((item.location as Json | undefined)?.display_name), description: stripHtml(item.description), date: text(item.created),
    salary: [item.salary_min, item.salary_max].filter(Boolean).join(" - "), employmentType: text(item.contract_type), sourceUrls: [text(item.redirect_url)].filter(Boolean),
  }))
}

type Board = { company: string; provider: "greenhouse" | "lever" | "ashby"; board: string; enabled?: boolean; sector?: string }

async function boards(): Promise<Board[]> {
  const file = Bun.file(new URL("../../../ats-search/boards.json", import.meta.url))
  const payload = await file.json() as { boards?: Board[] }
  return (payload.boards || []).filter((board) => board.enabled !== false)
}

async function ats(source: Extract<Source, "greenhouse" | "lever" | "ashby">): Promise<Job[]> {
  const selected = (await boards()).filter((board) => board.provider === source)
  const out: Job[] = []
  for (const board of selected) {
    try {
      if (source === "greenhouse") {
        const payload = await request(`https://boards-api.greenhouse.io/v1/boards/${encodeURIComponent(board.board)}/jobs?content=true`) as Json
        for (const item of (payload.jobs || []) as Json[]) out.push({
          id: `greenhouse:${board.board}:${item.id}`, externalId: `${board.board}:${item.id}`, source, title: text(item.title), company: board.company,
          url: text(item.absolute_url), location: text((item.location as Json | undefined)?.name), description: stripHtml(item.content), date: text(item.updated_at),
          sourceUrls: [text(item.absolute_url)].filter(Boolean),
        })
      } else if (source === "lever") {
        const payload = await request(`https://api.lever.co/v0/postings/${encodeURIComponent(board.board)}?mode=json`) as Json[]
        for (const item of payload) out.push({
          id: `lever:${board.board}:${item.id}`, externalId: `${board.board}:${item.id}`, source, title: text(item.text), company: board.company,
          url: text(item.hostedUrl || item.applyUrl), applyUrl: text(item.applyUrl), location: text((item.categories as Json | undefined)?.location),
          description: text(item.descriptionPlain || item.description), employmentType: text((item.categories as Json | undefined)?.commitment),
          sourceUrls: [text(item.hostedUrl || item.applyUrl)].filter(Boolean),
        })
      } else {
        const payload = await request(`https://api.ashbyhq.com/posting-api/job-board/${encodeURIComponent(board.board)}?includeCompensation=true`) as Json
        for (const item of (payload.jobs || []) as Json[]) {
          const description = stripHtml(item.descriptionHtml || item.descriptionPlain)
          out.push({
            id: `ashby:${board.board}:${item.jobUrl || item.id}`, externalId: `${board.board}:${item.jobUrl || item.id}`, source, title: text(item.title), company: board.company,
            url: text(item.jobUrl || item.applyUrl), applyUrl: text(item.applyUrl), location: text(item.location), workMode: declaredWorkMode(item.location, description, item.isRemote),
            description, employmentType: text(item.employmentType), seniority: text(item.seniority), salary: ashbySalary(item.compensation),
            sourceUrls: [text(item.jobUrl || item.applyUrl)].filter(Boolean),
          })
        }
      }
    } catch (error) {
      process.stderr.write(JSON.stringify({ warning: `${source}:${board.company}: ${error instanceof Error ? error.message : String(error)}` }) + "\n")
    }
  }
  return out
}

async function search(source: Source, queries: string[], jobage: number): Promise<{ results: Job[]; meta: Json }> {
  if (source === "remotive") {
    const rows = remotive(await request("https://remotive.com/api/remote-jobs?category=software-dev&limit=100") as Json)
    return { results: rows.filter((job) => matches(job, queries) && isRecent(job, jobage)), meta: { source, remote_only: true } }
  }
  if (source === "remoteok") {
    const rows = remoteOk(await request("https://remoteok.com/api"))
    return { results: rows.filter((job) => matches(job, queries) && isRecent(job, jobage)), meta: { source, remote_only: true } }
  }
  if (source === "jobicy") {
    const rows = jobicy(await request("https://jobicy.com/api/v2/remote-jobs?count=100&industry=dev") as Json)
    return { results: rows.filter((job) => matches(job, queries) && isRecent(job, jobage)), meta: { source, remote_only: true } }
  }
  if (source === "adzuna") {
    const appId = process.env.ADZUNA_APP_ID || ""
    const appKey = process.env.ADZUNA_APP_KEY || ""
    if (!appId || !appKey) return { results: [], meta: { source, skipped: "not configured" } }
    const countries = ["us", "gb", "de", "nl", "ca", "au", "sg"]
    const rows: Job[] = []
    for (const query of queries.length ? queries : ["software engineering manager"]) for (const country of countries) {
      const url = new URL(`https://api.adzuna.com/v1/api/jobs/${country}/search/1`)
      url.searchParams.set("app_id", appId); url.searchParams.set("app_key", appKey); url.searchParams.set("what", query); url.searchParams.set("results_per_page", "20")
      try { rows.push(...adzuna(await request(url.toString()) as Json, country)) } catch (error) { process.stderr.write(JSON.stringify({ warning: `adzuna:${country}: ${error instanceof Error ? error.message : String(error)}` }) + "\n") }
    }
    return { results: rows.filter((job) => isRecent(job, jobage)), meta: { source, countries } }
  }
  const rows = await ats(source)
  return { results: rows.filter((job) => matches(job, queries) && isRecent(job, jobage)), meta: { source, boards_checked: (await boards()).filter((board) => board.provider === source).length } }
}

async function main(): Promise<void> {
  const argv = process.argv.slice(2)
  const command = argv[0]
  const source = value(argv, "--source") as Source
  if (!(["search", "detail"].includes(command) && SOURCES.has(source))) {
    process.stderr.write(JSON.stringify({ error: "usage: <search|detail> --source <remotive|remoteok|jobicy|adzuna|greenhouse|lever|ashby> [--query text] [--id value] [--format json]", code: "BAD_ARG" }) + "\n")
    process.exit(1)
  }
  try {
    const jobage = Math.max(1, Number.parseInt(value(argv, "--jobage", "14"), 10) || 14)
    if (command === "detail") {
      const identifier = value(argv, "--id") || value(argv, "--url")
      const output = await search(source, [], Number.MAX_SAFE_INTEGER)
      const job = output.results.find((item) => item.id === identifier || item.externalId === identifier || item.url === identifier)
      if (!job) throw new Error("posting not found in the current public feed")
      process.stdout.write(JSON.stringify(job) + "\n")
      return
    }
    const output = await search(source, values(argv, "--query"), jobage)
    process.stdout.write(JSON.stringify(output) + "\n")
  } catch (error) {
    process.stderr.write(JSON.stringify({ error: error instanceof Error ? error.message : String(error), code: "API_ERROR" }) + "\n")
    process.exit(1)
  }
}

void main()
