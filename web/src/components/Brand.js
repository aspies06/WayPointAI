import { html } from "../html.js";

/** The title with the logo arrow running through it: a path from a starting dot (the waypoint)
 *  rising to an arrowhead. It sits behind the text at low opacity so the title stays readable. */
export function Brand() {
  return html`
    <h1 className="brand">
      <svg className="brand-arrow" viewBox="0 0 240 64" aria-hidden="true" focusable="false">
        <circle cx="10" cy="52" r="5" />
        <path d="M10 52 C 70 52, 120 36, 226 13" />
        <path d="M211 7 L228 13 L215 25" />
      </svg>
      <span className="brand-text">WayPointAI</span>
    </h1>
  `;
}
