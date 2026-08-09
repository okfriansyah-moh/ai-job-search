#!/usr/bin/env bun

type Json = Record<string, unknown>
type Source =
  | "remotive" | "remoteok" | "jobicy" | "adzuna" | "greenhouse" | "lever" | "ashby"
  | "highfive" | "eztrackr" | "hubstaff" | "remotewoman" | "wellfound"
  | "weworkremotely" | "workwave" | "aijobs" | "toptal" | "flexjobs" | "jsremotely"

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
  companyLocation?: string
  source: Source
  externalId: string
  sourceUrls: string[]
}

type SourceSpec = {
  label: string
  mode: "public-api" | "public-feed" | "public-html" | "employer-board" | "manual-only"
  enabledByDefault: boolean
  reason?: string
}

/**
 * Every requested source has an explicit registry entry. Sources without a
 * stable public listing contract stay visible but deliberately disabled: a
 * successful empty result must never masquerade as a working scraper.
 */
export const SOURCE_REGISTRY: Record<Source, SourceSpec> = {
  remotive: { label: "Remotive", mode: "public-api", enabledByDefault: true },
  remoteok: { label: "Remote OK", mode: "public-api", enabledByDefault: true },
  jobicy: { label: "Jobicy", mode: "public-api", enabledByDefault: false, reason: "contract and reuse terms need revalidation" },
  adzuna: { label: "Adzuna", mode: "public-api", enabledByDefault: true },
  greenhouse: { label: "Greenhouse", mode: "public-api", enabledByDefault: true },
  lever: { label: "Lever", mode: "public-api", enabledByDefault: true },
  ashby: { label: "Ashby", mode: "public-api", enabledByDefault: true },
  highfive: { label: "Highfive Global", mode: "manual-only", enabledByDefault: false, reason: "public WordPress API exposes talent profiles, not job postings" },
  eztrackr: { label: "Eztrackr", mode: "manual-only", enabledByDefault: false, reason: "job-application tracker, not a public job-board feed" },
  hubstaff: { label: "Hubstaff Talent", mode: "public-html", enabledByDefault: true },
  remotewoman: { label: "Remote Woman", mode: "public-api", enabledByDefault: true },
  wellfound: { label: "Wellfound", mode: "manual-only", enabledByDefault: false, reason: "no public job-search API; automated access is blocked" },
  weworkremotely: { label: "We Work Remotely", mode: "public-feed", enabledByDefault: true },
  workwave: { label: "WorkWave", mode: "employer-board", enabledByDefault: true },
  aijobs: { label: "AI Jobs", mode: "manual-only", enabledByDefault: false, reason: "the supplied domain does not currently serve a job board" },
  toptal: { label: "Toptal", mode: "manual-only", enabledByDefault: false, reason: "no public candidate job feed" },
  flexjobs: { label: "FlexJobs", mode: "manual-only", enabledByDefault: false, reason: "subscription service with no public search API" },
  jsremotely: { label: "JS Remotely", mode: "public-html", enabledByDefault: true },
}

const SOURCES = new Set<Source>(Object.keys(SOURCE_REGISTRY) as Source[])
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
  return String(value || "").replace(/<br\s*\/?>/gi, "\n").replace(/<\/(p|li|div|h\d)>/gi, "\n").replace(/<[^>]+>/g, " ").replace(/[ \t\u00a0]+/g, " ").replace(/ *\n */g, "\n").replace(/\n{3,}/g, "\n\n").trim()
}

function decodeHtml(value: unknown): string {
  return String(value || "")
    .replace(/&#(x[\da-f]+|\d+);/gi, (_match, encoded: string) => {
      const code = encoded.toLowerCase().startsWith("x") ? Number.parseInt(encoded.slice(1), 16) : Number.parseInt(encoded, 10)
      if (!Number.isInteger(code) || code < 0 || code > 0x10ffff) return ""
      return String.fromCodePoint(code)
    })
    .replace(/&nbsp;/gi, " ").replace(/&amp;/gi, "&").replace(/&quot;/gi, '"').replace(/&#39;|&apos;/gi, "'")
    .replace(/&ndash;/gi, "–").replace(/&mdash;/gi, "—")
    .replace(/&lt;/gi, "<").replace(/&gt;/gi, ">")
}

function absoluteUrl(base: string, value: unknown): string {
  const candidate = decodeHtml(value).trim()
  if (!candidate) return ""
  try { return new URL(candidate, base).toString() } catch { return "" }
}

function xml(value: string, tag: string): string {
  const match = value.match(new RegExp(`<${tag}(?:\\s[^>]*)?>([\\s\\S]*?)</${tag}>`, "i"))
  return match ? decodeHtml(stripHtml(match[1])) : ""
}

function xmlCdata(value: string, tag: string): string {
  const raw = xml(value, tag)
  return stripHtml(raw.replace(/^<!\[CDATA\[|\]\]>$/g, "")).trim()
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

async function fetchResponse(url: string, headers: Record<string, string> = {}): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const response = await fetch(url, { headers: { "User-Agent": "ai-job-search/1.0 (personal job search)", ...headers }, signal: controller.signal })
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
    return response
  } finally {
    clearTimeout(timer)
  }
}

async function request(url: string): Promise<unknown> {
  return (await fetchResponse(url, { Accept: "application/json" })).json()
}

async function requestText(url: string, headers: Record<string, string> = {}): Promise<string> {
  return (await fetchResponse(url, { Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", ...headers })).text()
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

function weWorkRemotely(feed: string): Job[] {
  return (feed.match(/<item>[\s\S]*?<\/item>/gi) || []).map((item) => {
    const title = xmlCdata(item, "title")
    const [company = "", ...rest] = title.split(/:\s*/)
    const url = xmlCdata(item, "link")
    const location = xmlCdata(item, "region") || xmlCdata(item, "country") || "Worldwide"
    return {
      id: `weworkremotely:${url || title}`, externalId: url || title, source: "weworkremotely" as const,
      title: rest.join(": ").trim() || title, company: company.trim(), url, location, workMode: "remote",
      description: xmlCdata(item, "description"), date: xmlCdata(item, "pubDate"), employmentType: xmlCdata(item, "type"),
      sourceUrls: [url].filter(Boolean),
    }
  }).filter((job) => Boolean(job.title && job.company && job.url))
}

function remoteWoman(payload: Json[]): Job[] {
  return payload.map((item) => {
    const meta = (item.meta || {}) as Json
    const url = text(item.link)
    const description = decodeHtml(stripHtml((item.content as Json | undefined)?.rendered))
    return {
      id: `remotewoman:${item.id}`, externalId: String(item.id || url), source: "remotewoman" as const,
      title: decodeHtml(stripHtml((item.title as Json | undefined)?.rendered)), company: decodeHtml(text(meta._company_name)), url,
      applyUrl: text(meta._application), location: text(meta._job_location || "Worldwide"), workMode: "remote",
      description, date: text(item.date), salary: text(meta._job_salary), sourceUrls: [url].filter(Boolean),
    }
  }).filter((job) => Boolean(job.title && job.company && job.url))
}

/** Rails UJS returns an escaped HTML fragment, never execute it. */
function hubstaff(html: string): Job[] {
  const decoded = decodeHtml(html.replace(/\\\//g, "/").replace(/\\"/g, '"').replace(/\\n/g, " "))
  return decoded.split(/<div\s+class=["']search-result["'][^>]*>/i).slice(1).map((card) => {
    const posting = /<a[^>]*class=["'][^"']*\bname\b[^"']*["'][^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i.exec(card)
    const company = /class=["']job-company["'][^>]*>[\s\S]*?<a[^>]*>([\s\S]*?)<\/a>/i.exec(card)?.[1] || ""
    const location = /class=["'][^"']*\blocation\b[^"']*["'][^>]*>([\s\S]*?)<\/span>/i.exec(card)?.[1] || "Remote"
    const url = absoluteUrl("https://hubstafftalent.net", posting?.[1])
    const title = stripHtml(posting?.[2])
    const rawLocation = text(location)
    // Hubstaff renders company headquarters as "HQ: …" in the same visual
    // slot as a location.  It is not an applicant eligibility restriction.
    // Keep it separately and retain the board's remote-work contract for the
    // job location, so downstream taxonomy cannot falsely label it US-only.
    const companyLocation = /^hq\s*:/i.test(rawLocation) ? rawLocation : ""
    const jobLocation = companyLocation ? "Remote" : rawLocation || "Remote"
    return {
      id: `hubstaff:${url}`, externalId: url, source: "hubstaff" as const, title, company: text(company), url,
      location: jobLocation, companyLocation, workMode: "remote", description: "", sourceUrls: [url].filter(Boolean),
    }
  }).filter((job) => Boolean(job.title && job.company && job.url))
}

function jsRemotely(html: string): Job[] {
  const cards = html.split(/<a\s+href=["']https:\/\/javascript\.jobs\/job\//i).slice(1)
  return cards.map((card) => {
    const url = absoluteUrl("https://javascript.jobs", `https://javascript.jobs/job/${card.split(/["']/)[0]}`)
    const title = decodeHtml((/tw-text-lg[^>]*>\s*([\s\S]*?)\s*<\/div>/i.exec(card)?.[1] || "").replace(/<[^>]+>/g, " "))
    const company = decodeHtml(/tw-card-title[^>]*>\s*([\s\S]*?)\s*<\/span>/i.exec(card)?.[1] || "")
    const employmentType = decodeHtml(/tw-bg-\[#E7F6EA\][^>]*>\s*([\s\S]*?)\s*<\/span>/i.exec(card)?.[1] || "")
    const posted = decodeHtml(/tw-text-\[#767F8C\][^>]*>\s*([\d]+[HDWM])\s*</i.exec(card)?.[1] || "")
    return {
      id: `jsremotely:${url}`, externalId: url, source: "jsremotely" as const, title: text(title), company: text(company), url,
      location: "Remote", workMode: "remote", employmentType: text(employmentType), date: posted, sourceUrls: [url].filter(Boolean),
    }
  }).filter((job) => Boolean(job.title && job.company && job.url))
}

function workWave(payload: Json[]): Job[] {
  return payload.map((item) => {
    const categories = (item.categories || {}) as Json
    const url = text(item.hostedUrl || item.applyUrl)
    const description = text(item.descriptionPlain || item.description)
    return {
      id: `workwave:${item.id}`, externalId: String(item.id || url), source: "workwave" as const,
      title: text(item.text), company: "WorkWave", url, applyUrl: text(item.applyUrl), location: text(categories.location),
      workMode: declaredWorkMode(categories.location, description, item.workplaceType === "remote"), description,
      employmentType: text(categories.commitment), sourceUrls: [url].filter(Boolean),
    }
  }).filter((job) => Boolean(job.title && job.url))
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
  const spec = SOURCE_REGISTRY[source]
  if (!spec.enabledByDefault) return { results: [], meta: { source, skipped: spec.reason || "disabled" } }
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
  if (source === "weworkremotely") {
    const rows = weWorkRemotely(await requestText("https://weworkremotely.com/remote-jobs.rss"))
    return { results: rows.filter((job) => matches(job, queries) && isRecent(job, jobage)), meta: { source, remote_only: true } }
  }
  if (source === "remotewoman") {
    const rows = remoteWoman(await request("https://remotewoman.com/wp-json/wp/v2/job-listings?per_page=100&orderby=date&order=desc") as Json[])
    return { results: rows.filter((job) => matches(job, queries) && isRecent(job, jobage)), meta: { source, remote_only: true } }
  }
  if (source === "hubstaff") {
    const searchQuery = queries[0] || "software engineering"
    const url = new URL("https://hubstafftalent.net/search/jobs")
    url.searchParams.set("search[keywords]", searchQuery)
    url.searchParams.set("page", "1")
    const rows = hubstaff(await requestText(url.toString(), { Accept: "text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest" }))
    return { results: rows.filter((job) => matches(job, queries)), meta: { source, remote_only: true, parser: "rails-ujs" } }
  }
  if (source === "jsremotely") {
    const url = new URL("https://javascript.jobs/remote")
    if (queries[0]) url.searchParams.set("keyword", queries[0])
    const rows = jsRemotely(await requestText(url.toString()))
    return { results: rows.filter((job) => matches(job, queries)), meta: { source, remote_only: true, canonical_site: "javascript.jobs" } }
  }
  if (source === "workwave") {
    const rows = workWave(await request("https://api.lever.co/v0/postings/workwave?mode=json") as Json[])
    return { results: rows.filter((job) => matches(job, queries) && isRecent(job, jobage)), meta: { source, employer: "WorkWave" } }
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
  if (source === "greenhouse" || source === "lever" || source === "ashby") {
    const rows = await ats(source)
    return { results: rows.filter((job) => matches(job, queries) && isRecent(job, jobage)), meta: { source, boards_checked: (await boards()).filter((board) => board.provider === source).length } }
  }
  throw new Error(`no public adapter is configured for ${source}`)
}

export const parserForTest = { decodeHtml, weWorkRemotely, remoteWoman, hubstaff, jsRemotely, workWave }

async function main(): Promise<void> {
  const argv = process.argv.slice(2)
  const command = argv[0]
  const source = value(argv, "--source") as Source
  if (!(["search", "detail"].includes(command) && SOURCES.has(source))) {
    process.stderr.write(JSON.stringify({ error: `usage: <search|detail> --source <${[...SOURCES].join("|")}> [--query text] [--id value] [--format json]`, code: "BAD_ARG" }) + "\n")
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
    const limit = Math.max(1, Math.min(100, Number.parseInt(value(argv, "--limit", "100"), 10) || 100))
    output.results = output.results.slice(0, limit)
    process.stdout.write(JSON.stringify(output) + "\n")
  } catch (error) {
    process.stderr.write(JSON.stringify({ error: error instanceof Error ? error.message : String(error), code: "API_ERROR" }) + "\n")
    process.exit(1)
  }
}

if (import.meta.main) void main()
