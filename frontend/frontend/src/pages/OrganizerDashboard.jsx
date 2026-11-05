import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAsync } from '../hooks'
import { useToast } from '../toast'
import { Empty, ErrorBox, Loading } from '../components/States'
import { availability, formatDateTime } from '../utils'

export default function OrganizerDashboard() {
  const { data, error, loading, reload } = useAsync(() => api.myEvents(), [])
  const notify = useToast()
  const [busyId, setBusyId] = useState(null)

  const cancelEvent = async (ev) => {
    if (!window.confirm(`Cancel “${ev.title}”? Registered participants will see it as cancelled. This cannot be undone.`)) return
    setBusyId(ev.id)
    try { await api.cancelEvent(ev.id); notify('Event cancelled.') } catch (e) { notify(e.message, 'error') }
    setBusyId(null); reload()
  }

  return (
    <>
      <div className="row-between wrap">
        <h1>My events</h1>
        <Link className="btn btn-primary" to="/organizer/events/new">+ Create event</Link>
      </div>
      {loading && !data && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && data.length === 0 && <Empty title="You haven’t created any events yet"><Link className="btn btn-primary" to="/organizer/events/new">Create your first event</Link></Empty>}
      {data && data.length > 0 && (
        <ul className="list">
          {data.map((ev) => {
            const a = availability(ev)
            const pct = Math.round((100 * ev.registered_count) / ev.capacity)
            return (
              <li key={ev.id} className="card card-body">
                <div className="row-between wrap">
                  <h3><Link to={`/events/${ev.id}`}>{ev.title}</Link></h3>
                  <span className={`pill pill-${a.tone}`}>{ev.status === 'cancelled' ? 'Cancelled' : a.label}</span>
                </div>
                <p className="muted">{formatDateTime(ev.start_time)} · {ev.location} · {ev.category_name}</p>
                <div className="meter" role="img" aria-label={`${ev.registered_count} of ${ev.capacity} spots filled`}><div style={{ width: `${pct}%` }} /></div>
                <p className="small muted">{ev.registered_count} / {ev.capacity} registered ({pct}%)</p>
                <div className="btn-row">
                  <Link className="btn btn-secondary" to={`/organizer/events/${ev.id}/attendees`}>Attendees</Link>
                  {ev.status !== 'cancelled' && <Link className="btn btn-secondary" to={`/organizer/events/${ev.id}/edit`}>Edit</Link>}
                  {ev.status !== 'cancelled' && <button className="btn btn-danger" disabled={busyId === ev.id} onClick={() => cancelEvent(ev)}>Cancel event</button>}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </>
  )
}
