import { Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth'
import { ToastProvider } from './toast'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Home from './pages/Home'
import Events from './pages/Events'
import EventDetail from './pages/EventDetail'
import { Login, Register } from './pages/AuthPages'
import MyRegistrations from './pages/MyRegistrations'
import OrganizerDashboard from './pages/OrganizerDashboard'
import EventForm from './pages/EventForm'
import Attendees from './pages/Attendees'
import Analytics from './pages/Analytics'

const NotFound = () => <div className="state"><h2>Page not found</h2><p>The page you are looking for does not exist.</p></div>
const org = (el) => <ProtectedRoute role="organizer">{el}</ProtectedRoute>

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="events" element={<Events />} />
            <Route path="events/:id" element={<EventDetail />} />
            <Route path="login" element={<Login />} />
            <Route path="register" element={<Register />} />
            <Route path="my-registrations" element={<ProtectedRoute role="participant"><MyRegistrations /></ProtectedRoute>} />
            <Route path="organizer" element={org(<OrganizerDashboard />)} />
            <Route path="organizer/analytics" element={org(<Analytics />)} />
            <Route path="organizer/events/new" element={org(<EventForm />)} />
            <Route path="organizer/events/:id/edit" element={org(<EventForm />)} />
            <Route path="organizer/events/:id/attendees" element={org(<Attendees />)} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </AuthProvider>
    </ToastProvider>
  )
}
