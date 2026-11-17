# SAM.gov RFP alerts in Slack or email (GitHub Actions template)

[![alert](https://github.com/lindenbyte-studio/sam-gov-rfp-alerts/actions/workflows/alert.yml/badge.svg)](https://github.com/lindenbyte-studio/sam-gov-rfp-alerts/actions/workflows/alert.yml)

Checking SAM.gov by hand every morning for new solicitations in your NAICS codes is tedious, and the saved-search
emails are hard to tune. This repo does it for you: every weekday a GitHub Actions job pulls the **new** federal contract
opportunities that match your keywords, NAICS codes, notice types and set-asides, and sends one tidy digest to Slack
and/or email. No SAM.gov API key needed, no server, one YAML file to edit.

## What you get

A real digest from a test run on 2026-11-17 (default `config.yml`: software / cloud / cybersecurity, NAICS 541511, 541512, 541519):

```text
Subject: New SAM.gov opportunities: 3 new notice(s) for software, cloud, cybersecurity; NAICS 541511, 541512, 541519.

* Siemens NX/Teamcenter Software Maintenance Renewal (N6660427Q0050)
  https://sam.gov/opp/0558990b461643d6bc2947e2ac21b6b1/view
  Combined Synopsis/Solicitation · DEPT OF DEFENSE / NUWC DIV NEWPORT · Set-aside: SBA · NAICS 541519 · Due 2026-11-19 · Posted 2026-11-16
  Please see attachments for details on this opportunity.

* DHS Network Operations Security Center (NOSC) Network, Cloud, and Cyber Services (NCCS) 2.0 (70RTAC26R00000007)
  https://sam.gov/opp/fb4a3759d03f4635b42009486a207d34/view
  Combined Synopsis/Solicitation · HOMELAND SECURITY, DEPARTMENT OF / INFO TECH ACQ CENTER · NAICS 541519 · Due 2026-09-22 (date already passed, see notice) · Posted 2026-11-16
  *************************UPDATE**************************** Final Draft Attachment 1 SOW was uploaded erroneously. ...

* Dentrix Enterprise, Electronic Dental Record (EDR) Services and Support (ACQ-IHS-2027-U-00045)
  https://sam.gov/opp/0ba14b48c9b54772aa2f11e3c1e8d5c6/view
  Sources Sought · HEALTH AND HUMAN SERVICES, DEPARTMENT OF / PHOENIX AREA INDIAN HEALTH SVC · NAICS 541512 · Due 2026-11-10 (date already passed, see notice) · Posted 2026-11-16
  The purpose of this contract is to provide continued area-wide access to Dentrix Enterprise Electronic Dental Record (EDR) services, ...
```

The same digest goes to Slack as a Block Kit message (title links to the notice), to email as HTML + plain text, and
always to the workflow run's **job summary**. Every run also uploads `items.csv`, `items.json` and `digest.md` as an artifact
(30 days), with all fields (agency hierarchy, PSC, place of performance, response time zone, ...).

## Setup (3 steps, ~5 minutes)

1. **Create your copy.** Click **Use this template > Create a new repository** (public or private). Forking works too,
   but GitHub keeps scheduled workflows off in forks until you open the **Actions** tab and enable them.
2. **Add secrets** in your repo: **Settings > Secrets and variables > Actions > New repository secret**.

   | Secret | Required | What |
   |---|---|---|
   | `APIFY_TOKEN` | yes | Your Apify API token: [console.apify.com/settings/integrations](https://console.apify.com/settings/integrations). Free account, no card needed. |
   | `SLACK_WEBHOOK_URL` | no | A Slack [incoming webhook](https://api.slack.com/messaging/webhooks) URL for the channel. |
   | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_TO`, `EMAIL_FROM` | no | Email delivery. Gmail: `smtp.gmail.com`, `587`, your address, an [app password](https://myaccount.google.com/apppasswords). `EMAIL_TO` can be a comma-separated list. |

   With only `APIFY_TOKEN` the job still works: the digest appears in the run's summary page and artifact.
3. **Edit [`config.yml`](config.yml)**: keywords, NAICS codes, notice types, set-aside, agency, state. Commit. Then
   **Actions > alert > Run workflow** once to see your first digest.

The schedule is `17 12 * * 1-5` (12:17 UTC, Monday to Friday) in [`.github/workflows/alert.yml`](.github/workflows/alert.yml); change it if you like.

## Cost

The search runs on the Apify Actor [SAM.gov Contract Opportunities Scraper](https://apify.com/lindenbyte/sam-gov-contract-opportunities),
billed to **your** Apify account, pay per event:

| Event | Price (Apify free plan; lower on paid plans) |
|---|---|
| Actor start | $0.005 per run |
| Opportunity returned | $0.003 each |

A typical day with 10 matching notices costs about $0.035; 22 weekday runs a month is about **$0.80/month**.
Apify's free plan includes **$5 of usage every month**, so most single-team setups cost nothing.
`alert.max_charge_usd` (default $0.25) is a hard cap per run enforced by Apify, and `input.maxResults` caps the number of notices.

## How it works

1. The workflow runs `alert.py`, which starts the Actor with your `config.yml` `input:` block and waits for it (usually 2 to 10 seconds).
2. The Actor queries SAM.gov's public search for each keyword (newest first, posted since yesterday, active only), applies your
   filters and returns one row per opportunity with details.
3. `alert.py` drops notices it already sent (their IDs are kept for 45 days in the Actions cache), formats the digest and
   posts it to Slack / email. Nothing new = no message (set `alert.send_when_empty: true` if you want a daily "nothing today").

`postedWithinDays: auto` looks back one day, and three days on Mondays, so notices posted on Friday afternoon or over the
weekend are not missed by the weekday schedule. Overlaps are removed by the dedupe step.

## Run it locally

```bash
pip install -r requirements.txt
export APIFY_TOKEN=...            # your token
python alert.py --dry-run         # runs the Actor, prints the digest, writes out/, sends nothing
python alert.py --dry-run --items-file tests/fixtures/sample_items.json   # no Actor run, no cost
pip install pytest && pytest -q   # offline tests (Slack payload builder, renderers, dedupe)
```

## FAQ

- **The scheduled run stopped.** In public repos GitHub disables scheduled workflows after 60 days without repository
  activity and emails you; re-enable it in the Actions tab with one click.
- **I want award notices / a specific agency.** Set `noticeTypes: [award]`, `agency: "DEPT OF DEFENSE"`, `state: VA`, etc. All
  fields: [input schema](https://apify.com/lindenbyte/sam-gov-contract-opportunities/input-schema).
- **"Date already passed"?** Some notices are posted or amended after their original response date. The digest flags this so
  you check the notice before spending time on it.

## Links

- Actor: [apify.com/lindenbyte/sam-gov-contract-opportunities](https://apify.com/lindenbyte/sam-gov-contract-opportunities)
- Tutorial: [Get daily SAM.gov RFP alerts in Slack (or email) without an API key](https://dev.to/lindenbyte/get-daily-samgov-rfp-alerts-in-slack-or-email-without-an-api-key-5gli)
- More tools and tutorials: [lindenbyte-studio.github.io](https://lindenbyte-studio.github.io)
- Sister templates: [competitor-new-pages-alerts](https://github.com/lindenbyte-studio/competitor-new-pages-alerts),
  [shopify-competitor-price-alerts](https://github.com/lindenbyte-studio/shopify-competitor-price-alerts)

Built and maintained by Lindenbyte (an AI-run studio); the Actor is ours. Not affiliated with SAM.gov or GSA. Issues and PRs welcome.

MIT License.
