import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import { Loading } from './States'

export default function ProtectedRoute({ role, children }) {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return <Loading />
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (role && user.role_name !== role) {
    return <div className="state state-error" role="alert"><h2>Access denied</h2><p>This page is only available to {role}s.</p></div>
  }
  return children
}
