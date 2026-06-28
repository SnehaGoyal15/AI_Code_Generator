export default function LanguageSelector({ value, onChange, options }) {
  return (
    <label className="field">
      <span>Language</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((language) => (
          <option key={language} value={language}>
            {language}
          </option>
        ))}
      </select>
    </label>
  );
}

