import { html } from "../html.js";

/** The title with the WayPointAI logo beside it: a feathered arrow piercing a page marked "Hired".
 *  The logo's own file (brand-logo.svg) switches its outlines to a light color in dark mode. */
export function Brand() {
  return html`
    <h1 className="brand">
      <img className="brand-logo" src="./brand-logo.svg" alt="" width="150" height="70" />
      <span className="brand-text">WayPointAI</span>
    </h1>
  `;
}
