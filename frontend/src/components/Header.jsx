export default function Header({ currentUser, onLogout }) {
  return (
    <header className="workspace-header">
      <div className="workspace-header__brand">
        <p className="workspace-header__eyebrow">AI Coding Workspace</p>
        <h1>CodeMentor AI</h1>
        <p className="workspace-header__copy">
          A structured workspace for generating, explaining, debugging, optimizing, and reviewing code.
        </p>
      </div>
      <div className="workspace-header__panel">
        <span className="workspace-header__badge">Authenticated session</span>
        {currentUser ? (
          <div className="header-user">
            <span className="header-user__label">Signed in as</span>
            <strong>{currentUser.email}</strong>
            <button type="button" className="button button--secondary button--compact" onClick={onLogout}>
              Logout
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}
