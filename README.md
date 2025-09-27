# Job Bot

Automated job search, scoring, and tracking pipeline built with **Python**, **Typer**, **Adzuna API**, **OpenAI**, and **Google Sheets**.

This project helps me streamline my job search by fetching job postings, enriching them with AI evaluations, checking for contacts at relevant companies, and writing results into a central Google Sheet for tracking.

---

## 🚀 Features

- **Adzuna API integration**
  - Query by role, location, salary, recency, and more.
  - Automatically normalizes Adzuna’s JSON into a clean schema.

- **CLI built with Typer**
  - `new-from-adzuna` — fetch new jobs, filter out duplicates, score them with AI, and append to Google Sheets.
  - `llm_test` — quick smoke test of AI evaluation pipeline.
  - `sheets_debug`, `jobs_headers`, etc. for debugging.

- **AI-powered job evaluation (OpenAI)**
  - Returns structured JSON with:
    - `fit_score` (0–10) — job alignment with my background.
    - `fit_notes` — rationale for the score.
    - `company_summary` — concise company blurb w/ size or funding.
    - `job_summary` — 200–250 char description of responsibilities.

- **Fuzzy contact matching (RapidFuzz)**
  - Matches job company names against my exported LinkedIn contacts.
  - Handles variations like “Microsoft” vs “Microsoft Corp”.

- **Google Sheets integration**
  - Jobs are persisted into a spreadsheet for easy tracking.
  - Avoids duplicate entries by checking Adzuna IDs.

---

## 🛠️ Tech Stack

- **Python 3.10+**
- [Typer](https://typer.tiangolo.com/) — intuitive CLI framework
- [RapidFuzz](https://maxbachmann.github.io/RapidFuzz/) — fast fuzzy string matching
- [gspread](https://github.com/burnash/gspread) — Google Sheets API client
- [python-dotenv](https://github.com/theskumar/python-dotenv) — env var management
- [OpenAI](https://pypi.org/project/openai/) — AI-powered evaluation
- Adzuna API — job search data source

---

## 📦 Installation

Clone the repo and install dependencies:

```bash
git clone https://github.com/<your-username>/job-bot.git
cd job-bot
pip install -r requirements.txt
```

Set up your `.env` with API credentials:

```env
ADZUNA_APP_ID=your-adzuna-id
ADZUNA_APP_KEY=your-adzuna-key
OPENAI_API_KEY=your-openai-key
```

Authenticate Google Sheets with a service account JSON key, saved as service_account_jobbot.json.

---

## ⚡ Usage

Fetch new jobs:
```python -m jobs.cli new-from-adzuna "analytics engineer" --limit 20 --score
```
Preview without writing to Sheets:
```python -m jobs.cli new-from-adzuna "data engineer" --limit 5 --score --dry-run
```
Run a quick AI evaluation test:
```python -m jobs.cli llm_test
```
---

## 🧠 What I Learned

This was my first major project building a CLI in Python:

- **Typer** — my first time using it; intuitive and made CLI UX a lot cleaner and more snazzy
- **Migration from n8n** — I originally hacked this together in a no-code tool (n8n), but porting it to Python gave me more control, transparency, and maintainability
- **APIs & data pipelines** — learned how to normalize inconsistent API responses, design clean schemas, and connect multiple APIs (Adzuna, OpenAI, Google Sheets)
- **Error handling** — built in guards for bad JSON from LLMs, missing IDs, and Google Sheets edge cases
- **AI-assisted coding** — I leaned heavily on AI tools like Cursor and ChatGPT, but not just for “vibe coding.” I researched trade-offs (e.g. regex vs fuzzy matching, prompt length vs cost, rate limiting strategies) and made deliberate design decisions.
- **Architectural trade-offs** — simplicity (e.g. sleep-based rate limiting) vs sophistication (full retry logic, parallelization)

---

## 🔮 Future Improvements

- Support additional job boards (e.g. LinkedIn, Indeed)?
- Smarter AI prompts for richer summaries.
- More robust scheduling/automation layer (cron, Airflow, etc.).
- Expand fuzzy contact matching to include affiliated companies, not just fuzzy matches