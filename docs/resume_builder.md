# Resume builder

## User flow

1. Open Resume builder, agree to keep stories in this browser, and choose a passphrase.
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

- `resume/api.py` exposes the interview questions, story preview, role insights and
  drafting under `/api/resume`. It stores nothing; drafting takes the stories in the request.
- `web/src/lib/storyVault.js` keeps the story bank (answers, narrative, optional organization
  and dates, timestamps) encrypted in the browser's IndexedDB.
- `resume/store.py` is the earlier server-side SQLite store. Nothing uses it now; it's kept
  until the team decides whether to remove it.
- `resume/generation.py` ranks saved experiences and assembles grounded drafts,
  optionally asking a local Hugging Face model to rewrite concise bullets with
  source references. `resume/wording.py` supplies conservative grammar editing
  when generation is unavailable.
- `web/src/components/resume/ResumeBuilder.jsx` provides the interview and draft UI beside
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

## Local data and privacy

**Stored locally, never in the cloud.** The story bank exists only in the user's browser:

- Before the first story, the user agrees to keep stories in this browser and chooses a
  passphrase (10+ characters).
- Stories are encrypted with AES-256-GCM. The key is derived from the passphrase with
  PBKDF2-SHA256 (600,000 iterations, random 16-byte salt), is non-extractable, and is held in
  memory only while the bank is open. A fresh 12-byte IV is used on every save. The passphrase
  is never stored.
- The encrypted record lives in IndexedDB (`waypoint-story-bank`). The page asks the browser
  to keep it persistent so it isn't evicted to free space.
- **Lock** forgets the key. A wrong passphrase, or a backup that was altered, fails to decrypt.
- **Download encrypted backup** exports the same encrypted record; **Restore backup** checks the
  passphrase before replacing the browser's bank. Backups are for moving to another browser
  or computer, and for surviving cleared browser data.
- **Delete my story bank** erases it from this browser. A forgotten passphrase can't be
  recovered, so deleting and starting over (or restoring a backup) is the only way back.

Hashing isn't encryption: a hash can't be reversed to read the story again, so the bank is
encrypted instead.

The API keeps no story database. Previews and drafts receive the stories they need in the
request body, use them in memory, and return. Responses under `/api/resume/` have
`Cache-Control: no-store`. Uploaded roadmap resumes are also read in memory only.

Why not user accounts? Accounts would mean storing stories on a server, which adds a
breach target and a password database, and isn't needed for one person on one device.
The encrypted backup covers moving between devices. Accounts become worth it only if the
app is hosted for many users and needs sync; then add real authentication and encrypt
stories on the device before upload.

The page's privacy notice (`web/src/components/layout/PrivacyNotice.jsx`) lists exactly what is and
isn't stored. Keep it in step with the code.

## Role insights from O*NET

Choosing a target role shows two panels, built offline by
`scripts/build_role_insights.py` into `data/role_insights.json` and served by
`GET /api/resume/insights?role=...`. The only source is O*NET 31.0 (U.S. Department of
Labor, Employment and Training Administration; CC BY 4.0), credited under the panel:

- **What people in this job do**: the tasks rated most important by people who hold the
  closest O*NET occupation. Some roles have no exact O*NET occupation; those are labeled
  as the closest match.
- **Technologies in demand**: technologies O*NET flags as In Demand for the occupation
  (often listed in employer job postings). O*NET's broader "Hot Technology" flag is not
  shown because it reflects demand across all jobs.

When generating, the role's in-demand technologies help rank which stories come first,
and the panel marks each as found or not found in the saved stories (everyday names count:
"Active Directory" matches "Microsoft Active Directory"). Role data never adds claims: a
technology appears in the draft only if a saved story says it.

Nothing is scraped (no LinkedIn or other job-site scraping). To rebuild the O*NET data, download
the O*NET text database to `~/waypoint-data/onet/db_31_0_text/` and run:

```bash
python scripts/build_role_insights.py
```

### AI/ML Engineer: job listings instead of O*NET

O*NET has no machine learning engineer occupation. Its closest, Computer and Information
Research Scientists, describes research work (designing computers, PhDs common), so
AI/ML Engineer uses a second source for its skills:

- **Source:** the AI Dev Jobs public API (aidevboard.com), found through the CC0 list
  [awesome-job-boards](https://github.com/emredurukn/awesome-job-boards). Its
  [terms](https://aidevboard.com/terms) allow API data to be used in applications but not
  resold as a standalone dataset, and say listing content belongs to the hiring companies.
- **What's kept:** only how many listings carry each skill tag, and the share. No listing text,
  titles, companies or links are stored (`data/aiml_listings.json`).
- **Which listings:** junior and mid-level listings whose title names a machine learning or AI
  engineering role (300 in the October 2026 sample). Industry tags such as healthcare or
  payments are dropped, as are vague ones (platform, search, infrastructure).
- **Core tools:** listing tags don't name languages or libraries, so Python, SQL, Git,
  scikit-learn and pandas come from O*NET's in-demand technologies for related jobs.
  Experience still comes from O*NET (applied only to mid-level targets), and education is its
  most common level, a bachelor's degree.

The roadmap shows these shares as real percentages ("47% of the junior and mid-level AI/ML
Engineer job listings we sampled ask for LLMs") and credits the source. To refresh:

```bash
python scripts/build_aiml_listings.py
```

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

Tests use fake model outputs. They cover that the API stores nothing, interview
validation, missing outcomes, source-backed drafting, and the existing roadmap behavior
without downloading model weights. The browser vault was checked by hand: encrypt, reopen,
wrong passphrase, altered backup, restore, delete.
