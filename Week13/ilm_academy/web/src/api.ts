// Typed calls to the FastAPI backend (ilm/api/main.py). The session is an httpOnly cookie,
// so every call sends credentials; the app never sees or stores the token itself.

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, {
      credentials: 'include',
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
      ...init,
    })
  } catch {
    throw new ApiError(0, "We couldn't reach the server. Check your connection; your code is saved on this device.")
  }
  if (!res.ok) {
    let message = `Something went wrong (${res.status}).`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') message = body.detail
    } catch { /* keep the generic message */ }
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
}

export type Role = 'student' | 'teacher'
export interface Me { username: string; name: string; role: Role }

export interface PathStep {
  concept: string
  name: string
  p_known: number
  kind: 'learn' | 'quick check'
  status: string
  lessons: string[]
  est_answers: number
  est_minutes: number
}
export interface Plan {
  mastered: string[]
  strongest: string[]
  weakest: string[]
  concepts_total: number
  quick_checks: string[]
  quick_check_minutes: number
  total_minutes: number
  minutes_per_day: number
  days: number
  message_urdulish: string | null
  path: PathStep[]
}

export interface ExerciseSummary {
  id: string
  function: string
  concept: string
  concept_id: string
  difficulty: number
  lesson: string | null
  first_line: string
}
export interface VisibleTest { call: string; expect: string | null; raises: string | null }
export interface RecentRun { id: string; status: string; created: number; mark: number | null; passed: number | null; total: number | null }
export interface Exercise extends ExerciseSummary {
  stem: string
  code: string | null
  starter: string
  visible_tests: VisibleTest[]
  hidden_tests: number
  recent?: RecentRun[]
}

export interface Result {
  mark: number
  passed: number
  total: number
  visible_failed: { call: string; expected: string; got: string; why: string }[]
  hidden_failed: number
  hidden_failed_how: { how: string; count: number }[]
  rules: string[]
  slow: boolean
  quality: string[]
  next_step: { kind: string; text: string }
  lesson: { title: string; url: string; lesson: string } | null
  sandbox: string
  message?: string
}
export interface Submission {
  id: string
  exercise: string
  status: 'queued' | 'running' | 'done' | 'error'
  result: Result | null
  created: number
  seconds: number | null
  code: string
}

export const api = {
  me: () => call<Me>('/me'),
  login: (username: string, password: string) =>
    call<Me>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => call<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
  path: () => call<Plan>('/me/path'),
  exercises: () => call<ExerciseSummary[]>('/exercises'),
  exercise: (id: string) => call<Exercise>(`/exercises/${encodeURIComponent(id)}`),
  submit: (exercise: string, code: string) =>
    call<{ id: string }>('/submissions', { method: 'POST', body: JSON.stringify({ exercise, code }) }),
  submission: (id: string) => call<Submission>(`/submissions/${encodeURIComponent(id)}`),
}
