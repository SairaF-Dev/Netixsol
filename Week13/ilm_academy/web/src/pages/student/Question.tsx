import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ApiError, api, type AnswerResult, type Mastery, type PracticeQuestion } from '../../api'
import { knownLabel } from '../../format'

export default function QuestionPage() {
  const [params] = useSearchParams()
  const concept = params.get('concept') ?? ''
  const state = useQuery({ queryKey: ['practice', concept], queryFn: () => api.nextQuestion(concept), enabled: !!concept })

  if (!concept) return <div className="page"><p className="error-box">No concept chosen.</p></div>
  if (state.isLoading) return <div className="page" aria-busy="true"><div className="skeleton" style={{ height: 360 }} /></div>
  if (state.isError) return <div className="page"><p className="error-box">{(state.error as Error).message}</p></div>
  const s = state.data!

  return (
    <div className="page question-page">
      <Link to="/student" className="back small"><ArrowLeft size={14} strokeWidth={1.5} /> Today</Link>
      <header className="page-head">
        <h1>{s.concept_name}</h1>
        <p className="muted num small">
          {s.done} of {s.total} questions right so far · <MasteryLine m={s.mastery} />
        </p>
      </header>
      {s.question
        ? <Asker key={`${s.question.id}-${s.mastery.answers}`} q={s.question} concept={concept} position={s.done + 1} total={s.total} />
        : <Finished name={s.concept_name} concept={concept} hasCode={s.has_code_exercise} total={s.total} />}
    </div>
  )
}

function MasteryLine({ m }: { m: Mastery }) {
  if (m.p_known == null) return null
  return <>{m.mastered ? 'Mastered' : knownLabel(m.p_known)} <span className="muted">(P(known) {m.p_known.toFixed(2)})</span></>
}

function Asker({ q, concept, position, total }: { q: PracticeQuestion; concept: string; position: number; total: number }) {
  const qc = useQueryClient()
  const [choice, setChoice] = useState<number | null>(null)
  const [text, setText] = useState('')
  const [result, setResult] = useState<AnswerResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const ready = q.type === 'mcq' ? choice !== null : text.trim().length > 0

  async function check() {
    if (!ready || busy || result) return
    setBusy(true)
    setError(null)
    try {
      setResult(await api.answer(q.id, q.type === 'mcq' ? choice : null, q.type === 'short' ? text : null))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not check the answer.')
    } finally {
      setBusy(false)
    }
  }

  function next() {
    qc.invalidateQueries({ queryKey: ['practice', concept] })
    qc.invalidateQueries({ queryKey: ['path'] })
  }

  // keyboard: 1-5 pick an option, Enter checks / goes on
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'TEXTAREA' || (e.target as HTMLElement).tagName === 'INPUT') {
        if (e.key === 'Enter' && q.type === 'short') { e.preventDefault(); if (result) next(); else check() }
        return
      }
      const n = Number(e.key)
      if (q.type === 'mcq' && !result && n >= 1 && n <= (q.options?.length ?? 0)) setChoice(n - 1)
      if (e.key === 'Enter') { if (result) next(); else check() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  return (
    <section className="question panel" aria-labelledby="q-stem">
      <p className="small muted num">Question {Math.min(position, total)} of {total} · Level {q.difficulty}</p>
      <p id="q-stem" className="q-stem">{q.stem}</p>
      {q.code && <pre className="code-block">{q.code}</pre>}

      {q.type === 'mcq' ? (
        <div className="options" role="radiogroup" aria-labelledby="q-stem">
          {q.options!.map((o, i) => {
            const state = result ? (o === result.right_answer ? 'is-right' : i === choice ? 'is-wrong' : '') : ''
            return (
              <button key={i} role="radio" aria-checked={choice === i} disabled={!!result}
                      className={`option ${choice === i ? 'is-chosen' : ''} ${state}`} onClick={() => setChoice(i)}>
                <span className="option-key num" aria-hidden="true">{i + 1}</span>
                <span className="option-text">{o}</span>
                {state === 'is-right' && <Check size={16} strokeWidth={2} aria-label="correct answer" />}
                {state === 'is-wrong' && <X size={16} strokeWidth={2} aria-label="your answer" />}
              </button>
            )
          })}
        </div>
      ) : (
        <label className="field">
          <span>Your answer</span>
          <input value={text} onChange={(e) => setText(e.target.value)} disabled={!!result} maxLength={300}
                 autoCapitalize="none" autoComplete="off" spellCheck={false} className="mono-input" />
        </label>
      )}

      {error && <p className="error-box" role="alert">{error}</p>}

      {!result ? (
        <div className="q-actions">
          <button className="btn btn-primary" onClick={check} disabled={!ready || busy}>{busy ? 'Checking…' : 'Check'}</button>
          {q.type === 'mcq' && <span className="small muted hide-sm">Keys 1 to {q.options!.length} pick an option, Enter checks.</span>}
        </div>
      ) : (
        <div className={`q-result ${result.correct ? 'is-right' : 'is-wrong'}`} aria-live="polite">
          <p className="q-verdict">{result.correct ? 'Right.' : 'Not quite.'}</p>
          {!result.correct && <p>The answer is <code>{result.right_answer}</code>.</p>}
          {result.misconception && <p>That option comes from a common mix-up: {result.misconception}.</p>}
          {result.output != null && <p className="small muted">The program really prints: <code>{result.output}</code></p>}
          <p className="small muted num">
            {result.before.p_known != null && result.after.p_known != null && (
              <>
                {result.after.mastered ? 'Mastered' : knownLabel(result.after.p_known)} · P(known){' '}
                {result.before.p_known.toFixed(2)} → {result.after.p_known.toFixed(2)}
              </>
            )}
          </p>
          <button className="btn btn-primary" onClick={next} autoFocus>Next question</button>
        </div>
      )}
    </section>
  )
}

function Finished({ name, concept, hasCode, total }: { name: string; concept: string; hasCode: boolean; total: number }) {
  return (
    <section className="panel empty">
      <h2>You've answered all {total} questions on {name}</h2>
      <p className="muted">Each one has been answered correctly at least once.</p>
      <div className="q-actions">
        {hasCode && <Link className="btn btn-primary" to={`/student/practice?concept=${concept}`}>Try the coding exercise</Link>}
        <Link className="btn" to="/student">Back to Today</Link>
      </div>
    </section>
  )
}
