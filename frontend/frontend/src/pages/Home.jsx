import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAsync } from '../hooks'
import EventCard from '../components/EventCard'
import { Empty, ErrorBox, Loading } from '../components/States'
import { useAuth } from '../auth'

export default function Home() {
  const { user } = useAuth()
  const { data, error, loading, reload } = useAsync(() => api.events({ limit: 3 }), [])
  return (
    <>
      <section className="hero">
        <h1>Find your next campus event</h1>
        <p>Workshops, seminars, competitions and student activities, all in one place. Register in a click and manage everything you have signed up for.</p>
        <div className="hero-actions">
          <Link className="btn btn-primary btn-lg" to="/events">Browse events</Link>
          {!user && <Link className="btn btn-secondary btn-lg" to="/register">Create an account</Link>}
        </div>
      </section>

      <section aria-labelledby="upcoming">
        <div className="row-between"><h2 id="upcoming">Coming up</h2><Link to="/events">See all events →</Link></div>
        {loading && <Loading />}
        {error && <ErrorBox message={error} onRetry={reload} />}
        {data && data.length === 0 && <Empty title="No upcoming events yet">Check back soon, or ask an organizer to add one.</Empty>}
        {data && data.length > 0 && <div className="grid">{data.map((e) => <EventCard key={e.id} event={e} />)}</div>}
      </section>

      <section aria-labelledby="how" className="steps">
        <h2 id="how">How it works</h2>
        <div className="grid">
          <div className="card card-body"><h3>1. Discover</h3><p className="muted">Search and filter events by category, date and place.</p></div>
          <div className="card card-body"><h3>2. Register</h3><p className="muted">Reserve your spot instantly. Cancel any time before the event starts.</p></div>
          <div className="card card-body"><h3>3. Organize</h3><p className="muted">Organizers publish events, track sign-ups and see participation insights.</p></div>
        </div>
      </section>
    </>
  )
}
