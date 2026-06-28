const runtimeEnv = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {};
const isLocalHost =
  typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
const API_BASE_URL =
  runtimeEnv.VITE_API_BASE_URL ||
  (isLocalHost ? 'http://127.0.0.1:8000' : '');
const USE_MOCK_AI = runtimeEnv.VITE_USE_MOCK_AI === 'true';
const AUTH_TOKEN_KEY = 'codementor-ai-auth-token';

const ACTION_ENDPOINTS = {
  generate_code: '/api/generate',
  explain_code: '/api/explain',
  debug_code: '/api/debug',
  optimize_code: '/api/optimize',
  review_code: '/api/review',
  generate_documentation: '/api/documentation',
};

const ACTION_LABELS = {
  generate_code: 'Generate Code',
  explain_code: 'Explain Code',
  debug_code: 'Debug Code',
  optimize_code: 'Optimize Code',
  review_code: 'Review Code',
  generate_documentation: 'Generate Documentation',
};

class AuthError extends Error {
  constructor(message = 'Authentication required.') {
    super(message);
    this.name = 'AuthError';
  }
}

function readStoredToken() {
  try {
    if (typeof window === 'undefined') {
      return '';
    }
    return window.localStorage.getItem(AUTH_TOKEN_KEY) || '';
  } catch {
    return '';
  }
}

let authToken = readStoredToken();

function setAuthToken(token) {
  authToken = token || '';
  try {
    if (typeof window === 'undefined') {
      return;
    }
    if (authToken) {
      window.localStorage.setItem(AUTH_TOKEN_KEY, authToken);
    } else {
      window.localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  } catch {
    // Ignore storage failures in local-only mode.
  }
}

function clearAuthToken() {
  setAuthToken('');
}

function getAuthToken() {
  return authToken;
}

function friendlyActionLabel(actionType) {
  return ACTION_LABELS[actionType] || 'Action';
}

function mockSuggestionSet() {
  return [
    'Add edge case handling.',
    'Write tests for the main workflow.',
    'Keep the implementation readable and modular.',
  ];
}

function buildMockResult({ actionType, prompt, language, code }) {
  const label = friendlyActionLabel(actionType);
  const basePrompt = (prompt || '').trim() || 'No prompt provided.';
  const baseCode = (code || '').trim();

  switch (actionType) {
    case 'explain_code':
      return {
        code: baseCode || '// Paste code to explain.',
        explanation: `This ${language} code is explained in simple terms. ${basePrompt}`,
        time_complexity: 'O(n)',
        space_complexity: 'O(1)',
        issues: [],
        static_checks: [],
        suggestions: ['Read the code from top to bottom.', 'Trace one example input by hand.'],
        quality_breakdown: [],
        quality_score: null,
        top_improvements: [],
        documentation: null,
      };
    case 'debug_code':
      return {
        code: baseCode || '// Paste buggy code here.',
        explanation: 'This mock debugger highlights likely issues and safer fixes.',
        time_complexity: 'O(n)',
        space_complexity: 'O(1)',
        issues: [
          {
            type: 'Logical Error',
            line_hint: 'General flow',
            message: 'A logic issue may be causing incorrect output.',
            fix: 'Review the control flow and expected conditions.',
          },
        ],
        static_checks: [],
        suggestions: ['Check variable names.', 'Guard against null or empty inputs.'],
        quality_breakdown: [],
        quality_score: null,
        top_improvements: [],
        documentation: null,
      };
    case 'optimize_code':
      return {
        code: baseCode || '// Paste code to optimize.',
        explanation: 'This mock optimizer suggests a more efficient and clearer version.',
        time_complexity: 'O(n)',
        space_complexity: 'O(1)',
        issues: [
          {
            type: 'Style Issue',
            line_hint: 'Repeated work',
            message: 'There may be unnecessary repeated computation.',
            fix: 'Cache repeated results and remove duplicate logic.',
          },
        ],
        static_checks: [],
        suggestions: ['Remove unnecessary loops.', 'Use direct lookups when possible.'],
        quality_breakdown: [],
        quality_score: null,
        top_improvements: [],
        documentation: null,
      };
    case 'review_code':
      return {
        code: baseCode || '// Paste code for review.',
        explanation: 'This review focuses on readability, maintainability, and safety. It may surface likely issues rather than guaranteed bugs.',
        time_complexity: 'O(n)',
        space_complexity: 'O(1)',
        issues: [
          {
            type: 'Style Issue',
            severity: 'Low',
            line_hint: 'Naming and structure',
            message: 'Potential issue: the code could be easier to scan.',
            fix: 'Use clearer names and reduce nesting where possible.',
          },
        ],
        static_checks: [],
        suggestions: ['Split large functions.', 'Use descriptive names.', 'Add comments for tricky logic.'],
        quality_breakdown: [
          {
            category: 'Correctness and potential bugs',
            score: 1,
            max_score: 2,
            notes: 'No guaranteed bug is visible, but one or two paths may deserve closer review.',
          },
          {
            category: 'Readability and naming',
            score: 1,
            max_score: 2,
            notes: 'The structure is understandable, but naming could be more consistent.',
          },
          {
            category: 'Efficiency',
            score: 1,
            max_score: 2,
            notes: 'Consider whether repeated work can be reduced.',
          },
          {
            category: 'Maintainability and structure',
            score: 2,
            max_score: 2,
            notes: 'The overall layout is reasonably easy to follow.',
          },
          {
            category: 'Documentation and comments',
            score: 1,
            max_score: 2,
            notes: 'Consider adding clearer comments or docstrings for non-obvious logic.',
          },
        ],
        quality_score: 6,
        top_improvements: [
          'Consider extracting repeated logic into smaller helper functions.',
          'Improve naming consistency so the flow is easier to scan.',
          'Add brief comments or docstrings for the most important branches.',
        ],
        documentation: null,
      };
    case 'generate_documentation':
      return {
        code: baseCode || '// Reference code or context goes here.',
        explanation: 'A starter documentation draft has been generated.',
        time_complexity: null,
        space_complexity: null,
        issues: [],
        static_checks: [],
        suggestions: ['Add installation steps.', 'Include usage examples.'],
        quality_breakdown: [],
        quality_score: null,
        top_improvements: [],
        documentation: `# ${language} Documentation\n\n## Overview\nThis project is documented using placeholder content.\n\n## Usage\nDescribe how to run and use the code here.\n`,
      };
    case 'generate_code':
    default:
      return {
        code:
          language === 'SQL'
            ? 'SELECT id, name\nFROM users\nORDER BY created_at DESC;'
            : `// Mock ${language} code generated from the prompt.\n${basePrompt}`,
        explanation: `Generated using a placeholder workflow for ${label.toLowerCase()}.`,
        time_complexity: 'O(n)',
        space_complexity: 'O(1)',
        issues: [],
        static_checks: [],
        suggestions: mockSuggestionSet(),
        quality_breakdown: [],
        quality_score: null,
        top_improvements: [],
        documentation: null,
      };
  }
}

function isEmptyAiResponse(response) {
  if (!response || typeof response !== 'object') {
    return true;
  }

  return !(
    response.code ||
    response.explanation ||
    response.documentation ||
    (Array.isArray(response.issues) && response.issues.length > 0) ||
    (Array.isArray(response.static_checks) && response.static_checks.length > 0) ||
    (Array.isArray(response.suggestions) && response.suggestions.length > 0) ||
    (Array.isArray(response.quality_breakdown) && response.quality_breakdown.length > 0) ||
    (Array.isArray(response.top_improvements) && response.top_improvements.length > 0) ||
    response.time_complexity ||
    response.space_complexity ||
    (response.quality_score !== null && response.quality_score !== undefined)
  );
}

async function parseJsonResponse(response) {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error('The server returned an invalid response.');
  }
}

async function request(path, options = {}, { auth = true } = {}) {
  if (!API_BASE_URL) {
    throw new Error('Backend URL is not configured for this deployment.');
  }

  if (auth && !authToken) {
    throw new AuthError();
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(auth && authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;

    if (response.status === 401) {
      throw new AuthError(typeof detail === 'string' ? detail : 'Authentication required.');
    }

    throw new Error(typeof detail === 'string' ? detail : 'Request failed.');
  }

  return parseJsonResponse(response);
}

export async function registerUser(payload) {
  const response = await request('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, { auth: false });

  if (response?.access_token) {
    setAuthToken(response.access_token);
  }

  return response;
}

export async function loginUser(payload) {
  const response = await request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, { auth: false });

  return response;
}

export async function verifyLoginOtp(payload) {
  const response = await request('/api/auth/verify-login-otp', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, { auth: false });

  if (response?.access_token) {
    setAuthToken(response.access_token);
  }

  return response;
}

export async function fetchCurrentUser() {
  return request('/api/auth/me');
}

export async function getHealth() {
  return request('/api/health', {}, { auth: false });
}

export async function fetchHistory() {
  return request('/api/history');
}

export async function saveHistory(payload) {
  return request('/api/history', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function runAction(actionType, payload) {
  const endpoint = ACTION_ENDPOINTS[actionType];

  if (!endpoint) {
    throw new Error('Unsupported action.');
  }

  if (USE_MOCK_AI) {
    return {
      ...buildMockResult({
        actionType,
        prompt: payload.prompt,
        language: payload.language,
        code: payload.code,
      }),
      history_id: Date.now(),
      action_type: actionType,
    };
  }

  try {
    const response = await request(endpoint, {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    if (USE_MOCK_AI || isEmptyAiResponse(response)) {
      return {
        ...buildMockResult({
          actionType,
          prompt: payload.prompt,
          language: payload.language,
          code: payload.code,
        }),
        history_id: response?.history_id ?? response?.historyId ?? Date.now(),
        action_type: response?.action_type ?? actionType,
        mock_mode: true,
        static_checks: response?.static_checks || [],
        quality_breakdown: response?.quality_breakdown || [],
        top_improvements: response?.top_improvements || [],
      };
    }

    return response;
  } catch (error) {
    if (error instanceof Error && /request failed|invalid response/i.test(error.message)) {
      return {
        ...buildMockResult({
          actionType,
          prompt: payload.prompt,
          language: payload.language,
          code: payload.code,
        }),
        history_id: Date.now(),
        action_type: actionType,
        mock_mode: true,
      };
    }
    throw error;
  }
}

export function getAuthTokenValue() {
  return authToken;
}

export function logoutUser() {
  clearAuthToken();
}

export { AuthError, setAuthToken, clearAuthToken, ACTION_LABELS, friendlyActionLabel, buildMockResult };
