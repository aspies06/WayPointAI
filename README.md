# WayPointAI
This AI application turns career-skill gaps into a concrete, scheduled roadmap
for the role and experience level a user is targeting.

## Run the web interface

The Gradio interface accepts a PDF or UTF-8 text resume and one or more target
tech roles. It matches resume text against the selected role profiles in
`role_profiles.py`, uses `gap_analyzer.py` to calculate skill gaps, and generates
a role-specific roadmap using the curated catalog and planner in `roadmap/`.
Resume matching is deterministic and based on explicit mentions of profile
skills; it is not a general-purpose resume parser.

Roadmap preferences include experience level, years of relevant experience,
weekly study time, target timeline, budget, and optional background context.
See [docs/gap_list_spec.md](docs/gap_list_spec.md) for the roadmap input format.

Install dependencies and start the app:

```bash
python -m pip install -r requirements.txt
python app.py
```

To skip optional model-generated tips and use the rule-based roadmap, set
`ROADMAP_AI=0` before starting the app.

## Roadmap module

`roadmap/` turns a gap list (what a user is missing compared with people in their target role) into a scheduled, concrete roadmap for internship, junior and mid-level candidates in all nine roles. See [docs/roadmap.md](docs/roadmap.md) for setup and design, and [docs/gap_list_spec.md](docs/gap_list_spec.md) for the input and output format.
