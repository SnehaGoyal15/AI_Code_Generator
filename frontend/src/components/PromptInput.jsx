export default function PromptInput({ value, onChange }) {
  return (
    <label className="field field--wide">
      <span>Prompt</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={5}
        placeholder="Describe the coding task, bug, optimization, or documentation request..."
      />
    </label>
  );
}

