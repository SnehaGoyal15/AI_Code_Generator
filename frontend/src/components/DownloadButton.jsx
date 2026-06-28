export default function DownloadButton({ disabled, onClick, label = 'Download Code' }) {
  return (
    <button type="button" className="button button--secondary" onClick={onClick} disabled={disabled}>
      {label}
    </button>
  );
}
