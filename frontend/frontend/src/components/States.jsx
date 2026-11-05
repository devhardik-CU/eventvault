export const Loading = ({ label = 'Loading…' }) => (
  <div className="state" role="status"><span className="spinner" aria-hidden="true" />{label}</div>
)

export const ErrorBox = ({ message, onRetry }) => (
  <div className="state state-error" role="alert">
    <p>{message}</p>
    {onRetry && <button className="btn btn-secondary" onClick={onRetry}>Try again</button>}
  </div>
)

export const Empty = ({ title, children }) => (
  <div className="state">
    <h3>{title}</h3>
    {children}
  </div>
)
