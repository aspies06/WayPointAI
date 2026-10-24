export const PRIORITY_LABELS = {
  must_do: "Must do",
  should_do: "Should do",
  nice_to_have: "Nice to have",
};

export const BENEFIT_LABELS = {
  certification: "Certification",
  certificate: "Certificate of completion",
  portfolio: "Portfolio project",
  knowledge: "Knowledge benefit",
};

/** "2027-05-31" -> "May 31, 2027", without the time-zone shift new Date("2027-05-31") causes. */
export function formatDate(iso) {
  if (!iso) return "";
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export const formatCost = (usd) => (usd ? `$${usd.toLocaleString("en-US")}` : "Free");

/** Shapes typing into MM-DD-YYYY ("05312027" -> "05-31-2027"). A short number like "12"
 *  is left alone, because the target date also accepts a number of weeks. */
export function maskDate(value) {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}-${digits.slice(2)}`;
  return `${digits.slice(0, 2)}-${digits.slice(2, 4)}-${digits.slice(4)}`;
}
