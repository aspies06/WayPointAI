# WayPointAI web app

React 18 with [Vite](https://vite.dev). Talks to `api.py` in the repo root.

## Run it

Needs [Node.js](https://nodejs.org) (LTS). From this folder:

```bash
npm install        # first time, and after package.json changes
npm run dev        # http://127.0.0.1:5173, updates instantly as you edit
```

Start the API too, from the repo root: `python api.py` (port 8000).

Other commands:

| Command | What it does |
|---|---|
| `npm run build` | Optimized site in `dist/` (small JS and CSS, ready to host) |
| `npm run preview` | Serves `dist/` at http://127.0.0.1:4173 to try the build |

If the API runs somewhere else, set `VITE_API_BASE` (e.g. `VITE_API_BASE=http://127.0.0.1:9000 npm run dev`)
or add `?api=http://host:port` to the page address. The API only accepts these addresses by default:
5173 (dev), 4173 (preview) and 5500 (Live Server on `dist/`).

## Layout

```
index.html                    page shell; Vite injects the built JS and CSS
vite.config.js                dev server and preview ports
public/                       copied as-is: logo.svg (tab icon), brand-logo.svg, assets/flowers.jpg
src/main.jsx                  mounts <App />
src/styles.css                all styles; colors are tokens with light and dark values
src/lib/
  api.js                      calls to api.py: options, roadmaps, the /api/resume calls
  config.js                   API address (only this computer's addresses for ?api=)
  format.js                   dates, money, labels, MM-DD-YYYY input mask
  theme.js                    light / dark / auto, remembered in this browser
  storyVault.js               the encrypted story bank, kept only in this browser
src/components/
  layout/
    App.jsx                   header, tabs, footer; loads options and holds results
    Brand.jsx                 title with the logo behind it
    ThemeSwitch.jsx           Auto / Light / Dark
    PrivacyNotice.jsx         exactly what's stored and where
  roadmap/
    PlannerForm.jsx           the questions (time first, never guessed)
    Results.jsx               one tab per role
    RoadmapView.jsx           summary, timeline, steps by priority, optional items button
    StepCard.jsx              one step: why, deliverable, done when, sources, suggestions
  resume/
    ResumeBuilder.jsx         five-question story bank, review, editing, and resume drafts
    RoleInsights.jsx          what people in a role do and what employers ask for, with sources
```

## Notes

- Every link shown comes from the checked catalog through the API, never from what the user typed.
- Roles, levels, workloads and questions come from `GET /api/options`, so they stay in sync with Python.
- `node_modules/` and `dist/` are not committed; `package-lock.json` is, so everyone gets the same versions.
- Image credits and licenses: `public/assets/CREDITS.md`.
- The resume builder's story bank lives only in this browser, encrypted
  (`src/lib/storyVault.js`); `/api/resume` keeps nothing. See
  [the resume builder notes](../docs/resume_builder.md).
- `?api=` only accepts this computer's addresses (127.0.0.1, localhost, [::1]), so a shared
  link can't point the page at another server and send it someone's stories.
