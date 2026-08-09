import { describe, expect, test } from "bun:test"
import { parserForTest, SOURCE_REGISTRY } from "../src/cli"

describe("shared global-source parsers", () => {
  test("registers each requested source with an explicit collection policy", () => {
    for (const source of ["highfive", "remotive", "eztrackr", "hubstaff", "remotewoman", "wellfound", "weworkremotely", "workwave", "aijobs", "toptal", "flexjobs", "jsremotely", "remoteok"] as const) {
      expect(SOURCE_REGISTRY[source]).toBeDefined()
    }
    expect(SOURCE_REGISTRY.wellfound.enabledByDefault).toBe(false)
    expect(SOURCE_REGISTRY.flexjobs.reason).toContain("public")
  })

  test("parses an RSS item without retaining markup in the description", () => {
    const jobs = parserForTest.weWorkRemotely(`<rss><item><title>Example: Staff Engineer</title><link>https://example.test/jobs/1</link><region>Anywhere in the World</region><description><![CDATA[<p>Build <strong>reliable</strong> systems.</p>]]></description><pubDate>Sun, 09 Aug 2026 07:30:40 +0000</pubDate><type>Full-Time</type></item></rss>`)
    expect(jobs).toHaveLength(1)
    expect(jobs[0]).toMatchObject({ company: "Example", title: "Staff Engineer", workMode: "remote", employmentType: "Full-Time" })
    expect(jobs[0].description).toBe("Build reliable systems.")
  })

  test("parses Rails UJS cards as data without evaluating the response", () => {
    const jobs = parserForTest.hubstaff(`$('#results').html("<div class=\\"search-result\\"><a class=\\"name margin-right-10\\" href=\\"/jobs/staff-engineer\\">Staff Engineer<\\/a><div class=\\"job-company\\"><a href=\\"https://company.test\\">Example Co<\\/a><span class=\\"location text-success\\">Remote, Singapore<\\/span><\\/div><\\/div>")`)
    expect(jobs).toHaveLength(1)
    expect(jobs[0]).toMatchObject({ company: "Example Co", title: "Staff Engineer", location: "Remote, Singapore", url: "https://hubstafftalent.net/jobs/staff-engineer" })
  })

  test("does not turn Hubstaff company headquarters into a job restriction", () => {
    const jobs = parserForTest.hubstaff(`$('#results').html("<div class=\\"search-result\\"><a class=\\"name\\" href=\\"/jobs/staff-engineer\\">Staff Engineer<\\/a><div class=\\"job-company\\"><a>Example Co<\\/a><span class=\\"location\\">HQ: California, United States<\\/span><\\/div><\\/div>")`)
    expect(jobs).toHaveLength(1)
    expect(jobs[0]).toMatchObject({ location: "Remote", companyLocation: "HQ: California, United States" })
  })

  test("drops malformed JavaScript.jobs cards rather than emitting partial jobs", () => {
    const valid = `<a href="https://javascript.jobs/job/staff-engineer" class="jobcardStyle1"><div class="tw-text-lg">Staff Engineer</div><span class="tw-card-title">Example Co</span><span class="tw-bg-[#E7F6EA]">Full Time</span>`
    expect(parserForTest.jsRemotely(`${valid}<a href="https://javascript.jobs/job/broken"`).map((job) => job.title)).toEqual(["Staff Engineer"])
  })

  test("ignores invalid numeric HTML entities without throwing", () => {
    expect(() => parserForTest.decodeHtml("Broken &#99999999; entity")).not.toThrow()
    expect(parserForTest.decodeHtml("Broken &#99999999; entity")).toBe("Broken  entity")
  })
})
