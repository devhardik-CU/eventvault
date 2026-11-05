// End-to-end UI tests: render the real React app and talk to a REAL running backend (see scripts/run_integration_tests.sh).
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const uniq = Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
const futureLocal = (days, hour) => {
  const d = new Date(Date.now() + days * 864e5); d.setHours(hour, 0, 0, 0)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:00`
}
const renderAt = (path) => render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)

async function logIn(user, email, password = 'DemoPass123') {
  await user.type(screen.getByLabelText('Email'), email)
  await user.type(screen.getByLabelText('Password'), password)
  await user.click(screen.getByRole('button', { name: 'Log in' }))
}

beforeEach(() => { localStorage.clear(); vi.spyOn(window, 'confirm').mockReturnValue(true) })
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('browsing (public)', () => {
  it('shows real events, filters by search, and shows an empty state', async () => {
    const user = userEvent.setup()
    renderAt('/events')
    expect(await screen.findByRole('link', { name: 'Intro to Python Workshop' })).toBeInTheDocument()
    await user.type(screen.getByLabelText('Search'), 'hackathon')
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Intro to Python Workshop' })).not.toBeInTheDocument())
    expect(screen.getByRole('link', { name: 'Inter-College Hackathon' })).toBeInTheDocument()
    await user.clear(screen.getByLabelText('Search'))
    await user.type(screen.getByLabelText('Search'), 'zzzz-no-match')
    expect(await screen.findByText('No events match your search')).toBeInTheDocument()
  })

  it('shows event details with a login prompt for anonymous visitors', async () => {
    renderAt('/events/1')
    expect(await screen.findByRole('heading', { name: 'Intro to Python Workshop' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Log in to register' })).toBeInTheDocument()
  })

  it('shows an error state for a missing event', async () => {
    renderAt('/events/99999')
    expect(await screen.findByRole('alert')).toHaveTextContent('Event not found')
  })
})

describe('participant workflow', () => {
  it('signs up, registers for an event, sees it in My registrations, then cancels', async () => {
    const user = userEvent.setup()
    renderAt('/register')
    await user.type(screen.getByLabelText('Full name'), 'Test Participant')
    await user.type(screen.getByLabelText('Email'), `p-${uniq}@example.com`)
    await user.type(screen.getByLabelText('Password'), 'GoodPass123')
    await user.click(screen.getByRole('button', { name: 'Sign up' }))

    // lands on events after signup; open the Campus 5K run
    await user.click(await screen.findByRole('link', { name: 'Campus 5K Fun Run' }))
    await user.click(await screen.findByRole('button', { name: 'Register now' }))
    expect(await screen.findByText(/You are registered for this event/)).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: 'My registrations' }))
    const row = (await screen.findByRole('link', { name: 'Campus 5K Fun Run' })).closest('li')
    await user.click(within(row).getByRole('button', { name: 'Cancel registration' }))
    await waitFor(() => expect(screen.getByText('You haven’t registered for any events')).toBeInTheDocument())
  })

  it('shows client-side validation messages on bad sign-up input', async () => {
    const user = userEvent.setup()
    renderAt('/register')
    await user.type(screen.getByLabelText('Password'), 'short')
    await user.click(screen.getByRole('button', { name: 'Sign up' }))
    expect(await screen.findByText('Please enter your full name.')).toBeInTheDocument()
    expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument()
    expect(screen.getByText('Password must be at least 8 characters.')).toBeInTheDocument()
  })

  it('shows the server error for a wrong password', async () => {
    const user = userEvent.setup()
    renderAt('/login')
    await logIn(user, 'participant@eventvault.demo', 'WrongPassword1')
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.')
  })

  it('blocks participants from organizer pages', async () => {
    const user = userEvent.setup()
    renderAt('/login')
    await logIn(user, 'participant@eventvault.demo')
    await screen.findByRole('link', { name: 'My registrations' })
    cleanup()
    renderAt('/organizer')
    expect(await screen.findByText('Access denied')).toBeInTheDocument()
  })

  it('sees a full event as full and cannot register', async () => {
    const user = userEvent.setup()
    renderAt('/login')
    await logIn(user, 'dev@eventvault.demo') // seeded participant who is NOT registered; the 3-seat clinic is already full
    await screen.findByRole('link', { name: 'My registrations' })
    await user.click(screen.getByRole('link', { name: 'Browse events' }))
    await user.click(await screen.findByRole('link', { name: 'Resume & Interview Clinic' }))
    expect(await screen.findByText('This event is full.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Register now' })).not.toBeInTheDocument()
  })
})

describe('organizer workflow', () => {
  it('validates the form, creates an event, sees it on the dashboard, and views analytics', async () => {
    const user = userEvent.setup()
    renderAt('/login')
    await logIn(user, 'organizer@eventvault.demo')
    await user.click(await screen.findByRole('link', { name: '+ Create event' }))

    await user.click(screen.getByRole('button', { name: 'Create event' })) // empty submit
    expect(await screen.findByText('Title must be at least 3 characters.')).toBeInTheDocument()
    expect(screen.getByText('Choose a category.')).toBeInTheDocument()

    const title = `UI Test Event ${uniq}`
    await user.type(screen.getByLabelText('Title'), title)
    await user.selectOptions(screen.getByLabelText('Category'), 'Workshop')
    await user.type(screen.getByLabelText('Description'), 'Created by the automated UI test.')
    await user.type(screen.getByLabelText('Location'), 'Room 101')
    fireEvent.change(screen.getByLabelText('Starts'), { target: { value: futureLocal(10, 10) } })
    fireEvent.change(screen.getByLabelText('Ends'), { target: { value: futureLocal(10, 9) } }) // ends BEFORE start
    await user.click(screen.getByRole('button', { name: 'Create event' }))
    expect(await screen.findByText('End time must be after the start time.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Ends'), { target: { value: futureLocal(10, 12) } })
    await user.click(screen.getByRole('button', { name: 'Create event' }))
    expect(await screen.findByRole('link', { name: title })).toBeInTheDocument() // back on dashboard

    await user.click(screen.getByRole('link', { name: 'Analytics' }))
    expect(await screen.findByRole('heading', { name: 'Analytics' })).toBeInTheDocument()
    expect(await screen.findByRole('cell', { name: title })).toBeInTheDocument()
    expect(screen.getByText('Average fill rate')).toBeInTheDocument()
  })
})
