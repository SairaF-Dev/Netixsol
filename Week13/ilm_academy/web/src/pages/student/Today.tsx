import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, type PathStep } from '../../api'
import { useMe } from '../../auth'
import { lessonLabel, minutes } from '../../format'

export default function Today() {
  const { data: me } = useMe()
  const plan = useQuery({ queryKey: ['path'], queryFn: api.path })

  if (plan.isLoading) return <TodaySkeleton />
  if (plan.isError) return <div className="page"><p className="error-box">{(plan.error as Error).message}</p></div>
  const p = plan.data!
  const next = p.path.find((s) => s.kind === 'learn' && s.status === 'ready') ?? p.path.find((s) => s.kind === 'learn')
  const checks = p.path.filter((s) => s.kind === 'quick check')

  return (
    <div className="page today">
      <header className="page-head">
        <h1>{me?.name}, {p.days} days to finish at {p.minutes_per_day} min a day</h1>
        <p className="muted num">{p.mastered.length} of {p.concepts_total} concepts mastered</p>
      </header>

      {next && (
        <section aria-labelledby="next-h">
          <h2 id="next-h" className="label">Next</h2>
          <div className="next-card panel">
            <div className="next-main">
              <h3>{next.name}</h3>
              <p className="muted small">{next.lessons.map(lessonLabel).join(' · ')}</p>
            </div>
            <span className="muted num small">about {minutes(next.est_minutes)}</span>
            <Link className="btn btn-primary" to={`/student/question?concept=${next.concept}`}>Start</Link>
          </div>
        </section>
      )}

      {checks.length > 0 && (
        <section aria-labelledby="checks-h">
          <div className="section-row">
            <h2 id="checks-h" className="label">Quick checks · you probably know these</h2>
            <span className="small muted num">{checks.length} · {minutes(p.quick_check_minutes)}</span>
          </div>
          <ul className="rows panel">
            {checks.slice(0, 4).map((s) => <CheckRow key={s.concept} step={s} />)}
          </ul>
          {checks.length > 4 && <Link className="small" to="/student/path">Show all {checks.length}</Link>}
        </section>
      )}

      <section aria-labelledby="weak-h">
        <h2 id="weak-h" className="label">Practise more</h2>
        <ul className="rows panel">
          {p.weakest.map((name) => {
            const step = p.path.find((s) => s.name === name)
            return (
              <li key={name} className="row">
                <span>{name}</span>
                <span className="pill pill-warn">Weakest</span>
                {step && <Link className="btn btn-ghost" to={`/student/question?concept=${step.concept}`}>Practise</Link>}
              </li>
            )
          })}
        </ul>
      </section>

      {p.message_urdulish && (
        <details className="urdulish panel">
          <summary>Your plan in UrduLish</summary>
          <p>{p.message_urdulish}</p>
        </details>
      )}
    </div>
  )
}

function CheckRow({ step }: { step: PathStep }) {
  return (
    <li className="row">
      <span>{step.name}</span>
      <span className="muted small num">{minutes(step.est_minutes)}</span>
      <Link className="btn btn-ghost" to={`/student/question?concept=${step.concept}`}>Check</Link>
    </li>
  )
}

function TodaySkeleton() {
  return (
    <div className="page today" aria-busy="true">
      <div className="skeleton" style={{ height: 30, width: '70%' }} />
      <div className="skeleton" style={{ height: 18, width: '30%', marginTop: 8 }} />
      <div className="skeleton" style={{ height: 76, marginTop: 32 }} />
      <div className="skeleton" style={{ height: 160, marginTop: 32 }} />
    </div>
  )
}
