import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

function AuthForm({ mode }) {
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const isRegister = mode === 'register'
  const [form, setForm] = useState({ full_name: '', email: '', password: '', role: 'participant' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const validate = () => {
    const e = {}
    if (isRegister && form.full_name.trim().length < 2) e.full_name = 'Please enter your full name.'
    if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = 'Enter a valid email address.'
    if (isRegister) {
      if (form.password.length < 8) e.password = 'Password must be at least 8 characters.'
      else if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) e.password = 'Password needs at least one letter and one number.'
    } else if (!form.password) e.password = 'Enter your password.'
    return e
  }

  const submit = async (ev) => {
    ev.preventDefault()
    setFormError('')
    const e = validate()
    setErrors(e)
    if (Object.keys(e).length) return
    setBusy(true)
    try {
      const user = isRegister ? await register(form) : await login(form.email, form.password)
      const dest = location.state?.from || (user.role_name === 'organizer' ? '/organizer' : '/events')
      navigate(dest, { replace: true })
    } catch (err) {
      setErrors(err.fieldErrors || {})
      setFormError(err.message)
    } finally { setBusy(false) }
  }

  const field = (id, label, props = {}) => (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} value={form[id]} onChange={set(id)} aria-invalid={Boolean(errors[id])} aria-describedby={errors[id] ? `${id}-err` : undefined} {...props} />
      {errors[id] && <p className="field-error" id={`${id}-err`}>{errors[id]}</p>}
    </div>
  )

  return (
    <div className="auth-card card card-body">
      <h1>{isRegister ? 'Create your account' : 'Welcome back'}</h1>
      <form onSubmit={submit} noValidate>
        {formError && <div className="notice notice-error" role="alert">{formError}</div>}
        {isRegister && field('full_name', 'Full name', { autoComplete: 'name', maxLength: 100 })}
        {field('email', 'Email', { type: 'email', autoComplete: 'email', maxLength: 255 })}
        {field('password', 'Password', { type: 'password', autoComplete: isRegister ? 'new-password' : 'current-password', maxLength: 72 })}
        {isRegister && <>
          <p className="hint">At least 8 characters, with a letter and a number.</p>
          <div className="field">
            <label htmlFor="role">I want to</label>
            <select id="role" value={form.role} onChange={set('role')}>
              <option value="participant">Join events (participant)</option>
              <option value="organizer">Create and manage events (organizer)</option>
            </select>
          </div>
        </>}
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? 'Please wait…' : isRegister ? 'Sign up' : 'Log in'}</button>
      </form>
      <p className="muted center">
        {isRegister ? <>Already have an account? <Link to="/login" state={location.state}>Log in</Link></> : <>New here? <Link to="/register" state={location.state}>Create an account</Link></>}
      </p>
    </div>
  )
}

export const Login = () => <AuthForm mode="login" />
export const Register = () => <AuthForm mode="register" />
