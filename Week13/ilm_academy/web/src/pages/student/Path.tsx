import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, type PathStep } from '../../api'
import { knownLabel, lessonLabel, minutes } from '../../format'

export default function PathPage() {
  const plan = useQuery({ queryKey: ['path'], queryFn: api.path })
  if (plan.isLoading) return <div className="page" aria-busy="true"><div className="skeleton" style={{ height: 400 }} /></div>
  if (plan.isError) return <div className="page"><p className="error-box">{(plan.error as Error).message}</p></div>
  const p = plan.data!

  const groups: { lesson: string; steps: PathStep[] }[] = []
  for (const s of p.path) {
    const lesson = lessonLabel(s.lessons[0] ?? 'Other')
    const last = groups[groups.length - 1]
    if (last && last.lesson === lesson) last.steps.push(s)
    else groups.push({ lesson, steps: [s] })
  }

  return (
    <div className="page">
      <header className="page-head">
        <h1>Your path</h1>
        <p className="muted num">
          {p.path.length} concepts to go, about {minutes(p.total_minutes)} in total.
          Concepts you probably know are a quick check, not a full lesson.
        </p>
      </header>
      {groups.map((g, i) => (
        <section key={`${g.lesson}-${i}`} className="path-group">
          <h2 className="label">{g.lesson}</h2>
          <ol className="rows panel">
            {g.steps.map((s) => {
              const locked = s.status !== 'ready'
              return (
                <li key={s.concept} className={`row path-row${locked ? ' is-locked' : ''}`}>
                  <div className="path-name">
                    <span>{s.name}</span>
                    <span className="small muted">{locked ? s.status.replace(/^after /, 'After ') : 'Ready'}</span>
                  </div>
                  <div className="known" title={`P(known) ${s.p_known.toFixed(2)}`}>
                    <span className="known-bar" aria-hidden="true"><span style={{ width: `${Math.round(s.p_known * 100)}%` }} /></span>
                    <span className="small muted">{knownLabel(s.p_known)}</span>
                  </div>
                  <span className={`pill ${s.kind === 'learn' ? 'pill-accent' : ''}`}>{s.kind === 'learn' ? 'Learn' : 'Quick check'}</span>
                  <span className="small muted num path-min">{minutes(s.est_minutes)}</span>
                  <span className="path-action">{!locked && <Link className="btn btn-ghost" to={`/student/practice?concept=${s.concept}`}>Open</Link>}</span>
                </li>
              )
            })}
          </ol>
        </section>
      ))}
    </div>
  )
}
