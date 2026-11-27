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
  nextQuestion: (concept: string) => call<PracticeState>(`/practice/next?concept=${encodeURIComponent(concept)}`),
  answer: (question: string, choice: number | null, text: string | null) =>
    call<AnswerResult>('/answers', { method: 'POST', body: JSON.stringify({ question, choice, text }) }),
  tutorAsk: (message: string, language = 'auto') =>
    call<TutorReply>('/tutor/ask', { method: 'POST', body: JSON.stringify({ message, language }) }),
  tutorHint: (exercise: string, code: string, level: number, language = 'auto') =>
    call<TutorReply>('/tutor/hint', { method: 'POST', body: JSON.stringify({ exercise, code, level, language }) }),
}

// ---------------- teacher ----------------
export interface Weak { id: string; name: string; known: number; mastered: number; practised: number }
export interface Heatmap {
  concepts: { id: string; name: string }[]
  sections: { name: string; students: number; values: number[] }[]
}
export interface Overview {
  cohort: string
  week: number
  enrolled: number
  in_class: number
  left_before_week: number
  active_this_week: number
  high: number
  medium: number
  avg_mastered: number
  concepts_total: number
  weakest: Weak[]
  heatmap: Heatmap
  section_note: string
  review_open: number
}
export interface RiskStudent {
  student_id: string
  section: number
  level: 'high' | 'medium'
  risk: number
  reason: string
  why: string[]
  action: string
  level_action: string
  answers_total: number
  days_since_last: number
  acc_last10: number | null
  mastered: number
}
export type ReviewKind = 'similarity' | 'tampering' | 'low_mark'
export interface ReviewItem {
  id: string
  kind: ReviewKind
  exercise: string
  title: string
  why: string
  score: number
  decision: string | null
  options: string[]
}
export interface ReviewDetail extends Omit<ReviewItem, 'decision'> {
  stem: string
  decision: { decision: string; teacher: string; note: string; at: number } | null
  sides?: { label: string; code: string; matching: number[] }[]
  scores?: { combined: number; tokens: number; structure: number; meaning: number }
  code?: string
  grading?: { mark: number; passed: number; tests: number; rules_broken: string[]; status: string; failed: string[] }
}

export const teacherApi = {
  overview: () => call<Overview>('/class/overview'),
  atRisk: () => call<{ week: number; in_class: number; students: RiskStudent[] }>('/class/at-risk'),
  review: () => call<{ items: ReviewItem[]; open: number; counts: Record<ReviewKind, number> }>('/review'),
  reviewItem: (id: string) => call<ReviewDetail>(`/review/${encodeURIComponent(id)}`),
  decide: (id: string, decision: string, note: string) =>
    call<{ item: string; decision: string }>(`/review/${encodeURIComponent(id)}`, {
      method: 'POST', body: JSON.stringify({ decision, note }),
    }),
}

// ---------------- tutor ----------------
export interface TutorReply {
  text: string
  sources: { title: string; url: string }[]
  grounded: boolean
  language: string
  level: number | null
  level_name: string | null
  exercise: string | null
  leak_blocked: boolean
}

// ---------------- question practice ----------------
export interface Mastery { p_known: number | null; mastered: boolean; answers: number }
export interface PracticeQuestion { id: string; type: 'mcq' | 'short'; stem: string; code: string | null; difficulty: number; options?: string[] }
export interface PracticeState {
  concept: string
  concept_name: string
  total: number
  done: number
  mastery: Mastery
  has_code_exercise: boolean
  question: PracticeQuestion | null
}
export interface AnswerResult {
  correct: boolean
  right_answer: string
  misconception: string | null
  output: string | null
  before: Mastery
  after: Mastery
}

// ---------------- teacher extras ----------------
export interface HealthRow {
  id: string; type: string; concept: string; stem: string; code_line: string | null; author_level: number; measured_level: number | null
  discrimination: number | null; share_right: number | null; answers: number | null; reason: string
  decision: { decision: string; level: number | null } | null
}
export interface QuestionHealth {
  total: number
  counts: Record<string, number>
  retire: HealthRow[]
  relabel: HealthRow[]
  difficulty_agreement: { author: number; llm: number }
  generated: { asked: number; accepted: number; rate: number; funnel: { gate: string; rejected: number; still_in: number }[]; spread: Record<string, number> }
  source: string
  caveat: string
}
export interface EvalRun { label: string; exercise_turns: number; leaks: number; jailbreaks_resisted: number | null; fallbacks: number | null; correct: number | null; pedagogy: number | null; tone: number | null }
export interface TutorSafety {
  evaluation: EvalRun[]
  judge_caught_code_leaks: number | null
  live: { questions: number; hints: number; by_rung: Record<string, number>; urdulish_share: number | null; blocked: number; not_in_course: number; students: number }
  source: string
}
interface Side { dropped_by_week3: number; dropped_ever: number; concepts_known: number; hours: number }
interface Diff { diff: number; low: number; high: number }
export interface Impact {
  adaptive: { students: number; caveat: string; fixed: Side; adaptive: Side; diff: Record<keyof Side, Diff> }
  dropout_model: { lightgbm: number; baseline: number; ceiling_observable: number; ceiling_hidden: number; base_rate: number }
  grading: { kappa_final: number; kappa_tests_only: number; mae: number; within_2: number; reference: string }
  review_share: number
  sandbox: { attacks: number; contained: number }
  plagiarism: { false_alarm_rate: number; by_class: { students: number; pairs: number; copied_pairs: number; expected_flags: number; true: number; false: number; precision: number }[] }
  tutor: EvalRun[]
  sources: Record<string, string>
}

export const extrasApi = {
  health: () => call<QuestionHealth>('/questions/health'),
  decideQuestion: (id: string, decision: string, level: number | null) =>
    call<{ question: string }>(`/questions/${encodeURIComponent(id)}/decision`, { method: 'POST', body: JSON.stringify({ decision, level }) }),
  tutorSafety: () => call<TutorSafety>('/tutor/safety'),
  impact: () => call<Impact>('/impact'),
}
