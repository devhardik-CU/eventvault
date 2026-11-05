import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { useAsync } from '../hooks'
import { useToast } from '../toast'
import { ErrorBox, Loading } from '../components/States'
import { fromLocalInput, toLocalInput } from '../utils'

const EMPTY = { title: '', description: '', location: '', start_time: '', end_time: '', capacity: '30', category_id: '' }

export default function EventForm() {
  const { id } = useParams()
  const editing = Boolean(id)
  const navigate = useNavigate()
  const notify = useToast()
  const cats = useAsync(() => api.categories(), [])
  const existing = useAsync(() => (editing ? api.event(id) : Promise.resolve(null)), [id])
  const [form, setForm] = useState(EMPTY)
  const [file, setFile] = useState(null)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const e = existing.data
    if (e) setForm({ title: e.title, description: e.description, location: e.location, capacity: String(e.capacity),
      category_id: String(e.category_id), start_time: toLocalInput(e.start_time), end_time: toLocalInput(e.end_time) })
  }, [existing.data])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const validate = () => {
    const e = {}
    if (form.title.trim().length < 3) e.title = 'Title must be at least 3 characters.'
    if (form.description.trim().length < 10) e.description = 'Description must be at least 10 characters.'
    if (form.location.trim().length < 2) e.location = 'Enter a location.'
    if (!form.category_id) e.category_id = 'Choose a category.'
    const cap = Number(form.capacity)
    if (!Number.isInteger(cap) || cap < 1) e.capacity = 'Capacity must be a whole number of at least 1.'
    if (!form.start_time) e.start_time = 'Choose a start time.'
    else if (!editing && new Date(form.start_time) <= new Date()) e.start_time = 'Start time must be in the future.'
    if (!form.end_time) e.end_time = 'Choose an end time.'
    else if (form.start_time && new Date(form.end_time) <= new Date(form.start_time)) e.end_time = 'End time must be after the start time.'
    if (file && file.size > 2 * 1024 * 1024) e.poster = 'Poster must be 2 MB or smaller.'
    if (file && !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) e.poster = 'Poster must be a JPEG, PNG or WebP image.'
    return e
  }

  const submit = async (ev) => {
    ev.preventDefault()
    setFormError('')
    const v = validate()
    setErrors(v)
    if (Object.keys(v).length) return
    setBusy(true)
    const body = { ...form, title: form.title.trim(), description: form.description.trim(), location: form.location.trim(),
      capacity: Number(form.capacity), category_id: Number(form.category_id),
      start_time: fromLocalInput(form.start_time), end_time: fromLocalInput(form.end_time) }
    let saved
    try {
      saved = editing ? await api.updateEvent(id, body) : await api.createEvent(body)
    } catch (err) {
      setErrors(err.fieldErrors || {}); setFormError(err.message); setBusy(false); return
    }
    if (file) {
      try { await api.uploadPoster(saved.id, file) } catch (err) {
        // The event itself was saved; be honest that only the poster failed.
        notify(`Event saved, but the poster was NOT uploaded: ${err.message}`, 'error')
        navigate(`/organizer/events/${saved.id}/edit`); return
      }
    }
    notify(editing ? 'Event updated.' : 'Event created.')
    navigate('/organizer')
  }

  const err = (k) => errors[k] && <p className="field-error" id={`${k}-err`}>{errors[k]}</p>
  const aria = (k) => ({ 'aria-invalid': Boolean(errors[k]), 'aria-describedby': errors[k] ? `${k}-err` : undefined })

  if (editing && existing.loading) return <Loading />
  if (editing && existing.error) return <ErrorBox message={existing.error} onRetry={existing.reload} />

  return (
    <>
      <Link to="/organizer">← My events</Link>
      <h1>{editing ? 'Edit event' : 'Create event'}</h1>
      <form className="card card-body form" onSubmit={submit} noValidate>
        {formError && <div className="notice notice-error" role="alert">{formError}</div>}
        <div className="field"><label htmlFor="title">Title</label><input id="title" value={form.title} onChange={set('title')} maxLength={150} {...aria('title')} />{err('title')}</div>
        <div className="field"><label htmlFor="category_id">Category</label>
          <select id="category_id" value={form.category_id} onChange={set('category_id')} {...aria('category_id')}>
            <option value="">Select a category…</option>
            {(cats.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>{err('category_id')}</div>
        <div className="field"><label htmlFor="description">Description</label><textarea id="description" rows={5} value={form.description} onChange={set('description')} maxLength={4000} {...aria('description')} />{err('description')}</div>
        <div className="field"><label htmlFor="location">Location</label><input id="location" value={form.location} onChange={set('location')} maxLength={200} {...aria('location')} />{err('location')}</div>
        <div className="two-col">
          <div className="field"><label htmlFor="start_time">Starts</label><input id="start_time" type="datetime-local" value={form.start_time} onChange={set('start_time')} {...aria('start_time')} />{err('start_time')}</div>
          <div className="field"><label htmlFor="end_time">Ends</label><input id="end_time" type="datetime-local" value={form.end_time} onChange={set('end_time')} {...aria('end_time')} />{err('end_time')}</div>
        </div>
        <div className="field"><label htmlFor="capacity">Capacity (number of spots)</label><input id="capacity" type="number" min="1" value={form.capacity} onChange={set('capacity')} {...aria('capacity')} />{err('capacity')}</div>
        <div className="field"><label htmlFor="poster">Poster image (optional, JPEG/PNG/WebP, max 2 MB)</label>
          <input id="poster" type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setFile(e.target.files[0] || null)} {...aria('poster')} />
          {existing.data?.has_poster && !file && <p className="hint">This event already has a poster. Choose a file to replace it.</p>}
          {err('poster')}</div>
        <div className="btn-row">
          <button className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : editing ? 'Save changes' : 'Create event'}</button>
          <Link className="btn btn-secondary" to="/organizer">Cancel</Link>
        </div>
      </form>
    </>
  )
}
