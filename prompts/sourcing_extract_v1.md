Using web search, find up to {n} candidate judges for an AI safety hackathon.

Topic: {topic}
Tracks: {tracks}
Description: {description}

Search using these queries (and refine as needed):
{queries}

For each candidate record: name, affiliation, relevance_signal (their specific
paper, project, or role that makes them qualified), source_urls (pages you actually
fetched), and evidence_snippet (a short quote from a fetched page supporting the
relevance claim).

HARD CONTACT POLICY:
- NEVER output an email address unless it literally appears on a page you fetched.
- contact.type must be one of: public_email, webform, linkedin, profile_page, unknown.
- public_email additionally requires source_urls and an evidence_snippet quoting
  where the address appeared. When in doubt, use type "unknown" with an empty value.

Respond with JSON only:
{"judges": [{"name": "...", "affiliation": "...", "relevance_signal": "...",
  "contact": {"type": "unknown", "value": "", "verified": false},
  "source_urls": ["..."], "evidence_snippet": "...", "rank": 0}]}
