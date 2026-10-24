# WayPointAI
This AI application turns career-skill gaps into a concrete, scheduled roadmap
for the role and experience level a user is targeting.

## Project layout

```
api.py              the API the website talks to (run this)
skills/             what a role needs and what a resume is missing
  role_profiles.py    role profiles built from O*NET
  role_insights.py    O*NET tasks and in-demand technologies per role
  career_pipeline.py  reads a resume and matches its skills
  gap_analyzer.py     turns matches into a ranked gap list
roadmap/            turns a gap list into a dated, prioritized plan (python -m roadmap)
resume/             resume builder: story interview, drafting, wording
data/               the resource catalog, project templates, O*NET role data
web/                the React website (see web/README.md)
docs/               specs and notes
scripts/            data builds, demos and evaluations
tests/              pytest suite (ROADMAP_AI=0 RESUME_AI=0 .venv/bin/python -m pytest -q)
```

## Run the web interface

The interface is a React app in `web/` that talks to a small Python API
(`api.py`). It accepts a PDF or UTF-8 text resume (or typed skills, or
neither) and one or more target tech roles, asks how much time and money the
user has, and shows one roadmap per role: the most important work first, a
dated timeline, source links, and optional items behind a button.

Under the hood, `skills/career_pipeline.py` matches resume text against the role
profiles in `skills/role_profiles.py`, `skills/gap_analyzer.py` calculates the skill gaps,
and `roadmap/` builds the roadmap from the curated catalog. Resume matching is
deterministic and based on explicit mentions of profile skills; it is not a
general-purpose resume parser. See [docs/gap_list_spec.md](docs/gap_list_spec.md)
for the roadmap input format.

1. Install the Python dependencies and start the API (it listens on this computer only):

   ```bash
   python -m pip install -r requirements.txt
   python api.py            # http://127.0.0.1:8000, interactive docs at /docs
   ```

   To skip the optional model-generated tips and use the rule-based roadmap, set
   `ROADMAP_AI=0` before starting it.

2. Start the site (React + Vite; needs [Node.js](https://nodejs.org) LTS). In a second terminal:

   ```bash
   cd web
   npm install              # first time only
   npm run dev              # http://127.0.0.1:5173, updates instantly as you edit
   ```

   For an optimized build, run `npm run build` (output in `web/dist/`). Preview it with
   `npm run preview`, or open the repo in VS Code and click **Go Live**:
   `.vscode/settings.json` points Live Server at `web/dist/`.

See [web/README.md](web/README.md) for how the front end is organized.

## Resume builder and story bank

Open **Resume builder** in the web app to save experience once and reuse it for
different applications. The guided interview asks five short questions: your
role or project, the problem, your contribution, tools, and the outcome. Tools
and outcomes are optional; class projects and volunteering count too. Review
the story before saving it, and edit or delete it later.

Add optional name, contact, headline, and education details, then generate a
general resume or paste a job description to tailor the draft. Relevant saved
stories are prioritized, and each bullet shows its supporting answers. Copy
the draft or download it as a plain-text resume. Job descriptions and profile
details are used for that request and are not saved in the story database.

The optional local resume writer (`Qwen/Qwen3-0.6B`, about 1.2 GB downloaded on
first use) rewrites notes into professional bullets with references
back to the source answers. Checks reject unknown sources, unsupported numeric
results, tool names, and common invented claims; users must still review the
meaning of AI-written text. When AI is disabled, busy, unavailable, or returns
invalid output, the app supplies a grammar-edited draft instead of copying raw
notes. Tools appear separately from accomplishment bullets. Ambiguous time-saved
results prompt a short follow-up without inventing a weekly or monthly timeframe.
Matching recognizes aliases such as PowerBi / Power BI; it is keyword overlap,
not an ATS score. See [docs/resume_builder.md](docs/resume_builder.md).

**Stored locally, never in the cloud.** Stories are kept only in the user's browser,
encrypted with AES-256-GCM under a key derived from a passphrase they choose
(PBKDF2-SHA256, 600,000 iterations). The API stores nothing: the browser sends the
stories a request needs, and they're used in memory. There's no account, so a
forgotten passphrase can't be recovered; **Download encrypted backup** saves a file
that restores the bank in another browser or computer with the same passphrase. The
page's privacy notice lists exactly what is and isn't stored.

Pick a **target role** to see what people in that job do (tasks rated by people who
hold it) and the technologies in demand for it. The role helps rank your stories and
shows which of those technologies your stories cover; it never adds claims. Source:
O*NET 31.0 by USDOL/ETA (CC BY 4.0). O*NET has no machine learning engineer occupation, so
AI/ML Engineer skills come from junior and mid-level ML engineer listings on AI Dev Jobs
(aidevboard.com), read through its public API under its terms; only skill counts are stored.
Nothing is scraped. Details in
[docs/resume_builder.md](docs/resume_builder.md#role-insights-from-onet).

## Roadmap module

`roadmap/` turns a gap list (what a user is missing compared with people in their target role) into a scheduled, concrete roadmap for internship, junior and mid-level candidates in all nine roles. See [docs/roadmap.md](docs/roadmap.md) for setup and design, and [docs/gap_list_spec.md](docs/gap_list_spec.md) for the input and output format.
