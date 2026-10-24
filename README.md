# WayPointAI
This AI application turns career-skill gaps into a concrete, scheduled roadmap
for the role and experience level a user is targeting.

## Run the web interface

The interface is a React app in `web/` that talks to a small Python API
(`api.py`). It accepts a PDF or UTF-8 text resume (or typed skills, or
neither) and one or more target tech roles, asks how much time and money the
user has, and shows one roadmap per role: the most important work first, a
dated timeline, source links, and optional items behind a button.

Under the hood, `career_pipeline.py` matches resume text against the role
profiles in `role_profiles.py`, `gap_analyzer.py` calculates the skill gaps,
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

2. Open the folder in VS Code and click **Go Live** (Live Server extension).
   `.vscode/settings.json` points Live Server at `web/` on port 5500, so the app
   opens at http://127.0.0.1:5500 and reloads whenever you save a file.

There's no build step and nothing to install for the front end. See
[web/README.md](web/README.md) for how it's organized.

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

Stories persist in `.local/story-bank.sqlite3` (ignored by Git); override this
with `WAYPOINT_STORY_DB`. Each browser retains a random access key and can only
access its own bank. This is a local MVP, with no account sign-in, account
recovery, or cross-device sync. Clearing browser storage loses the access key;
it does not delete the saved stories. Keep the API on localhost as configured.

The older Gradio interface (`python app.py`) still works while the team
switches over.

## Roadmap module

`roadmap/` turns a gap list (what a user is missing compared with people in their target role) into a scheduled, concrete roadmap for internship, junior and mid-level candidates in all nine roles. See [docs/roadmap.md](docs/roadmap.md) for setup and design, and [docs/gap_list_spec.md](docs/gap_list_spec.md) for the input and output format.
