import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { api, type ExerciseSummary } from '../../api'

export default function Practice() {
  const [params, setParams] = useSearchParams()
  const concept = params.get('concept')
  const list = useQuery({ queryKey: ['exercises'], queryFn: api.exercises })

  if (list.isLoading) return <div className="page" aria-busy="true"><div className="skeleton" style={{ height: 320 }} /></div>
  if (list.isError) return <div className="page"><p className="error-box">{(list.error as Error).message}</p></div>

  const all = list.data!
  const shown = concept ? all.filter((e) => e.concept_id === concept) : all
  const groups = new Map<string, ExerciseSummary[]>()
  for (const e of shown) {
    const k = e.lesson ?? 'Other'
    groups.set(k, [...(groups.get(k) ?? []), e])
  }

  return (
    <div className="page">
      <header className="page-head">
        <h1>Coding exercises</h1>
        <p className="muted">
          Write a function, run it, and see which tests pass. Hidden tests check cases the task
          describes; you'll see how they failed, not what they are.
        </p>
      </header>

      {concept && (
        <div className="filter-bar">
          <span className="pill pill-accent">{all.find((e) => e.concept_id === concept)?.concept ?? concept}</span>
          <button className="btn btn-ghost" onClick={() => setParams({})}>Show all {all.length}</button>
        </div>
      )}

      {concept && (
        <div className="panel q-link">
          <div>
            <h2>Questions on this concept</h2>
            <p className="small muted">Short questions with instant feedback; your mastery updates as you answer.</p>
          </div>
          <Link className="btn btn-primary" to={`/student/question?concept=${concept}`}>Start questions</Link>
        </div>
      )}

      {concept && shown.length === 0 && (
        <p className="muted">There is no coding exercise for this concept; the questions above cover it.</p>
      )}

      {[...groups.entries()].map(([lesson, items]) => (
        <section key={lesson} className="path-group">
          <h2 className="label">{lesson}</h2>
          <ul className="rows panel">
            {items.map((e) => (
              <li key={e.id} className="row ex-row">
                <Link to={`/student/exercise/${e.id}`} className="ex-link">
                  <code className="ex-fn">{e.function}</code>
                  <span className="small muted">{e.first_line}</span>
                </Link>
                <span className="small muted">{e.concept}</span>
                <span className="small muted num" title="Difficulty from 1 (easiest) to 5">Level {e.difficulty}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
