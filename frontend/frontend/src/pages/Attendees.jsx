import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { useAsync } from '../hooks'
import { Empty, ErrorBox, Loading } from '../components/States'
import { formatDateTime } from '../utils'

export default function Attendees() {
  const { id } = useParams()
  const ev = useAsync(() => api.event(id), [id])
  const { data, error, loading, reload } = useAsync(() => api.attendees(id), [id])
  return (
    <>
      <Link to="/organizer">← My events</Link>
      <h1>Attendees{ev.data ? `: ${ev.data.title}` : ''}</h1>
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && data.length === 0 && <Empty title="No one has registered yet" />}
      {data && data.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Registered attendees</caption>
            <thead><tr><th scope="col">Name</th><th scope="col">Email</th><th scope="col">Registered</th></tr></thead>
            <tbody>{data.map((a) => <tr key={a.registration_id}><td>{a.full_name}</td><td>{a.email}</td><td>{formatDateTime(a.registered_at)}</td></tr>)}</tbody>
          </table>
        </div>
      )}
    </>
  )
}
