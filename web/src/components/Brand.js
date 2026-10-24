import { html } from "../html.js";

/** The title with the WayPointAI logo (a feathered arrow piercing a page marked "Hired") behind it.
 *  The logo starts at the first letter and is sized from the title's width so its last 15% hangs
 *  past the end of the name. The logo's own file switches its outlines to light in dark mode. */
export function Brand() {
  return html`
    <h1 className="brand">
      <span className="brand-name">
        <img className="brand-logo" src="./brand-logo.svg" alt="" />
        <span className="brand-text">WayPointAI</span>
      </span>
    </h1>
  `;
}
