// Thin wrapper around fetch(): adds the auth token, parses errors into friendly messages.
const BASE = import.meta.env.VITE_API_URL || ''
const TOKEN_KEY = 'eventvault_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY))

let onUnauthorized = null
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

export class ApiError extends Error {
  constructor(message, status, fieldErrors = {}) {
    super(message)
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

async function request(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }

  let res
  try {
    res = await fetch(BASE + path, { method, headers, body: payload })
  } catch {
    throw new ApiError('Cannot reach the server. Please check your connection and try again.', 0)
  }
  let data = null
  try { data = await res.json() } catch { /* empty body */ }
  if (!res.ok) {
    if (res.status === 401 && token && onUnauthorized) onUnauthorized()
    const fieldErrors = {}
    for (const e of data?.errors || []) fieldErrors[e.field] = e.message
    const msg = typeof data?.detail === 'string' ? data.detail : 'Something went wrong. Please try again.'
    throw new ApiError(msg, res.status, fieldErrors)
  }
  return data
}

const qs = (params) => {
  const p = new URLSearchParams()
  Object.entries(params || {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') p.set(k, v) })
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const api = {
  register: (body) => request('/api/auth/register', { method: 'POST', body }),
  login: (body) => request('/api/auth/login', { method: 'POST', body }),
  me: () => request('/api/auth/me'),
  categories: () => request('/api/categories'),
  events: (params) => request(`/api/events${qs(params)}`),
  event: (id) => request(`/api/events/${id}`),
  myEvents: () => request('/api/events/mine'),
  createEvent: (body) => request('/api/events', { method: 'POST', body }),
  updateEvent: (id, body) => request(`/api/events/${id}`, { method: 'PUT', body }),
  cancelEvent: (id) => request(`/api/events/${id}/cancel`, { method: 'POST' }),
  attendees: (id) => request(`/api/events/${id}/attendees`),
  uploadPoster: (id, file) => { const f = new FormData(); f.append('file', file); return request(`/api/events/${id}/poster`, { method: 'POST', form: f }) },
  registerFor: (id) => request(`/api/events/${id}/register`, { method: 'POST' }),
  cancelRegistration: (id) => request(`/api/events/${id}/register`, { method: 'DELETE' }),
  myRegistrations: () => request('/api/registrations/mine'),
  analytics: () => request('/api/analytics/organizer'),
  posterUrl: (id) => `${BASE}/api/events/${id}/poster`,
}
