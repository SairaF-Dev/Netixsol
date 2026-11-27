import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, Play, RotateCcw, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, api, type Exercise as Ex, type Result, type Submission } from '../../api'
import { useMe } from '../../auth'
import CodeEditor from '../../components/CodeEditor'
import Inline from '../../components/Inline'
import { ago } from '../../format'

type Tab = 'task' | 'code' | 'result'

export default function ExercisePage() {
  const { id = '' } = useParams()
  const ex = useQuery({ queryKey: ['exercise', id], queryFn: () => api.exercise(id) })
  if (ex.isLoading) return <div className="page" aria-busy="true"><div className="skeleton" style={{ height: 420 }} /></div>
  if (ex.isError) return <div className="page"><p className="error-box">{(ex.error as Error).message}</p></div>
  return <Workspace ex={ex.data!} />
}

function useDraft(key: string, initial: string) {
  const [code, setCode] = useState(() => localStorage.getItem(key) ?? initial)
  const [savedAt, setSavedAt] = useState<Date | null>(null)
  useEffect(() => {
    const t = setTimeout(() => {
      localStorage.setItem(key, code)
      setSavedAt(new Date())
    }, 400)
    return () => clearTimeout(t)
  }, [key, code])
  return { code, setCode, savedAt }
}

function Workspace({ ex }: { ex: Ex }) {
  const { data: me } = useMe()
  const qc = useQueryClient()
  const draft = useDraft(`ilm:code:${me?.username}:${ex.id}`, ex.starter)
  const [tab, setTab] = useState<Tab>('code')
  const [runId, setRunId] = useState<string | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const started = useRef<number>(0)

  const run = useQuery<Submission>({
    queryKey: ['submission', runId],
    queryFn: () => api.submission(runId!),
    enabled: !!runId,
    refetchInterval: (q) => (q.state.data && ['done', 'error'].includes(q.state.data.status) ? false : 700),
  })
  const running = !!runId && (!run.data || ['queued', 'running'].includes(run.data.status))

  useEffect(() => {
    if (run.data && ['done', 'error'].includes(run.data.status)) {
      qc.invalidateQueries({ queryKey: ['exercise', ex.id] })
    }
  }, [run.data, qc, ex.id])

  async function onRun() {
    setRunError(null)
    setTab('result')
    started.current = Date.now()
    try {
      const { id } = await api.submit(ex.id, draft.code)
      setRunId(id)
    } catch (e) {
      setRunError(e instanceof ApiError ? e.message : 'Could not start the run.')
    }
  }

  function onReset() {
    if (window.confirm('Replace your code with the starting code? Your current code will be lost.')) {
      draft.setCode(ex.starter)
    }
  }

  return (
    <div className="exercise">
      <div className="ex-tabs" role="tablist" aria-label="Exercise">
        {(['task', 'code', 'result'] as Tab[]).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className="ex-tab" onClick={() => setTab(t)}>
            {t === 'task' ? 'Task' : t === 'code' ? 'Code' : 'Result'}
          </button>
        ))}
      </div>

      <section className={`ex-task ${tab === 'task' ? 'is-active' : ''}`} aria-label="Task">
        <Link to="/student/practice" className="back small"><ArrowLeft size={14} strokeWidth={1.5} /> All exercises</Link>
        <h1><code>{ex.function}</code></h1>
        <p className="small muted">{ex.concept}{ex.lesson ? ` · ${ex.lesson}` : ''} · Level {ex.difficulty}</p>
        <p className="ex-stem">{ex.stem}</p>
        {ex.code && <pre className="code-block">{ex.code}</pre>}
        <h2 className="label">Example tests</h2>
        <ul className="test-list">
          {ex.visible_tests.map((t) => (
            <li key={t.call}><code>{t.call}</code> <span className="muted">gives</span> <code>{t.expect ?? `raises ${t.raises}`}</code></li>
          ))}
        </ul>
        {ex.hidden_tests > 0 && (
          <p className="small muted">
            Plus {ex.hidden_tests} hidden test{ex.hidden_tests > 1 ? 's' : ''} for the cases the task describes.
          </p>
        )}
        {ex.recent && ex.recent.length > 0 && (
          <>
            <h2 className="label">Your recent runs</h2>
            <ul className="recent">
              {ex.recent.map((r) => (
                <li key={r.id}>
                  <span className="num">{r.status === 'done' ? `${r.passed} of ${r.total} passed` : r.status}</span>
                  <span className="small muted">{ago(r.created)}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className={`ex-code ${tab === 'code' ? 'is-active' : ''}`} aria-label="Your code">
        <div className="editor-frame">
          <CodeEditor value={draft.code} onChange={draft.setCode} label={`Code for ${ex.function}`} />
        </div>
        <div className="editor-bar">
          <button className="btn btn-primary" onClick={onRun} disabled={running || !draft.code.trim()}>
            <Play size={16} strokeWidth={1.5} /> {running ? 'Running…' : 'Run tests'}
          </button>
          <button className="btn btn-ghost" onClick={onReset} title="Back to the starting code">
            <RotateCcw size={16} strokeWidth={1.5} /> <span className="hide-sm">Reset</span>
          </button>
          <span className="small muted saved">
            {draft.savedAt ? `Saved on this device ${draft.savedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}
          </span>
        </div>
      </section>

      <section className={`ex-result ${tab === 'result' ? 'is-active' : ''}`} aria-label="Result" aria-live="polite">
        {runError && <p className="error-box" role="alert">{runError}</p>}
        {!runId && !runError && (
          <div className="result-empty">
            <p className="muted">Run your code to see which tests pass.</p>
            <p className="small muted">It runs in a sandbox with no internet and a 10-second limit, so a mistake can't break anything.</p>
          </div>
        )}
        {running && <Running startedAt={started.current} />}
        {run.data?.status === 'error' && <p className="error-box">{run.data.result?.message ?? 'Grading failed. Try running again.'}</p>}
        {run.data?.status === 'done' && run.data.result && <ResultView r={run.data.result} seconds={run.data.seconds} />}
      </section>
    </div>
  )
}

function Running({ startedAt }: { startedAt: number }) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(t)
  }, [])
  const s = Math.max(0, Math.round((now - startedAt) / 1000))
  return (
    <div className="running">
      <p>Running your code in a safe sandbox… <span className="num muted">{s}s</span></p>
      {s >= 10 && <p className="small muted">Your code is taking a long time. Is there a loop that never ends?</p>}
    </div>
  )
}

function ResultView({ r, seconds }: { r: Result; seconds: number | null }) {
  const allPass = r.passed === r.total
  return (
    <div className="result">
      <div className={`score ${allPass ? 'is-pass' : ''}`}>
        <span className="score-main num">{r.passed} of {r.total} tests passed</span>
        <span className="small muted num">Mark {r.mark}/10{seconds != null ? ` · checked in ${seconds}s` : ''}</span>
      </div>

      {(r.visible_failed.length > 0 || r.hidden_failed > 0) && (
        <ul className="fails">
          {r.visible_failed.map((v) => (
            <li key={v.call} className="fail">
              <X size={16} strokeWidth={2} className="fail-icon" aria-label="failed" />
              <div>
                <p><code>{v.call}</code> should give <code>{v.expected}</code>, got <code>{v.got}</code></p>
                {v.why !== "returned a wrong value" && <p className="small muted">It {v.why}.</p>}
              </div>
            </li>
          ))}
          {r.hidden_failed_how.map((h) => (
            <li key={h.how} className="fail">
              <X size={16} strokeWidth={2} className="fail-icon" aria-label="failed" />
              <p>{h.count} hidden test{h.count > 1 ? 's' : ''}: your code {h.how}.</p>
            </li>
          ))}
        </ul>
      )}
      {allPass && (
        <p className="pass-line"><Check size={16} strokeWidth={2} aria-hidden="true" /> Every test passed, including the hidden ones.</p>
      )}

      {r.rules.map((rule) => <p key={rule} className="note note-warn">Task rule: <Inline text={rule} /></p>)}
      {r.slow && <p className="note note-warn">Correct, but too slow on a large input.</p>}
      {r.sandbox === 'flagged for review' && (
        <p className="note note-warn">Your code's output looked like a test result, so this run goes to your teacher to check.</p>
      )}

      <div className="next-step">
        <h2 className="label">Next step</h2>
        <p><Inline text={r.next_step.text} /></p>
      </div>

      {r.quality.length > 0 && (
        <div>
          <h2 className="label">Code quality</h2>
          <ul className="quality">{r.quality.map((q) => <li key={q}><Inline text={q} /></li>)}</ul>
        </div>
      )}

      {r.lesson && (
        <p className="lesson-link">
          Rewatch: <a href={r.lesson.url} target="_blank" rel="noreferrer">{r.lesson.title}</a>
        </p>
      )}
    </div>
  )
}
