# Resume builder

## User flow

1. Open Resume builder and create a story bank for this browser.
2. Answer five questions about one experience: context, problem, personal
   contribution, tools, and outcome. Only the first three are required. A
   qualitative result or unfinished project is valid; metrics are never required.
3. Review the assembled narrative and explicitly save it. Original answers stay
   alongside the narrative so future drafts have specific evidence to draw from.
4. Add more experiences or edit/delete saved stories.
5. Generate a general resume, or paste a job description to prioritize relevant
   stories and contributions. Optional profile details supply the resume header
   and education section. Inspect supporting answers, then copy or download text.

## Implementation

- `resume_api.py` exposes the interview, bank creation, story CRUD, preview, and
  drafting under `/api/resume`.
- `resume_store.py` persists the original answers, narrative, optional organization
  and dates, and timestamps in SQLite. It opens a separate connection per operation.
- `resume_generation.py` ranks saved experiences and assembles grounded drafts,
  optionally asking a local Hugging Face model to rewrite concise bullets with
  source references. `resume_wording.py` supplies conservative grammar editing
  when generation is unavailable.
- `web/src/components/ResumeBuilder.jsx` provides the interview and draft UI beside
  the existing roadmap planner.

The narrative is a deterministic assembly of the reviewed facts, so saving does
not silently replace the preview with different model output. Resume AI can
rewrite text, with answer IDs attached to each bullet. Validation rejects unknown
sources, new numeric values or metric units, unsupported known tools, and common
fabricated scope such as weekly savings, automation, leadership, and eligibility.
Source answers containing sensitive qualifiers or negation use conservative editing.
These checks are not a semantic proof of every claim: users must review the draft
against its original answers. Original stories are never overwritten by rewriting.

The fallback corrects common grammar, spelling, capitalization, and action-verb
tense, omits interview labels, and separates tools from achievements. It cannot
fully rewrite arbitrary prose. The UI calls this an **Edited draft**, distinguishes
model timeout/busy/invalid-output failures, and suggests clarifying the timeframe
for time savings without assuming it.

Resume text is generated on request rather than stored. Saved experience is the
reusable source of truth; a new job description creates a new draft from those facts.

## Local data and access

The default database is `.local/story-bank.sqlite3`, created lazily with
owner-only file permissions. Set `WAYPOINT_STORY_DB` to choose a different path.
Use a persistent filesystem location when restarting the API; an ephemeral
container filesystem will not retain stories after replacement.

`POST /api/resume/library` returns a random bearer key. The browser stores that
key scoped to the API URL; SQLite stores only its SHA-256 digest. Story reads,
updates, deletes, and generation require the key and scope queries to its bank.
Responses under `/api/resume/` have `Cache-Control: no-store`. Uploaded roadmap
resumes continue to be read in memory without being added to the story bank.

Anyone holding the browser's key can access that bank. There is no login, key
recovery, encryption at rest, or cross-device account synchronization. Clearing
browser storage loses access but does not delete server records. Before deploying
as a shared hosted service, add real account authentication/recovery and associate
story ownership with authenticated accounts; the current API binds to localhost.

## Configuration and tests

`RESUME_AI=0` disables model assistance for resumes. When unset, resume assistance
follows `ROADMAP_AI`. `RESUME_MODEL_ID` optionally selects a separate Hugging Face
instruction-following model for resume rewriting; the default is
`Qwen/Qwen3-0.6B`, with thinking disabled for concise drafting. The roadmap model
is configured separately. The first use downloads about 1.2 GB of model weights. The existing roadmap device settings still apply. Changing the
model may download its weights on first use. No external model API or new database
dependency is required.

The bundled `AnusmitaRC21/smolified-resume-analyzer` is fine-tuned for analysis. In a
live check it returned extracted details and advice instead of the requested rewrite.
Such output is rejected, and the edited fallback is shown. Resume rewriting therefore uses the separate Qwen writer by default. The interface
never labels fully fallback text as AI rewritten. Valid AI bullets can be combined
with a conservatively edited original outcome if the model omits it. Resume generation is bounded to a 45-second request timeout.

Run the automated suite with:

```bash
ROADMAP_AI=0 RESUME_AI=0 .venv/bin/python -m pytest -q
```

Tests use temporary SQLite databases and fake model outputs. They cover persistence,
ownership isolation, interview validation, missing outcomes, source-backed drafting,
and the existing roadmap behavior without downloading model weights.
