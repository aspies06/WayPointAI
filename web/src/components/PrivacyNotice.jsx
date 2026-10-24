/** Full disclosure of what WayPointAI keeps, where, and for how long. Keep it in step with the code:
 *  storyVault.js (the story bank), api.py and resume_api.py (nothing stored on the server). */
export function PrivacyNotice() {
  return (
    <details className="card privacy-notice" id="privacy">
      <summary>Privacy notice: exactly what's stored</summary>
      <h3>Stored on your device</h3>
      <ul>
        <li>
          <strong>Your story bank</strong>, only if you start one: your answers to the story questions, the organization
          and dates you add, the story summary, and when each story was saved or edited. It's encrypted (AES-256-GCM, with
          a key made from your passphrase) and kept in this browser's storage on this device. It stays until you delete
          it, delete a story, or clear this site's browser data.
        </li>
        <li>
          <strong>Backups you download</strong>: the same encrypted story bank, as a file you control. Opening it needs
          your passphrase.
        </li>
      </ul>
      <h3>Not stored anywhere</h3>
      <ul>
        <li>Your passphrase. The key made from it is held in memory only while your story bank is open.</li>
        <li>Resumes you upload for a roadmap, and skills you type in. They're read in memory to build your roadmap.</li>
        <li>Your roadmap answers (roles, hours, dates, budget) and the roadmap itself.</li>
        <li>Resume details (name, contact, headline, education) and job descriptions you paste.</li>
        <li>Generated resume drafts, unless you copy or download them yourself.</li>
      </ul>
      <h3>Where your information goes</h3>
      <ul>
        <li>
          When you build a roadmap, preview a story, or build a resume, what that request needs is sent to the WayPointAI
          API running on this computer. It's used in memory and dropped; the API keeps no database of your information.
        </li>
        <li>
          AI features run on this computer. The first time they're used, the API downloads the model files from
          Hugging Face; none of your information is sent with that download.
        </li>
        <li>No accounts, cookies, ads, analytics or tracking. Nothing you enter is sold or shared.</li>
      </ul>
      <h3>Good to know</h3>
      <ul>
        <li>Anyone who can use this browser profile and knows your passphrase can open your stories. Lock the story bank on a shared computer.</li>
        <li>A forgotten passphrase can't be reset. Delete the story bank and start again, or restore a backup you remember the passphrase for.</li>
      </ul>
    </details>
  );
}
