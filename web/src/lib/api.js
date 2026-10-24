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
    const message = response.status === 404 && path === "/api/resume/questions"
      ? `The API at ${API_BASE} hasn't loaded the resume builder. Restart the API with .venv/bin/python api.py, then click Try again. If you use a custom API address, check that it points to the updated WayPointAI server.`
      : body.detail || `The API returned an error (${response.status}).`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
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
  data.append("education_level", form.education);
  data.append("field_of_study", form.education ? form.fieldOfStudy : "");
  if (form.resume) data.append("resume", form.resume);
  return call("/api/roadmaps", { method: "POST", body: data });
}

function resumeCall(path, method = "GET", body) {
  return call(`/api/resume${path}`, {
    method,
    ...(body !== undefined ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
  });
}

// Stories are stored only in this browser (storyVault.js). These calls send what a request
// needs to the WayPointAI API on this computer, which uses it in memory and keeps nothing.
export const getStoryQuestions = () => resumeCall("/questions");
export const previewStory = (story) => resumeCall("/stories/preview", "POST", story);
export const generateResume = (input) => resumeCall("/generate", "POST", input);

/** What people in the role do and the technologies in demand for it (O*NET). Public data. */
export function getRoleInsights(role) {
  return call(`/api/resume/insights?${new URLSearchParams({ role })}`);
}
