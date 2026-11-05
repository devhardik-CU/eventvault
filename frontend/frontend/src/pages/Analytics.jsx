import { api } from '../api'
import { useAsync } from '../hooks'
import { Empty, ErrorBox, Loading } from '../components/States'
import { formatDate } from '../utils'

const Stat = ({ label, value }) => <div className="card card-body stat"><span className="stat-value">{value}</span><span className="muted">{label}</span></div>

export default function Analytics() {
  const { data: d, error, loading, reload } = useAsync(() => api.analytics(), [])
  if (loading && !d) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={reload} />
  const maxDaily = Math.max(1, ...d.registrations_last_14_days.map((x) => x.registrations))
  const maxCat = Math.max(1, ...d.by_category.map((x) => x.registrations))

  return (
    <>
      <h1>Analytics</h1>
      <p className="muted">Calculated live from your saved events and registrations.</p>
      <div className="stats">
        <Stat label="Total events" value={d.total_events} />
        <Stat label="Upcoming events" value={d.upcoming_events} />
        <Stat label="Cancelled events" value={d.cancelled_events} />
        <Stat label="Active registrations" value={d.total_registrations} />
        <Stat label="Cancelled registrations" value={d.total_cancellations} />
        <Stat label="Average fill rate" value={`${d.average_fill_rate_percent}%`} />
      </div>

      {d.total_events === 0 ? <Empty title="No data yet">Create an event to start seeing participation insights.</Empty> : <>
        <h2>Registrations per event</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">Event</th><th scope="col">Category</th><th scope="col">Date</th><th scope="col">Registered</th><th scope="col">Cancelled</th><th scope="col">Fill rate</th></tr></thead>
            <tbody>{d.events.map((e) => (
              <tr key={e.event_id}>
                <td>{e.title}</td><td>{e.category_name}</td><td>{formatDate(e.start_time)}</td>
                <td>{e.registered_count} / {e.capacity}</td><td>{e.cancelled_count}</td>
                <td><div className="meter small-meter" role="img" aria-label={`${e.fill_rate_percent}% full`}><div style={{ width: `${Math.min(e.fill_rate_percent, 100)}%` }} /></div> {e.fill_rate_percent}%</td>
              </tr>))}</tbody>
          </table>
        </div>

        <div className="two-col">
          <section>
            <h2>By category</h2>
            {d.by_category.length === 0 ? <p className="muted">No active events.</p> : <ul className="bars">{d.by_category.map((c) => (
              <li key={c.category_name}><span>{c.category_name} <span className="muted small">({c.events} event{c.events === 1 ? '' : 's'})</span></span>
                <div className="meter"><div style={{ width: `${(100 * c.registrations) / maxCat}%` }} /></div><strong>{c.registrations}</strong></li>))}</ul>}
          </section>
          <section>
            <h2>New registrations, last 14 days</h2>
            <ul className="bars">{d.registrations_last_14_days.map((x) => (
              <li key={x.date}><span className="small">{formatDate(x.date + 'T00:00:00Z').replace(/, \d{4}$/, '')}</span>
                <div className="meter"><div style={{ width: `${(100 * x.registrations) / maxDaily}%` }} /></div><strong>{x.registrations}</strong></li>))}</ul>
          </section>
        </div>
      </>}
    </>
  )
}
