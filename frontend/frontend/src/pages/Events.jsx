import { useState } from 'react'
import { api } from '../api'
import { useAsync, useDebounced } from '../hooks'
import EventCard from '../components/EventCard'
import { Empty, ErrorBox, Loading } from '../components/States'

export default function Events() {
  const [q, setQ] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const dq = useDebounced(q)
  const cats = useAsync(() => api.categories(), [])
  const { data, error, loading, reload } = useAsync(() => api.events({ q: dq, category_id: categoryId }), [dq, categoryId])
  const filtered = Boolean(dq || categoryId)

  return (
    <>
      <h1>Browse events</h1>
      <form className="filters" role="search" onSubmit={(e) => e.preventDefault()}>
        <div className="field grow">
          <label htmlFor="q">Search</label>
          <input id="q" type="search" value={q} maxLength={100} placeholder="Title, description or location" onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="cat">Category</label>
          <select id="cat" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">All categories</option>
            {(cats.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        {filtered && <button type="button" className="btn btn-secondary" onClick={() => { setQ(''); setCategoryId('') }}>Clear filters</button>}
      </form>

      {loading && <Loading label="Loading events…" />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {!loading && data && data.length === 0 && (
        <Empty title={filtered ? 'No events match your search' : 'No upcoming events yet'}>
          {filtered ? <p>Try a different keyword or clear the filters.</p> : <p>Check back soon.</p>}
        </Empty>
      )}
      {data && data.length > 0 && <div className="grid" aria-live="polite">{data.map((e) => <EventCard key={e.id} event={e} />)}</div>}
    </>
  )
}
