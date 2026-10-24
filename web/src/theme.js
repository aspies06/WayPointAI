/** Light or dark. The visitor's choice ("system", "light" or "dark") is remembered in this browser;
 *  "system" follows the device setting. index.html applies the same choice before the page draws. */
const KEY = "waypoint-theme";
const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

export function savedTheme() {
  try {
    const choice = localStorage.getItem(KEY);
    return ["light", "dark"].includes(choice) ? choice : "system";
  } catch {
    return "system";
  }
}

export function saveTheme(choice) {
  try {
    if (choice === "system") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, choice);
  } catch {
    /* not remembered; the choice still applies until the page closes */
  }
}

/** Sets data-theme on <html> and returns the theme in effect. */
export function applyTheme(choice) {
  const theme = choice === "system" ? (darkQuery.matches ? "dark" : "light") : choice;
  document.documentElement.dataset.theme = theme;
  return theme;
}

/** Calls back when the device setting changes (only matters while the choice is "system"). */
export function onSystemThemeChange(callback) {
  darkQuery.addEventListener("change", callback);
  return () => darkQuery.removeEventListener("change", callback);
}
