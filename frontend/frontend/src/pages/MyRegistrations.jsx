import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAsync } from '../hooks'
import { useToast } from '../toast'
import { Empty, ErrorBox, Loading } from '../components/States'
import { formatDateTime, hasStarted } from '../utils'

export default function MyRegistrations() {
  const { data, error, loading, reload } = useAsync(() => api.myRegistrations(), [])
  const notify = useToast()
  const [busyId, setBusyId] = useState(null)

  const cancel = async (r) => {
    if (!window.confirm(`Cancel your registration for “${r.event_title}”?`)) return
    setBusyId(r.event_id)
    try { await api.cancelRegistration(r.event_id); notify('Registration cancelled.') } catch (e) { notify(e.message, 'error') }
    setBusyId(null); reload()
  }

  if (loading && !data) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={reload} />
  const active = data.filter((r) => r.status === 'registered')
  const cancelled = data.filter((r) => r.status === 'cancelled')

  return (
    <>
      <h1>My registrations</h1>
      {active.length === 0 && <Empty title="You haven’t registered for any events"><Link className="btn btn-primary" to="/events">Browse events</Link></Empty>}
      <ul className="list">
        {active.map((r) => (
          <li key={r.id} className="card card-body row-between wrap">
            <div>
              <h3><Link to={`/events/${r.event_id}`}>{r.event_title}</Link></h3>
              <p className="muted">{formatDateTime(r.event_start_time)} · {r.event_location}</p>
              {r.event_status === 'cancelled' && <p className="danger-text">This event was cancelled by the organizer.</p>}
              {r.event_status !== 'cancelled' && hasStarted(r.event_start_time) && <p className="muted">Event has started.</p>}
            </div>
            {r.event_status !== 'cancelled' && !hasStarted(r.event_start_time) &&
              <button className="btn btn-danger" disabled={busyId === r.event_id} onClick={() => cancel(r)}>Cancel registration</button>}
          </li>
        ))}
      </ul>
      {cancelled.length > 0 && <>
        <h2>Cancelled</h2>
        <ul className="list">{cancelled.map((r) => (
          <li key={r.id} className="card card-body muted"><Link to={`/events/${r.event_id}`}>{r.event_title}</Link> · {formatDateTime(r.event_start_time)}</li>
        ))}</ul>
      </>}
    </>
  )
}
