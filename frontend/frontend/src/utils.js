const dateFmt = new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
const timeFmt = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' })

export const formatDate = (iso) => dateFmt.format(new Date(iso))
export const formatTime = (iso) => timeFmt.format(new Date(iso))
export const formatDateTime = (iso) => `${formatDate(iso)}, ${formatTime(iso)}`

const pad = (n) => String(n).padStart(2, '0')
// ISO (UTC) -> value for <input type="datetime-local"> in the user's own time zone
export function toLocalInput(iso) {
  const d = new Date(iso)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
// datetime-local value -> ISO string in UTC
export const fromLocalInput = (v) => new Date(v).toISOString()

export const hasStarted = (iso) => new Date(iso) <= new Date()

export function availability(ev) {
  if (ev.status === 'cancelled') return { label: 'Cancelled', tone: 'danger' }
  if (hasStarted(ev.start_time)) return { label: 'Started', tone: 'muted' }
  if (ev.spots_left === 0) return { label: 'Full', tone: 'warn' }
  return { label: `${ev.spots_left} spot${ev.spots_left === 1 ? '' : 's'} left`, tone: 'ok' }
}
