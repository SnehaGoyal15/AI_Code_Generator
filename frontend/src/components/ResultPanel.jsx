import CodeEditor from './CodeEditor';

const SEVERITY_ORDER = ['Critical', 'High', 'Medium', 'Low', 'Suggestion'];

function normalizeSeverity(value) {
  const label = String(value || 'Medium').trim().toLowerCase();
  if (label === 'critical') return 'Critical';
  if (label === 'high' || label === 'error') return 'High';
  if (label === 'medium' || label === 'warning') return 'Medium';
  if (label === 'low') return 'Low';
  return 'Suggestion';
}

function groupIssuesBySeverity() {
  return SEVERITY_ORDER.reduce((accumulator, severity) => {
    accumulator[severity] = [];
    return accumulator;
  }, {});
}

function buildGroupedIssues(issues) {
  const grouped = groupIssuesBySeverity();

  issues.forEach((issue) => {
    const severity = normalizeSeverity(issue.severity || issue.type);
    grouped[severity].push({ ...issue, severity, source: issue.source || 'AI' });
  });

  return grouped;
}

function ResultCard({ title, value, children }) {
  return (
    <article className="result-card">
      <div className="result-card__header">
        <h3>{title}</h3>
      </div>
      {children || <p>{value || 'No output yet.'}</p>}
    </article>
  );
}

function ComplexityBlock({ timeComplexity, spaceComplexity }) {
  return (
    <article className="result-card">
      <div className="result-card__header">
        <h3>Complexity</h3>
      </div>
      <dl className="complexity-grid">
        <div>
          <dt>Time</dt>
          <dd>{timeComplexity || 'No output yet.'}</dd>
        </div>
        <div>
          <dt>Space</dt>
          <dd>{spaceComplexity || 'No output yet.'}</dd>
        </div>
      </dl>
    </article>
  );
}

function QualitySummary({ score }) {
  const displayScore = score === null || score === undefined ? 'N/A' : score;

  return (
    <article className="result-card result-card--score">
      <div className="result-card__header">
        <h3>Quality Score</h3>
      </div>
      <div className="score-badge">
        <span className="score-badge__value">{displayScore}</span>
        <span className="score-badge__label">/10</span>
      </div>
      <p className="muted">
        This is a rubric-based review score. It highlights potential concerns, not guaranteed bugs.
      </p>
    </article>
  );
}

function QualityBreakdown({ breakdown }) {
  if (!breakdown.length) {
    return (
      <article className="result-card">
        <div className="result-card__header">
          <h3>Rubric Breakdown</h3>
        </div>
        <p>No breakdown available yet.</p>
      </article>
    );
  }

  return (
    <article className="result-card">
      <div className="result-card__header">
        <h3>Rubric Breakdown</h3>
      </div>
      <div className="quality-breakdown">
        {breakdown.map((item) => (
          <div className="quality-breakdown__item" key={item.category}>
            <div className="quality-breakdown__meta">
              <strong>{item.category}</strong>
              <span>{item.score}/{item.max_score}</span>
            </div>
            <p>{item.notes || 'No notes provided.'}</p>
          </div>
        ))}
      </div>
    </article>
  );
}

function IssuesBySeverity({ issues }) {
  const grouped = buildGroupedIssues(issues);

  return (
    <article className="result-card">
      <div className="result-card__header">
        <h3>Issues Found</h3>
      </div>
      {SEVERITY_ORDER.some((severity) => grouped[severity].length > 0) ? (
        <div className="severity-groups">
          {SEVERITY_ORDER.map((severity) => {
            const severityIssues = grouped[severity];
            if (!severityIssues.length) {
              return null;
            }

            return (
              <section className="severity-group" key={severity}>
                <div className="severity-group__header">
                  <strong>{severity}</strong>
                  <span>{severityIssues.length}</span>
                </div>
                <div className="issues-list">
                  {severityIssues.map((issue, index) => (
                    <div className="issue-item" key={`${severity}-${issue.source}-${issue.type || issue.message}-${index}`}>
                      <div className="issue-item__meta">
                        <strong>{issue.source}</strong>
                        <span>{issue.severity}</span>
                      </div>
                      <p>{issue.message}</p>
                      {issue.line_hint ? <small>Line hint: {issue.line_hint}</small> : null}
                      {issue.fix ? <small>Fix: {issue.fix}</small> : null}
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      ) : (
        <p>No issues found.</p>
      )}
    </article>
  );
}

function SuggestionsList({ suggestions, title = 'Suggestions' }) {
  return (
    <article className="result-card">
      <div className="result-card__header">
        <h3>{title}</h3>
      </div>
      {suggestions.length ? (
        <ul className="result-list">
          {suggestions.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>No suggestions yet.</p>
      )}
    </article>
  );
}

function TopImprovements({ items }) {
  return (
    <article className="result-card">
      <div className="result-card__header">
        <h3>Top 3 Improvements</h3>
      </div>
      {items.length ? (
        <ol className="result-list result-list--ordered">
          {items.slice(0, 3).map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ol>
      ) : (
        <p>No refactoring suggestions yet.</p>
      )}
    </article>
  );
}

export default function ResultPanel({ language, result, actionLabel, onCopyCode, hasCodeOutput }) {
  const suggestions = Array.isArray(result.suggestions) ? result.suggestions : [];
  const aiIssues = Array.isArray(result.issues) ? result.issues : [];
  const staticChecks = Array.isArray(result.staticChecks) ? result.staticChecks : [];
  const qualityBreakdown = Array.isArray(result.qualityBreakdown) ? result.qualityBreakdown : [];
  const topImprovements = Array.isArray(result.topImprovements) ? result.topImprovements : [];
  const mergedIssues = [
    ...aiIssues.map((issue) => ({ ...issue, source: issue.source || 'AI' })),
    ...staticChecks.map((check) => ({ ...check, source: 'Static Check' })),
  ];
  const reviewMode = result.actionType === 'review_code' || qualityBreakdown.length > 0 || topImprovements.length > 0;

  return (
    <section className="result-panel">
      <div className="section-heading">
        <div>
          <p className="section-heading__eyebrow">Output</p>
          <h2>{actionLabel || 'Result Panel'}</h2>
        </div>
        <span>{result.actionType || 'Awaiting action'}</span>
      </div>

      <div className="result-panel__grid">
        <div className="result-panel__wide">
          <div className="result-panel__code-header">
            <h3>Corrected/Generated Code</h3>
            <button type="button" className="button button--secondary button--compact" onClick={onCopyCode} disabled={!hasCodeOutput}>
              Copy Code
            </button>
          </div>
          <CodeEditor
            label={result.historyId ? `Saved #${result.historyId}` : 'Generated Code'}
            language={language}
            value={result.code}
            readOnly
            height="320px"
          />
        </div>

        <ResultCard title="Explanation" value={result.explanation} />
        <ComplexityBlock timeComplexity={result.timeComplexity} spaceComplexity={result.spaceComplexity} />

        {reviewMode ? <QualitySummary score={result.qualityScore} /> : null}
        {reviewMode ? <QualityBreakdown breakdown={qualityBreakdown} /> : null}
        <IssuesBySeverity issues={mergedIssues} />
        {reviewMode ? <TopImprovements items={topImprovements} /> : null}
        <SuggestionsList suggestions={suggestions} title={reviewMode ? 'Additional Suggestions' : 'Suggestions'} />

        {!reviewMode ? <QualitySummary score={result.qualityScore} /> : null}
        <ResultCard title="Documentation" value={result.documentation} />
      </div>
    </section>
  );
}
