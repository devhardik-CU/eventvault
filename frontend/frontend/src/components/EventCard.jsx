import { Link } from 'react-router-dom'
import { api } from '../api'
import { availability, formatDateTime } from '../utils'

export function Poster({ event, className = '' }) {
  return event.has_poster
    ? <img className={`poster ${className}`} src={api.posterUrl(event.id)} alt={`Poster for ${event.title}`} loading="lazy" />
    : <div className={`poster poster-fallback ${className}`} aria-hidden="true">{event.category_name.slice(0, 1)}</div>
}

export default function EventCard({ event }) {
  const a = availability(event)
  return (
    <article className="card event-card">
      <Poster event={event} />
      <div className="card-body">
        <div className="row-between">
          <span className="badge">{event.category_name}</span>
          <span className={`pill pill-${a.tone}`}>{a.label}</span>
        </div>
        <h3><Link to={`/events/${event.id}`}>{event.title}</Link></h3>
        <p className="muted">{formatDateTime(event.start_time)}</p>
        <p className="muted">{event.location}</p>
      </div>
    </article>
  )
}
