import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { useAsync } from '../hooks'
import { useToast } from '../toast'
import { Poster } from '../components/EventCard'
import { ErrorBox, Loading } from '../components/States'
import { availability, formatDate, formatTime, hasStarted } from '../utils'

export default function EventDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const notify = useToast()
  const { data: ev, error, loading, reload } = useAsync(() => api.event(id), [id, user?.id])
  const [busy, setBusy] = useState(false)

  const act = async (fn, okMsg) => {
    setBusy(true)
    try { await fn(); notify(okMsg); reload() } catch (e) { notify(e.message, 'error'); reload() } finally { setBusy(false) }
  }

  if (loading && !ev) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={reload} />
  const a = availability(ev)
  const closed = ev.status === 'cancelled' || hasStarted(ev.start_time)

  let action
  if (!user) action = <Link className="btn btn-primary" to="/login" state={{ from: `/events/${ev.id}` }}>Log in to register</Link>
  else if (user.role_name === 'organizer') {
    action = user.id === ev.organizer_id
      ? <div className="btn-row"><Link className="btn btn-primary" to={`/organizer/events/${ev.id}/edit`}>Edit event</Link><Link className="btn btn-secondary" to={`/organizer/events/${ev.id}/attendees`}>View attendees</Link></div>
      : <p className="muted">Organizer accounts can’t register for events.</p>
  } else if (ev.is_registered) {
    action = (
      <div>
        <p className="success-text">✓ You are registered for this event.</p>
        {!closed && <button className="btn btn-danger" disabled={busy}
          onClick={() => window.confirm('Cancel your registration?') && act(() => api.cancelRegistration(ev.id), 'Registration cancelled.')}>Cancel registration</button>}
      </div>
    )
  } else if (closed) action = <p className="muted">Registration is closed for this event.</p>
  else if (ev.spots_left === 0) action = <p className="muted">This event is full.</p>
  else action = <button className="btn btn-primary" disabled={busy} onClick={() => act(() => api.registerFor(ev.id), 'You are registered!')}>{busy ? 'Registering…' : 'Register now'}</button>

  return (
    <article className="detail">
      <Link to="/events">← All events</Link>
      <Poster event={ev} className="poster-large" />
      <div className="row-between wrap">
        <h1>{ev.title}</h1>
        <span className={`pill pill-${a.tone}`}>{a.label}</span>
      </div>
      {ev.status === 'cancelled' && <div className="notice notice-error" role="alert">This event has been cancelled by the organizer.</div>}
      <dl className="facts">
        <div><dt>Category</dt><dd>{ev.category_name}</dd></div>
        <div><dt>Date</dt><dd>{formatDate(ev.start_time)}</dd></div>
        <div><dt>Time</dt><dd>{formatTime(ev.start_time)} – {formatTime(ev.end_time)}</dd></div>
        <div><dt>Location</dt><dd>{ev.location}</dd></div>
        <div><dt>Organizer</dt><dd>{ev.organizer_name}</dd></div>
        <div><dt>Registered</dt><dd>{ev.registered_count} / {ev.capacity}</dd></div>
      </dl>
      <h2>About this event</h2>
      <p className="prewrap">{ev.description}</p>
      <div className="action-panel">{action}</div>
    </article>
  )
}
