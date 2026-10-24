/** The story bank, kept only in this browser on this device, encrypted.
 *
 *  Stories are encrypted with AES-256-GCM before they're written to IndexedDB. The key comes from
 *  the user's passphrase (PBKDF2-SHA256, 600,000 iterations, random salt), is held only in memory
 *  while the bank is open, and can't be exported. The passphrase itself is never stored, so a
 *  forgotten passphrase can't be recovered: the bank can only be deleted and started over.
 *
 *  An export is the same encrypted record, so a backup file is as safe as the bank itself. */

const DB_NAME = "waypoint-story-bank";
const STORE = "vault";
const RECORD = "bank";
const ITERATIONS = 600000;
const FORMAT = "waypoint-story-bank";
export const MIN_PASSPHRASE = 10;

export class WrongPassphrase extends Error {
  constructor() {
    super("That passphrase doesn't open this story bank.");
  }
}

const UNAVAILABLE =
  "This browser can't save your story bank (private browsing or blocked site data). Your stories won't be kept after you close this tab.";

function toBase64(bytes) {
  const view = new Uint8Array(bytes);
  let text = "";
  for (let i = 0; i < view.length; i += 0x8000) text += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(text);
}
const fromBase64 = (text) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));

function openDb() {
  return new Promise((resolve, reject) => {
    let request;
    try {
      request = indexedDB.open(DB_NAME, 1);
    } catch {
      reject(new Error(UNAVAILABLE));
      return;
    }
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error(UNAVAILABLE));
  });
}

async function withStore(mode, action) {
  const db = await openDb();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode);
      const request = action(tx.objectStore(STORE));
      tx.oncomplete = () => resolve(request?.result);
      tx.onerror = () => reject(new Error(UNAVAILABLE));
    });
  } finally {
    db.close();
  }
}

const readRecord = () => withStore("readonly", (store) => store.get(RECORD));
const writeRecord = (record) => withStore("readwrite", (store) => store.put(record, RECORD));

async function deriveKey(passphrase, salt, iterations = ITERATIONS) {
  const material = await crypto.subtle.importKey("raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", hash: "SHA-256", salt, iterations },
    material,
    { name: "AES-GCM", length: 256 },
    false, // not extractable: page code can use the key but never read it
    ["encrypt", "decrypt"],
  );
}

async function seal(session, stories) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const data = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, session.key, new TextEncoder().encode(JSON.stringify(stories)));
  return { format: FORMAT, version: 1, kdf: "PBKDF2-SHA256", iterations: session.iterations,
           salt: toBase64(session.salt), iv: toBase64(iv), data: toBase64(data) };
}

async function unseal(record, passphrase) {
  if (record?.format !== FORMAT || record.version !== 1) throw new Error("That file isn't a WayPointAI story bank backup.");
  const salt = fromBase64(record.salt);
  const session = { key: await deriveKey(passphrase, salt, record.iterations), salt, iterations: record.iterations };
  try {
    const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: fromBase64(record.iv) }, session.key, fromBase64(record.data));
    return { session, stories: JSON.parse(new TextDecoder().decode(plain)) };
  } catch {
    throw new WrongPassphrase(); // AES-GCM also fails if the data was altered
  }
}

export async function bankExists() {
  return Boolean(await readRecord());
}

/** A new, empty bank locked with this passphrase. Replaces any bank already here. */
export async function createBank(passphrase) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const session = { key: await deriveKey(passphrase, salt), salt, iterations: ITERATIONS };
  await writeRecord(await seal(session, []));
  navigator.storage?.persist?.().catch(() => {}); // ask the browser not to clear it to free space
  return session;
}

export async function openBank(passphrase) {
  return unseal(await readRecord(), passphrase);
}

export async function saveStories(session, stories) {
  await writeRecord(await seal(session, stories));
}

export async function deleteBank() {
  await withStore("readwrite", (store) => store.delete(RECORD));
}

/** The encrypted bank as a backup file's text. Opening it needs the same passphrase. */
export async function exportBank() {
  return JSON.stringify(await readRecord(), null, 1);
}

/** Replace this browser's bank with a backup, after checking the passphrase opens it. */
export async function importBank(text, passphrase) {
  let record;
  try {
    record = JSON.parse(text);
  } catch {
    throw new Error("That file isn't a WayPointAI story bank backup.");
  }
  const opened = await unseal(record, passphrase);
  await writeRecord(record);
  return opened;
}

export function newStoryId() {
  return crypto.randomUUID().replaceAll("-", "");
}
