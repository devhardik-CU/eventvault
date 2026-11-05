import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const doLogout = () => { logout(); navigate('/') }
  return (
    <>
      <a className="skip-link" href="#main">Skip to main content</a>
      <header className="site-header">
        <div className="container nav">
          <Link to="/" className="brand">Event<span>Vault</span></Link>
          <nav aria-label="Main" className="nav-links">
            <NavLink to="/events">Browse events</NavLink>
            {user?.role_name === 'participant' && <NavLink to="/my-registrations">My registrations</NavLink>}
            {user?.role_name === 'organizer' && <>
              <NavLink to="/organizer" end>My events</NavLink>
              <NavLink to="/organizer/analytics">Analytics</NavLink>
            </>}
          </nav>
          <div className="nav-auth">
            {user ? <>
              <span className="muted small">{user.full_name} · {user.role_name}</span>
              <button className="btn btn-secondary" onClick={doLogout}>Log out</button>
            </> : <>
              <Link className="btn btn-secondary" to="/login">Log in</Link>
              <Link className="btn btn-primary" to="/register">Sign up</Link>
            </>}
          </div>
        </div>
      </header>
      <main id="main" className="container main"><Outlet /></main>
      <footer className="site-footer"><div className="container muted small">EventVault · a student project for discovering and managing events</div></footer>
    </>
  )
}
