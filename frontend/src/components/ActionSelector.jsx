export default function ActionSelector({ value, onChange, options }) {
  return (
    <label className="field">
      <span>Action</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((action) => (
          <option key={action.value} value={action.value}>
            {action.label}
          </option>
        ))}
      </select>
    </label>
  );
}

