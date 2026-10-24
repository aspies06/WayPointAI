const CHOICES = [
  ["system", "Auto"],
  ["light", "Light"],
  ["dark", "Dark"],
];

/** Light, dark, or follow the device ("Auto"). */
export function ThemeSwitch({ choice, onChange }) {
  return (
    <div className="theme-switch" role="group" aria-label="Color theme">
      {CHOICES.map(([value, label]) => (
        <button key={value} type="button" aria-pressed={choice === value} onClick={() => onChange(value)}
          title={value === "system" ? "Match your device's setting" : `${label} mode`}>
          {label}
        </button>
      ))}
    </div>
  );
}
