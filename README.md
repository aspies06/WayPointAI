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

The older Gradio interface (`python app.py`) still works while the team
switches over.

## Roadmap module

`roadmap/` turns a gap list (what a user is missing compared with people in their target role) into a scheduled, concrete roadmap for internship, junior and mid-level candidates in all nine roles. See [docs/roadmap.md](docs/roadmap.md) for setup and design, and [docs/gap_list_spec.md](docs/gap_list_spec.md) for the input and output format.
