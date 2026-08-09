# Remote Woman source contract

- Feed: `GET https://remotewoman.com/wp-json/wp/v2/job-listings?per_page=100&orderby=date&order=desc`
- Fields: `id`, `title.rendered`, `link`, `content.rendered`, `date`, and `meta._company_name`, `_job_location`, `_application`.
- The scraper preserves the board listing as `url` and the employer apply destination as `applyUrl`.
