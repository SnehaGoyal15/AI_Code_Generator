import { useEffect, useMemo, useState } from 'react';
import ActionSelector from './components/ActionSelector';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import CodeEditor from './components/CodeEditor';
import DownloadButton from './components/DownloadButton';
import ErrorMessage from './components/ErrorMessage';
import Header from './components/Header';
import HistorySidebar from './components/HistorySidebar';
import LanguageSelector from './components/LanguageSelector';
import LoadingIndicator from './components/LoadingIndicator';
import PromptInput from './components/PromptInput';
import ResultPanel from './components/ResultPanel';
import {
  AuthError,
  clearAuthToken,
  fetchCurrentUser,
  friendlyActionLabel,
  loginUser,
  logoutUser,
  registerUser,
  runAction,
  saveHistory,
  verifyLoginOtp,
} from './services/api';
import './styles/app.css';

const supportedLanguages = ['Python', 'Java', 'C', 'C++', 'JavaScript', 'SQL'];

const actionOptions = [
  { value: 'generate_code', label: 'Generate Code' },
  { value: 'explain_code', label: 'Explain Code' },
  { value: 'debug_code', label: 'Debug Code' },
  { value: 'optimize_code', label: 'Optimize Code' },
  { value: 'review_code', label: 'Review Code' },
  { value: 'generate_documentation', label: 'Generate Documentation' },
];

const initialResult = {
  historyId: null,
  actionType: 'generate_code',
  code: '',
  explanation: '',
  timeComplexity: '',
  spaceComplexity: '',
  issues: [],
  staticChecks: [],
  suggestions: [],
  qualityBreakdown: [],
  qualityScore: null,
  topImprovements: [],
  documentation: '',
};

const HISTORY_CACHE_PREFIX = 'codementor-ai-history-cache';
const ACTION_FILE_STEM = {
  generate_code: 'generate',
  explain_code: 'explain',
  debug_code: 'debug',
  optimize_code: 'optimize',
  review_code: 'review',
  generate_documentation: 'documentation',
};

const LANGUAGE_EXTENSION = {
  Python: 'py',
  Java: 'java',
  C: 'c',
  'C++': 'cpp',
  JavaScript: 'js',
  SQL: 'sql',
};

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

function getHistoryCacheKey(userId) {
  return `${HISTORY_CACHE_PREFIX}:${userId || 'anonymous'}`;
}

function buildDisplayRecord(source) {
  return {
    historyId: source.history_id ?? source.historyId ?? null,
    actionType: normalizeActionType(source.action_type ?? source.actionType),
    prompt: source.prompt ?? '',
    language: source.language ?? 'Python',
    code: source.code ?? source.generated_code ?? source.generatedCode ?? '',
    explanation: source.explanation ?? '',
    timeComplexity: source.time_complexity ?? source.timeComplexity ?? '',
    spaceComplexity: source.space_complexity ?? source.spaceComplexity ?? '',
    issues: source.issues ?? [],
    staticChecks: source.static_checks ?? source.staticChecks ?? [],
    suggestions: source.suggestions ?? [],
    qualityBreakdown: source.quality_breakdown ?? source.qualityBreakdown ?? [],
    qualityScore: source.quality_score ?? source.qualityScore ?? null,
    topImprovements: source.top_improvements ?? source.topImprovements ?? [],
    documentation: source.documentation ?? '',
    inputCode: source.code ?? source.input_code ?? source.inputCode ?? '',
  };
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

function writeHistoryCache(cacheKey, historyId, record) {
  if (!cacheKey) {
    return;
  }

  try {
    const cache = readHistoryCache(cacheKey);
    cache[String(historyId)] = record;
    window.localStorage.setItem(cacheKey, JSON.stringify(cache));
  } catch {
    // Non-blocking: history still exists in the backend.
  }
}

function getActionPayload({ actionType, prompt, language, inputCode }) {
  if (actionType === 'generate_code') {
    return { prompt, language, code: null };
  }

  return { prompt: '', language, code: inputCode };
}

function formatTimestampForFile(date = new Date()) {
  return date
    .toISOString()
    .replaceAll(':', '-')
    .replaceAll('.', '-')
    .replace('T', '_')
    .replace('Z', '');
}

function sanitizeFilePart(value) {
  return String(value || 'item')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'item';
}

function triggerDownload(filename, content, mimeType = 'text/plain;charset=utf-8') {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function App() {
  const [authStatus, setAuthStatus] = useState('loading');
  const [authView, setAuthView] = useState('login');
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');
  const [authForm, setAuthForm] = useState({
    name: '',
    email: '',
    password: '',
    otp: '',
  });
  const [loginStep, setLoginStep] = useState('credentials');
  const [authNotice, setAuthNotice] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('Python');
  const [actionType, setActionType] = useState('generate_code');
  const [prompt, setPrompt] = useState('Write a clean function that reverses a string.');
  const [inputCode, setInputCode] = useState('');
  const [result, setResult] = useState(initialResult);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;

    fetchCurrentUser()
      .then((user) => {
        if (!active) {
          return;
        }
        setCurrentUser(user);
        setAuthStatus('authenticated');
      })
      .catch(() => {
        if (!active) {
          return;
        }
        clearAuthToken();
        setCurrentUser(null);
        setAuthStatus('unauthenticated');
      });

    return () => {
      active = false;
    };
  }, []);

  const shouldShowInputEditor = actionType !== 'generate_code';
  const hasCodeOutput = Boolean(result.code && result.code.trim());
  const actionLabel = useMemo(
    () => friendlyActionLabel(actionType),
    [actionType],
  );
  const canDownloadCode = hasCodeOutput;
  const canDownloadReport = Boolean(prompt.trim() || hasCodeOutput || result.explanation || result.documentation);
  const historyCacheKey = currentUser?.id ? getHistoryCacheKey(currentUser.id) : null;

  function handleAuthFieldChange(field, value) {
    if (field === 'email' && loginStep === 'otp') {
      setLoginStep('credentials');
      setAuthNotice('');
      setAuthForm((current) => ({
        ...current,
        [field]: value,
        password: '',
        otp: '',
      }));
      return;
    }
    setAuthForm((current) => ({ ...current, [field]: value }));
  }

  async function handleLogin(event) {
    event.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    setAuthNotice('');

    try {
      if (loginStep === 'credentials') {
        const response = await loginUser({
          email: authForm.email,
          password: authForm.password,
        });

        if (response?.verification_required) {
          setLoginStep('otp');
          setAuthNotice('We sent a one-time code to your email. Enter it to finish signing in.');
          setAuthForm((current) => ({ ...current, password: '', otp: '' }));
          return;
        }

        setAuthError('We could not start OTP login right now.');
        return;
      }

      const response = await verifyLoginOtp({
        email: authForm.email,
        otp: authForm.otp,
      });

      setCurrentUser(response.user);
      setAuthStatus('authenticated');
      setAuthView('login');
      setLoginStep('credentials');
      setAuthNotice('');
      setAuthForm({ name: '', email: '', password: '', otp: '' });
    } catch (error) {
      if (error instanceof AuthError) {
        setAuthError(loginStep === 'otp' ? 'Invalid or expired OTP.' : 'Invalid email or password.');
      } else {
        setAuthError('We could not complete login right now.');
      }
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleRegister(event) {
    event.preventDefault();
    setAuthLoading(true);
    setAuthError('');

    try {
      const response = await registerUser({
        name: authForm.name,
        email: authForm.email,
        password: authForm.password,
      });
      setCurrentUser(response.user);
      setAuthStatus('authenticated');
      setAuthView('login');
      setLoginStep('credentials');
      setAuthNotice('');
      setAuthForm({ name: '', email: '', password: '', otp: '' });
    } catch (error) {
      if (error instanceof AuthError) {
        setAuthError('Authentication failed.');
      } else {
        setAuthError('We could not create your account right now.');
      }
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    logoutUser();
    setCurrentUser(null);
    setAuthStatus('unauthenticated');
    setAuthView('login');
    setAuthError('');
    setAuthNotice('');
    setLoginStep('credentials');
    setAuthForm({ name: '', email: '', password: '', otp: '' });
    setResult(initialResult);
    setPrompt('Write a clean function that reverses a string.');
    setInputCode('');
    setHistoryRefreshKey((current) => current + 1);
  }

  function handleResetLoginStep() {
    setLoginStep('credentials');
    setAuthNotice('');
    setAuthError('');
    setAuthForm((current) => ({ ...current, otp: '', password: '' }));
  }

  function handleSwitchToRegister() {
    setAuthView('register');
    setAuthError('');
    setAuthNotice('');
    setLoginStep('credentials');
    setAuthForm({ name: '', email: '', password: '', otp: '' });
  }

  function handleSwitchToLogin() {
    setAuthView('login');
    setAuthError('');
    setAuthNotice('');
    setLoginStep('credentials');
    setAuthForm((current) => ({ ...current, otp: '', password: '' }));
  }

  async function handleRunAction() {
    setLoading(true);
    setError('');

    try {
      const payload = getActionPayload({
        actionType,
        prompt,
        language: selectedLanguage,
        inputCode,
      });

      const response = await runAction(actionType, payload);
      const displayRecord = buildDisplayRecord({
        ...response,
        prompt,
        language: selectedLanguage,
        code: response.code,
        action_type: response.action_type || actionType,
      });

      setResult(displayRecord);

      if (displayRecord.historyId && historyCacheKey) {
        writeHistoryCache(historyCacheKey, displayRecord.historyId, {
          ...displayRecord,
          prompt,
          language: selectedLanguage,
          inputCode,
        });
      }

      setHistoryRefreshKey((current) => current + 1);
    } catch (error) {
      if (error instanceof AuthError) {
        handleLogout();
        setError('Your session expired. Please log in again.');
        return;
      }
      setError('We could not complete that action right now. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveToHistory() {
    setError('');

    try {
      const payload = {
        prompt,
        language: selectedLanguage,
        action_type: actionType,
        input_code: shouldShowInputEditor ? inputCode : null,
        generated_code: result.code || null,
        explanation: result.explanation || null,
        time_complexity: result.timeComplexity || null,
        space_complexity: result.spaceComplexity || null,
        suggestions: result.suggestions || [],
        quality_breakdown: result.qualityBreakdown || [],
        top_improvements: result.topImprovements || [],
      };

      const saved = await saveHistory(payload);
      const historyId = saved.id ?? saved.history_id;

      if (historyId && historyCacheKey) {
        writeHistoryCache(historyCacheKey, historyId, {
          ...result,
          historyId,
          prompt,
          language: selectedLanguage,
          inputCode,
        });
      }

      setHistoryRefreshKey((current) => current + 1);
    } catch (error) {
      if (error instanceof AuthError) {
        handleLogout();
        setError('Your session expired. Please log in again.');
        return;
      }
      setError('We could not save this result to history right now.');
    }
  }

  function handleDownload() {
    if (!canDownloadCode) {
      return;
    }

    const actionStem = ACTION_FILE_STEM[actionType] || sanitizeFilePart(actionType);
    const extension = LANGUAGE_EXTENSION[selectedLanguage] || 'txt';
    const filename = `codementor_${actionStem}_${formatTimestampForFile()}.${extension}`;

    triggerDownload(filename, result.code);
  }

  function handleDownloadFullReport() {
    const reportSections = [
      `Prompt:\n${prompt || 'N/A'}`,
      `Language:\n${selectedLanguage || 'N/A'}`,
      `Action:\n${actionLabel || 'N/A'}`,
      `Input Code:\n${inputCode || 'N/A'}`,
      `Output Code:\n${result.code || 'N/A'}`,
      `Explanation:\n${result.explanation || 'N/A'}`,
      `Complexity:\nTime: ${result.timeComplexity || 'N/A'}\nSpace: ${result.spaceComplexity || 'N/A'}`,
      `Issues:\n${result.issues.length ? result.issues.map((issue, index) => `${index + 1}. ${issue.type}: ${issue.message} | ${issue.fix}`).join('\n') : 'N/A'}`,
      `Suggestions:\n${result.suggestions.length ? result.suggestions.map((item, index) => `${index + 1}. ${item}`).join('\n') : 'N/A'}`,
      `Top Improvements:\n${result.topImprovements?.length ? result.topImprovements.map((item, index) => `${index + 1}. ${item}`).join('\n') : 'N/A'}`,
      `Rubric Breakdown:\n${result.qualityBreakdown?.length ? result.qualityBreakdown.map((item) => `${item.category}: ${item.score}/${item.max_score} - ${item.notes || 'No notes provided.'}`).join('\n') : 'N/A'}`,
      `Quality Score:\n${result.qualityScore === null || result.qualityScore === undefined ? 'N/A' : `${result.qualityScore}/10`}`,
      `Documentation:\n${result.documentation || 'N/A'}`,
      `Generated Timestamp:\n${new Date().toLocaleString()}`,
    ];

    const actionStem = ACTION_FILE_STEM[actionType] || sanitizeFilePart(actionType);
    const filename = `codementor_${actionStem}_${formatTimestampForFile()}.txt`;
    triggerDownload(filename, reportSections.join('\n\n'));
  }

  function handleCopyCode() {
    if (!hasCodeOutput || !navigator.clipboard) {
      setError('Copy is unavailable in this browser.');
      return;
    }

    navigator.clipboard
      .writeText(result.code)
      .catch(() => setError('We could not copy the code right now.'));
  }

  function handleHistorySelect(item) {
    setPrompt(item.prompt || '');
    setSelectedLanguage(item.language || 'Python');
    setActionType(item.actionType || 'generate_code');
    setInputCode(item.inputCode || '');
    setResult({
      historyId: item.historyId ?? item.id ?? null,
      actionType: item.actionType || 'generate_code',
      code: item.code || item.generatedCode || '',
      explanation: item.explanation || '',
      timeComplexity: item.timeComplexity || '',
      spaceComplexity: item.spaceComplexity || '',
      issues: item.issues || [],
      staticChecks: item.staticChecks || [],
      suggestions: item.suggestions || [],
      qualityBreakdown: item.qualityBreakdown || [],
      qualityScore: item.qualityScore ?? null,
      topImprovements: item.topImprovements || [],
      documentation: item.documentation || '',
    });
  }

  if (authStatus === 'loading') {
    return (
      <main className="shell">
        <LoadingIndicator />
      </main>
    );
  }

  if (authStatus === 'unauthenticated') {
    return (
      <main className="shell auth-shell">
        {authView === 'login' ? (
          <LoginPage
            values={authForm}
            onChange={handleAuthFieldChange}
            onSubmit={handleLogin}
            onToggleMode={handleSwitchToRegister}
            loading={authLoading}
            error={authError}
            notice={authNotice}
            loginStep={loginStep}
            onResetLoginStep={handleResetLoginStep}
          />
        ) : (
          <RegisterPage
            values={authForm}
            onChange={handleAuthFieldChange}
            onSubmit={handleRegister}
            onToggleMode={handleSwitchToLogin}
            loading={authLoading}
            error={authError}
            notice={authNotice}
          />
        )}
      </main>
    );
  }

  return (
    <main className="shell">
      <Header currentUser={currentUser} onLogout={handleLogout} />

      <section className="workspace-toolbar">
        <PromptInput value={prompt} onChange={setPrompt} />

        <div className="workspace-toolbar__controls">
          <LanguageSelector value={selectedLanguage} onChange={setSelectedLanguage} options={supportedLanguages} />
          <ActionSelector value={actionType} onChange={setActionType} options={actionOptions} />
        </div>

        {selectedLanguage === 'SQL' ? (
          <div className="sql-notice" role="status" aria-live="polite">
            <strong>SQL Analysis Only - No Query Execution.</strong>
            <span>
              SQL in CodeMentor AI is text-only. The app never connects to a real database or executes your query.
            </span>
          </div>
        ) : null}
      </section>

      <section className="workspace-layout">
        <HistorySidebar
          onSelect={handleHistorySelect}
          refreshToken={historyRefreshKey}
          cacheKey={historyCacheKey}
          onAuthError={handleLogout}
        />

        <div className="workspace-main">
          <div className="workspace-actions">
            <button
              type="button"
              className="button button--primary"
              onClick={handleRunAction}
              disabled={loading}
            >
              {loading ? 'Running...' : 'Run AI Action'}
            </button>
            <button type="button" className="button button--secondary" onClick={handleSaveToHistory}>
              Save to History
            </button>
            <DownloadButton disabled={!canDownloadCode} onClick={handleDownload} />
            <DownloadButton disabled={!canDownloadReport} onClick={handleDownloadFullReport} label="Download Full Report" />
          </div>

          <ErrorMessage message={error} />
          {loading ? <LoadingIndicator /> : null}

          {shouldShowInputEditor ? (
            <CodeEditor
              label="Input Code"
              language={selectedLanguage}
              value={inputCode}
              onChange={(value) => setInputCode(value || '')}
              height="280px"
              placeholder="Paste existing code here for explanation, debugging, optimization, or review."
            />
          ) : null}

          <ResultPanel
            language={selectedLanguage}
            result={result}
            actionLabel={actionLabel}
            onCopyCode={handleCopyCode}
            hasCodeOutput={hasCodeOutput}
          />
        </div>
      </section>
    </main>
  );
}
