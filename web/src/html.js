// JSX-like templates without a build step: html`<div className=${x}>...</div>`.
// Components are used as <${Component} prop=${value} />. See https://github.com/developit/htm
import htm from "htm";
import { createElement } from "react";

export const html = htm.bind(createElement);
