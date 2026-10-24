# WayPointAI web app

React 18 with no build step. The browser loads React straight from a pinned CDN
URL (see the import map in `index.html`), so VS Code's **Live Server** can serve
this folder as-is and reload on every save. No Node.js or `npm install` needed.

## Run it

1. Start the API from the repo root: `python api.py` (port 8000).
2. In VS Code, click **Go Live**. `.vscode/settings.json` serves this folder at
   http://127.0.0.1:5500.

If the API runs somewhere else, add `?api=http://host:port` to the page URL.

## Layout

```
index.html                 page shell + import map (React, ReactDOM, htm)
styles.css                 all styles; colors are tokens with light and dark values
src/main.js                mounts <App />
src/html.js                the `html` template tag (htm bound to React)
src/api.js                 calls to api.py: getOptions(), getRoadmaps(form)
src/config.js              API base URL
src/format.js              dates, money, labels, MM-DD-YYYY input mask
src/components/
  App.js                   loads options, submits the form, holds results
  PlannerForm.js           the questions (time first, never guessed)
  ResumeBuilder.js         five-question story bank, review, editing, and resume drafts
  Results.js               one tab per role
  RoadmapView.js           summary, timeline, steps by priority, optional items button
  StepCard.js              one step: why, deliverable, done when, sources, suggestions
```

## Writing components

Components are plain functions using React hooks. Instead of JSX, markup goes in
an `html` template, which reads almost the same:

```js
import { useState } from "react";
import { html } from "../html.js";

export function Counter({ start }) {
  const [n, setN] = useState(start);
  return html`<button onClick=${() => setN(n + 1)}>Clicked ${n} times</button>`;
}
// use it: html`<${Counter} start=${0} />`
```

Differences from JSX: values go in `${...}`, components are written `<${Name} />`,
and lists still need a `key`.

## Notes

- Every link shown comes from the checked catalog through the API, never from
  what the user typed.
- The roles, levels, workloads and questions come from `GET /api/options`, so
  they stay in sync with the Python side.
- Moving to a build tool later (for example Vite) only means renaming files to
  `.jsx` and swapping the `html` templates for JSX; the component structure stays.
- Resume builder uses `/api/resume` and retains a bank access key in browser
  storage, scoped to the API URL. Experience stories are persisted by the API in
  SQLite; clearing browser storage loses the key. See
  [the resume builder notes](../docs/resume_builder.md).
