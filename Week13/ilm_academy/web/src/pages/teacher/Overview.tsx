import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { teacherApi, type Heatmap } from '../../api'

const pct = (x: number) => `${Math.round(x * 100)}%`

export default function Overview() {
  const q = useQuery({ queryKey: ['overview'], queryFn: teacherApi.overview })
  if (q.isLoading) return <div className="page wide" aria-busy="true"><div className="skeleton" style={{ height: 520 }} /></div>
  if (q.isError) return <div className="page"><p className="error-box">{(q.error as Error).message}</p></div>
  const o = q.data!

  return (
    <div className="page wide">
      <header className="page-head">
        <h1>Class overview</h1>
        <p className="muted num">
          Week {o.week} · {o.in_class.toLocaleString()} students still enrolled of {o.enrolled.toLocaleString()}
          {' '}({o.left_before_week} left before week {o.week})
        </p>
      </header>

      <dl className="stats">
        <div className="stat">
          <dt>Active this week</dt>
          <dd className="num">{o.active_this_week}</dd>
          <span className="small muted">{pct(o.active_this_week / o.in_class)} of the class</span>
        </div>
        <div className="stat">
          <dt>At risk of dropping out</dt>
          <dd className="num"><Link to="/teacher/at-risk">{o.high} high · {o.medium} medium</Link></dd>
          <span className="small muted">top 10% and next 20% by risk</span>
        </div>
        <div className="stat">
          <dt>Concepts mastered</dt>
          <dd className="num">{o.avg_mastered} <span className="muted small">of {o.concepts_total}, on average</span></dd>
          <span className="small muted">3 right in a row and P(known) 0.95 or more</span>
        </div>
        <div className="stat">
          <dt>Review queue</dt>
          <dd className="num"><Link to="/teacher/review">{o.review_open} open</Link></dd>
          <span className="small muted">similarity, low marks, flags</span>
        </div>
      </dl>

      <section aria-labelledby="weak-h">
        <h2 id="weak-h" className="label">Weakest concepts this week</h2>
        <p className="small muted">Among concepts at least 20% of the class has practised.</p>
        <ul className="rows panel weak-list">
          {o.weakest.map((w) => (
            <li key={w.id} className="row">
              <span>{w.name}</span>
              <span className="known">
                <span className="known-bar wide-bar" aria-hidden="true"><span style={{ width: pct(w.known) }} /></span>
                <span className="small num">{pct(w.known)} likely know it</span>
              </span>
              <span className="small muted num weak-practised">{pct(w.practised)} have practised it</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="heat-h">
        <h2 id="heat-h" className="label">Mastery by section and concept</h2>
        <p className="small muted">
          Each cell: the estimated share of the section who know the concept (BKT, from their answers so far).
          Concepts in course order. {o.section_note}
        </p>
        <HeatmapGrid h={o.heatmap} />
      </section>

      <p className="small muted">Data: {o.cohort}.</p>
    </div>
  )
}

const STEPS = [0.15, 0.3, 0.45, 0.6, 0.75, 0.9]

function shade(v: number): string {
  const i = STEPS.findIndex((s) => v < s)
  const level = i === -1 ? STEPS.length : i
  return `color-mix(in srgb, var(--accent) ${8 + level * 15}%, var(--surface))`
}

function HeatmapGrid({ h }: { h: Heatmap }) {
  return (
    <div className="heat-wrap panel">
      <table className="heat">
        <thead>
          <tr>
            <th scope="col" className="heat-corner" />
            {h.concepts.map((c) => (
              <th key={c.id} scope="col" className="heat-col"><span>{c.name}</span></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {h.sections.map((s) => (
            <tr key={s.name}>
              <th scope="row" className="heat-row">{s.name}<span className="small muted num"> · {s.students}</span></th>
              {s.values.map((v, i) => (
                <td key={h.concepts[i].id} style={{ background: shade(v) }}
                    title={`${s.name} · ${h.concepts[i].name}: ${pct(v)} likely know it`}>
                  <span className="visually-hidden">{pct(v)}</span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="heat-legend small muted">
        <span>Few know it</span>
        {[0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 0.95].map((v) => <span key={v} className="heat-swatch" style={{ background: shade(v) }} />)}
        <span>Most know it</span>
      </div>
    </div>
  )
}
