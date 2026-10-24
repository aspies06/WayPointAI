import { useEffect, useRef, useState } from "react";
import {
  createStoryLibrary, deleteStory, generateResume, getStories, getStoryQuestions,
  previewStory, readStoryKey, rememberStoryKey, saveStory,
} from "../api.js";

const emptyStory = () => ({
  answers: { context: "", problem: "", actions: "", tools: "", outcome: "" },
  organization: "", dates: "",
});
const LIMITS = { context: 600, problem: 2000, actions: 3000, tools: 1000, outcome: 2000 };
const FIELD_LABELS = { context: "Context", problem: "Problem", actions: "Your contribution", tools: "Tools", outcome: "Outcome" };

export function ResumeBuilder() {
  const [access] = useState(readStoryKey);
  const [libraryKey, setLibraryKey] = useState(access.key);
  const [storageWarning, setStorageWarning] = useState(access.warning);
  const [restoreKey, setRestoreKey] = useState("");
  const [questions, setQuestions] = useState([]);
  const [questionError, setQuestionError] = useState("");
  const [stories, setStories] = useState([]);
  const [bankLoaded, setBankLoaded] = useState(false);
  const [busy, setBusy] = useState(access.key ? "loading" : "");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [editor, setEditor] = useState(null);
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState(emptyStory);
  const [preview, setPreview] = useState(null);
  const [deleteId, setDeleteId] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [profile, setProfile] = useState({ name: "", contact: "", headline: "", education: "" });
  const [generated, setGenerated] = useState(null);
  const [copyStatus, setCopyStatus] = useState("");
  const editorRef = useRef(null);
  const resultRef = useRef(null);

  useEffect(() => {
    let active = true;
    getStoryQuestions().then(
      (data) => { if (active) setQuestions(data.questions); },
      (err) => { if (active) setQuestionError(err.message); },
    );
    if (access.key) {
      getStories(access.key).then(
        (data) => {
          if (active) { setStories(data.stories); setBankLoaded(true); }
        },
        (err) => { if (active) setError(bankError(err)); },
      ).finally(() => { if (active) setBusy(""); });
    }
    return () => { active = false; };
  }, [access]);

  useEffect(() => {
    if (editor !== null) editorRef.current?.querySelector("textarea")?.focus();
  }, [editor, step]);

  function bankError(err) {
    return err.status === 401
      ? "This access key wasn't recognized. Restore your story bank with a saved key below, or explicitly create a new bank."
      : err.message;
  }

  async function reloadQuestions() {
    setQuestionError("");
    try { setQuestions((await getStoryQuestions()).questions); }
    catch (err) { setQuestionError(err.message); }
  }

  function openEditor(story) {
    setEditor(story?.id || "new");
    setDraft(story ? { answers: { ...story.answers }, organization: story.organization || "", dates: story.dates || "" } : emptyStory());
    setStep(0);
    setPreview(null);
    setError("");
    setStatus("");
    setDeleteId("");
    requestAnimationFrame(() => editorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  async function startStory() {
    if (!bankLoaded) {
      setBusy("starting");
      setError("");
      try {
        const data = await createStoryLibrary();
        setLibraryKey(data.library_key);
        setStorageWarning(rememberStoryKey(data.library_key));
        setStories([]);
        setBankLoaded(true);
        setGenerated(null);
      } catch (err) {
        setError(err.message);
        return;
      } finally { setBusy(""); }
    }
    openEditor();
  }

  async function restoreBank(event) {
    event.preventDefault();
    if (!restoreKey.trim()) return;
    setBusy("restoring");
    setError("");
    try {
      const key = restoreKey.trim();
      const data = await getStories(key);
      setLibraryKey(key);
      setStorageWarning(rememberStoryKey(key));
      setStories(data.stories);
      setBankLoaded(true);
      setEditor(null);
      setGenerated(null);
      setRestoreKey("");
      setStatus("Your story bank is open.");
    } catch (err) { setError(bankError(err)); }
    finally { setBusy(""); }
  }

  async function retryBank() {
    setBusy("loading");
    setError("");
    try {
      const data = await getStories(libraryKey);
      setStories(data.stories);
      setBankLoaded(true);
      setStatus("Your saved stories are ready.");
    } catch (err) { setError(bankError(err)); }
    finally { setBusy(""); }
  }

  function answer(event) {
    const question = questions[step];
    setDraft({ ...draft, answers: { ...draft.answers, [question.id]: event.target.value } });
    setError("");
  }

  async function nextQuestion(event) {
    event.preventDefault();
    const question = questions[step];
    if (question.required && !draft.answers[question.id].trim()) {
      setError("Add a short answer before continuing. A sentence or two is enough.");
      return;
    }
    setError("");
    if (step < questions.length - 1) { setStep(step + 1); return; }
    setBusy("previewing");
    try { setPreview(await previewStory(libraryKey, draft)); }
    catch (err) { setError(bankError(err)); }
    finally { setBusy(""); }
  }

  async function confirmStory() {
    setBusy("saving");
    setError("");
    try {
      const saved = await saveStory(libraryKey, draft, editor === "new" ? undefined : editor);
      setStories((previous) => editor === "new" ? [saved, ...previous] : previous.map((story) => story.id === saved.id ? saved : story));
      setEditor(null);
      setPreview(null);
      setGenerated(null);
      setStatus("Story saved. You can reuse it for any job description.");
    } catch (err) { setError(bankError(err)); }
    finally { setBusy(""); }
  }

  async function removeStory(id) {
    setBusy("deleting");
    setError("");
    try {
      await deleteStory(libraryKey, id);
      setStories((previous) => previous.filter((story) => story.id !== id));
      setDeleteId("");
      setGenerated(null);
      setStatus("Story deleted.");
    } catch (err) { setError(bankError(err)); }
    finally { setBusy(""); }
  }

  async function buildResume(event) {
    event.preventDefault();
    setBusy("generating");
    setError("");
    setCopyStatus("");
    setGenerated(null);
    try {
      setGenerated(await generateResume(libraryKey, { job_description: jobDescription, profile, max_stories: 5 }));
      requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (err) { setError(bankError(err)); }
    finally { setBusy(""); }
  }

  async function copyText(text, key = false) {
    try {
      await navigator.clipboard.writeText(text);
      if (key) setStatus("Access key copied. Keep it private; it opens your story bank.");
      else setCopyStatus("Resume copied.");
    } catch {
      if (key) setStatus("Copy wasn't available. Use Download access key to keep a copy.");
      else setCopyStatus("Copy wasn't available. Download the text file instead.");
    }
  }

  function downloadText(text, filename) {
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const question = questions[step];
  const disabled = Boolean(busy);
  const setProfileField = (field) => (event) => {
    setProfile({ ...profile, [field]: event.target.value });
    setGenerated(null);
  };
  const closeEditor = () => { setEditor(null); setError(""); };

  return (
    <div className="resume-builder">
      <section className="card story-intro">
        <span className="eyebrow">Your experience, ready to reuse</span>
        <h2>Tell your story once. Build on it for every application.</h2>
        <p className="muted">
          Answer five short questions about a job, class project, personal project, or volunteer
          experience. Review your story, save it, then turn your experience into resume bullets for a
          job you want.
        </p>
        <ol className="story-flow" aria-label="How it works">
          <li><span>1</span> Answer a few questions</li>
          <li><span>2</span> Review and save your story</li>
          <li><span>3</span> Draft or tailor a resume</li>
        </ol>
      </section>

      {error && <p className="alert alert-error" role="alert">{error}</p>}
      {storageWarning && <p className="alert alert-warn" role="status">{storageWarning}</p>}
      <p className="status-message" role="status">{status}</p>
      {busy === "loading" && <p className="muted" role="status">Opening your saved stories…</p>}
      {questionError && (
        <div className="alert alert-error" role="alert">
          {questionError}{" "}
          <button type="button" className="text-button" onClick={reloadQuestions}>Try again</button>
        </div>
      )}

      <section className="card">
        <div className="section-heading">
          <div>
            <h2>Your story bank {bankLoaded && <span className="tag">{stories.length} saved</span>}</h2>
            <p className="hint">Saved stories stay available when you return using this browser or your private access key.</p>
          </div>
          {editor === null && (
            <button type="button" className="primary" disabled={disabled || !questions.length}
              onClick={!bankLoaded && libraryKey ? retryBank : startStory}>
              {busy === "starting" ? "Opening your bank…" : bankLoaded ? "Add a story" : libraryKey ? "Retry opening story bank" : "Start my story bank"}
            </button>
          )}
        </div>
        {!stories.length && editor === null && (
          <div className="story-empty">
            <h3>Start with one thing you worked on.</h3>
            <p className="muted">
              A bug you fixed, a process you improved, or a project you built all count. Rough notes are
              enough, and you don't need numbers for every result.
            </p>
          </div>
        )}

        {editor !== null && question && (
          <section className="story-interview" ref={editorRef} aria-label="Experience interview" aria-busy={disabled}>
            {preview ? (
              <>
                <h3>Does this sound like your experience?</h3>
                <p className="muted">Check the details before saving. You can edit this story later.</p>
                <p className="story-narrative">{preview.narrative}</p>
                <details className="story-details">
                  <summary>Review the original answers</summary>
                  <dl className="story-evidence">
                    {questions.map((q) => (
                      <div key={q.id}><dt>{FIELD_LABELS[q.id] || q.id}</dt><dd>{draft.answers[q.id] || "Not provided"}</dd></div>
                    ))}
                  </dl>
                </details>
                <div className="actions compact">
                  <button type="button" className="primary" disabled={disabled} onClick={confirmStory}>
                    {busy === "saving" ? "Saving…" : "Save this story"}
                  </button>
                  <button type="button" className="secondary" disabled={disabled} onClick={() => { setPreview(null); setStep(0); }}>
                    Edit answers
                  </button>
                  <button type="button" className="text-button" disabled={disabled} onClick={closeEditor}>Cancel</button>
                </div>
              </>
            ) : (
              <>
                <div className="interview-progress">
                  <span>Question {step + 1} of {questions.length}</span>
                  <span>{question.required ? "A short answer is enough" : "Optional — skip if you're unsure"}</span>
                </div>
                <progress value={step + 1} max={questions.length} aria-label="Interview progress"></progress>
                <form onSubmit={nextQuestion} noValidate>
                  <fieldset className="resume-fieldset" disabled={disabled}>
                    <label className="field">
                      <span className="question-title">{question.prompt}</span>
                      <span className="hint" id="story-question-hint">{question.hint}</span>
                      <textarea rows="4" value={draft.answers[question.id]} onChange={answer} maxLength={LIMITS[question.id]}
                        aria-describedby="story-question-hint" required={question.required} />
                    </label>
                    {step === 0 && (
                      <details className="story-details">
                        <summary>Add organization and dates <span className="muted">(optional)</span></summary>
                        <div className="grid two">
                          <label className="field">
                            <span className="label">Organization or school</span>
                            <input value={draft.organization} maxLength="200" placeholder="Example: Campus robotics club"
                              onChange={(event) => setDraft({ ...draft, organization: event.target.value })} />
                          </label>
                          <label className="field">
                            <span className="label">When was this?</span>
                            <input value={draft.dates} maxLength="100" placeholder="Example: Jan – May 2026"
                              onChange={(event) => setDraft({ ...draft, dates: event.target.value })} />
                          </label>
                        </div>
                      </details>
                    )}
                    <div className="actions compact">
                      {step > 0 && (
                        <button type="button" className="secondary" onClick={() => { setStep(step - 1); setError(""); }}>Back</button>
                      )}
                      <button type="submit" className="primary">
                        {busy === "previewing" ? "Preparing your story…"
                          : step === questions.length - 1 ? "Review my story"
                          : question.required || draft.answers[question.id].trim() ? "Next question" : "Skip for now"}
                      </button>
                      <button type="button" className="text-button" onClick={closeEditor}>Cancel</button>
                    </div>
                  </fieldset>
                </form>
              </>
            )}
          </section>
        )}

        <div className="story-list">
          {stories.map((story) => (
            <article className="saved-story" key={story.id}>
              <h3>{story.answers.context}</h3>
              {(story.organization || story.dates) && (
                <p className="meta">{[story.organization, story.dates].filter(Boolean).join(" · ")}</p>
              )}
              <p className="story-narrative">{story.narrative}</p>
              <div className="actions compact">
                <button type="button" className="text-button" disabled={disabled || editor !== null} onClick={() => openEditor(story)}>Edit story</button>
                <button type="button" className="text-button danger" disabled={disabled || editor !== null} onClick={() => setDeleteId(story.id)}>Delete</button>
              </div>
              {deleteId === story.id && (
                <div className="alert alert-warn">
                  <p>Delete this saved story? It won't be available for future resumes.</p>
                  <div className="actions compact">
                    <button type="button" className="secondary" disabled={disabled} onClick={() => removeStory(story.id)}>
                      {busy === "deleting" ? "Deleting…" : "Delete story"}
                    </button>
                    <button type="button" className="text-button" disabled={disabled} onClick={() => setDeleteId("")}>Keep story</button>
                  </div>
                </div>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className={"card" + (stories.length ? " card-accent" : "")}>
        <h2>Build your resume</h2>
        <p className="muted">
          Paste a job description to prioritize relevant experience, or leave it blank for a general
          draft. Only saved stories are used.
        </p>
        {!stories.length && (
          <p className="alert alert-info">Save your first story to start. You can add more experiences whenever you're ready.</p>
        )}
        {editor !== null && (
          <p className="alert alert-info">Save or cancel your current story before generating a resume.</p>
        )}
        <form onSubmit={buildResume}>
          <fieldset className="resume-fieldset" disabled={disabled || !stories.length || editor !== null || !bankLoaded}>
            <details className="story-details">
              <summary>Your resume details <span className="muted">(optional)</span></summary>
              <div className="grid two">
                <label className="field">
                  <span className="label">Name</span>
                  <input autoComplete="name" maxLength="200" value={profile.name} onChange={setProfileField("name")} />
                </label>
                <label className="field">
                  <span className="label">Contact and links</span>
                  <input maxLength="500" placeholder="Email · LinkedIn · Portfolio" value={profile.contact} onChange={setProfileField("contact")} />
                </label>
              </div>
              <label className="field">
                <span className="label">Professional headline</span>
                <input maxLength="300" placeholder="Example: Computer science student" value={profile.headline} onChange={setProfileField("headline")} />
              </label>
              <label className="field">
                <span className="label">Education</span>
                <textarea rows="2" maxLength="2000" placeholder="School, degree, graduation date — use your actual details"
                  value={profile.education} onChange={setProfileField("education")} />
              </label>
              <p className="hint">These details are used in this draft and aren't saved to your story bank.</p>
            </details>
            <label className="field">
              <span className="label">Job description <span className="muted">(optional)</span></span>
              <textarea rows="6" maxLength="15000" placeholder="Paste the responsibilities and qualifications for a job you're interested in…"
                value={jobDescription} onChange={(event) => { setJobDescription(event.target.value); setGenerated(null); }} />
              <span className="hint">The job description guides emphasis. Review the draft against your saved facts before using it.</span>
            </label>
            <div className="actions compact">
              <button type="submit" className="primary">
                {busy === "generating" ? "Building your resume…" : jobDescription.trim() ? "Tailor my resume" : "Build my resume"}
              </button>
              {busy === "generating" && (
                <span className="hint" role="status">Selecting relevant experience. This may take a minute with AI enabled.</span>
              )}
            </div>
          </fieldset>
        </form>
      </section>

      {generated && (
        <section className="card resume-result" ref={resultRef} aria-label="Generated resume">
          <div className="section-heading">
            <h2>Your resume draft</h2>
            <span className={"tag " + (generated.mode === "ai" ? "tag-ai" : "")}>{generated.mode === "ai" ? "AI rewritten" : "Edited draft"}</span>
          </div>
          <p className="muted">Review the wording and details before submitting an application.</p>
          {generated.notice && <p className="alert alert-info">{generated.notice}</p>}
          {generated.follow_up_questions?.length > 0 && (
            <aside className="alert alert-info">
              <strong>One detail could strengthen this draft</strong>
              <ul>{generated.follow_up_questions.map((item, index) => <li key={index}>{item.question}</li>)}</ul>
            </aside>
          )}
          <pre className="resume-preview">{generated.text}</pre>
          <div className="actions compact">
            <button type="button" className="primary" onClick={() => copyText(generated.text)}>Copy resume</button>
            <button type="button" className="secondary" onClick={() => downloadText(generated.text, "waypoint-resume.txt")}>Download .txt</button>
            <span className="hint" role="status">{copyStatus}</span>
          </div>
          {generated.matched_terms?.length > 0 && (
            <p className="match-note"><strong>Relevant terms in your stories:</strong> {generated.matched_terms.join(", ")}</p>
          )}
          {generated.unmatched_terms?.length > 0 && (
            <p className="match-note">
              <strong>Not found in your saved stories:</strong> {generated.unmatched_terms.join(", ")}. Add another story if
              you have relevant experience. These terms were not added as claims.
            </p>
          )}
          <details className="story-details">
            <summary>See which story supports each bullet</summary>
            {generated.sections?.map((section) => (
              <div className="bullet-sources" key={section.story_id}>
                <h3>{section.context}</h3>
                {section.bullets.map((bullet, index) => (
                  <div key={index}>
                    <p><strong>{bullet.text}</strong></p>
                    <dl className="story-evidence">
                      {bullet.evidence.map((evidence, item) => (
                        <div key={item}><dt>{FIELD_LABELS[evidence.field] || evidence.field}</dt><dd>{evidence.quote}</dd></div>
                      ))}
                    </dl>
                  </div>
                ))}
              </div>
            ))}
          </details>
        </section>
      )}

      <details className="card story-access">
        <summary>Story bank access</summary>
        <p className="hint">
          This local app uses a private access key to reopen your stories. Your browser remembers it. Keep
          a copy if you switch browsers or clear browser data; anyone with the key can open your story bank.
        </p>
        {libraryKey && (
          <div className="actions compact">
            <button type="button" className="secondary" disabled={disabled} onClick={() => copyText(libraryKey, true)}>Copy access key</button>
            <button type="button" className="text-button" disabled={disabled} onClick={() => downloadText(libraryKey, "waypoint-story-access-key.txt")}>
              Download access key
            </button>
          </div>
        )}
        <form onSubmit={restoreBank}>
          <fieldset className="resume-fieldset" disabled={disabled || editor !== null}>
            <label className="field">
              <span className="label">Open an existing story bank</span>
              <input type="password" autoComplete="off" value={restoreKey} onChange={(event) => setRestoreKey(event.target.value)}
                placeholder="Paste your saved access key" maxLength="200" />
            </label>
            <button type="submit" className="secondary" disabled={!restoreKey.trim()}>
              {busy === "restoring" ? "Opening…" : "Use access key"}
            </button>
          </fieldset>
        </form>
        {libraryKey && !bankLoaded && (
          <div className="new-bank-option">
            <p className="hint">
              Want to start over? Creating a new bank replaces the key remembered in this browser. Save your
              current key first if you want to return to it.
            </p>
            <button type="button" className="text-button" disabled={disabled || !questions.length} onClick={startStory}>
              Create a new empty story bank
            </button>
          </div>
        )}
      </details>
    </div>
  );
}
