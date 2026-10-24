import { html } from "../html.js";

// One sleek arrow pointing right: the tail tapers to a point and widens into a sharp head.
const ARROW = "M0 20 L62 14 L56 2 L100 20 L56 38 L62 26 Z";

/** The title with the logo behind it: two staggered arrows rising to the right, the back one
 *  lighter, so together they read as one arrow in motion. Low opacity keeps the title readable. */
export function Brand() {
  return html`
    <h1 className="brand">
      <svg className="brand-arrow" viewBox="0 0 260 80" aria-hidden="true" focusable="false">
        <g transform="rotate(-12 130 40)">
          <path className="back" d=${ARROW} transform="translate(70 4) scale(1.5 0.9)" />
          <path d=${ARROW} transform="translate(30 22) scale(1.5 0.9)" />
        </g>
      </svg>
      <span className="brand-text">WayPointAI</span>
    </h1>
  `;
}
