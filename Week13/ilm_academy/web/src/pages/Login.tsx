import { useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError, api } from '../api'
import { homeFor, useMe } from '../auth'

export default function Login() {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (me) return <Navigate to={homeFor(me.role)} replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const user = await api.login(username, password)
      qc.setQueryData(['me'], user)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from && from.startsWith(homeFor(user.role)) ? from : homeFor(user.role), { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed. Try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <section className="login-about">
        <div className="login-brand">
          <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" rx="6" fill="var(--accent)" />
            <circle cx="16" cy="9.5" r="2.75" fill="var(--paper)" /><rect x="13.75" y="14" width="4.5" height="11" rx="1.2" fill="var(--paper)" />
          </svg>
          <span>Ilm Academy</span>
        </div>
        <h1>Learn Python one concept at a time.</h1>
        <p className="muted">
          Lessons from Harvard's CS50P and MIT 6.0001. Your path skips what you already know,
          your code is checked the moment you run it, and the tutor helps you think instead of
          handing you the answer.
        </p>
        <dl className="login-facts">
          <div><dt className="num">65</dt><dd>concepts, in the order the lectures teach them</dd></div>
          <div><dt className="num">225</dt><dd>practice questions; coding and output questions are checked by running the code</dd></div>
          <div><dt className="num">4</dt><dd>hint levels, from a guiding question to a similar worked example</dd></div>
        </dl>
      </section>

      <section className="login-form-wrap">
        <form className="login-form panel" onSubmit={onSubmit} noValidate>
          <h2>Log in</h2>
          <label className="field">
            <span>Username</span>
            <input
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <p className="error-box" role="alert">{error}</p>}
          <button className="btn btn-primary" type="submit" disabled={busy || !username || !password}>
            {busy ? 'Logging in…' : 'Log in'}
          </button>
          <p className="small muted">
            Demo accounts: <code>ali</code> or <code>sara</code> (students), <code>teacher</code>.
            {import.meta.env.DEV && <> Dev password: <code>ilm-demo-2026</code>.</>}
          </p>
        </form>
      </section>
    </div>
  )
}
