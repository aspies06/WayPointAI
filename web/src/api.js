import { API_BASE } from "./config.js";

async function call(path, options) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new Error(
      `Can't reach the WayPointAI API at ${API_BASE}. Start it with: .venv/bin/python api.py`
    );
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `The API returned an error (${response.status}).`);
  }
  return body;
}

export const getOptions = () => call("/api/options");

/** form: the PlannerForm state. Sends it as multipart so a resume file can ride along. */
export function getRoadmaps(form) {
  const data = new FormData();
  form.roles.forEach((role) => data.append("roles", role));
  data.append("level", form.level);
  data.append("experience_years", form.experienceYears || "0");
  data.append("hours_per_week", form.workload === "custom" ? form.customHours : form.workload);
  data.append("start_date", form.startDate);
  data.append("target_date", form.targetDate);
  data.append("budget_usd", form.budget);
  data.append("background", form.background);
  data.append("skills_text", form.skills);
  if (form.resume) data.append("resume", form.resume);
  return call("/api/roadmaps", { method: "POST", body: data });
}
