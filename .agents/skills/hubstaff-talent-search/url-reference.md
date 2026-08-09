# Hubstaff Talent source contract

- Search: `GET https://hubstafftalent.net/search/jobs?search[keywords]=<query>&page=1`
- Required headers: `Accept: text/javascript, */*; q=0.01` and `X-Requested-With: XMLHttpRequest`
- Parser anchors: one `div.search-result` per card, `a.name` for the title/link, `.job-company` for company, `.location` for location.
- The response is escaped JavaScript containing HTML. It is decoded as text only and is never evaluated.
