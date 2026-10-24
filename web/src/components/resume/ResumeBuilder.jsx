import { useEffect, useRef, useState } from "react";
import { generateResume, getRoleInsights, getStoryQuestions, previewStory } from "../../lib/api.js";
import {
  MIN_PASSPHRASE, bankExists, createBank, deleteBank, exportBank, importBank, newStoryId, openBank, saveStories,
} from "../../lib/storyVault.js";
import { RoleInsights } from "./RoleInsights.jsx";

const emptyStory = () => ({
  answers: { context: "", problem: "", actions: "", tools: "", outcome: "" },
  organization: "", dates: "",
});
const LIMITS = { context: 600, problem: 2000, actions: 3000, tools: 1000, outcome: 2000 };
const FIELD_LABELS = { context: "Context", problem: "Problem", actions: "Your contribution", tools: "Tools", outcome: "Outcome" };
const newestFirst = (stories) => [...stories].sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));

export function ResumeBuilder({ roles = [] }) {
  // vault: "checking" | "none" (no bank in this browser) | "locked" | "open"
  const [vault, setVault] = useState("checking");
  const [session, setSession] = useState(null); // the decryption key, in memory only
  const [passphrase, setPassphrase] = useState("");
  const [passphraseAgain, setPassphraseAgain] = useState("");
  const [consent, setConsent] = useState(false);
  const [backupFile, setBackupFile] = useState(null);
  const [backupPassphrase, setBackupPassphrase] = useState("");
  const [questions, setQuestions] = useState([]);
  const [questionError, setQuestionError] = useState("");
  const [stories, setStories] = useState([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [editor, setEditor] = useState(null);
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState(emptyStory);
  const [preview, setPreview] = useState(null);
  const [deleteId, setDeleteId] = useState("");
  const [confirmDeleteBank, setConfirmDeleteBank] = useState(false);
  const [jobDescription, setJobDescription] = useState("");
  const [role, setRole] = useState("");
  const [insights, setInsights] = useState(null);
  const [profile, setProfile] = useState({ name: "", contact: "", headline: "", education: "" });
  const [generated, setGenerated] = useState(null);
  const [copyStatus, setCopyStatus] = useState("");
  const editorRef = useRef(null);
  const resultRef = useRef(null);
  const bankOpen = vault === "open";

  useEffect(() => {
    let active = true;
    getStoryQuestions().then(
      (data) => { if (active) setQuestions(data.questions); },
      (err) => { if (active) setQuestionError(err.message); },
    );
    bankExists().then(
      (exists) => { if (active) setVault(exists ? "locked" : "none"); },
      (err) => { if (active) { setVault("none"); setError(err.message); } },
    );
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (editor !== null) editorRef.current?.querySelector("textarea")?.focus();
  }, [editor, step]);

  // What the chosen role looks like, shown before generating so it can prompt new stories.
  useEffect(() => {
    let active = true;
    setInsights(null);
    if (role) {
      getRoleInsights(role).then(
        (data) => { if (active) setInsights(data); },
        () => { if (active) setInsights(null); },
      );
    }
    return () => { active = false; };
  }, [role]);

  async function reloadQuestions() {
    setQuestionError("");
    try { setQuestions((await getStoryQuestions()).questions); }
    catch (err) { setQuestionError(err.message); }
  }

  function opened(newSession, saved, message) {
    setSession(newSession);
    setStories(newestFirst(saved));
    setVault("open");
    setPassphrase("");
    setPassphraseAgain("");
    setBackupPassphrase("");
    setBackupFile(null);
    setEditor(null);
    setGenerated(null);
    setStatus(message);
  }

  async function run(label, action) {
    setBusy(label);
    setError("");
    setStatus("");
    try { await action(); }
    catch (err) { setError(err.message); }
    finally { setBusy(""); }
  }

  function startBank(event) {
    event.preventDefault();
    if (!consent) { setError("Check the box to agree before starting your story bank."); return; }
    if (passphrase.length < MIN_PASSPHRASE) { setError(`Use a passphrase of at least ${MIN_PASSPHRASE} characters.`); return; }
    if (passphrase !== passphraseAgain) { setError("The two passphrases don't match."); return; }
    run("starting", async () => opened(await createBank(passphrase), [], "Your story bank is ready. Add your first story."));
  }

  function unlockBank(event) {
    event.preventDefault();
    run("unlocking", async () => {
      const { session: unlocked, stories: saved } = await openBank(passphrase);
      opened(unlocked, saved, "Your story bank is open.");
    });
  }

  function lockBank() {
    setSession(null);
    setStories([]);
    setVault("locked");
    setEditor(null);
    setGenerated(null);
    setConfirmDeleteBank(false);
    setStatus("Your story bank is locked.");
  }

  async function keep(next) {
    await saveStories(session, next);
    setStories(next);
    setGenerated(null);
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

  function eraseBank() {
    run("erasing", async () => {
      await deleteBank();
      setSession(null);
      setStories([]);
      setVault("none");
      setEditor(null);
      setGenerated(null);
      setConfirmDeleteBank(false);
      setConsent(false);
      setStatus("Your story bank and all its stories were deleted from this browser.");
    });
  }

  function exportBackup() {
    run("exporting", async () => {
      downloadText(await exportBank(), "waypoint-story-bank-backup.json", "application/json");
      setStatus("Backup downloaded. It's encrypted: opening it needs your passphrase.");
    });
  }

  function restoreBackup(event) {
    event.preventDefault();
    if (!backupFile) return;
    run("importing", async () => {
      const { session: unlocked, stories: saved } = await importBank(await backupFile.text(), backupPassphrase);
      opened(unlocked, saved, `Backup restored: ${saved.length === 1 ? "1 story" : `${saved.length} stories`}.`);
    });
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
    try { setPreview(await previewStory(draft)); }
    catch (err) { setError(err.message); }
    finally { setBusy(""); }
  }

  function confirmStory() {
    run("saving", async () => {
      const now = new Date().toISOString();
      const old = stories.find((story) => story.id === editor);
      const saved = { ...draft, narrative: preview.narrative, id: old?.id || newStoryId(),
                      created_at: old?.created_at || now, updated_at: now };
      await keep(old ? stories.map((story) => story.id === old.id ? saved : story) : [saved, ...stories]);
      setEditor(null);
      setPreview(null);
      setStatus("Story saved in this browser. You can reuse it for any job description.");
    });
  }

  function removeStory(id) {
    run("deleting", async () => {
      await keep(stories.filter((story) => story.id !== id));
      setDeleteId("");
      setStatus("Story deleted.");
    });
  }

  async function buildResume(event) {
    event.preventDefault();
    setCopyStatus("");
    setGenerated(null);
    await run("generating", async () => {
      setGenerated(await generateResume({ stories, job_description: jobDescription, profile, max_stories: 5, role }));
      requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    });
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus("Resume copied.");
    } catch {
      setCopyStatus("Copy wasn't available. Download the text file instead.");
    }
  }

  function downloadText(text, filename, type = "text/plain") {
    const url = URL.createObjectURL(new Blob([text], { type: `${type};charset=utf-8` }));
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
  const submitLabel = jobDescription.trim() ? "Tailor my resume" : role ? `Build my ${role} resume` : "Build my resume";

  return (
    <div className="resume-builder">
      <section className="card story-intro">
        <span className="eyebrow">Your experience, ready to reuse</span>
        <h2>Tell your story once. Build on it for every application.</h2>
        <p className="muted">
          Answer five short questions about a job, class project, personal project, or volunteer experience. Review your
          story, save it, then turn your experience into resume bullets for a job you want.
        </p>
        <ol className="story-flow" aria-label="How it works">
          <li><span>1</span> Answer a few questions</li>
          <li><span>2</span> Review and save your story</li>
          <li><span>3</span> Draft or tailor a resume</li>
        </ol>
      </section>

      {error && bankOpen && <p className="alert alert-error" role="alert">{error}</p>}
      <p className="status-message" role="status">{status}</p>
      {questionError && (
        <div className="alert alert-error" role="alert">
          {questionError} <button type="button" className="text-button" onClick={reloadQuestions}>Try again</button>
        </div>
      )}

      <section className="card">
        <h2>The role you're aiming for <span className="muted">(optional)</span></h2>
        <p className="hint">
          Pick a role to see what people in that job do and the technologies in demand for it. Use it to remember
          experiences worth saving as stories. Your resume only ever uses what your stories say.
        </p>
        <label className="field role-picker">
          <span className="label">Role</span>
          <select value={role} onChange={(e) => { setRole(e.target.value); setGenerated(null); }}>
            <option value="">No specific role</option>
            {roles.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        {insights && <RoleInsights insights={generated?.role_insights || insights} />}
      </section>

      <section className="card">
        <div className="section-heading">
          <div>
            <h2>Your story bank {bankOpen && <span className="tag">{stories.length} saved</span>}</h2>
            <p className="hint">Stored locally, encrypted, in this browser on this device. Never in the cloud.</p>
          </div>
          {bankOpen && editor === null && (
            <div className="actions compact">
              <button type="button" className="primary" disabled={disabled || !questions.length} onClick={() => openEditor()}>
                Add a story
              </button>
              <button type="button" className="text-button" disabled={disabled} onClick={lockBank}>Lock</button>
            </div>
          )}
        </div>

        {vault === "none" && (
          <form className="bank-gate" onSubmit={startBank}>
            <h3>Start your story bank</h3>
            <p className="muted">
              Your stories are encrypted with a passphrase you choose and saved only in this browser on this device.
              WayPointAI has no account and no copy, so <strong>a forgotten passphrase can't be recovered</strong>. Download
              a backup once you've saved a few stories.
            </p>
            <fieldset className="resume-fieldset" disabled={disabled}>
              <div className="grid two">
                <label className="field">
                  <span className="label">Passphrase</span>
                  <input type="password" autoComplete="new-password" minLength={MIN_PASSPHRASE} maxLength="200"
                    value={passphrase} onChange={(e) => setPassphrase(e.target.value)} aria-describedby="passphrase-hint" />
                  <span className="hint" id="passphrase-hint">At least {MIN_PASSPHRASE} characters. A few unrelated words work well.</span>
                </label>
                <label className="field">
                  <span className="label">Type it again</span>
                  <input type="password" autoComplete="new-password" maxLength="200"
                    value={passphraseAgain} onChange={(e) => setPassphraseAgain(e.target.value)} />
                </label>
              </div>
              <label className="check">
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
                <span>
                  I agree to save my stories in this browser. They're sent to the WayPointAI API on this computer only
                  when I preview a story or build a resume, and it doesn't keep them. I've read the privacy notice at the bottom of this page.
                </span>
              </label>
              {error && <p className="alert alert-error" role="alert">{error}</p>}
              <button type="submit" className="primary">{busy === "starting" ? "Starting…" : "Start my story bank"}</button>
            </fieldset>
          </form>
        )}

        {vault === "locked" && (
          <form className="bank-gate" onSubmit={unlockBank}>
            <h3>Unlock your story bank</h3>
            <p className="muted">Your saved stories are encrypted in this browser. Enter your passphrase to open them.</p>
            <fieldset className="resume-fieldset" disabled={disabled}>
              <label className="field">
                <span className="label">Passphrase</span>
                <input type="password" autoComplete="current-password" maxLength="200"
                  value={passphrase} onChange={(e) => setPassphrase(e.target.value)} />
              </label>
              {error && <p className="alert alert-error" role="alert">{error}</p>}
              <button type="submit" className="primary" disabled={!passphrase}>{busy === "unlocking" ? "Unlocking…" : "Unlock"}</button>
            </fieldset>
          </form>
        )}

        {bankOpen && !stories.length && editor === null && (
          <div className="story-empty">
            <h3>Start with one thing you worked on.</h3>
            <p className="muted">
              A bug you fixed, a process you improved, or a project you built all count. Rough notes are enough, and you
              don't need numbers for every result.
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
                  <button type="button" className="text-button" disabled={disabled} onClick={() => { setEditor(null); setError(""); }}>
                    Cancel
                  </button>
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
                        aria-describedby="story-question-hint" required={question.required}></textarea>
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
                      <button type="button" className="text-button" onClick={() => { setEditor(null); setError(""); }}>Cancel</button>
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
                <button type="button" className="text-button" disabled={disabled || editor !== null} onClick={() => openEditor(story)}>
                  Edit story
                </button>
                <button type="button" className="text-button danger" disabled={disabled || editor !== null} onClick={() => setDeleteId(story.id)}>
                  Delete
                </button>
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
          Paste a job description to prioritize relevant experience, or leave it blank for a general draft
          {role ? ` aimed at ${role} roles` : ""}. Only saved stories are used.
        </p>
        {!stories.length && <p className="alert alert-info">Save your first story to start. You can add more experiences whenever you're ready.</p>}
        {editor !== null && <p className="alert alert-info">Save or cancel your current story before generating a resume.</p>}
        <form onSubmit={buildResume}>
          <fieldset className="resume-fieldset" disabled={disabled || !stories.length || editor !== null || !bankOpen}>
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
                  value={profile.education} onChange={setProfileField("education")}></textarea>
              </label>
              <p className="hint">These details are used in this draft and aren't saved to your story bank.</p>
            </details>
            <label className="field">
              <span className="label">Job description <span className="muted">(optional)</span></span>
              <textarea rows="6" maxLength="15000" placeholder="Paste the responsibilities and qualifications for a job you're interested in…"
                value={jobDescription} onChange={(event) => { setJobDescription(event.target.value); setGenerated(null); }}></textarea>
              <span className="hint">The job description guides emphasis. Review the draft against your saved facts before using it.</span>
            </label>
            <div className="actions compact">
              <button type="submit" className="primary">{busy === "generating" ? "Building your resume…" : submitLabel}</button>
              {busy === "generating" && <span className="hint" role="status">Selecting relevant experience. This may take a minute with AI enabled.</span>}
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
          <p className="disclaimer" role="note">
            {generated.mode === "ai" ? "AI-generated" : "Automatically edited"} draft. It can make mistakes, so
            review the wording and details against your stories before submitting an application.
          </p>
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
              <strong>Not found in your saved stories:</strong> {generated.unmatched_terms.join(", ")}. Add another story if you
              have relevant experience. These terms were not added as claims.
            </p>
          )}
          {generated.role_insights && (
            <p className="match-note">
              Checked against what employers ask for in {generated.role_insights.role} roles; see the role panel above for
              which skills your stories cover.
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
        <summary>Backup, restore and delete</summary>
        <p className="hint">
          Your story bank lives only in this browser, so clearing browser data or switching computers loses it. A backup
          is an encrypted file you keep yourself; restore it here or on another computer with the same passphrase.
        </p>
        {bankOpen && (
          <div className="actions compact">
            <button type="button" className="secondary" disabled={disabled || editor !== null} onClick={exportBackup}>
              Download encrypted backup
            </button>
          </div>
        )}
        <form onSubmit={restoreBackup}>
          <fieldset className="resume-fieldset" disabled={disabled || editor !== null}>
            <label className="field">
              <span className="label">Restore from a backup file</span>
              <input type="file" accept="application/json,.json" onChange={(e) => setBackupFile(e.target.files?.[0] || null)} />
            </label>
            <label className="field">
              <span className="label">That backup's passphrase</span>
              <input type="password" autoComplete="off" maxLength="200" value={backupPassphrase}
                onChange={(e) => setBackupPassphrase(e.target.value)} />
            </label>
            {vault !== "none" && (
              <p className="hint">Restoring replaces the story bank in this browser with the one in the backup.</p>
            )}
            {error && !bankOpen && backupFile && <p className="alert alert-error" role="alert">{error}</p>}
            <button type="submit" className="secondary" disabled={!backupFile || !backupPassphrase}>
              {busy === "importing" ? "Restoring…" : "Restore backup"}
            </button>
          </fieldset>
        </form>
        {vault !== "none" && vault !== "checking" && (
          <div className="delete-bank">
            {confirmDeleteBank ? (
              <div className="alert alert-warn">
                <p>
                  Delete your story bank? This erases {bankOpen ? (stories.length === 1 ? "your 1 saved story" : `all ${stories.length} saved stories`) : "every saved story"} from
                  this browser. Backups you downloaded aren't affected.
                </p>
                <div className="actions compact">
                  <button type="button" className="secondary" disabled={disabled} onClick={eraseBank}>
                    {busy === "erasing" ? "Deleting…" : "Delete everything"}
                  </button>
                  <button type="button" className="text-button" disabled={disabled} onClick={() => setConfirmDeleteBank(false)}>Keep my stories</button>
                </div>
              </div>
            ) : (
              <button type="button" className="text-button danger" disabled={disabled || editor !== null} onClick={() => setConfirmDeleteBank(true)}>
                {vault === "locked" ? "Forgot your passphrase? Delete this story bank" : "Delete my story bank"}
              </button>
            )}
          </div>
        )}
      </details>
    </div>
  );
}
