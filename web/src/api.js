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
  if (form.resume) data.append("resume", form.resume);
  return call("/api/roadmaps", { method: "POST", body: data });
}

// The browser remembers only a private access key. Story content lives in the API's database.
const STORY_KEY = `waypoint-story-library:${API_BASE.replace(/\/$/, "")}`;

export function readStoryKey() {
  try {
    return { key: localStorage.getItem(STORY_KEY) || "", warning: "" };
  } catch {
    return { key: "", warning: "This browser cannot remember your story bank. Copy its access key to return later." };
  }
}

export function rememberStoryKey(key) {
  try {
    localStorage.setItem(STORY_KEY, key);
    return "";
  } catch {
    return "Your stories are saved, but this browser cannot remember the access key. Copy it below before leaving.";
  }
}

function resumeCall(path, key, method = "GET", body) {
  const headers = {};
  if (key) headers.Authorization = `Bearer ${key}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  return call(`/api/resume${path}`, {
    method,
    headers,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
}

export const getStoryQuestions = () => resumeCall("/questions");
export const createStoryLibrary = () => resumeCall("/library", "", "POST");
export const getStories = (key) => resumeCall("/stories", key);
export const previewStory = (key, story) => resumeCall("/stories/preview", key, "POST", story);
export const saveStory = (key, story, id) =>
  resumeCall(id ? `/stories/${encodeURIComponent(id)}` : "/stories", key, id ? "PUT" : "POST", story);
export const deleteStory = (key, id) => resumeCall(`/stories/${encodeURIComponent(id)}`, key, "DELETE");
export const generateResume = (key, input) => resumeCall("/generate", key, "POST", input);
export const deleteStoryLibrary = (key) => resumeCall("/library", key, "DELETE");

export function forgetStoryKey() {
  try {
    localStorage.removeItem(STORY_KEY);
  } catch {
    /* nothing remembered */
  }
}

/** What people in the role do and the technologies in demand for it (O*NET). Public data. */
export function getRoleInsights(role) {
  return call(`/api/resume/insights?${new URLSearchParams({ role })}`);
}
