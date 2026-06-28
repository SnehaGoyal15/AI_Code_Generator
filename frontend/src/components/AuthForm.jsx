export default function AuthForm({
  mode,
  values,
  onChange,
  onSubmit,
  onToggleMode,
  loading = false,
  error = '',
  notice = '',
  loginStep = 'credentials',
  onResetLoginStep,
}) {
  const isLogin = mode === 'login';
  const isOtpStep = isLogin && loginStep === 'otp';

  return (
    <section className="auth-card">
      <div className="auth-card__header">
        <p className="workspace-header__eyebrow">{isLogin ? 'Welcome back' : 'Create account'}</p>
        <h1>{isLogin ? 'Login to CodeMentor AI' : 'Register for CodeMentor AI'}</h1>
        <p className="workspace-header__copy">
          {isLogin
            ? 'Request a one-time code by email, then verify it to sign in securely.'
            : 'Create an account to save coding history securely with a JWT session.'}
        </p>
      </div>

      <form className="auth-form" onSubmit={onSubmit}>
        {!isLogin ? (
          <>
            <label className="field">
              <span>Name</span>
              <input
                type="text"
                value={values.name}
                onChange={(event) => onChange('name', event.target.value)}
                placeholder="Your name"
                autoComplete="name"
                required
              />
            </label>

            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={values.email}
                onChange={(event) => onChange('email', event.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </label>

            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={values.password}
                onChange={(event) => onChange('password', event.target.value)}
                placeholder="Create a strong password"
                autoComplete="new-password"
                required
                minLength={8}
              />
            </label>
          </>
        ) : isOtpStep ? null : (
          <>
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={values.email}
                onChange={(event) => onChange('email', event.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </label>

            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={values.password}
                onChange={(event) => onChange('password', event.target.value)}
                placeholder="At least 8 characters"
                autoComplete="current-password"
                required
                minLength={8}
              />
            </label>
          </>
        )}

        {isOtpStep ? (
          <label className="field">
            <span>One-Time Password</span>
            <input
              type="text"
              value={values.otp}
              onChange={(event) => onChange('otp', event.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="Enter the 6-digit code"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              maxLength={6}
            />
          </label>
        ) : null}

        {notice ? <div className="auth-notice">{notice}</div> : null}
        {error ? <div className="error-box">{error}</div> : null}

        <button type="submit" className="button button--primary" disabled={loading}>
          {loading ? 'Please wait...' : isOtpStep ? 'Verify OTP' : isLogin ? 'Send OTP' : 'Register'}
        </button>
      </form>

      {isLogin && isOtpStep && onResetLoginStep ? (
        <button type="button" className="button button--secondary auth-switch" onClick={onResetLoginStep}>
          Use a different email
        </button>
      ) : null}

      <button type="button" className="button button--secondary auth-switch" onClick={onToggleMode}>
        {isLogin ? 'Need an account? Register' : 'Already have an account? Login'}
      </button>
    </section>
  );
}
