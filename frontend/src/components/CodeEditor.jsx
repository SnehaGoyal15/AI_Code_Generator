import Editor from '@monaco-editor/react';

const monacoLanguage = {
  Python: 'python',
  Java: 'java',
  C: 'c',
  'C++': 'cpp',
  JavaScript: 'javascript',
  SQL: 'sql',
};

export default function CodeEditor({
  label,
  language,
  value,
  onChange,
  readOnly = false,
  height = '260px',
  placeholder = '',
}) {
  return (
    <section className="editor-card">
      <div className="editor-card__header">
        <h2>{label}</h2>
        <span>{language}</span>
      </div>
      <Editor
        height={height}
        language={monacoLanguage[language] || 'plaintext'}
        theme="vs-dark"
        value={value || ''}
        onChange={onChange}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          smoothScrolling: true,
          scrollBeyondLastLine: false,
          readOnly,
          wordWrap: 'on',
          placeholder,
        }}
      />
    </section>
  );
}

