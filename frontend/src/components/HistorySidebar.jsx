import { useEffect, useState } from 'react';
import { AuthError, fetchHistory } from '../services/api';
const BACKEND_TO_UI_ACTION = {
  generate: 'generate_code',
  explain: 'explain_code',
  debug: 'debug_code',
  optimize: 'optimize_code',
  review: 'review_code',
  documentation: 'generate_documentation',
};

function normalizeActionType(actionType) {
  return BACKEND_TO_UI_ACTION[actionType] || actionType || 'generate_code';
}

function formatTimestamp(value) {
  return new Date(value).toLocaleString();
}

function readHistoryCache(cacheKey) {
  if (!cacheKey) {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(cacheKey);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function parseMaybeJsonArray(value) {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value;
  }

  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [value];
    } catch {
      return [value];
    }
  }

  return [];
}

function normalizeRecord(item, cacheKey) {
  const cache = readHistoryCache(cacheKey);
  const cached = cache[String(item.id)] || {};

  return {
    historyId: item.id,
    prompt: cached.prompt || item.prompt || '',
    language: cached.language || item.language || 'Python',
    actionType: normalizeActionType(cached.actionType || item.action_type),
    inputCode: cached.inputCode || item.input_code || '',
    code: cached.code || item.generated_code || '',
    explanation: cached.explanation || item.explanation || '',
    timeComplexity: cached.timeComplexity || item.time_complexity || '',
    spaceComplexity: cached.spaceComplexity || item.space_complexity || '',
    issues: cached.issues || parseMaybeJsonArray(item.issues),
    staticChecks: cached.staticChecks || parseMaybeJsonArray(item.static_checks),
    suggestions: cached.suggestions || parseMaybeJsonArray(item.suggestions),
    qualityBreakdown: cached.qualityBreakdown || parseMaybeJsonArray(item.quality_breakdown),
    qualityScore: cached.qualityScore ?? item.quality_score ?? null,
    topImprovements: cached.topImprovements || parseMaybeJsonArray(item.top_improvements),
    documentation: cached.documentation || item.documentation || '',
    createdAt: item.created_at,
  };
}

export default function HistorySidebar({ onSelect, refreshToken, cacheKey, onAuthError }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    setLoading(true);
    fetchHistory()
      .then((items) => {
        if (!active) return;
        setHistory(items.map((item) => normalizeRecord(item, cacheKey)));
        setError('');
      })
      .catch((error) => {
        if (!active) return;
        if (error instanceof AuthError) {
          onAuthError?.();
          return;
        }
        setError('Could not load saved history right now.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [refreshToken, cacheKey, onAuthError]);

  return (
    <aside className="history-sidebar">
      <div className="section-heading">
        <div>
          <p className="section-heading__eyebrow">Saved Work</p>
          <h2>History</h2>
        </div>
        <span>{history.length} items</span>
      </div>

      {loading ? <p className="muted">Loading history...</p> : null}
      {error ? <p className="error-box">{error}</p> : null}

      {!loading && !error && history.length === 0 ? (
        <p className="muted">No saved history yet.</p>
      ) : null}

      <div className="history-list">
        {history.map((item) => (
          <button
            key={item.historyId}
            type="button"
            className="history-item"
            onClick={() => onSelect(item)}
          >
            <strong>{item.actionType.replaceAll('_', ' ')}</strong>
            <span>{item.language}</span>
            <p>{item.prompt}</p>
            <small>{formatTimestamp(item.createdAt)}</small>
          </button>
        ))}
      </div>
    </aside>
  );
}
