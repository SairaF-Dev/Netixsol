import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { extrasApi, type Impact as ImpactData } from '../../api'

const pct = (x: number) => `${Math.round(x * 100)}%`
const pts = (x: number) => `${x > 0 ? '+' : '−'}${Math.abs(Math.round(x * 100))} pts`
const signed = (x: number, d = 1) => `${x > 0 ? '+' : '−'}${Math.abs(x).toFixed(d)}`

export default function Impact() {
  const q = useQuery({ queryKey: ['impact'], queryFn: extrasApi.impact })
  if (q.isLoading) return <div className="page wide" aria-busy="true"><div className="skeleton" style={{ height: 520 }} /></div>
  if (q.isError) return <div className="page"><p className="error-box">{(q.error as Error).message}</p></div>
  const d = q.data!
  return (
    <div className="page wide impact">
      <header className="page-head">
        <h1>Impact</h1>
        <p className="muted">What the platform changes, measured so far. Each section names the report its numbers come from.</p>
      </header>
      <Adaptive d={d} />
      <Hours d={d} />
      <Dropout d={d} />
      <Grading d={d} />
      <Safety d={d} />
      <section className="impact-block">
        <h2>Real-student A/B test</h2>
        <p className="takeaway">Not run yet. Everything above comes from simulated students or prepared submissions.</p>
        <p className="small muted">The test design (who gets the adaptive path, for how long, what is measured, and when to stop) is part of the launch plan; this page will show its results once real students have used both paths.</p>
      </section>
    </div>
  )
}

function Adaptive({ d }: { d: ImpactData }) {
  const a = d.adaptive
  const rows: { label: string; key: keyof typeof a.fixed; fmt: (x: number) => string; dfmt: (x: number) => string }[] = [
    { label: 'Gone by week 3', key: 'dropped_by_week3', fmt: pct, dfmt: pts },
    { label: 'Gone by the end', key: 'dropped_ever', fmt: pct, dfmt: pts },
    { label: 'Concepts known at the end', key: 'concepts_known', fmt: (x) => x.toFixed(1), dfmt: (x) => signed(x) },
    { label: 'Hours studied', key: 'hours', fmt: (x) => x.toFixed(1), dfmt: (x) => signed(x) },
  ]
  return (
    <section className="impact-block">
      <h2>Adaptive path vs one fixed path</h2>
      <p className="takeaway">
        {Math.abs(Math.round(a.diff.dropped_by_week3.diff * 100))} points fewer students are gone by week 3, but they end
        knowing {Math.abs(a.diff.concepts_known.diff).toFixed(1)} fewer concepts: the adaptive path goes deeper on fewer concepts.
      </p>
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th scope="col">{a.students.toLocaleString()} simulated students each</th><th scope="col" className="num">Fixed</th><th scope="col" className="num">Adaptive</th><th scope="col" className="num">Difference (95% range)</th></tr></thead>
          <tbody>
            {rows.map((r) => {
              const df = a.diff[r.key]
              return (
                <tr key={r.key}>
                  <td>{r.label}</td>
                  <td className="num">{r.fmt(a.fixed[r.key])}</td>
                  <td className="num">{r.fmt(a.adaptive[r.key])}</td>
                  <td className="num">{r.dfmt(df.diff)} <span className="muted small">({r.dfmt(df.low)} to {r.dfmt(df.high)})</span></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="small muted">{a.caveat} Source: {d.sources.adaptive}.</p>
    </section>
  )
}

function Hours({ d }: { d: ImpactData }) {
  const [subs, setSubs] = useState(3000)
  const [mins, setMins] = useState(3)
  const [human, setHuman] = useState(Math.round(d.review_share * 100))
  const saved = (subs * (1 - human / 100) * mins) / 60
  return (
    <section className="impact-block">
      <h2>Teacher time saved by auto-grading</h2>
      <p className="takeaway">About <span className="num">{Math.round(saved)}</span> teacher hours a week, with the assumptions below. Change them to match your school.</p>
      <div className="panel calc">
        <label className="field"><span className="small">Code submissions per week</span>
          <input type="number" min={0} value={subs} onChange={(e) => setSubs(Math.max(0, Number(e.target.value)))} /></label>
        <label className="field"><span className="small">Minutes a teacher spends marking one</span>
          <input type="number" min={0} step={0.5} value={mins} onChange={(e) => setMins(Math.max(0, Number(e.target.value)))} /></label>
        <label className="field"><span className="small">Share a teacher still reviews (%)</span>
          <input type="number" min={0} max={100} value={human} onChange={(e) => setHuman(Math.min(100, Math.max(0, Number(e.target.value))))} /></label>
      </div>
      <p className="small muted">
        Hours saved = submissions × (1 − share reviewed) × minutes ÷ 60. The 3,000 a week is the scenario's figure; the
        {` ${Math.round(d.review_share * 100)}%`} reviewed is the share of the 50 graded submissions with a mark under 4 (the review queue's rule).
        Minutes per submission is an assumption, not a measurement.
      </p>
    </section>
  )
}

function Dropout({ d }: { d: ImpactData }) {
  const m = d.dropout_model
  return (
    <section className="impact-block">
      <h2>Dropout early warning</h2>
      <p className="takeaway">The warning is as good as the visible data allows; a simple model with three signals does as well as the bigger one.</p>
      <dl className="stats">
        <div className="stat"><dt>LightGBM</dt><dd className="num">{m.lightgbm.toFixed(2)}</dd><span className="small muted">PR-AUC on unseen students</span></div>
        <div className="stat"><dt>Simple baseline</dt><dd className="num">{m.baseline.toFixed(2)}</dd><span className="small muted">3 signals, logistic</span></div>
        <div className="stat"><dt>Best possible from activity</dt><dd className="num">{m.ceiling_observable.toFixed(2)}</dd><span className="small muted">the simulator's own rule</span></div>
        <div className="stat"><dt>Chance</dt><dd className="num">{m.base_rate.toFixed(2)}</dd><span className="small muted">share who drop at a checkpoint</span></div>
      </dl>
      <p className="small muted">Only the simulator's hidden motivation would do better ({m.ceiling_hidden.toFixed(2)}), and no app can see that. Source: {d.sources.dropout}.</p>
    </section>
  )
}

function Grading({ d }: { d: ImpactData }) {
  const g = d.grading
  return (
    <section className="impact-block">
      <h2>Code grading</h2>
      <p className="takeaway">
        Automatic marks agree closely with careful human-style marking (kappa {g.kappa_final}), but only because the grader also
        checks the task's rules; tests alone reach {g.kappa_tests_only}.
      </p>
      <p className="small muted">Average gap {g.mae} marks out of 10; {pct(g.within_2)} within 2 marks. Reference: {g.reference}. Source: {d.sources.grading}.</p>
    </section>
  )
}

function Safety({ d }: { d: ImpactData }) {
  const first = d.tutor[0]
  const latest = d.tutor[d.tutor.length - 1]
  const p100 = d.plagiarism.by_class.find((c) => c.students === 100)
  return (
    <section className="impact-block">
      <h2>Safety</h2>
      <ul className="safety-list">
        <li><span className="num">{d.sandbox.contained} of {d.sandbox.attacks}</span> attacks on the code sandbox contained (fork bomb, memory bomb, network, secrets, grade forgery).</li>
        {first && latest && (
          <li>Tutor answers given away: <span className="num">{first.leaks} of {first.exercise_turns}</span> in the first version,
            <span className="num"> {latest.leaks} of {latest.exercise_turns}</span> in the latest (unseen exercises).</li>
        )}
        {p100 && (
          <li>Copy detection flags pairs for a teacher, never a penalty. With 100 students it would raise about
            <span className="num"> {Math.round(p100.expected_flags)}</span> flags per exercise, of which about
            <span className="num"> {p100.true}</span> real, so the teacher sees a short ranked list instead.</li>
        )}
      </ul>
      <p className="small muted">Sources: {d.sources.sandbox}; reports/tutor_eval; {d.sources.plagiarism}.</p>
    </section>
  )
}
